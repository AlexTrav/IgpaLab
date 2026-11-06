"""Панель «студент × учебный год»: признаки года t и цели года t+1 для одного набора правил и одного слоя данных.

Слой true – истина стенда (потолок качества), obs – то, что видно в АСУ (реалистичный случай).
Оценки (GPA, дисциплины) одинаковы для обоих слоёв: их даёт учебная часть, а не раздел IGPA.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from generator.asu import APPROVED, state_at
from generator.common import on
from igpa import CATEGORIES, CATEGORY_BY_CODE

RULES = ("default", "eduscore")
LAYERS = ("true", "obs")
CODES = [c.code for c in CATEGORIES]
BLOCK = {code: c.block.value for code, c in CATEGORY_BY_CODE.items()}
CATEGORICAL = ["level", "faculty", "form", "language"]
TABLES = ("students", "enrollment", "courses", "gpa_semester", "gpa_year", "records_true", "records_asu",
          "snapshots_year", "snapshots_year_eduscore")
TARGETS = ["igpa_next", "gpa_next", "iros_next", "ssci_next", "delta", "risk"]


def load(version_dir: Path) -> dict[str, pd.DataFrame]:
    return {name: pd.read_parquet(version_dir / f"{name}.parquet") for name in TABLES}


def grades(d: dict) -> pd.DataFrame:
    """Признаки из оценок за учебный год: GPA года, семестров, накопленный, FX и F, низкие баллы, несданные кредиты."""
    c = d["courses"]
    per = c.groupby(["student_id", "year"]).agg(
        fx_count=("letter", lambda s: int(s.isin(["FX", "F"]).sum())),
        min_score=("score", "min"),
        low_count=("score", lambda s: int((s < 65).sum())),
    ).reset_index()
    failed = c[c.score < 50].groupby(["student_id", "year"]).credits.sum().rename("failed_credits")
    sem = d["gpa_semester"].pivot_table(index=["student_id", "year"], columns="semester", values="gpa")
    sem.columns = ["gpa_fall", "gpa_spring"]
    year = d["gpa_year"].set_index(["student_id", "year"])[["gpa", "gpa_cum"]]
    out = year.join(sem).join(per.set_index(["student_id", "year"])).join(failed).reset_index()
    out["failed_credits"] = out.failed_credits.fillna(0)
    out["sem_trend"] = out.gpa_spring - out.gpa_fall
    return out


def _block_counts(records: pd.DataFrame) -> pd.DataFrame:
    counts = (records.assign(block=records.category.map(BLOCK))
              .pivot_table(index=["student_id", "year"], columns="block", values="category", aggfunc="count", fill_value=0))
    return counts.reindex(columns=["research", "one_time", "permanent"], fill_value=0).rename(columns=lambda b: f"n_{b}")


def _asu_on_year_end(d: dict) -> pd.DataFrame:
    """Записи АСУ каждого учебного года в состоянии на конец года (30 июня)."""
    asu = d["records_asu"]
    parts = []
    for year, recs in asu.groupby("year"):
        day = on(year, "06-30")
        recs = recs[recs.event_date <= pd.Timestamp(day)].copy()
        recs["state"] = state_at(recs, day)
        parts.append(recs[recs.state.notna()])
    return pd.concat(parts, ignore_index=True)


def _behaviour(d: dict) -> pd.DataFrame:
    """Поведение студента в АСУ за год: есть ли записи, как быстро вносит, доля отклонённых."""
    recs = _asu_on_year_end(d)
    recs["delay"] = (recs.entered_at - recs.event_date).dt.days
    g = recs.groupby(["student_id", "year"])
    out = pd.DataFrame({
        "asu_records": g.size(),
        "asu_delay": g.delay.mean(),
        "asu_rejected_share": g.state.apply(lambda s: (s == "Отклонено").mean()),
        "asu_pending_share": g.state.apply(lambda s: s.isin(["На согласовании", "Черновик"]).mean()),
    })
    approved = recs[recs.state == APPROVED]
    return out.join(_block_counts(approved), how="left").fillna({"n_research": 0, "n_one_time": 0, "n_permanent": 0})


def build(d: dict, rules: str = "default", layer: str = "true") -> tuple[pd.DataFrame, list[str]]:
    """Панель и список признаков. Строки – завершённые годы; цели заполнены, если студент учится и в году t+1."""
    snap = d["snapshots_year"] if rules == "default" else d[f"snapshots_year_{rules}"]
    snap = snap[~snap.partial]
    keep = {f"{layer}_iros": "iros", f"{layer}_ssci": "ssci", f"{layer}_igpa": "igpa",
            **{f"{layer}_pts_{c}": f"pts_{c}" for c in CODES}}
    p = snap[["student_id", "year", "year_of_study", *keep]].rename(columns=keep)
    p = p.merge(grades(d), on=["student_id", "year"], how="left")

    if layer == "true":
        counts = _block_counts(d["records_true"])
        p = p.merge(counts, on=["student_id", "year"], how="left")
        behaviour = []
    else:
        p = p.merge(_behaviour(d), on=["student_id", "year"], how="left")
        p["asu_records"] = p.asu_records.fillna(0)
        p["asu_has_records"] = (p.asu_records > 0).astype(int)
        behaviour = ["asu_records", "asu_has_records", "asu_delay", "asu_rejected_share", "asu_pending_share"]
    for col in ("n_research", "n_one_time", "n_permanent"):
        p[col] = p[col].fillna(0)

    lag_cols = ["gpa", "iros", "ssci", "igpa", "n_research", "n_one_time", "n_permanent"]
    prev = p[["student_id", "year", *lag_cols]].assign(year=p.year + 1)
    p = p.merge(prev.rename(columns={c: f"{c}_prev" for c in lag_cols}), on=["student_id", "year"], how="left")
    p["gpa_trend"] = p.gpa - p.gpa_prev
    p["igpa_trend"] = p.igpa - p.igpa_prev
    p["has_history"] = p.gpa_prev.notna().astype(int)

    st = d["students"][["student_id", *CATEGORICAL]]
    p = p.merge(st, on="student_id")
    p["master"] = (p.level != "bachelor").astype(int)

    nxt = p[["student_id", "year", "igpa", "gpa", "iros", "ssci"]].assign(year=p.year - 1)
    p = p.merge(nxt.rename(columns={c: f"{c}_next" for c in ("igpa", "gpa", "iros", "ssci")}),
                on=["student_id", "year"], how="left")
    p["delta"] = p.igpa_next - p.igpa
    p["risk"] = (p.delta <= -0.1).astype(float).where(p.delta.notna())
    p["active"] = ((p.n_research + p.n_one_time + p.n_permanent) > 0).astype(int)
    p["_rules"], p["_layer"] = rules, layer   # служебные: гибриду нужно знать правила и слой, в признаки не входят

    features = (["gpa", "gpa_fall", "gpa_spring", "sem_trend", "gpa_cum", "gpa_prev", "gpa_trend", "fx_count",
                 "min_score", "low_count", "failed_credits",
                 "iros", "ssci", "igpa", "iros_prev", "ssci_prev", "igpa_prev", "igpa_trend",
                 "n_research", "n_one_time", "n_permanent", "n_research_prev", "n_one_time_prev", "n_permanent_prev",
                 *[f"pts_{c}" for c in CODES], *behaviour,
                 "year_of_study", "master", "has_history", *CATEGORICAL])
    return p.sort_values(["year", "student_id"], ignore_index=True), features


def transitions(panel: pd.DataFrame) -> pd.DataFrame:
    """Только строки с известным годом t+1 – на них обучаем и проверяем."""
    return panel[panel.igpa_next.notna()].reset_index(drop=True)


def numeric(features: list[str]) -> list[str]:
    return [f for f in features if f not in CATEGORICAL]


def design(frame: pd.DataFrame, features: list[str], columns: list[str] | None = None) -> pd.DataFrame:
    """Числовая матрица для линейных моделей и леса: one-hot категорий, пропуски лагов – нулём и флагом has_history."""
    X = pd.get_dummies(frame[features], columns=[c for c in CATEGORICAL if c in features], dtype=float)
    X = X.fillna(0.0)
    if columns is not None:
        X = X.reindex(columns=columns, fill_value=0.0)
    return X




GROUPS = {
    "grades": ["gpa", "gpa_fall", "gpa_spring", "sem_trend", "gpa_cum", "fx_count", "min_score", "low_count",
               "failed_credits"],
    "grades_dynamics": ["gpa_prev", "gpa_trend"],
    "achievements": ["iros", "ssci", "igpa", *[f"pts_{c}" for c in CODES], "n_research", "n_one_time", "n_permanent"],
    "achievements_dynamics": ["iros_prev", "ssci_prev", "igpa_prev", "igpa_trend", "n_research_prev",
                              "n_one_time_prev", "n_permanent_prev"],
    "asu": ["asu_records", "asu_has_records", "asu_delay", "asu_rejected_share", "asu_pending_share"],
    "context": ["year_of_study", "master", "has_history", *CATEGORICAL],
}


def group_features(*names: str, without: tuple[str, ...] = ()) -> list[str]:
    """Признаки нескольких групп; without – исключить группы (для серии S3)."""
    keep = names or tuple(GROUPS)
    return [f for g in keep if g not in without for f in GROUPS[g]]
