"""Запись версии датасета: таблицы Parquet, выгрузки xlsx в формате шаблонов АСУ, CSV для просмотра."""

import datetime as dt
from pathlib import Path

import openpyxl
import pandas as pd

from igpa import CATEGORIES, Block, Profile, categories, statuses

from .asu import APPROVED, state_at
from .common import TEMPLATES, academic_year, on

IGPA_TEMPLATE = "*Сводная выгрузка студентов по IGPA.xlsx"
IROS_TEMPLATE = "*Сводная таблица по IROS.xlsx"
STAMP = 'Сформировано из системы АСУ "ТУРАН" - Синтетические данные IgpaLab - {:%d.%m.%Y} 12:00:00'
# блок SSCI -> (шаблон, имя файла выгрузки без даты), как в АСУ
SSCI_TEMPLATES = {
    Block.ONE_TIME: ("*Сводная таблица по SSCI-За разовые мероприятия.xlsx",
                     "Сводная таблица по SSCI-За разовые мероприятия"),
    Block.PERMANENT: ("*Сводная таблица по SSCI-В рамках постоянно реализуемых*.xlsx",
                      "Сводная таблица по SSCI-В рамках постоянно реализуемых университетских проектов (в течении года)"),
}


def write_tables(out: Path, tables: dict[str, pd.DataFrame]):
    out.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_parquet(out / f"{name}.parquet", index=False, compression="zstd")


def write_csv(version_dir: Path):
    """CSV в UTF-8 с BOM, чтобы Excel открыл кириллицу; в git не идут."""
    target = version_dir / "csv"
    target.mkdir(exist_ok=True)
    for path in sorted(version_dir.glob("*.parquet")):
        pd.read_parquet(path).to_csv(target / f"{path.stem}.csv", index=False, encoding="utf-8-sig")


def write_asu(out: Path, data: dict, cfg: dict):
    """Выгрузки АСУ на конец каждого учебного года и на «сегодня»; сценарий «как в жизни» – в asu_real."""
    now = cfg["now"]
    snap = data["snapshots_year"]
    for year in sorted(snap.year.unique()):
        day = min(on(year, cfg["asu"]["snapshots"]["year_end"]), now)
        _export_all(out / "asu" / f"{day}", day, year, snap[snap.year == year], data["records_asu"], data["students"])
    _export_all(out / "asu_real" / f"{now}", now, academic_year(now), data["snapshots_real"],
                data["records_asu_real"], data["students"])


def _export_all(folder: Path, day: dt.date, year: int, rows, asu, students):
    folder.mkdir(parents=True, exist_ok=True)
    prefix = f"{day} 12-00-00"
    igpa_export(folder / f"{prefix}Сводная выгрузка студентов по IGPA.xlsx", day, rows, students)
    pivot = _pivot_counts(asu, year, day)
    iros_pivot(folder / f"{prefix}Сводная таблица по IROS.xlsx", day, pivot)
    for block, (_, name) in SSCI_TEMPLATES.items():
        ssci_pivot(folder / f"{prefix}{name}.xlsx", day, pivot, block)


def _template(pattern: str):
    wb = openpyxl.load_workbook(next(TEMPLATES.glob(pattern)))
    # в свойствах шаблона ФИО сотрудника, сформировавшего выгрузку: в синтетику оно попасть не должно
    wb.properties.creator = wb.properties.lastModifiedBy = "IgpaLab"
    return wb


def igpa_export(path: Path, day: dt.date, rows: pd.DataFrame, students: pd.DataFrame, layer: str = "obs"):
    """Сводная выгрузка студентов по IGPA: строка на студента; общий балл – коэффициент 0–1, по типам – баллы."""
    wb = _template(IGPA_TEMPLATE)
    ws = wb.active
    ws["A1"] = STAMP.format(day)
    data = rows.join(students.set_index("student_id"), on="student_id").sort_values("student_id")
    for i, r in enumerate(data.itertuples(index=False), start=1):
        ws.append([i, r.fio, r.faculty, r.program, int(r.year_of_study), r.form, r.language,
                   round(getattr(r, f"{layer}_iros"), 2), round(getattr(r, f"{layer}_ssci"), 2),
                   *[int(getattr(r, f"{layer}_pts_{c.code}")) for c in CATEGORIES]])
    wb.save(path)


def _pivot_counts(asu: pd.DataFrame, year: int, day: dt.date) -> pd.DataFrame:
    """Сколько студентов имеют согласованные записи: всего по типу и по каждому статусу."""
    recs = asu[asu.year == year]
    recs = recs[state_at(recs, day) == APPROVED]
    total = recs.groupby("category").student_id.nunique().rename("total")
    by_status = recs.groupby(["category", "status"]).student_id.nunique().unstack(fill_value=0)
    return pd.concat([total, by_status], axis=1).fillna(0).astype(int)


def _fill_pivot(ws, profile: Profile, status_list, pivot: pd.DataFrame, first_row: int = 5, block: Block | None = None):
    for row, category in enumerate(categories(profile=profile, block=block), start=first_row):
        counts = pivot.loc[category.code] if category.code in pivot.index else {}
        ws.cell(row, 1, row - first_row + 1)
        ws.cell(row, 2, category.asu_title)
        ws.cell(row, 3, int(counts.get("total", 0)))
        for col, status in enumerate(status_list, start=4):
            ws.cell(row, col, int(counts.get(status.code, 0)))


def iros_pivot(path: Path, day: dt.date, pivot: pd.DataFrame):
    wb = _template(IROS_TEMPLATE)
    ws = wb.active
    ws["A1"] = STAMP.format(day)
    _fill_pivot(ws, Profile.IROS, statuses(Block.RESEARCH), pivot)
    wb.save(path)


def ssci_pivot(path: Path, day: dt.date, pivot: pd.DataFrame, block: Block):
    """Сводная по SSCI: в АСУ две таблицы – за разовые мероприятия (5 типов × 4 уровня) и в рамках постоянных
    университетских проектов (5 типов, один статус); шаблоны получены 09.11.2026."""
    wb = _template(SSCI_TEMPLATES[block][0])
    ws = wb.active
    ws["A1"] = STAMP.format(day)
    _fill_pivot(ws, Profile.SSCI, statuses(block), pivot, block=block)
    wb.save(path)
