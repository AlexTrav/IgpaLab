"""Базовые уровни: B0 «IGPA не изменится» и B1 «только GPA»."""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression


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
