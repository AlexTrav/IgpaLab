from pathlib import Path

import numpy as np
import pytest

from forecast import baselines as B
from forecast import review as R
from forecast.features import build, load, transitions

DATA = Path("/repo/data/synthetic/v1")


def test_calibration_of_calibrated_and_overconfident_scores():
    rng = np.random.default_rng(0)
    p = rng.uniform(0.02, 0.6, 20000)
    y = rng.random(20000) < p
    good = R.calibration(y, p)
    assert abs(good["cal_intercept"]) < 0.05 and abs(good["cal_slope"] - 1) < 0.08
    sharp = 1 / (1 + np.exp(-2 * np.log(p / (1 - p))))   # слишком уверенные вероятности – наклон меньше 1
    assert R.calibration(y, sharp)["cal_slope"] < 0.7
    assert R.ece(y, p) < 0.02


def test_risk_metrics_confusion_matrix():
    y = np.array([1, 1, 0, 0, 0, 1, 0, 0])
    s = np.array([0.9, 0.2, 0.8, 0.1, 0.1, 0.7, 0.3, 0.2])
    m = R.risk_metrics(y, s, 0.5)
    assert (m["tp"], m["fp"], m["fn"], m["tn"]) == (2, 1, 1, 4)
    assert m["precision"] == pytest.approx(2 / 3) and m["recall"] == pytest.approx(2 / 3)
    assert m["specificity"] == pytest.approx(0.8) and m["alert_rate"] == pytest.approx(3 / 8)


def test_conformal_covers_nominal_share():
    rng = np.random.default_rng(1)
    lo, hi = R.conformal(rng.normal(0, 1, 2000))
    test = rng.normal(0, 1, 20000)
    assert 0.78 < ((test >= lo) & (test <= hi)).mean() < 0.83


def test_paired_difference_sign():
    y = np.zeros(500)
    good, bad = np.full(500, 0.1), np.full(500, 0.3)
    r = R.paired(y, good, bad)
    assert r["diff"] == pytest.approx(-0.2) and r["diff_hi"] < 0


@pytest.mark.parametrize("cls", [B.B2, B.Huber, B.ENet, B.Cohort, B.KNN, B.Comp])
def test_extra_baselines_contract(cls):
    if not DATA.exists():
        pytest.skip("нет версии датасета v1: make -C data generate")
    panel, features = build(load(DATA), "default", "obs")
    data = transitions(panel)
    train = data[data.year < 2024].sample(1500, random_state=0)
    test = data[data.year == 2024].sample(300, random_state=0)
    m = cls().fit(train, features)
    pred, risk = m.predict(test), m.risk(test)
    assert pred.shape == (len(test),) and np.isfinite(pred).all()
    assert risk.shape == (len(test),) and ((risk >= 0) & (risk <= 1)).all()
    # простые модели не должны быть хуже наивного прогноза больше чем на 20%
    assert np.abs(test.igpa_next - pred).mean() < 1.2 * np.abs(test.igpa_next - test.igpa).mean()
