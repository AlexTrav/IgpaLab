"""Протокол проверки: расширяющееся окно по времени, метрики, бутстреп по студентам, Уилкоксон с поправкой Холма."""

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import average_precision_score, f1_score, mean_absolute_error, r2_score, roc_auc_score

TEST_YEARS = (2022, 2023, 2024)   # год t проверочных переходов t → t+1; 2024 – основная (последняя) проверка
FINAL = TEST_YEARS[-1]


def folds(frame: pd.DataFrame, test_years=TEST_YEARS, disjoint: bool = False):
    """Обучение на переходах из лет < y, проверка на переходах из года y.

    Переход (y−1 → y) в обучении законен: к моменту прогноза итоги года y уже известны.
    disjoint=True – контрольный вариант: студенты проверки не попадают в обучение совсем.
    """
    for year in test_years:
        train, test = frame[frame.year < year], frame[frame.year == year]
        if disjoint:
            train = train[~train.student_id.isin(test.student_id)]
        yield year, train, test


def inner_split(train: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Валидация для подбора параметров: последний год обучающей части.

    В первой проверке обучающий год один – тогда валидация совпадает с обучением (порог по обучающим данным).
    """
    last = train.year.max()
    if train.year.nunique() == 1:
        return train, train
    return train[train.year < last], train[train.year == last]


def regression(y, pred) -> dict:
    y, pred = np.asarray(y, float), np.asarray(pred, float)
    return {"mae": mean_absolute_error(y, pred), "rmse": float(np.sqrt(np.mean((y - pred) ** 2))),
            "r2": r2_score(y, pred)}


def best_threshold(y, score) -> float:
    """Порог, максимизирующий F1 (выбирается на валидации, не на проверке)."""
    candidates = np.unique(np.quantile(score, np.linspace(0.02, 0.98, 97)))
    f1 = [f1_score(y, score >= t, zero_division=0) for t in candidates]
    return float(candidates[int(np.argmax(f1))])


def recall_threshold(y, score, recall: float = 0.8) -> float:
    """Наибольший порог, при котором на валидации выявляется не меньше доли recall будущих снижений."""
    y, score = np.asarray(y, int), np.asarray(score, float)
    if y.sum() == 0:
        return float(np.max(score))
    return float(np.quantile(score[y == 1], 1 - recall, method="lower"))


def classification(y, score, threshold: float) -> dict:
    y, score = np.asarray(y, int), np.asarray(score, float)
    return {"roc_auc": roc_auc_score(y, score), "pr_auc": average_precision_score(y, score),
            "f1": f1_score(y, score >= threshold, zero_division=0), "prevalence": float(y.mean()),
            "threshold": threshold}


def bootstrap(values: np.ndarray, fn, n: int = 1000, seed: int = 0) -> tuple[float, float]:
    """95% ДИ: строки проверки – разные студенты (один переход на студента в году), поэтому ресэмплинг строк = студентов."""
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(values), (n, len(values)))
    stats_ = np.array([fn(i) for i in idx])
    return float(np.nanquantile(stats_, 0.025)), float(np.nanquantile(stats_, 0.975))


def mae_ci(y, pred, n=1000, seed=0):
    err = np.abs(np.asarray(y, float) - np.asarray(pred, float))
    return bootstrap(err, lambda i: err[i].mean(), n, seed)


def diff_ci(y, pred_a, pred_b, n=1000, seed=0):
    """ДИ разности MAE (a − b): отрицательная граница выше нуля значит, что a хуже."""
    y = np.asarray(y, float)
    d = np.abs(y - np.asarray(pred_a, float)) - np.abs(y - np.asarray(pred_b, float))
    return bootstrap(d, lambda i: d[i].mean(), n, seed)


def auc_ci(y, score, n=1000, seed=0):
    y, score = np.asarray(y, int), np.asarray(score, float)

    def auc(i):
        yi = y[i]
        return roc_auc_score(yi, score[i]) if 0 < yi.sum() < len(yi) else np.nan
    lo, hi = bootstrap(np.arange(len(y)), auc, n, seed)
    return lo, hi


def wilcoxon(y, pred_a, pred_b) -> float:
    """Парный критерий Уилкоксона по абсолютным ошибкам двух моделей."""
    y = np.asarray(y, float)
    a, b = np.abs(y - np.asarray(pred_a, float)), np.abs(y - np.asarray(pred_b, float))
    if np.allclose(a, b):
        return 1.0
    return float(stats.wilcoxon(a, b).pvalue)


def holm(pvalues: dict[str, float]) -> dict[str, float]:
    """Поправка Холма на множественные сравнения."""
    items = sorted(pvalues.items(), key=lambda kv: kv[1])
    m, running, out = len(items), 0.0, {}
    for i, (name, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[name] = running
    return out
