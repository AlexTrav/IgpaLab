import datetime as dt
import zipfile

import openpyxl
import pandas as pd
import pytest

from generator.common import TEMPLATES
from generator.export import SSCI_TEMPLATES, _pivot_counts, igpa_export, iros_pivot, ssci_pivot
from igpa import CATEGORIES, Block, Profile, categories, statuses

DAY = dt.date(2026, 6, 30)


def _template(pattern):
    return openpyxl.load_workbook(next(TEMPLATES.glob(pattern))).active


@pytest.fixture(scope="module")
def year_rows(data):
    snap = data["snapshots_year"]
    return snap[snap.year == 2025]


def test_igpa_export_keeps_template(data, year_rows, tmp_path):
    path = tmp_path / "igpa.xlsx"
    igpa_export(path, DAY, year_rows, data["students"])
    ws, tpl = openpyxl.load_workbook(path).active, _template("*Сводная выгрузка студентов по IGPA.xlsx")
    assert "Синтетические данные IgpaLab" in ws["A1"].value and "30.06.2026" in ws["A1"].value
    assert ws["A2"].value == tpl["A2"].value
    assert [c.value for c in ws[3]] == [c.value for c in tpl[3]]
    assert {str(m) for m in ws.merged_cells.ranges} == {str(m) for m in tpl.merged_cells.ranges}
    assert ws.max_row == 3 + len(year_rows)
    first = [c.value for c in ws[4]]
    assert first[0] == 1 and first[1].startswith("Студент ") and len(first) == 9 + len(CATEGORIES)


def test_iros_pivot_keeps_template(data, tmp_path):
    path = tmp_path / "iros.xlsx"
    pivot = _pivot_counts(data["records_asu"], 2025, DAY)
    iros_pivot(path, DAY, pivot)
    ws, tpl = openpyxl.load_workbook(path).active, _template("*Сводная таблица по IROS.xlsx")
    for row in (2, 3, 4):
        assert [c.value for c in ws[row]] == [c.value for c in tpl[row]]
    assert [ws.cell(r, 2).value for r in range(5, 11)] == [tpl.cell(r, 2).value for r in range(5, 11)]
    for r in range(5, 11):
        total, by_status = ws.cell(r, 3).value, [ws.cell(r, c).value for c in range(4, 8)]
        assert total >= max(by_status) and total <= sum(by_status)


@pytest.mark.parametrize("block", [Block.ONE_TIME, Block.PERMANENT])
def test_ssci_pivots_keep_templates(data, tmp_path, block):
    path = tmp_path / "ssci.xlsx"
    pivot = _pivot_counts(data["records_asu"], 2025, DAY)
    ssci_pivot(path, DAY, pivot, block)
    ws, tpl = openpyxl.load_workbook(path).active, _template(SSCI_TEMPLATES[block][0])
    for row in (2, 3, 4):
        assert [c.value for c in ws[row]] == [c.value for c in tpl[row]]
    assert {str(m) for m in ws.merged_cells.ranges} == {str(m) for m in tpl.merged_cells.ranges}
    # типы в шаблоне АСУ идут в том же порядке, что в справочнике, а уровни – как статусы блока
    cats = categories(profile=Profile.SSCI, block=block)
    assert [ws.cell(r, 2).value for r in range(5, 5 + len(cats))] == [tpl.cell(r, 2).value for r in range(5, 5 + len(cats))]
    assert ws.max_column == 3 + len(statuses(block)) and ws.max_row == 4 + len(cats)
    for r, c in enumerate(cats, start=5):
        expected = pivot.loc[c.code] if c.code in pivot.index else {}
        assert ws.cell(r, 3).value == int(expected.get("total", 0))


def test_no_template_author_in_exports(data, year_rows, tmp_path):
    author = openpyxl.load_workbook(next(TEMPLATES.glob("*IGPA.xlsx"))).properties.creator
    pivot = _pivot_counts(data["records_asu"], 2025, DAY)
    igpa_export(tmp_path / "a.xlsx", DAY, year_rows, data["students"])
    iros_pivot(tmp_path / "b.xlsx", DAY, pivot)
    ssci_pivot(tmp_path / "c.xlsx", DAY, pivot, Block.ONE_TIME)
    ssci_pivot(tmp_path / "d.xlsx", DAY, pivot, Block.PERMANENT)
    for path in tmp_path.glob("*.xlsx"):
        with zipfile.ZipFile(path) as z:
            assert not any(author in z.read(name).decode("utf-8", "ignore") for name in z.namelist()), path
        assert openpyxl.load_workbook(path).properties.creator == "IgpaLab"


def test_pivot_counts_students_not_records(data):
    pivot = _pivot_counts(data["records_asu"], 2025, DAY)
    active = data["enrollment"].query("year == 2025").student_id.nunique()
    assert (pivot.total <= active).all()
    assert isinstance(pivot, pd.DataFrame)
