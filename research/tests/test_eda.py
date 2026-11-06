from pathlib import Path

import numpy as np
import pytest

from analysis import eda

DATA = Path("/repo/data/synthetic/v1")


@pytest.fixture(scope="module")
def d():
    if not DATA.exists():
        pytest.skip("нет версии датасета v1: make -C data generate")
    return eda.load(DATA)


@pytest.fixture(scope="module")
def panel(d):
    return eda.year_panel(d)


def test_panel_one_row_per_student_year(panel):
    assert not panel.duplicated(["student_id", "year"]).any()


def test_next_year_values_are_next_year(panel, d):
    snap = eda.snapshot(d, "default").set_index(["student_id", "year"])
    t = panel[panel.true_igpa_next.notna()].sample(300, random_state=0)
    expected = snap.loc[list(zip(t.student_id, t.year + 1)), "true_igpa"].to_numpy()
    assert np.allclose(t.true_igpa_next.to_numpy(), expected)


def test_previous_gpa_is_previous_year(panel, d):
    gpa = d["gpa_year"].set_index(["student_id", "year"]).gpa
    t = panel[panel.gpa_prev.notna()].sample(300, random_state=0)
    assert np.allclose(t.gpa_prev.to_numpy(), gpa.loc[list(zip(t.student_id, t.year - 1))].to_numpy())


def test_counts_match_records(panel, d):
    rec = d["records_true"]
    t = panel.sample(200, random_state=1)
    for row in t.itertuples():
        mine = rec[(rec.student_id == row.student_id) & (rec.year == row.year)]
        assert row.n_research + row.n_one_time + row.n_permanent == len(mine) == row.true_n


def test_risk_definition(panel):
    t = panel[panel.delta_true.notna()]
    assert ((t.risk_true == 1) == (t.delta_true <= -0.1)).all()


def test_components_shares(d):
    comp = eda.components(d)
    assert comp.achievement_share.between(0, 1).all()
    lit = comp[(comp.rules == "default") & (comp.layer == "true")].iloc[0]
    edu = comp[(comp.rules == "eduscore") & (comp.layer == "true")].iloc[0]
    assert edu.achievement_share > lit.achievement_share
    assert lit.gpa_part + lit.iros_part + lit.ssci_part == pytest.approx(lit.igpa_mean)
