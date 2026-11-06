"""Рекомендации «что если»: точный прирост IGPA по формуле и реалистичность по истории похожих студентов.

Портфель года t – записи студента за год t (достижения считаются за учебный год, в следующем году портфель
собирается заново; «повторишь то же и добавишь X»). Прирост действия считает калькулятор igpa с учётом предела
пяти лучших записей и правил. Реалистичность – доля похожих студентов (ближайшие соседи по профилю года t
в обучающих годах), получивших в следующем году такое же достижение того же или более высокого уровня.
"""

from collections import defaultdict

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from igpa import CATEGORIES, CATEGORY_BY_CODE, STATUS_BY_CODE, Block, Record, calculate, igpa_parts, statuses

GPA_STEPS = (0.1, 0.2)
NEIGHBOURS = 50
SMOOTHING = 5.0
PROFILE = ["gpa", "gpa_trend", "n_research", "n_one_time", "n_permanent", "year_of_study", "master"]
LEVEL = {s.code: i for b in (Block.RESEARCH, Block.ONE_TIME) for i, s in enumerate(statuses(b))}
LEVEL["SSCI_PERMANENT"] = 0


def actions() -> list[tuple]:
    """Все действия: достижение (тип, уровень своей карты) и рост GPA на шаг."""
    out = [("record", c.code, s.code) for c in CATEGORIES for s in statuses(c.block)]
    return out + [("gpa", None, step) for step in GPA_STEPS]


class Portfolio:
    """Записи студентов по (студент, год) и быстрый пересчёт iROS и SSCI с кэшем по набору записей."""

    def __init__(self, records: pd.DataFrame, rules):
        self.rules = rules
        self.by_key = defaultdict(list)
        for sid, year, cat, st in zip(records.student_id, records.year, records.category, records.status):
            self.by_key[(sid, year)].append((cat, st))
        self._cache = {}

    def components(self, items) -> tuple[float, float]:
        key = tuple(sorted(items))
        if key not in self._cache:
            r = calculate([Record(c, s) for c, s in key], 0.0, self.rules)
            self._cache[key] = (r.iros, r.ssci)
        return self._cache[key]

    def igpa(self, gpa: float, items) -> float:
        return sum(igpa_parts(min(4.0, gpa), *self.components(items), self.rules))

    def gain(self, gpa: float, items, action) -> float:
        kind, code, value = action
        base = self.igpa(gpa, items)
        if kind == "gpa":
            return self.igpa(gpa + value, items) - base
        return self.igpa(gpa, list(items) + [(code, value)]) - base


class Feasibility:
    """Реалистичность действия по ближайшим соседям из обучающих лет, сглаженная к доле по всем обучающим студентам."""

    def __init__(self, train: pd.DataFrame, portfolio: Portfolio):
        self.scaler = StandardScaler().fit(train[PROFILE].fillna(0))
        self.nn = NearestNeighbors(n_neighbors=NEIGHBOURS).fit(self.scaler.transform(train[PROFILE].fillna(0)))
        self.train = train.reset_index(drop=True)
        acts = actions()
        hit = np.zeros((len(train), len(acts)), dtype=bool)
        for i, row in enumerate(self.train.itertuples()):
            nxt = portfolio.by_key.get((row.student_id, row.year + 1), [])
            best = {}
            for cat, st in nxt:
                best[cat] = max(best.get(cat, -1), LEVEL.get(st, 0))
            for j, (kind, code, value) in enumerate(acts):
                if kind == "gpa":
                    hit[i, j] = (row.gpa_next - row.gpa) >= value
                elif code in best and STATUS_BY_CODE[value].family is CATEGORY_BY_CODE[code].block:
                    hit[i, j] = best[code] >= LEVEL[value]
        self.hit = hit
        self.prior = hit.mean(axis=0)
        self.delta = self.train.igpa_next.to_numpy() - self.train.igpa.to_numpy()

    def __call__(self, frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        """Реалистичность (студенты × действия) и индексы соседей."""
        idx = self.nn.kneighbors(self.scaler.transform(frame[PROFILE].fillna(0)), return_distance=False)
        counts = self.hit[idx].sum(axis=1)
        return (counts + SMOOTHING * self.prior) / (NEIGHBOURS + SMOOTHING), idx

    def evidence(self, idx: np.ndarray, j: int) -> tuple[float, float]:
        """Среднее изменение IGPA соседей, сделавших и не сделавших действие j."""
        did = self.hit[idx, j]
        d = self.delta[idx]
        return (float(d[did].mean()) if did.any() else np.nan, float(d[~did].mean()) if (~did).any() else np.nan)


def recommend(frame: pd.DataFrame, portfolio: Portfolio, feasibility: Feasibility, top: int = 3) -> pd.DataFrame:
    """Топ действий на студента: прирост по формуле, реалистичность, ожидаемый прирост, свидетельство соседей."""
    acts = actions()
    feas, idx = feasibility(frame)
    rows = []
    for i, row in enumerate(frame.itertuples()):
        items = portfolio.by_key.get((row.student_id, row.year), [])
        gains = np.array([portfolio.gain(row.gpa, items, a) for a in acts])
        expected = gains * feas[i]
        order = [j for j in np.argsort(-expected) if gains[j] > 1e-9][:top]
        for rank, j in enumerate(order, start=1):
            did, didnt = feasibility.evidence(idx[i], j)
            kind, code, value = acts[j]
            rows.append({"student_id": row.student_id, "year": row.year, "rank": rank, "kind": kind,
                         "category": code, "status": value if kind == "record" else None,
                         "gpa_step": value if kind == "gpa" else None, "gain": gains[j], "feasibility": feas[i, j],
                         "expected": expected[j], "igpa_now": portfolio.igpa(row.gpa, items),
                         "neighbours_did": did, "neighbours_didnt": didnt})
    return pd.DataFrame(rows)


def follow(frame: pd.DataFrame, portfolio: Portfolio, feasibility: Feasibility, seed: int = 0) -> pd.DataFrame:
    """Проверка на стенде: студент следует одной рекомендации; реальный прирост IGPA на фактическом портфеле года t+1.

    Стратегии: наша (максимум ожидаемого прироста), только по приросту формулы, самое частое достижение
    (участие в научном мероприятии уровня ОВПО), случайное действие.
    """
    acts = actions()
    feas, _ = feasibility(frame)
    common = acts.index(("record", "IROS_EVENT", "IROS_OVPO"))
    rng = np.random.default_rng(seed)
    rows = []
    for i, row in enumerate(frame.itertuples()):
        now = portfolio.by_key.get((row.student_id, row.year), [])
        nxt = portfolio.by_key.get((row.student_id, row.year + 1), [])
        claimed = np.array([portfolio.gain(row.gpa, now, a) for a in acts])
        realized = np.array([portfolio.gain(row.gpa_next, nxt, a) for a in acts])
        picks = {"Наша: прирост × реалистичность": int(np.argmax(claimed * feas[i])),
                 "Только прирост по формуле": int(np.argmax(claimed)),
                 "Самое частое достижение": common,
                 "Случайное действие": int(rng.integers(len(acts)))}
        for strategy, j in picks.items():
            rows.append({"student_id": row.student_id, "strategy": strategy, "action": j,
                         "claimed": claimed[j], "realized": realized[j], "feasibility": feas[i, j],
                         "expected_realized": realized[j] * feas[i, j]})
    return pd.DataFrame(rows)


def feasibility_quality(frame: pd.DataFrame, portfolio: Portfolio, feasibility: Feasibility) -> dict:
    """Насколько реалистичность предсказывает, что студент действительно получит достижение (ROC-AUC по всем парам)."""
    from sklearn.metrics import roc_auc_score
    acts = actions()
    feas, _ = feasibility(frame)
    y = np.zeros_like(feas, dtype=bool)
    for i, row in enumerate(frame.itertuples()):
        best = {}
        for cat, st in portfolio.by_key.get((row.student_id, row.year + 1), []):
            best[cat] = max(best.get(cat, -1), LEVEL.get(st, 0))
        for j, (kind, code, value) in enumerate(acts):
            y[i, j] = ((row.gpa_next - row.gpa) >= value) if kind == "gpa" else (code in best and best[code] >= LEVEL[value])
    records = [j for j, a in enumerate(acts) if a[0] == "record"]
    return {"auc_records": roc_auc_score(y[:, records].ravel(), feas[:, records].ravel()),
            "mean_feasibility": float(feas[:, records].mean()), "observed_rate": float(y[:, records].mean())}
