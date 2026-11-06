import numpy as np
import pandas as pd

from generator.common import academic_year, on
from generator.population import program_table
from igpa import CATEGORY_BY_CODE, STATUS_BY_CODE, Block


def test_students(data, cfg):
    s = data["students"]
    assert s.student_id.is_unique and len(s) == cfg["students"]
    programs = program_table(cfg["university"])
    allowed = set(zip(programs.group, programs.faculty, programs.program))
    group = np.where(s.level == "bachelor", "bachelor", "master")
    assert all(key in allowed for key in zip(group, s.faculty, s.program))
    for level, spec in cfg["levels"].items():
        assert abs((s.level == level).mean() - spec["share"]) < 0.05


def test_records_only_while_enrolled(data, cfg):
    rec, enr = data["records_true"], data["enrollment"]
    keys = set(zip(enr.student_id, enr.year))
    assert all(k in keys for k in zip(rec.student_id, rec.year))
    starts = rec.year.map(lambda y: pd.Timestamp(on(y, "09-01")))
    ends = rec.year.map(lambda y: pd.Timestamp(on(y, "06-15")))
    assert ((rec.event_date >= starts) & (rec.event_date <= ends)).all()
    assert (rec.event_date <= pd.Timestamp(cfg["now"])).all()


def test_true_statuses_match_blocks(data):
    rec = data["records_true"]
    assert all(STATUS_BY_CODE[s].family is CATEGORY_BY_CODE[c].block for c, s in zip(rec.category, rec.status))


def test_internship_only_for_masters(data):
    rec = data["records_true"].merge(data["students"][["student_id", "level"]])
    assert (rec[rec.category == "IROS_INTERNSHIP"].level != "bachelor").all()


def test_permanent_once_a_year(data):
    rec = data["records_true"]
    permanent = rec[rec.category.map(lambda c: CATEGORY_BY_CODE[c].block is Block.PERMANENT)]
    assert not permanent.duplicated(["student_id", "year", "category"]).any()


def test_courses_and_gpa(data, cfg):
    c = data["courses"]
    assert (c.groupby(["student_id", "year", "semester"]).credits.sum() == 30).all()
    assert c.score.between(0, 100).all()
    for low, letter, points in cfg["grades"]["scale"]:
        assert (c[c.letter == letter].score >= low).all()
        assert (c[c.letter == letter].points == points).all()
    assert data["gpa_year"].gpa.between(0, 4).all()


def test_transfer_rules(data, cfg):
    enr = data["enrollment"].merge(data["students"][["student_id", "level"]])
    for level, rules in cfg["grades"]["transfer"].items():
        for course, (credits, gpa) in rules.items():
            rows = enr[(enr.level == level) & (enr.year_of_study == int(course))]
            failed = (rows.credits_earned < credits) | (rows.gpa_cum < gpa)
            assert (rows[rows.outcome.isin(["repeat", "expelled"])].index.isin(rows[failed].index)).all()
            assert not failed[rows.outcome == "promoted"].any()


def test_current_year_is_open(data, cfg):
    enr = data["enrollment"]
    current = academic_year(cfg["now"])
    assert (enr[enr.year == current].outcome == "current").all()
    assert (enr[enr.year < current].outcome != "current").all()
