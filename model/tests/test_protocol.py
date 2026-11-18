from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from forecast import protocol as P
from forecast.baselines import B0
from forecast.features import CATEGORICAL, TARGETS, build, design, load, transitions

DATA = Path("/repo/data/synthetic/v1")


@pytest.fixture(scope="module")
def d():
    if not DATA.exists():
        pytest.skip("нет версии датасета v1: make -C data generate")
    return load(DATA)


@pytest.fixture(scope="module", params=[("default", "true"), ("eduscore", "obs")])
def built(d, request):
    return build(d, *request.param), request.param


def test_targets_are_not_features(built):
    (panel, features), _ = built
    assert not set(features) & set(TARGETS)
    assert not any(f.endswith("_next") for f in features)


@pytest.mark.parametrize("cut", [2022, 2023])
def test_no_leakage_from_future(d, cut):
    """Признаки года t не меняются, если вырезать из данных всё, что было после года t."""
    past = {name: (t[t.year <= cut] if "year" in t else t) for name, t in d.items()}
    for rules, layer in (("default", "true"), ("default", "obs"), ("eduscore", "obs")):
        full, features = build(d, rules, layer)
        trunc, _ = build(past, rules, layer)
        a = full[full.year == cut].set_index("student_id")[features]
        b = trunc[trunc.year == cut].set_index("student_id")[features].loc[a.index]
        num = [f for f in features if f not in CATEGORICAL]
        assert np.allclose(a[num].to_numpy(float), b[num].to_numpy(float), equal_nan=True), (rules, layer)
        assert trunc[trunc.year == cut].igpa_next.isna().all()


@pytest.mark.parametrize("cut", [2022, 2023])
def test_no_leakage_from_late_asu_entries(d, cut):
    """Признаки года t видят АСУ на конец года t: записи, внесённые позже (даже о событиях года t), их не меняют."""
    end = pd.Timestamp(f"{cut + 1}-06-30")
    early = {**d, "records_asu": d["records_asu"][d["records_asu"].entered_at <= end]}
    full, features = build(d, "default", "obs")
    trunc, _ = build(early, "default", "obs")
    a = full[full.year == cut].set_index("student_id")[features]
    b = trunc[trunc.year == cut].set_index("student_id")[features].loc[a.index]
    num = [f for f in features if f not in CATEGORICAL]
    assert np.allclose(a[num].to_numpy(float), b[num].to_numpy(float), equal_nan=True)


def test_next_year_target(built, d):
    (panel, _), (rules, layer) = built
    t = transitions(panel).sample(300, random_state=0)
    snap = (d["snapshots_year"] if rules == "default" else d[f"snapshots_year_{rules}"]).set_index(["student_id", "year"])
    assert np.allclose(t.igpa_next, snap.loc[list(zip(t.student_id, t.year + 1)), f"{layer}_igpa"])
    assert ((t.risk == 1) == (t.delta <= -0.1)).all()


def test_obs_layer_has_behaviour(d):
    _, features = build(d, "default", "obs")
    assert {"asu_has_records", "asu_delay", "asu_rejected_share"} <= set(features)
    _, features = build(d, "default", "true")
    assert not any(f.startswith("asu_") for f in features)


def test_folds_are_ordered_and_disjoint(built):
    (panel, _), _ = built
    data = transitions(panel)
    for year, train, test in P.folds(data):
        assert train.year.max() < year and (test.year == year).all()
    for year, train, test in P.folds(data, disjoint=True):
        assert not set(train.student_id) & set(test.student_id)


def test_one_transition_per_student_in_test(built):
    (panel, _), _ = built
    for _, _, test in P.folds(transitions(panel)):
        assert test.student_id.is_unique


def test_design_matrix(built):
    (panel, features), _ = built
    X = design(panel, features)
    assert not X.isna().any().any()
    assert any(c.startswith("faculty_") for c in X)
    assert design(panel.head(5), features, list(X.columns)).shape[1] == X.shape[1]


def test_b0_and_metrics(built):
    (panel, features), _ = built
    t = transitions(panel)
    pred = B0().fit(t, features).predict(t)
    assert np.allclose(pred, t.igpa)
    assert P.regression(t.igpa_next, t.igpa_next)["mae"] == 0
    lo, hi = P.mae_ci(t.igpa_next, pred, n=200)
    assert lo <= np.abs(t.igpa_next - pred).mean() <= hi


def test_holm_and_threshold():
    adj = P.holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert adj["a"] == pytest.approx(0.03) and adj["c"] == pytest.approx(0.06) and adj["b"] == pytest.approx(0.06)
    y = np.array([0, 0, 1, 1])
    assert P.best_threshold(y, np.array([0.1, 0.2, 0.8, 0.9])) <= 0.8
