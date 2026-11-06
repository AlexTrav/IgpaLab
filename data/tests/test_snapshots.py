import numpy as np
import pytest

from generator.common import academic_year
from igpa import Record, calculate, load_rules


def test_true_snapshot_matches_calculator(data, cfg):
    snap = data["snapshots_year"]
    rec = data["records_true"]
    gpa = data["gpa_year"].set_index(["student_id", "year"]).gpa
    rules = load_rules(cfg["rules"])
    sample = snap[~snap.partial].sample(60, random_state=1)
    for row in sample.itertuples():
        mine = rec[(rec.student_id == row.student_id) & (rec.year == row.year)]
        result = calculate([Record(c, s) for c, s in zip(mine.category, mine.status)], gpa[row.student_id, row.year], rules)
        assert row.true_iros == pytest.approx(result.iros)
        assert row.true_ssci == pytest.approx(result.ssci)
        assert row.true_igpa == pytest.approx(result.igpa)


def test_partial_only_for_current_year(data, cfg):
    snap = data["snapshots_year"]
    current = academic_year(cfg["now"])
    assert (snap.partial == (snap.year == current)).all()
    assert snap[snap.partial].true_igpa.isna().all()
    assert snap[~snap.partial].true_igpa.between(0, 4).all()


def test_bounds(data):
    for name in ("snapshots_year", "snapshots_semester", "snapshots_real"):
        snap = data[name]
        for col in [c for c in snap if c.endswith(("_iros", "_ssci"))]:
            assert snap[col].between(0, 1 + 1e-9).all(), (name, col)


def test_semester_parts(data, cfg):
    sem = data["snapshots_semester"]
    current = academic_year(cfg["now"])
    assert set(sem.part) == {"fall", "spring"}
    assert not ((sem.part == "spring") & (sem.year == current)).any()


def test_observed_layer_is_incomplete(data):
    done = data["snapshots_year"].query("not partial")
    assert done.obs_n.sum() < done.true_n.sum() * 1.05
    assert (done.obs_approved == 0).mean() > (done.true_n == 0).mean()


def test_realistic_ranges(data):
    done = data["snapshots_year"].query("not partial")
    assert 2.6 < data["gpa_year"].gpa.mean() < 3.4
    assert 0.15 < (done.true_n == 0).mean() < 0.6
    wide = done.pivot(index="student_id", columns="year", values="true_igpa")
    drops = np.concatenate([(wide[y + 1] - wide[y]).dropna() for y in wide.columns[:-1]])
    assert 0.05 < (drops <= -0.1).mean() < 0.4
