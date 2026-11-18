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
    assert r["rel"] == pytest.approx(-2 / 3)


def test_calibration_curve_bins():
    rng = np.random.default_rng(3)
    p = rng.uniform(0, 0.5, 10000)
    y = rng.random(10000) < p
    c = R.calibration_curve(y, p)
    assert len(c) == 10 and c.n.sum() == 10000
    assert np.all(np.diff(c.mean_pred) > 0) and np.abs(c.mean_pred - c.observed).max() < 0.05


def test_fp_per_tp():
    y = np.array([1, 1, 0, 0, 0, 0])
    s = np.array([0.9, 0.1, 0.8, 0.7, 0.2, 0.1])
    assert R.risk_metrics(y, s, 0.5)["fp_per_tp"] == pytest.approx(2.0)


def test_small_programs_are_lower_quartile():
    import pandas as pd
    sizes = {"a": 10, "b": 20, "c": 30, "d": 40, "e": 50}
    students = pd.DataFrame([(f"{p}{i}", p) for p, n in sizes.items() for i in range(n)],
                            columns=["student_id", "program"])
    small, q1 = R.small_programs(students)
    assert q1 == 20 and small == {"a"}


@pytest.mark.parametrize("cls", [B.Drift, B.Lin, B.Huber, B.ENet, B.Cohort])
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


def test_recall_threshold_finds_80_percent():
    from forecast import protocol as P
    rng = np.random.default_rng(2)
    y = rng.random(5000) < 0.2
    score = rng.random(5000) + y * 0.5
    t = P.recall_threshold(y, score, 0.8)
    assert 0.79 <= (score[y] >= t).mean() <= 0.82


def test_stack_never_sees_the_year_it_predicts(monkeypatch):
    """Стекинг: базовая модель, прогнозирующая год y для мета-модели, обучена только на годах до y."""
    import pandas as pd
    from forecast import models as M
    seen = []

    class Probe:
        def __init__(self, target="delta", use=None):
            pass

        def fit(self, train, features):
            self.years = set(train.year)
            return self

        def predict(self, block):
            seen.append((self.years, set(block.year)))
            return block.igpa.to_numpy(float)

        def risk(self, block):
            return np.full(len(block), 0.3)

    monkeypatch.setattr(M, "BASES", (Probe, Probe, Probe))
    rng = np.random.default_rng(0)
    train = pd.DataFrame({"year": np.repeat([2021, 2022, 2023], 50), "igpa": rng.random(150),
                          "delta": rng.normal(0, 0.1, 150), "risk": (rng.random(150) < 0.3).astype(float)})
    M.StackModel().fit(train, [])
    blocks = [(tr, te) for tr, te in seen if te != set(train.year)]
    assert {frozenset(te) for _, te in blocks} == {frozenset({2022}), frozenset({2023})}
    assert all(max(tr) < min(te) for tr, te in blocks)


def test_transfer_scenarios_hold_out_the_group():
    import pandas as pd
    from forecast import transfer
    rng = np.random.default_rng(4)
    frame = pd.DataFrame({"faculty": rng.choice(["A", "B", "C"], 400),
                          "level": rng.choice(["bachelor", "master_profile"], 400)})
    train, test = frame.iloc[:300], frame.iloc[300:]
    names = []
    for name, tr, te in transfer.scenarios(train, test):
        names.append(name)
        if "факультета" in name:
            f = te.faculty.iloc[0]
            assert (te.faculty == f).all() and not (tr.faculty == f).any()
        else:
            assert (tr.level == "bachelor").all() and (te.level != "bachelor").all()
    assert len(names) == 4


def test_stress_shift_touches_only_target_year():
    if not DATA.exists():
        pytest.skip("нет версии датасета v1: make -C data generate")
    from forecast import stress
    d = load(DATA)
    s, info = stress.shifted(d)
    assert info["added_true"] == round(stress.SHARE * info["pool"]) and info["added_asu"] > 0
    assert len(s["records_true"]) == len(d["records_true"]) + info["added_true"]
    a = d["snapshots_year_eduscore"].set_index(["student_id", "year"]).sort_index()
    b = s["snapshots_year_eduscore"].set_index(["student_id", "year"]).sort_index()
    other = a.index.get_level_values("year") != stress.SHIFT_YEAR
    assert np.allclose(a.true_igpa[other], b.true_igpa[other], equal_nan=True)
    target = ~other & a.true_igpa.notna().to_numpy()
    assert (b.true_ssci[target] >= a.true_ssci[target] - 1e-9).all()
    assert b.true_ssci[target].mean() > a.true_ssci[target].mean()


def test_advice_follow_marks_done_actions():
    if not DATA.exists():
        pytest.skip("нет версии датасета v1: make -C data generate")
    from igpa import load_rules
    from forecast import recommend as Rec
    from forecast.protocol import FINAL
    d = load(DATA)
    data = transitions(build(d, "default", "true")[0])
    train, test = data[data.year < FINAL], data[data.year == FINAL].sample(200, random_state=0)
    portfolio = Rec.Portfolio(d["records_true"], load_rules("default"))
    f = Rec.follow(test, portfolio, Rec.Feasibility(train, portfolio))
    done = Rec.observed(test, portfolio)
    ours = f[f.strategy.str.startswith("Наша")].reset_index(drop=True)
    assert (ours.did.to_numpy() == done[np.arange(len(test)), ours.action.to_numpy()]).all()
    assert set(f.kind) <= {"GPA", "iROS", "SSCI"}
    # regret против лучшего действия задним числом по той же метрике: не меньше нуля, у оракула ноль
    assert (f.regret >= -1e-12).all()
    assert np.allclose(f.oracle - f.regret, f.expected_realized)
