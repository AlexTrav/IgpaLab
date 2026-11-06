from pathlib import Path

import numpy as np
import pytest

from forecast import models as M
from forecast.features import build, group_features, load, transitions

DATA = Path("/repo/data/synthetic/v1")


@pytest.fixture(scope="module")
def split():
    if not DATA.exists():
        pytest.skip("нет версии датасета v1: make -C data generate")
    panel, features = build(load(DATA), "default", "obs")
    data = transitions(panel)
    train = data[data.year < 2024].sample(1500, random_state=0)
    test = data[data.year == 2024].sample(300, random_state=0)
    return train, test, features


@pytest.fixture(autouse=True)
def small(monkeypatch):
    """Уменьшенные сетки: тест проверяет устройство моделей, а не качество."""
    monkeypatch.setattr(M.CatBoostModel, "GRID", [(4, 3)])
    monkeypatch.setattr(M.CatBoostModel, "COMMON", {**M.CatBoostModel.COMMON, "iterations": 200})
    monkeypatch.setattr(M.ForestModel, "GRID", [(20, 0.33)])
    monkeypatch.setattr(M.ForestModel, "TREES", 50)
    M._CACHE.clear()


@pytest.mark.parametrize("cls", [M.RidgeModel, M.ForestModel, M.CatBoostModel, M.StackModel, M.MeanModel])
def test_model_contract(split, cls):
    train, test, features = split
    model = cls().fit(train, features)
    pred, risk = model.predict(test), model.risk(test)
    assert pred.shape == (len(test),) and np.isfinite(pred).all()
    assert risk.shape == (len(test),) and ((risk >= 0) & (risk <= 1)).all()
    assert np.abs(pred - test.igpa_next).mean() < 0.5


def test_stack_weights(split):
    train, test, features = split
    stack = M.StackModel().fit(train, features)
    assert stack.weights.min() >= 0 and stack.weights.sum() == pytest.approx(1)


def test_level_target_and_feature_subset(split):
    train, test, features = split
    level = M.CatBoostModel(target="level").fit(train, features)
    assert np.isfinite(level.predict(test)).all()
    s0 = M.CatBoostModel(use=group_features("grades", "context")).fit(train, features)
    assert set(s0.features) == set(group_features("grades", "context"))


def test_cache_reuses_fitted_base(split):
    train, _, features = split
    first = M.CatBoostModel().fit(train, features)
    second = M.CatBoostModel().fit(train, features)
    assert second.reg is first.reg


def test_shared_params_for_series(split):
    train, _, features = split
    full = M.CatBoostModel().fit(train, features)
    s0 = M.CatBoostModel(use=group_features("grades", "context"), shared=True).fit(train, features)
    assert s0.params == full.params
    assert set(s0.features) == set(group_features("grades", "context"))
