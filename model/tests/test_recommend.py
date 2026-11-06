from pathlib import Path

import numpy as np
import pytest

from forecast import recommend as R
from forecast.features import build, load, transitions
from igpa import Record, calculate, load_rules

DATA = Path("/repo/data/synthetic/v1")


@pytest.fixture(scope="module")
def setup():
    if not DATA.exists():
        pytest.skip("нет версии датасета v1: make -C data generate")
    d = load(DATA)
    panel, _ = build(d, "default", "true")
    data = transitions(panel)
    train = data[data.year < 2024].sample(800, random_state=0)
    test = data[data.year == 2024].sample(80, random_state=0)
    portfolio = R.Portfolio(d["records_true"], load_rules())
    return train, test, portfolio, R.Feasibility(train, portfolio)


def test_gain_is_exact_recalculation(setup):
    _, test, portfolio, _ = setup
    rules = load_rules()
    row = test.iloc[0]
    items = portfolio.by_key.get((row.student_id, row.year), [])
    for action in R.actions()[::7]:
        kind, code, value = action
        if kind == "gpa":
            expected = 0.5 * value if row.gpa + value <= 4 else 0.5 * (4 - row.gpa)
        else:
            before = calculate([Record(c, s) for c, s in items], row.gpa, rules).igpa
            expected = calculate([Record(c, s) for c, s in items] + [Record(code, value)], row.gpa, rules).igpa - before
        assert portfolio.gain(row.gpa, items, action) == pytest.approx(expected)


def test_feasibility_bounds(setup):
    _, test, _, feas = setup
    values, idx = feas(test)
    assert values.shape == (len(test), len(R.actions())) and idx.shape == (len(test), R.NEIGHBOURS)
    assert ((values > 0) & (values < 1)).all()


def test_recommendations_ranked_and_positive(setup):
    _, test, portfolio, feas = setup
    rec = R.recommend(test, portfolio, feas)
    assert (rec.gain > 0).all() and rec["rank"].between(1, 3).all()
    for _, g in rec.groupby("student_id"):
        assert g.sort_values("rank").expected.is_monotonic_decreasing


def test_follow_strategies(setup):
    _, test, portfolio, feas = setup
    f = R.follow(test, portfolio, feas)
    assert f.strategy.nunique() == 4 and len(f) == 4 * len(test)
    assert np.isfinite(f.realized).all()
