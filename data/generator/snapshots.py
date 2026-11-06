"""Срезы: GPA, баллы по типам, iROS, SSCI и IGPA каждого студента на конец периода, истинные и по данным АСУ.

Достижения учитываются за учебный год (допущение до ответа научного руководителя, вопрос 10),
IGPA считается с годовым GPA (вопрос 11).
"""

from collections import defaultdict

import numpy as np
import pandas as pd

from igpa import CATEGORIES, FlagKind, Record, Rules, calculate

from .asu import APPROVED, DRAFT, PENDING, REJECTED, state_at
from .common import academic_year, on

CODES = [c.code for c in CATEGORIES]


def gpa_tables(courses: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """GPA семестра и учебного года, накопленный GPA на конец года."""
    c = courses.assign(cp=courses.credits * courses.points)
    sem = c.groupby(["student_id", "year", "semester"], as_index=False).agg(credits=("credits", "sum"), cp=("cp", "sum"))
    sem["gpa"] = sem.cp / sem.credits
    year = c.groupby(["student_id", "year"], as_index=False).agg(credits=("credits", "sum"), cp=("cp", "sum"))
    year["gpa"] = year.cp / year.credits
    cum = year.groupby("student_id")[["credits", "cp"]].cumsum()
    year["gpa_cum"] = cum.cp / cum.credits
    return sem.drop(columns="cp"), year.drop(columns="cp")


def snapshots(enrollment: pd.DataFrame, sem_gpa: pd.DataFrame, year_gpa: pd.DataFrame,
              layers: dict[str, pd.DataFrame], cfg: dict, rules: Rules, part: str = "year",
              years: list[int] | None = None) -> pd.DataFrame:
    """Срез на конец учебного года (part="year") или семестра ("fall", "spring").

    layers: {"true": истинные записи, "obs": записи АСУ}. Текущий незавершённый период считается на «сегодня»
    (partial=True); GPA для него ещё нет, поэтому IGPA не считается.
    """
    now = cfg["now"]
    current = academic_year(now)
    rows = enrollment if years is None else enrollment[enrollment.year.isin(years)]
    if part == "year":
        gpa = year_gpa.set_index(["student_id", "year"]).gpa.to_dict()
    else:
        semester = sem_gpa[sem_gpa.semester == (1 if part == "fall" else 2)]
        gpa = semester.set_index(["student_id", "year"]).gpa.to_dict()
    cum = year_gpa.set_index(["student_id", "year"]).gpa_cum.to_dict()

    out = []
    for year, group in rows.groupby("year"):
        day = on(year, cfg["asu"]["snapshots"]["fall_end" if part == "fall" else "year_end"])
        partial = day > now
        day = min(day, now)
        by_layer = {name: _records_by_student(recs, year, day, part) for name, recs in layers.items()}
        for row in group.itertuples(index=False):
            key = (row.student_id, year)
            g = gpa.get(key, np.nan)
            item = {"student_id": row.student_id, "year": year, "part": part, "date": day, "partial": partial,
                    "year_of_study": row.year_of_study, "gpa": g, "gpa_cum_prev": cum.get((row.student_id, year - 1), np.nan)}
            for name, grouped in by_layer.items():
                item.update(_score(name, grouped.get(row.student_id, []), g, rules))
            out.append(item)
    df = pd.DataFrame(out)
    df["date"] = pd.to_datetime(df.date)
    return df


def _records_by_student(recs: pd.DataFrame, year: int, day, part: str) -> dict[str, list]:
    """Записи учебного года, известные на дату day: (тип, статус, состояние в АСУ или None для истинных)."""
    recs = recs[recs.year == year]
    if part == "fall":
        recs = recs[recs.semester == 1]
    recs = recs[recs.event_date <= pd.Timestamp(day)]
    states = state_at(recs, day) if "decision" in recs else np.full(len(recs), APPROVED, dtype=object)
    grouped = defaultdict(list)
    for sid, cat, status, state in zip(recs.student_id, recs.category, recs.status, states):
        if state is not None:
            grouped[sid].append((cat, status, state))
    return grouped


def _score(layer: str, items: list, gpa: float, rules: Rules) -> dict:
    result = calculate([Record(c, s, state == APPROVED) for c, s, state in items],
                       0.0 if np.isnan(gpa) else gpa, rules)
    out = {f"{layer}_iros": result.iros, f"{layer}_ssci": result.ssci,
           f"{layer}_igpa": np.nan if np.isnan(gpa) else result.igpa, f"{layer}_n": len(items)}
    out.update({f"{layer}_pts_{code}": result.categories[code].points for code in CODES})
    if layer != "true":
        states = [state for *_, state in items]
        kinds = [f.kind for f in result.flags]
        out.update({
            f"{layer}_approved": states.count(APPROVED), f"{layer}_pending": states.count(PENDING),
            f"{layer}_rejected": states.count(REJECTED), f"{layer}_draft": states.count(DRAFT),
            f"{layer}_mapped": kinds.count(FlagKind.STATUS_MAPPED),
            f"{layer}_mismatch": kinds.count(FlagKind.STATUS_MISMATCH),
        })
    return out
