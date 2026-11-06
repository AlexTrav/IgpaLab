"""Сверка с движком EduScore: случаи из eduscore-gpa-service/internal/domain/scoring/engine_test.go."""

import pytest

from igpa import CATEGORY_BY_CODE, Block, Profile, Record, calculate, eduscore_max, load_rules

RULES = load_rules("eduscore")

# уровни EduScore -> статусы АСУ
LEVEL = {
    Block.RESEARCH: {"UNIVERSITY": "IROS_OVPO", "CITY": "IROS_REP_CITY", "REPUBLIC": "IROS_REP_CITY",
                     "INTERNATIONAL_RK": "IROS_INT_RK", "INTERNATIONAL": "IROS_INT_ABROAD"},
    Block.ONE_TIME: {"UNIVERSITY": "SSCI_UNIVERSITY", "CITY": "SSCI_CITY_REGION", "REPUBLIC": "SSCI_REPUBLIC",
                     "INTERNATIONAL": "SSCI_INTERNATIONAL"},
    Block.PERMANENT: {"UNIVERSITY": "SSCI_PERMANENT"},
}


def rec(code: str, level: str) -> Record:
    return Record(code, LEVEL[CATEGORY_BY_CODE[code].block][level])


IROS_MAX, SSCI_MAX = 30.0, 108.0
PERMANENT = [rec("SSCI_STUDENT_ORG", "UNIVERSITY"), rec("SSCI_UNIVERSITY_IMAGE", "UNIVERSITY"),
             rec("SSCI_IMAGE_PROJECT", "UNIVERSITY")]

CASES = [
    ("нет достижений", 3.0, [], 0, 0, 1.5),
    ("IROS_EVENT международный", 3.0, [rec("IROS_EVENT", "INTERNATIONAL")], 4 / IROS_MAX, 0, 1.6867),
    ("IROS_PUBLICATION международный в РК", 3.0, [rec("IROS_PUBLICATION", "INTERNATIONAL_RK")],
     5.4 / IROS_MAX, 0, 1.752),
    ("два iROS", 3.0, [rec("IROS_EVENT", "INTERNATIONAL"), rec("IROS_PRIZE", "CITY")], 6.8 / IROS_MAX, 0, 1.8173),
    ("SSCI_VOLUNTEER международный", 3.0, [rec("SSCI_VOLUNTEER", "INTERNATIONAL")], 0, 4 / SSCI_MAX, 1.522),
    ("iROS и SSCI", 3.0, [rec("IROS_EVENT", "INTERNATIONAL"), rec("SSCI_VOLUNTEER", "INTERNATIONAL")],
     4 / IROS_MAX, 4 / SSCI_MAX, 1.7089),
    ("два SSCI", 3.0, [rec("SSCI_VOLUNTEER", "INTERNATIONAL"), rec("SSCI_SPORT", "CITY")], 0, 7 / SSCI_MAX, 1.539),
    ("пять публикаций международных", 4.0, [rec("IROS_PUBLICATION", "INTERNATIONAL")] * 5, 1, 0, 3.40),
    ("членство в организации", 3.0, [rec("SSCI_STUDENT_ORG", "UNIVERSITY")], 0, 40 / SSCI_MAX, 1.7222),
    ("три постоянных проекта", 3.0, PERMANENT, 0, 100 / SSCI_MAX, 2.0556),
    ("полный SSCI", 4.0, PERMANENT + [rec("SSCI_VOLUNTEER", "INTERNATIONAL"), rec("SSCI_SPORT", "INTERNATIONAL")],
     0, 1, 2.60),
    ("членство дважды учитывается раз", 3.0, [rec("SSCI_STUDENT_ORG", "UNIVERSITY")] * 2, 0, 40 / SSCI_MAX, 1.7222),
]


def test_max_possible():
    assert eduscore_max(RULES, Profile.IROS) == pytest.approx(IROS_MAX)
    assert eduscore_max(RULES, Profile.SSCI) == pytest.approx(SSCI_MAX)


@pytest.mark.parametrize("name, gpa, records, iros, ssci, igpa", CASES, ids=[c[0] for c in CASES])
def test_engine_cases(name, gpa, records, iros, ssci, igpa):
    r = calculate(records, gpa, RULES)
    assert r.iros == pytest.approx(iros)
    assert r.ssci == pytest.approx(ssci)
    assert r.igpa == pytest.approx(igpa, abs=1e-3)  # в EduScore ожидания IGPA округлены
