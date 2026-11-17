"""Базовые уровни: B0 «IGPA не изменится» и B1 «только GPA».

Дополнительные простые модели (по рецензии, 17.11.2026): B2 – линейная по последнему IGPA, его тренду и курсу;
Huber и Elastic Net на всех признаках; Cohort – среднее изменение по уровню и курсу; KNN – среднее изменение
у 50 похожих студентов; Comp – простая формульная модель компонентов: меняется только GPA (линейная модель),
достижения сохраняются, IGPA пересчитывается с весом 0,5. Регрессии учат изменение IGPA, как и основные модели.
"""

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.linear_model import ElasticNet, HuberRegressor, LinearRegression, LogisticRegression
from sklearn.metrics import mean_absolute_error
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .features import design
from .protocol import inner_split


class B0:
    """Наивный прогноз: IGPA года t+1 равен IGPA года t. Риска не ранжирует."""
    name = "B0"

    def fit(self, train: pd.DataFrame, features: list[str]) -> "B0":
        return self

    def predict(self, test: pd.DataFrame) -> np.ndarray:
        return test.igpa.to_numpy(float)

    def risk(self, test: pd.DataFrame) -> np.ndarray | None:
        return None


class B1:
    """Только GPA года: линейная регрессия IGPA t+1 и логистическая регрессия риска снижения."""
    name = "B1"

    def fit(self, train: pd.DataFrame, features: list[str]) -> "B1":
        X = train[["gpa"]].to_numpy(float)
        self.reg = LinearRegression().fit(X, train.igpa_next)
        self.clf = LogisticRegression().fit(X, train.risk.astype(int))
        return self

    def predict(self, test: pd.DataFrame) -> np.ndarray:
        return self.reg.predict(test[["gpa"]].to_numpy(float))

    def risk(self, test: pd.DataFrame) -> np.ndarray:
        return self.clf.predict_proba(test[["gpa"]].to_numpy(float))[:, 1]


def _fill(frame: pd.DataFrame, cols: list[str]) -> np.ndarray:
    """Лаги и тренды без истории – нулём (флаг has_history в признаках сложных моделей; здесь не нужен)."""
    return frame[cols].astype(float).fillna(0.0).to_numpy()


class B2:
    """Линейная модель по последнему IGPA, его тренду и курсу (+ магистратура): изменение IGPA и риск."""
    name = "B2"
    COLS = ["igpa", "igpa_trend", "year_of_study", "master"]

    def fit(self, train, features):
        X = _fill(train, self.COLS)
        self.reg = LinearRegression().fit(X, train.delta)
        self.clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(X, train.risk.astype(int))
        return self

    def predict(self, test):
        return test.igpa.to_numpy(float) + self.reg.predict(_fill(test, self.COLS))

    def risk(self, test):
        return self.clf.predict_proba(_fill(test, self.COLS))[:, 1]


class _Linear:
    """Общая часть Huber и Elastic Net: все признаки, стандартизация, параметр по валидационному году."""
    GRID: tuple = ()

    def _make(self, p):
        raise NotImplementedError

    def fit(self, train, features):
        self.features = features
        self.cols = design(train, features).columns
        fit_part, val = inner_split(train)
        Xf, Xv = design(fit_part, features, self.cols), design(val, features, self.cols)
        self.param = min(self.GRID, key=lambda p: mean_absolute_error(
            val.delta, make_pipeline(StandardScaler(), self._make(p)).fit(Xf, fit_part.delta).predict(Xv)))
        X = design(train, features, self.cols)
        self.reg = make_pipeline(StandardScaler(), self._make(self.param)).fit(X, train.delta)
        self.clf = make_pipeline(StandardScaler(), LogisticRegression(
            penalty="elasticnet", solver="saga", l1_ratio=0.5, C=0.1, max_iter=3000)).fit(X, train.risk.astype(int))
        return self

    def predict(self, test):
        return test.igpa.to_numpy(float) + self.reg.predict(design(test, self.features, self.cols))

    def risk(self, test):
        return self.clf.predict_proba(design(test, self.features, self.cols))[:, 1]


class Huber(_Linear):
    """Регрессия Хьюбера: устойчива к выбросам изменения IGPA."""
    name = "Huber"
    GRID = (1.1, 1.35, 1.75, 2.5)

    def _make(self, p):
        return HuberRegressor(epsilon=p, alpha=1e-3, max_iter=2000)


class ENet(_Linear):
    """Elastic Net (l1_ratio = 0,5)."""
    name = "ENet"
    GRID = (1e-4, 1e-3, 3e-3, 1e-2, 3e-2)

    def _make(self, p):
        return ElasticNet(alpha=p, l1_ratio=0.5, max_iter=20000)


class Cohort:
    """Когортный дрейф: среднее изменение IGPA и доля снижений по уровню и курсу в обучающих данных."""
    name = "Cohort"
    KEY = ["level", "year_of_study"]

    def fit(self, train, features):
        g = train.groupby(self.KEY)
        self.delta, self.share = g.delta.mean(), g.risk.mean()
        self.delta0, self.share0 = train.delta.mean(), train.risk.mean()
        return self

    def _lookup(self, test, table, default):
        idx = pd.MultiIndex.from_frame(test[self.KEY])
        return table.reindex(idx).fillna(default).to_numpy(float)

    def predict(self, test):
        return test.igpa.to_numpy(float) + self._lookup(test, self.delta, self.delta0)

    def risk(self, test):
        return self._lookup(test, self.share, self.share0)


class KNN:
    """Похожие студенты: среднее изменение IGPA и доля снижений у 50 ближайших по IGPA, GPA, трендам и курсу."""
    name = "KNN"
    COLS = ["igpa", "gpa", "gpa_trend", "igpa_trend", "year_of_study", "master"]
    K = 50

    def fit(self, train, features):
        self.scaler = StandardScaler().fit(_fill(train, self.COLS))
        self.nn = NearestNeighbors(n_neighbors=self.K).fit(self.scaler.transform(_fill(train, self.COLS)))
        self.delta, self.dec = train.delta.to_numpy(float), train.risk.to_numpy(float)
        return self

    def _idx(self, test):
        return self.nn.kneighbors(self.scaler.transform(_fill(test, self.COLS)), return_distance=False)

    def predict(self, test):
        return test.igpa.to_numpy(float) + self.delta[self._idx(test)].mean(axis=1)

    def risk(self, test):
        return self.dec[self._idx(test)].mean(axis=1)


class Comp:
    """Простая формульная модель компонентов: прогноз изменения GPA линейной моделью по оценкам, iROS и SSCI
    без изменений, IGPA = текущий IGPA + 0,5 · ΔGPA; риск – из нормального приближения остатков."""
    name = "Comp"
    COLS = ["gpa", "gpa_trend", "gpa_cum", "sem_trend", "fx_count", "min_score", "failed_credits", "year_of_study"]

    def fit(self, train, features):
        X = _fill(train, self.COLS)
        dg = (train.gpa_next - train.gpa).to_numpy(float)
        self.reg = LinearRegression().fit(X, dg)
        self.sigma = float(np.std(train.delta.to_numpy(float) - 0.5 * self.reg.predict(X)))
        return self

    def _delta(self, test):
        return 0.5 * self.reg.predict(_fill(test, self.COLS))

    def predict(self, test):
        return test.igpa.to_numpy(float) + self._delta(test)

    def risk(self, test):
        return norm.cdf((-0.1 - self._delta(test)) / self.sigma)
