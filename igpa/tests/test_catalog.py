from pathlib import Path

import openpyxl
import pytest

from igpa import CATEGORIES, STATUSES, Block, Profile, categories, find_category, find_status, statuses

EXAMPLE = Path(__file__).resolve().parents[2] / "data" / "example"


def _sheet(pattern: str):
    path = next(EXAMPLE.glob(pattern))
    return openpyxl.load_workbook(path).active


def test_columns_follow_export_j_to_y():
    assert [c.column for c in CATEGORIES] == list("JKLMNOPQRSTUVWXY")
    assert len({c.code for c in CATEGORIES}) == 16


def test_blocks_by_columns():
    assert [c.column for c in categories(block=Block.RESEARCH)] == list("JKLMNO")
    assert [c.column for c in categories(block=Block.ONE_TIME)] == list("PQRST")
    assert [c.column for c in categories(block=Block.PERMANENT)] == list("UVWXY")
    assert len(categories(profile=Profile.IROS)) == 6
    assert len(categories(profile=Profile.SSCI)) == 10


def test_new_types_are_not_in_regulation():
    assert [c.column for c in CATEGORIES if not c.in_regulation] == list("KNWY")


def test_nine_statuses():
    assert len(STATUSES) == 9
    assert [len(statuses(b)) for b in Block] == [4, 4, 1]


def test_export_headers_match_template():
    ws = _sheet("*Сводная выгрузка студентов по IGPA.xlsx")
    assert [ws[f"{col}3"].value for col in "ABCDEFGHI"] == [
        "№", "ФИО", "Факультет", "ОП", "Год обучения", "Форма обучения", "Язык обучения",
        "Общий балл по IROS", "Общий балл по SSCI"]
    assert [ws[f"{c.column}3"].value for c in CATEGORIES] == [c.export_header for c in CATEGORIES]


def test_iros_pivot_matches_template():
    ws = _sheet("*Сводная таблица по IROS.xlsx")
    assert [ws[f"B{row}"].value for row in range(5, 11)] == [c.asu_title for c in categories(profile=Profile.IROS)]
    assert [ws[f"{col}4"].value for col in "DEFG"] == [s.asu_name for s in statuses(Block.RESEARCH)]


@pytest.mark.parametrize("text, code", [
    ("SSCI_VOLUNTEER", "SSCI_VOLUNTEER"),
    ("Участие в волонтёрском движении (баллы)", "SSCI_VOLUNTEER"),
    ("  участие в   волонтерском движении ", "SSCI_VOLUNTEER"),
    ("Научная стажировка", "IROS_INTERNSHIP"),
    ("Участие в интеллектуальных, дебатных мероприятиях. Мероприятиях по развитию soft skills(мастер-классы, "
     "карьерные ярмарки и  (баллы)", "SSCI_INTELLECTUAL"),
])
def test_find_category(text, code):
    assert find_category(text).code == code


def test_find_unknown():
    assert find_category("Олимпиада по шахматам") is None
    assert find_status("Областной") is None


@pytest.mark.parametrize("text, code", [
    ("ОВПО", "IROS_OVPO"),
    (" международные ", "SSCI_INTERNATIONAL"),
    ("Международный в Республике Казахстан", "IROS_INT_RK"),
    ("В рамках постоянно реализуемых университетских проектов (в течение года)", "SSCI_PERMANENT"),
])
def test_find_status(text, code):
    assert find_status(text).code == code
