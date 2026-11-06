"""Своя модель IGPA-Hybrid: прогноз по компонентам и точный пересчёт по формуле Положения.

Компоненты не зависят от правил расчёта:
- GPA следующего года – CatBoost на изменение GPA (подбор параметров как у CatBoostModel);
- число записей следующего года по каждому из 16 типов – CatBoost с пуассоновской функцией потерь;
- уровни записей – распределение по истории студента в этом типе, сглаженное к распределению по вузу.
Сборка: SAMPLES розыгрышей записей и GPA (с ошибкой GPA из валидации), IGPA каждого розыгрыша считает калькулятор
igpa по нужным правилам; прогноз – среднее, риск – доля розыгрышей со снижением на 0,1 и больше.
Смена правил не требует переобучения: меняется только калькулятор.
"""

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor

from igpa import CATEGORIES, Record, calculate, igpa_parts, load_rules

from .features import CATEGORICAL, _asu_on_year_end
from .models import SEED, CatBoostModel
from .protocol import inner_split

CODES = [c.code for c in CATEGORIES]
RULE_DEPENDENT = {"iros", "ssci", "igpa", "iros_prev", "ssci_prev", "igpa_prev", "igpa_trend"}
SAMPLES = 200
PRIOR = 3.0          # сила сглаживания распределения уровней студента к распределению по вузу
POISSON = {"depth": 6, "learning_rate": 0.05, "iterations": 2000, "l2_leaf_reg": 3, "random_seed": SEED,
           "verbose": False, "thread_count": -1, "allow_writing_files": False, "loss_function": "Poisson"}

_RECORDS: dict[str, pd.DataFrame] = {}
_COMPONENTS: dict = {}


def prepare(d: dict):
    """Записи по слоям: истина – все достижения; АСУ – согласованные к концу учебного года (статус как внесён)."""
    asu = _asu_on_year_end(d)
    _RECORDS["true"] = d["records_true"][["student_id", "year", "category", "status"]]
    _RECORDS["obs"] = asu[asu.state == "Подтверждено"][["student_id", "year", "category", "status"]]


def _counts(layer: str) -> pd.DataFrame:
    return (_RECORDS[layer].pivot_table(index=["student_id", "year"], columns="category", values="status",
                                        aggfunc="count", fill_value=0)
            .reindex(columns=CODES, fill_value=0).add_prefix("cnt_"))


class _Components:
    """Модели компонент для одного слоя и одной обучающей выборки; от правил не зависят."""

    def __init__(self, layer: str, train: pd.DataFrame, features: list[str]):
        self.layer = layer
        counts = _counts(layer)
        self.cnt_cols = list(counts.columns)
        self.features = [f for f in features if f not in RULE_DEPENDENT and not f.startswith("pts_")] + self.cnt_cols
        self.cats = [c for c in CATEGORICAL if c in self.features]
        train = self.attach(train)
        fit_part, val = inner_split(train)

        # GPA: изменение GPA, параметры подбираются как у CatBoostModel
        gpa = CatBoostModel(use=self.features)
        gpa._y = lambda f: (f.gpa_next - f.gpa).to_numpy(float)
        gpa.cats, gpa.features = self.cats, self.features
        params = gpa._search(CatBoostRegressor, {"loss_function": "RMSE"}, fit_part, val, gpa._y(fit_part),
                             gpa._y(val), lambda m: np.abs(gpa._y(val) - m.predict(gpa._X(val))).mean())
        probe = CatBoostRegressor(**params, cat_features=self.cats, loss_function="RMSE",
                                  **{k: v for k, v in CatBoostModel.COMMON.items() if k != "iterations"})
        probe.fit(gpa._X(fit_part), gpa._y(fit_part))
        self.gpa_residuals = gpa._y(val) - probe.predict(gpa._X(val))
        self.gpa = CatBoostRegressor(**params, cat_features=self.cats, loss_function="RMSE",
                                     **{k: v for k, v in CatBoostModel.COMMON.items() if k != "iterations"})
        self.gpa.fit(gpa._X(train), gpa._y(train))
        self._X = gpa._X

        # число записей следующего года по каждому типу
        nxt = self.next_counts(train)
        nxt_fit, nxt_val = self.next_counts(fit_part), self.next_counts(val)
        self.rates = {}
        for code in CODES:
            col = f"cnt_{code}"
            if nxt[col].sum() == 0:
                self.rates[code] = None
                continue
            m = CatBoostRegressor(**POISSON, cat_features=self.cats)
            m.fit(self._X(fit_part), nxt_fit[col], eval_set=(self._X(val), nxt_val[col]), early_stopping_rounds=100)
            final = CatBoostRegressor(**{**POISSON, "iterations": max(50, m.get_best_iteration() + 1)},
                                      cat_features=self.cats)
            self.rates[code] = final.fit(self._X(train), nxt[col])

        # распределение уровней по вузу в каждом типе – по записям, известным обучающей выборке (до года t+1 её целей)
        recs = _RECORDS[layer]
        history = recs[recs.year <= int(train.year.max()) + 1]
        self.global_levels = {code: g.status.value_counts(normalize=True) for code, g in history.groupby("category")}

    def attach(self, frame: pd.DataFrame) -> pd.DataFrame:
        counts = _counts(self.layer)
        out = frame.drop(columns=[c for c in self.cnt_cols if c in frame], errors="ignore")
        out = out.join(counts, on=["student_id", "year"])
        out[self.cnt_cols] = out[self.cnt_cols].fillna(0)
        return out

    def next_counts(self, frame: pd.DataFrame) -> pd.DataFrame:
        counts = _counts(self.layer)
        keys = pd.MultiIndex.from_arrays([frame.student_id, frame.year + 1])
        return counts.reindex(keys, fill_value=0).reset_index(drop=True)

    def levels(self, frame: pd.DataFrame) -> dict:
        """Распределение уровней студента по типам: его записи до года t включительно, сглаженные к вузу."""
        recs = _RECORDS[self.layer]
        mine = recs[recs.student_id.isin(frame.student_id)]
        out = {}
        for (sid, code), g in mine.groupby(["student_id", "category"]):
            out[(sid, code)] = g[["year", "status"]]
        return out


class HybridModel:
    """IGPA-Hybrid: компоненты + розыгрыши + калькулятор igpa по правилам постановки."""
    name = "Hybrid"

    def __init__(self, samples: int = SAMPLES, rules: str | None = None):
        self.samples, self.rules_override = samples, rules

    def fit(self, train: pd.DataFrame, features: list[str]):
        self.layer, self.rules_name = train._layer.iloc[0], train._rules.iloc[0]
        key = (self.layer, tuple(features), len(train),
               int(pd.util.hash_pandas_object(train[["student_id", "year"]], index=False).sum()))
        if key not in _COMPONENTS:   # компоненты общие для обоих правил: обучаются один раз на слой и выборку
            _COMPONENTS[key] = _Components(self.layer, train, features)
        self.c = _COMPONENTS[key]
        self.rules = load_rules(self.rules_override or self.rules_name)
        self._cache = {}
        return self

    def _simulate(self, test: pd.DataFrame) -> np.ndarray:
        """Матрица IGPA: строки – студенты, столбцы – розыгрыши."""
        if getattr(self, "_last", None) is not None and self._last[0] is test:
            return self._last[1]
        c = self.c
        frame = c.attach(test)
        X = c._X(frame)
        rng = np.random.default_rng(SEED)
        gpa_mean = frame.gpa.to_numpy(float) + c.gpa.predict(X)
        gpa = np.clip(gpa_mean[:, None] + rng.choice(c.gpa_residuals, (len(frame), self.samples)), 0, 4)
        rates = np.column_stack([np.zeros(len(frame)) if c.rates[code] is None
                                 else c.rates[code].predict(X, prediction_type="Exponent") for code in CODES])
        counts = rng.poisson(rates[:, :, None], (len(frame), len(CODES), self.samples))
        history = c.levels(frame)
        igpa = np.empty((len(frame), self.samples))
        for i, (sid, year) in enumerate(zip(frame.student_id, frame.year)):
            per_code = []
            for j, code in enumerate(CODES):
                n = counts[i, j]
                if n.max() == 0:
                    per_code.append(None)
                    continue
                prior = c.global_levels.get(code)
                own = history.get((sid, code))
                own = own[own.year <= year].status.value_counts() if own is not None else pd.Series(dtype=float)
                probs = (prior * PRIOR).add(own, fill_value=0)
                probs = probs / probs.sum()
                draws = rng.choice(probs.index.to_numpy(), (self.samples, n.max()), p=probs.to_numpy())
                per_code.append((n, draws))
            for s in range(self.samples):
                key = tuple(sorted((CODES[j], st) for j, item in enumerate(per_code) if item is not None
                                   for st in item[1][s, :item[0][s]]))
                iros_ssci = self._cache.get(key)
                if iros_ssci is None:
                    r = calculate([Record(cat, st) for cat, st in key], 0.0, self.rules)
                    iros_ssci = self._cache[key] = (r.iros, r.ssci)
                igpa[i, s] = sum(igpa_parts(gpa[i, s], *iros_ssci, self.rules))
        self._last = (test, igpa)
        return igpa

    def predict(self, test: pd.DataFrame) -> np.ndarray:
        return self._simulate(test).mean(axis=1)

    def risk(self, test: pd.DataFrame) -> np.ndarray:
        igpa = self._simulate(test)
        return (igpa <= test.igpa.to_numpy(float)[:, None] - 0.1).mean(axis=1)
