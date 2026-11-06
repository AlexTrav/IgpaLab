"""Что попадает в АСУ: внесение записей студентами, ошибки ввода и согласование по этапам (Положение, п. 6.3 и 6.4)."""

import datetime as dt

import numpy as np
import pandas as pd

from igpa import CATEGORY_BY_CODE, Block, statuses

from .common import academic_year, sigmoid

LEVEL_INDEX = {s.code: i for block in (Block.RESEARCH, Block.ONE_TIME) for i, s in enumerate(statuses(block))}
LEVEL_INDEX["SSCI_PERMANENT"] = 1
DRAFT, APPROVED, REJECTED, PENDING = "Черновик", "Подтверждено", "Отклонено", "На согласовании"


def observe(records: pd.DataFrame, students: pd.DataFrame, enrollment: pd.DataFrame, latent: pd.DataFrame,
            cfg: dict, rng: np.random.Generator, launch: dt.date, shift: float = 0.0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Записи АСУ и история согласования при запуске раздела IGPA в дату launch; shift сдвигает logit внесения."""
    a = cfg["asu"]
    now, start = np.datetime64(cfg["now"], "D"), np.datetime64(launch, "D")
    rep = records.student_id.map(latent.set_index("student_id").rep).to_numpy()
    level = records.student_id.map(students.set_index("student_id").level).to_numpy()
    senior = (level == "master_research") & (records.year_of_study.to_numpy() >= 2)
    event = records.event_date.to_numpy().astype("datetime64[D]")

    # после запуска вносят по ходу; прошлое – задним числом и только те, кто учится на момент запуска
    after = event >= start
    years_ago = (start - event).astype(int) / 365
    enter, retro = a["enter"], a["retro"]
    logit = (shift + np.where(after, enter["base"], retro["base"] + retro["years_ago"] * years_ago) + enter["rep"] * rep
             + enter["level"] * records.status.map(LEVEL_INDEX).to_numpy() + enter["senior_master"] * senior)
    on_launch = set(enrollment.loc[enrollment.year == academic_year(launch), "student_id"])
    eligible = after | records.student_id.isin(on_launch).to_numpy()
    entered = eligible & (rng.random(len(records)) < sigmoid(logit))
    delay = np.ceil(rng.exponential(np.where(after, a["delay_days"], a["retro_days"]))).astype(int)
    entered_at = np.where(after, event, start) + delay.astype("timedelta64[D]")
    keep = entered & (entered_at <= now)

    asu = records.loc[keep, ["record_id", "student_id", "year", "semester", "year_of_study", "category", "status",
                             "title", "event_date"]].rename(columns={"record_id": "true_record_id"})
    asu["entered_at"] = entered_at[keep]
    asu = _input_errors(asu.reset_index(drop=True), a, rng, now)
    asu.insert(0, "record_id", [f"A{i:07d}" for i in range(1, len(asu) + 1)])
    asu["file_attached"] = rng.random(len(asu)) < a["file_p"]
    approvals = _approve(asu, a, rng, now)
    asu["state_now"] = state_at(asu, now)
    return asu, approvals


def _input_errors(asu: pd.DataFrame, a: dict, rng, now) -> pd.DataFrame:
    """Ошибки ввода: похожий тип, статус «чужой» карты из общего списка, повторное внесение."""
    k = len(asu)
    category, status = asu.category.to_numpy(dtype=object), asu.status.to_numpy(dtype=object)
    error = np.full(k, "", dtype=object)
    p = a["errors"]

    swap = a["wrong_category"]
    wrong = (rng.random(k) < p["wrong_category"]) & np.isin(category, list(swap))
    category[wrong] = [swap[c] for c in category[wrong]]
    error[wrong] = "wrong_category"

    permanent = np.array([CATEGORY_BY_CODE[c].block is Block.PERMANENT for c in category], dtype=bool)
    foreign = rng.random(k) < np.where(permanent, p["foreign_status_permanent"], p["foreign_status"])
    status[foreign] = [a["foreign_status"][s] for s in status[foreign]]
    error[foreign] = np.where(error[foreign] == "", "foreign_status", error[foreign] + ",foreign_status")
    asu = asu.assign(category=category, status=status, gt_error=error)

    duplicate = asu[rng.random(k) < p["duplicate"]].copy()
    duplicate["entered_at"] += rng.integers(1, 11, len(duplicate)).astype("timedelta64[D]")
    duplicate["gt_error"] = "duplicate"
    asu = pd.concat([asu, duplicate[duplicate.entered_at <= now]], ignore_index=True)
    return asu.sort_values(["entered_at", "student_id"], kind="stable").reset_index(drop=True)


def _approve(asu: pd.DataFrame, a: dict, rng, now) -> pd.DataFrame:
    """Согласование по этапам; в истории только решения, принятые до «сегодня». Дописывает в asu итог и его дату."""
    n = len(asu)
    profile = np.array([CATEGORY_BY_CODE[c].profile.value for c in asu.category])
    stages = {p: np.array(names, dtype=object) for p, names in a["stages"].items()}
    n_stages = np.where(profile == "IROS", len(stages["IROS"]), len(stages["SSCI"]))
    draft = rng.random(n) < a["draft_p"]
    error = asu.gt_error.to_numpy()
    reject = a["reject"]

    t = asu.entered_at.to_numpy().astype("datetime64[D]") + rng.integers(0, 3, n).astype("timedelta64[D]")
    decision = np.where(draft, "draft", "pending").astype(object)
    rows = []
    for j in range(n_stages.max()):
        act = (decision == "pending") & (j < n_stages)
        if not act.any():
            break
        days = np.ceil(rng.exponential(a["stage_days"]["first" if j == 0 else "other"], n)).astype(int)
        t_j = t + days.astype("timedelta64[D]")
        if j == 0:
            p = np.select([error == "duplicate", error != ""], [reject["duplicate"], reject["error"]], reject["first"])
        else:
            p = np.full(n, reject["other"])
        rejected = act & (rng.random(n) < p)
        names = np.where(profile == "IROS", stages["IROS"][min(j, len(stages["IROS"]) - 1)],
                         stages["SSCI"][min(j, len(stages["SSCI"]) - 1)])
        rows.append(pd.DataFrame({
            "record_id": asu.record_id.to_numpy()[act], "stage": j + 1, "stage_name": names[act],
            "decided_at": t_j[act], "decision": np.where(rejected[act], REJECTED, APPROVED),
        }))
        t = np.where(act, t_j, t)
        decision[rejected] = "rejected"
        decision[act & ~rejected & (j + 1 == n_stages)] = "approved"

    asu["draft"] = draft
    asu["decision"] = decision
    asu["decided_at"] = np.where(draft, np.datetime64("NaT"), t).astype("datetime64[D]")
    approvals = pd.concat(rows, ignore_index=True)
    approvals = approvals[approvals.decided_at <= now]
    return approvals.sort_values(["record_id", "stage"]).reset_index(drop=True)


def state_at(asu: pd.DataFrame, day) -> np.ndarray:
    """Статус записи в АСУ на дату day; None – запись ещё не внесена."""
    day = np.datetime64(day, "D")
    decided = asu.decided_at.to_numpy().astype("datetime64[D]") <= day
    decision = asu.decision.to_numpy()
    state = np.full(len(asu), PENDING, dtype=object)
    state[decided & (decision == "approved")] = APPROVED
    state[decided & (decision == "rejected")] = REJECTED
    state[asu.draft.to_numpy()] = DRAFT
    state[asu.entered_at.to_numpy().astype("datetime64[D]") > day] = None
    return state
