import pandas as pd

from generator.asu import APPROVED, DRAFT, REJECTED
from generator.common import academic_year
from igpa import CATEGORY_BY_CODE


def test_records_come_from_true_history(data, cfg):
    asu, true = data["records_asu"], data["records_true"].set_index("record_id")
    assert asu.true_record_id.isin(true.index).all()
    assert (asu.entered_at >= asu.event_date).all()
    assert (asu.entered_at <= pd.Timestamp(cfg["now"])).all()
    assert set(asu.gt_error) <= {"", "wrong_category", "foreign_status", "wrong_category,foreign_status", "duplicate"}


def test_approval_history(data, cfg):
    asu = data["records_asu"].set_index("record_id")
    ap = data["approvals"]
    assert ap.groupby("record_id").stage.apply(lambda s: list(s) == list(range(1, len(s) + 1))).all()
    assert ap.groupby("record_id").decided_at.apply(lambda s: s.is_monotonic_increasing).all()
    assert not ap.record_id.isin(asu.index[asu.draft]).any()
    rejected = ap[ap.decision == "Отклонено"]
    last = ap.groupby("record_id").stage.max()
    assert (rejected.stage.to_numpy() == last[rejected.record_id].to_numpy()).all()
    stages = {p: len(names) for p, names in cfg["asu"]["stages"].items()}
    approved = asu[asu.state_now == APPROVED]
    need = approved.category.map(lambda c: stages[CATEGORY_BY_CODE[c].profile.value])
    assert (ap.groupby("record_id").size()[approved.index] == need).all()
    assert (asu[asu.draft].state_now == DRAFT).all()
    assert set(asu.state_now) <= {APPROVED, REJECTED, DRAFT, "На согласовании"}


def test_real_scenario(data, cfg):
    real, enr = data["records_asu_real"], data["enrollment"]
    launch = pd.Timestamp(cfg["real_launch"])
    assert (real.entered_at >= launch).all()
    on_launch = set(enr[enr.year == academic_year(cfg["real_launch"])].student_id)
    assert real[real.event_date < launch].student_id.isin(on_launch).all()
    assert len(real) < len(data["records_asu"])
