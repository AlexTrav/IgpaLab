import random

import pytest

from igpa import (CATEGORIES, STATUSES, Block, FlagKind, Profile, Record, calculate, categories, igpa_value,
                  load_rules, statuses)

RULES = load_rules()


def full(code: str, status: str, n: int = 5) -> list[Record]:
    return [Record(code, status)] * n


def kinds(result) -> list[tuple[int, FlagKind]]:
    return [(f.index, f.kind) for f in result.flags]


def test_no_records():
    r = calculate([], 3.0)
    assert (r.iros, r.ssci, r.igpa) == (0, 0, 1.5)
    assert list(r.categories) == [c.code for c in CATEGORIES]


def test_eduscore_screen_formula():
    # экран EduScore: GPA 3,90, iROS 0,69, SSCI 0,10 -> 2,98
    assert igpa_value(3.90, 0.69, 0.10) == pytest.approx(2.976)


def test_parts_sum_to_igpa():
    r = calculate(full("IROS_PROJECT", "IROS_INT_RK", 2) + [Record("SSCI_SPORT", "SSCI_REPUBLIC")], 3.2)
    assert r.gpa_part == pytest.approx(1.6)
    assert r.gpa_part + r.iros_part + r.ssci_part == pytest.approx(r.igpa)
    assert r.iros_part == pytest.approx(0.35 * 4 * r.iros)


def test_regulation_example_top_five_in_category():
    # статья ТМИ: одно международное и пять вузовских в типе с весом 0,2 -> вклад 0,20 × 60/100 = 0,12
    regulation_only = RULES.with_changes(category_weights={**RULES.category_weights, "IROS_TALK": 0,
                                                           "IROS_INTERNSHIP": 0})
    records = [Record("IROS_EVENT", "IROS_INT_ABROAD")] + full("IROS_EVENT", "IROS_OVPO")
    r = calculate(records, 3.0, regulation_only)
    event = r.categories["IROS_EVENT"]
    assert (event.points, event.counted) == (60, 5)
    assert event.contribution == pytest.approx(0.12)
    assert kinds(r) == [(5, FlagKind.OVER_LIMIT)]
    # с новыми типами АСУ веса нормируются: 0,2 / 1,5
    assert calculate(records, 3.0).categories["IROS_EVENT"].contribution == pytest.approx(0.6 * 0.2 / 1.5)


def test_sixth_record_changes_nothing():
    five = full("IROS_PUBLICATION", "IROS_REP_CITY")
    assert calculate(five + [Record("IROS_PUBLICATION", "IROS_OVPO")], 3.0).igpa == calculate(five, 3.0).igpa


def test_full_category_gives_block_weight():
    r = calculate(full("IROS_PUBLICATION", "IROS_INT_ABROAD"), 3.0)
    assert r.iros == pytest.approx(RULES.block_weight("IROS_PUBLICATION"))
    assert r.iros == pytest.approx(0.2)


def test_maximum_is_four():
    records = [rec for c in categories(profile=Profile.IROS) for rec in full(c.code, "IROS_INT_ABROAD")]
    records += [rec for c in categories(block=Block.ONE_TIME) for rec in full(c.code, "SSCI_INTERNATIONAL")]
    records += [Record(c.code, "SSCI_PERMANENT") for c in categories(block=Block.PERMANENT)]
    r = calculate(records, 4.0)
    assert (r.iros, r.ssci, r.igpa) == (pytest.approx(1), pytest.approx(1), pytest.approx(4))


def test_ssci_mean_of_two_parts():
    one_time = [rec for c in categories(block=Block.ONE_TIME) for rec in full(c.code, "SSCI_INTERNATIONAL")]
    permanent = [Record(c.code, "SSCI_PERMANENT") for c in categories(block=Block.PERMANENT)]
    assert calculate(one_time, 3.0).ssci == pytest.approx(0.5)
    assert calculate(permanent, 3.0).ssci == pytest.approx(0.5)


def test_ssci_sum_clip():
    rules = RULES.with_changes(ssci_blocks="sum_clip")
    one_time = [rec for c in categories(block=Block.ONE_TIME) for rec in full(c.code, "SSCI_INTERNATIONAL")]
    permanent = [Record(c.code, "SSCI_PERMANENT") for c in categories(block=Block.PERMANENT)]
    assert calculate(one_time, 3.0, rules).ssci == pytest.approx(1)
    both = calculate(one_time + permanent, 3.0, rules)
    assert both.ssci == pytest.approx(1)
    assert sum(both.categories[c.code].contribution for c in categories(profile=Profile.SSCI)) == pytest.approx(1)


def test_permanent_project_counts_once():
    r = calculate([Record("SSCI_STUDENT_ORG", "SSCI_PERMANENT")] * 2, 3.0)
    assert (r.categories["SSCI_STUDENT_ORG"].points, r.categories["SSCI_STUDENT_ORG"].counted) == (100, 1)
    assert kinds(r) == [(1, FlagKind.OVER_LIMIT)]


def test_foreign_status_mapped():
    r = calculate([Record("IROS_EVENT", "SSCI_INTERNATIONAL")], 3.0)
    assert r.categories["IROS_EVENT"].points == 18
    assert kinds(r) == [(0, FlagKind.STATUS_MAPPED)]


def test_foreign_status_rejected():
    r = calculate([Record("IROS_EVENT", "SSCI_INTERNATIONAL")], 3.0, RULES.with_changes(foreign_status="reject"))
    assert r.iros == 0
    assert kinds(r) == [(0, FlagKind.STATUS_MISMATCH)]


def test_permanent_status_on_one_time_type_not_counted():
    r = calculate([Record("SSCI_SPORT", "SSCI_PERMANENT"), Record("IROS_PRIZE", "SSCI_PERMANENT")], 3.0)
    assert (r.iros, r.ssci) == (0, 0)
    assert kinds(r) == [(0, FlagKind.STATUS_MISMATCH), (1, FlagKind.STATUS_MISMATCH)]


def test_permanent_type_takes_permanent_points():
    r = calculate([Record("SSCI_STUDENT_ORG", "SSCI_UNIVERSITY")], 3.0)
    assert r.categories["SSCI_STUDENT_ORG"].points == 100
    assert kinds(r) == [(0, FlagKind.STATUS_MAPPED)]


def test_not_approved_skipped():
    records = [Record("IROS_PRIZE", "IROS_INT_RK", approved=False)]
    r = calculate(records, 3.0)
    assert r.iros == 0 and kinds(r) == [(0, FlagKind.NOT_APPROVED)]
    assert calculate(records, 3.0, RULES.with_changes(only_approved=False)).iros > 0


def test_zero_weight_type_has_no_rule():
    rules = RULES.with_changes(category_weights={**RULES.category_weights, "IROS_TALK": 0})
    r = calculate([Record("IROS_TALK", "IROS_INT_RK")], 3.0, rules)
    assert r.iros == 0 and kinds(r) == [(0, FlagKind.NO_RULE)]


@pytest.mark.parametrize("gpa", [-0.1, 4.01])
def test_gpa_out_of_scale(gpa):
    with pytest.raises(ValueError):
        calculate([], gpa)


@pytest.mark.parametrize("record", [Record("IROS_CONFERENCE", "IROS_OVPO"), Record("IROS_EVENT", "REGIONAL")])
def test_unknown_codes(record):
    with pytest.raises(ValueError):
        calculate([record], 3.0)


def _random_profiles(seed: int, n: int):
    rng = random.Random(seed)
    for _ in range(n):
        records = [Record(rng.choice(CATEGORIES).code, rng.choice(STATUSES).code, rng.random() > 0.1)
                   for _ in range(rng.randint(0, 40))]
        yield records, round(rng.uniform(0, 4), 2)


@pytest.mark.parametrize("preset", ["default", "eduscore"])
def test_bounds_and_contributions(preset):
    rules = load_rules(preset)
    for records, gpa in _random_profiles(1, 300):
        r = calculate(records, gpa, rules)
        assert 0 <= r.iros <= 1 + 1e-9 and 0 <= r.ssci <= 1 + 1e-9 and 0 <= r.igpa <= 4 + 1e-9
        assert sum(r.categories[c.code].contribution for c in categories(profile=Profile.IROS)) == pytest.approx(r.iros)
        assert sum(r.categories[c.code].contribution for c in categories(profile=Profile.SSCI)) == pytest.approx(r.ssci)


@pytest.mark.parametrize("preset", ["default", "eduscore"])
def test_adding_record_never_decreases_igpa(preset):
    rules = load_rules(preset)
    for records, gpa in _random_profiles(2, 40):
        base = calculate(records, gpa, rules).igpa
        for category in CATEGORIES:
            for status in STATUSES:
                assert calculate(records + [Record(category.code, status.code)], gpa, rules).igpa >= base - 1e-12
