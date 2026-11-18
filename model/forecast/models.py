"""Три открытых алгоритма (Ridge и логистическая регрессия, Random Forest, CatBoost) и их ансамбли.

Регрессия по умолчанию учит изменение IGPA (target="delta"): прогноз = IGPA года t + предсказанное изменение,
то есть модель учится поправке к сильному наивному прогнозу B0. target="level" – прогноз уровня напрямую (контроль).
Параметры подбираются по сетке на валидационном году внутри обучающей части (protocol.inner_split).
"""

import itertools

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, CatBoostRegressor
from scipy.optimize import nnls
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import log_loss, mean_absolute_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .features import CATEGORICAL, design
from .protocol import inner_split

SEED = 20261107
_CACHE: dict = {}


def _frame_key(frame: pd.DataFrame) -> tuple:
    """Отпечаток обучающей выборки: какие строки и при каких правилах и слое (суммы IGPA различают постановки)."""
    rows = int(pd.util.hash_pandas_object(frame[["student_id", "year"]], index=False).sum())
    return len(frame), rows, round(float(frame.igpa.sum()), 6), round(float(frame.igpa_next.sum()), 6)


class _Base:
    name = "base"

    def __init__(self, target: str = "delta", use: list[str] | None = None):
        self.target, self.use = target, use

    def _features(self, features: list[str]) -> list[str]:
        return features if self.use is None else [f for f in features if f in self.use]

    def _y(self, frame: pd.DataFrame) -> np.ndarray:
        return (frame.delta if self.target == "delta" else frame.igpa_next).to_numpy(float)

    def _to_igpa(self, frame: pd.DataFrame, pred: np.ndarray) -> np.ndarray:
        return frame.igpa.to_numpy(float) + pred if self.target == "delta" else pred

    def fit(self, train: pd.DataFrame, features: list[str]):
        key = (type(self).__name__, self.target, tuple(self.use or ()), tuple(features), _frame_key(train))
        if key in _CACHE:   # стекинг и среднее переиспользуют уже обученные базы, а не обучают их заново
            self.__dict__.update(_CACHE[key].__dict__)
            return self
        self.features = self._features(features)
        fit_part, val = inner_split(train)
        self.params = self._tune(fit_part, val)
        self._fit_final(train, self.params)
        _CACHE[key] = self
        return self


class RidgeModel(_Base):
    """Ridge для изменения IGPA и логистическая регрессия для риска; признаки стандартизуются."""
    name = "Ridge"
    ALPHAS = (0.1, 1, 10, 100, 1000)
    CS = (0.003, 0.01, 0.03, 0.1, 1)

    def _X(self, frame):
        return design(frame, self.features, getattr(self, "columns", None))

    def _tune(self, fit_part, val):
        self.columns = list(design(fit_part, self.features).columns)
        Xf, Xv = self._X(fit_part), self._X(val)
        alpha = min(self.ALPHAS, key=lambda a: mean_absolute_error(
            self._y(val), make_pipeline(StandardScaler(), Ridge(alpha=a)).fit(Xf, self._y(fit_part)).predict(Xv)))
        c = min(self.CS, key=lambda c: log_loss(val.risk.astype(int), make_pipeline(
            StandardScaler(), LogisticRegression(C=c, max_iter=5000)).fit(Xf, fit_part.risk.astype(int)).predict_proba(Xv)[:, 1]))
        return {"alpha": alpha, "C": c}

    def _fit_final(self, train, p):
        self.columns = list(design(train, self.features).columns)
        X = self._X(train)
        self.reg = make_pipeline(StandardScaler(), Ridge(alpha=p["alpha"])).fit(X, self._y(train))
        self.clf = make_pipeline(StandardScaler(), LogisticRegression(C=p["C"], max_iter=5000)).fit(X, train.risk.astype(int))

    def predict(self, test):
        return self._to_igpa(test, self.reg.predict(self._X(test)))

    def risk(self, test):
        return self.clf.predict_proba(self._X(test))[:, 1]


class ForestModel(_Base):
    """Random Forest: бэггинг деревьев; сетка по минимальному размеру листа и доле признаков в узле."""
    name = "RF"
    GRID = list(itertools.product((5, 20, 50), (0.33, 0.6)))
    TREES = 500

    def _X(self, frame):
        return design(frame, self.features, getattr(self, "columns", None))

    def _forest(self, cls, leaf, share):
        return cls(n_estimators=self.TREES, min_samples_leaf=leaf, max_features=share, n_jobs=-1, random_state=SEED)

    def _tune(self, fit_part, val):
        self.columns = list(design(fit_part, self.features).columns)
        Xf, Xv = self._X(fit_part), self._X(val)
        reg = min(self.GRID, key=lambda g: mean_absolute_error(
            self._y(val), self._forest(RandomForestRegressor, *g).fit(Xf, self._y(fit_part)).predict(Xv)))
        clf = min(self.GRID, key=lambda g: log_loss(val.risk.astype(int), np.clip(
            self._forest(RandomForestClassifier, *g).fit(Xf, fit_part.risk.astype(int)).predict_proba(Xv)[:, 1],
            1e-4, 1 - 1e-4)))
        return {"reg": reg, "clf": clf}

    def _fit_final(self, train, p):
        self.columns = list(design(train, self.features).columns)
        X = self._X(train)
        self.reg = self._forest(RandomForestRegressor, *p["reg"]).fit(X, self._y(train))
        self.clf = self._forest(RandomForestClassifier, *p["clf"]).fit(X, train.risk.astype(int))

    def predict(self, test):
        return self._to_igpa(test, self.reg.predict(self._X(test)))

    def risk(self, test):
        return self.clf.predict_proba(self._X(test))[:, 1]


class CatBoostModel(_Base):
    """CatBoost: градиентный бустинг с родной обработкой категорий; сетка по глубине и L2, ранняя остановка."""
    name = "CatBoost"
    GRID = list(itertools.product((4, 6, 8), (3, 10)))

    def __init__(self, target: str = "delta", use: list[str] | None = None, shared: bool = False):
        """shared=True – параметры не подбирать, а взять у CatBoost на полном наборе признаков, обученного на тех же
        данных (серии S0–S3: сравниваются наборы признаков при одинаковых параметрах)."""
        super().__init__(target, use)
        self.shared = shared

    def fit(self, train, features):
        if not self.shared:
            return super().fit(train, features)
        full = CatBoostModel(self.target).fit(train, features)
        self.features = self._features(features)
        self.cats = [c for c in CATEGORICAL if c in self.features]
        self.params = full.params
        self._fit_final(train, self.params)
        return self
    COMMON = {"iterations": 3000, "learning_rate": 0.03, "random_seed": SEED, "verbose": False, "thread_count": -1,
              "allow_writing_files": False}

    def _X(self, frame):
        X = frame[self.features].copy()
        for c in self.cats:
            X[c] = X[c].astype(str)
        return X

    def _search(self, cls, extra, fit_part, val, y_fit, y_val, score):
        best = None
        for depth, l2 in self.GRID:
            m = cls(depth=depth, l2_leaf_reg=l2, cat_features=self.cats, **self.COMMON, **extra)
            m.fit(self._X(fit_part), y_fit, eval_set=(self._X(val), y_val), early_stopping_rounds=150)
            s = score(m)
            if best is None or s < best[0]:
                best = (s, {"depth": depth, "l2_leaf_reg": l2, "iterations": max(50, m.get_best_iteration() + 1)})
        return best[1]

    def _tune(self, fit_part, val):
        self.cats = [c for c in CATEGORICAL if c in self.features]
        Xv = self._X(val)
        reg = self._search(CatBoostRegressor, {"loss_function": "RMSE"}, fit_part, val, self._y(fit_part), self._y(val),
                           lambda m: mean_absolute_error(self._y(val), m.predict(Xv)))
        clf = self._search(CatBoostClassifier, {"loss_function": "Logloss"}, fit_part, val, fit_part.risk.astype(int),
                           val.risk.astype(int), lambda m: log_loss(val.risk.astype(int), m.predict_proba(Xv)[:, 1]))
        return {"reg": reg, "clf": clf}

    def _fit_final(self, train, p):
        common = {k: v for k, v in self.COMMON.items() if k != "iterations"}
        self.reg = CatBoostRegressor(**p["reg"], cat_features=self.cats, loss_function="RMSE", **common).fit(
            self._X(train), self._y(train))
        self.clf = CatBoostClassifier(**p["clf"], cat_features=self.cats, loss_function="Logloss", **common).fit(
            self._X(train), train.risk.astype(int))

    def predict(self, test):
        return self._to_igpa(test, self.reg.predict(self._X(test)))

    def risk(self, test):
        return self.clf.predict_proba(self._X(test))[:, 1]


BASES = (RidgeModel, ForestModel, CatBoostModel)


class StackModel(_Base):
    """Стекинг на прогнозах «вне времени»: для каждого года y обучающей части, кроме первого, базовые модели учатся
    (и подбирают параметры) только на годах до y и прогнозируют год y; по всем таким прогнозам подбираются
    неотрицательные веса (NNLS, сумма 1) для изменения IGPA и логистическая мета-модель для риска; затем базы
    переобучаются на всей обучающей части. Проверочный год в этом не участвует. Если обучающий год один
    (первая проверка), прогнозов вне времени нет – веса равные, мета-модель учится на самом этом году."""
    name = "Stack"

    def fit(self, train, features):
        self.features = self._features(features)
        years = sorted(train.year.unique())
        blocks = [(train[train.year < y], train[train.year == y]) for y in years[1:]] or [(train, train)]
        deltas, scores, targets, risks = [], [], [], []
        for past, block in blocks:
            probes = [cls(self.target, self.use).fit(past, features) for cls in BASES]
            deltas.append(np.column_stack([m.predict(block) - block.igpa.to_numpy(float) for m in probes]))
            scores.append(np.column_stack([_logit(m.risk(block)) for m in probes]))
            targets.append(block.delta.to_numpy(float))
            risks.append(block.risk.astype(int).to_numpy())
        P, S = np.vstack(deltas), np.vstack(scores)
        w, _ = nnls(P, np.concatenate(targets)) if len(years) > 1 else (np.ones(len(BASES)), None)
        self.weights = w / w.sum() if w.sum() > 0 else np.full(len(BASES), 1 / len(BASES))
        self.meta = LogisticRegression(max_iter=5000).fit(S, np.concatenate(risks))
        self.models = [cls(self.target, self.use).fit(train, features) for cls in BASES]
        return self

    def predict(self, test):
        deltas = np.column_stack([m.predict(test) - test.igpa.to_numpy(float) for m in self.models])
        return test.igpa.to_numpy(float) + deltas @ self.weights

    def risk(self, test):
        return self.meta.predict_proba(np.column_stack([_logit(m.risk(test)) for m in self.models]))[:, 1]


class MeanModel(_Base):
    """Простое среднее трёх моделей: прогнозов IGPA и вероятностей риска."""
    name = "Mean"

    def fit(self, train, features):
        self.models = [cls(self.target, self.use).fit(train, features) for cls in BASES]
        return self

    def predict(self, test):
        return np.mean([m.predict(test) for m in self.models], axis=0)

    def risk(self, test):
        return np.mean([m.risk(test) for m in self.models], axis=0)


def _logit(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))
