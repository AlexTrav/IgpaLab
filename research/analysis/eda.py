"""Расчёты разведочного анализа синтетического датасета: всё, что нужно для решений по моделям и для статьи."""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from igpa import CATEGORY_BY_CODE

TABLES = ("students", "latent", "enrollment", "gpa_year", "gpa_semester", "courses", "records_true", "records_asu",
          "approvals", "records_asu_real", "snapshots_year", "snapshots_real", "snapshots_year_eduscore")
BLOCK = {code: c.block.value for code, c in CATEGORY_BY_CODE.items()}
RULES = ("default", "eduscore")


def load(version_dir: Path) -> dict[str, pd.DataFrame]:
    return {name: pd.read_parquet(version_dir / f"{name}.parquet") for name in TABLES}


def snapshot(d: dict, rules: str) -> pd.DataFrame:
    """Годовые срезы по набору правил, только завершённые годы."""
    snap = d["snapshots_year"] if rules == "default" else d[f"snapshots_year_{rules}"]
    return snap[~snap.partial].copy()


def year_panel(d: dict, rules: str = "default") -> pd.DataFrame:
    """Студент × учебный год: признаки года t и значения года t+1 (если студент учится и в следующем году)."""
    snap = snapshot(d, rules)
    rec = d["records_true"].assign(block=lambda r: r.category.map(BLOCK))
    counts = rec.pivot_table(index=["student_id", "year"], columns="block", values="record_id", aggfunc="count",
                             fill_value=0).rename(columns=lambda b: f"n_{b}").reset_index()
    p = (snap.merge(counts, on=["student_id", "year"], how="left")
         .merge(d["students"][["student_id", "level", "faculty"]], on="student_id"))
    for col in ("n_research", "n_one_time", "n_permanent"):
        p[col] = p[col].fillna(0).astype(int)
    p["master"] = (p.level != "bachelor").astype(int)
    prev = p[["student_id", "year", "gpa"]].assign(year=p.year + 1).rename(columns={"gpa": "gpa_prev"})
    p = p.merge(prev, on=["student_id", "year"], how="left")
    p["gpa_trend"] = p.gpa - p.gpa_prev
    p["obs_share"] = np.where(p.true_n > 0, p.obs_approved / p.true_n.where(p.true_n > 0), np.nan)
    nxt = p[["student_id", "year", "gpa", "true_iros", "true_ssci", "true_igpa", "obs_igpa"]].assign(year=p.year - 1)
    p = p.merge(nxt.rename(columns=lambda c: c if c in ("student_id", "year") else f"{c}_next"),
                on=["student_id", "year"], how="left")
    p["delta_true"] = p.true_igpa_next - p.true_igpa
    p["delta_obs"] = p.obs_igpa_next - p.obs_igpa
    p["risk_true"] = (p.delta_true <= -0.1).astype(float).where(p.delta_true.notna())
    p["risk_obs"] = (p.delta_obs <= -0.1).astype(float).where(p.delta_obs.notna())
    return p


def overview(d: dict) -> dict:
    p = year_panel(d)
    return {
        "students": len(d["students"]),
        "student_years": len(p),
        "transitions": int(p.delta_true.notna().sum()),
        "by_year": p.groupby("year").size().to_dict(),
        "transitions_by_year": p[p.delta_true.notna()].groupby("year").size().to_dict(),
    }


def components(d: dict) -> pd.DataFrame:
    """По каждому набору правил: распределения GPA, iROS, SSCI, IGPA и средние вклады в IGPA."""
    rows = []
    for rules in RULES:
        s = snapshot(d, rules)
        for layer in ("true", "obs"):
            iros, ssci, igpa = s[f"{layer}_iros"], s[f"{layer}_ssci"], s[f"{layer}_igpa"]
            rows.append({
                "rules": rules, "layer": layer, "n": len(s),
                "gpa_mean": s.gpa.mean(), "gpa_sd": s.gpa.std(),
                "iros_mean": iros.mean(), "iros_p90": iros.quantile(.9), "iros_max": iros.max(), "iros_zero": (iros == 0).mean(),
                "ssci_mean": ssci.mean(), "ssci_p90": ssci.quantile(.9), "ssci_max": ssci.max(), "ssci_zero": (ssci == 0).mean(),
                "igpa_mean": igpa.mean(), "igpa_sd": igpa.std(), "igpa_p10": igpa.quantile(.1), "igpa_p90": igpa.quantile(.9),
                "gpa_part": 0.5 * s.gpa.mean(), "iros_part": 1.4 * iros.mean(), "ssci_part": 0.6 * ssci.mean(),
                # доля дисперсии IGPA, которую не объясняет 0,5·GPA (с учётом ковариации)
                "achievement_share": 1 - np.corrcoef(s.gpa, igpa)[0, 1] ** 2,
            })
    return pd.DataFrame(rows)


def completeness(d: dict) -> dict:
    """Насколько АСУ отражает истину: студенто-годы по группам, смещение iROS, SSCI, IGPA, внесение по типам."""
    s = snapshot(d, "default")
    groups = np.select([s.true_n == 0, s.obs_approved == 0, s.obs_approved < s.true_n],
                       ["none", "hidden", "part"], "full")
    share = pd.Series(groups).value_counts(normalize=True).reindex(["none", "hidden", "part", "full"]).fillna(0)
    by_year = pd.crosstab(s.year, groups, normalize="index").reindex(columns=["none", "hidden", "part", "full"]).fillna(0)
    true, asu = d["records_true"], d["records_asu"]
    entered = asu[asu.gt_error != "duplicate"].true_record_id.unique()
    by_cat = true.assign(entered=true.record_id.isin(entered)).groupby("category").entered.mean()
    lat = d["latent"].set_index("student_id").rep
    s = s.assign(rep_q=pd.qcut(s.student_id.map(lat), 4, labels=["Q1", "Q2", "Q3", "Q4"]))
    with_true = s[s.true_n > 0]
    by_rep = (with_true.obs_approved / with_true.true_n).groupby(with_true.rep_q, observed=True).mean()
    return {
        "groups": share.to_dict(), "groups_by_year": by_year,
        "bias": {k: float((s[f"obs_{k}"] - s[f"true_{k}"]).mean()) for k in ("iros", "ssci", "igpa")},
        "corr": {k: float(np.corrcoef(s[f"obs_{k}"], s[f"true_{k}"])[0, 1]) for k in ("iros", "ssci", "igpa")},
        "entered_by_category": by_cat, "entered_by_rep": by_rep.to_dict(),
    }


def dynamics(d: dict) -> pd.DataFrame:
    """Устойчивость показателей год к году и изменения IGPA (основа для B0 и задачи B)."""
    rows = []
    for rules in RULES:
        p = year_panel(d, rules)
        t = p[p.delta_true.notna()]
        row = {"rules": rules, "n": len(t)}
        for k in ("gpa", "true_iros", "true_ssci", "true_igpa"):
            row[f"r_{k}"] = stats.pearsonr(t[k], t[f"{k}_next"])[0]
        row["r_obs_igpa"] = stats.pearsonr(t.obs_igpa, t.obs_igpa_next)[0]
        row.update(delta_mean=t.delta_true.mean(), delta_sd=t.delta_true.std(), b0_mae=t.delta_true.abs().mean(),
                   risk_true=t.risk_true.mean(), risk_obs=t.risk_obs.mean(),
                   risk_agree=(t.risk_true == t.risk_obs).mean())
        rows.append(row)
    return pd.DataFrame(rows)


FEATURES = ["gpa", "gpa_trend", "gpa_cum_prev", "true_iros", "true_ssci", "n_research", "n_one_time", "n_permanent",
            "year_of_study", "master", "obs_share"]


def associations(d: dict, rules: str = "default") -> pd.DataFrame:
    """Спирмен: признаки года t против IGPA t+1, изменения IGPA и риска снижения."""
    p = year_panel(d, rules)
    t = p[p.delta_true.notna()]
    rows = []
    for f in FEATURES:
        x = t[f]
        ok = x.notna()
        rows.append({"feature": f.replace("true_", ""), "n": int(ok.sum()),
                     "igpa_next": stats.spearmanr(x[ok], t.true_igpa_next[ok])[0],
                     "delta": stats.spearmanr(x[ok], t.delta_true[ok])[0],
                     "risk": stats.spearmanr(x[ok], t.risk_true[ok])[0]})
    return pd.DataFrame(rows)


def _ols_mae(train, test, cols, target):
    X = np.column_stack([np.ones(len(train))] + [train[c] for c in cols])
    beta = np.linalg.lstsq(X, train[target], rcond=None)[0]
    Xt = np.column_stack([np.ones(len(test))] + [test[c] for c in cols])
    pred = Xt @ beta
    resid = test[target] - pred
    return float(np.abs(resid).mean()), float(1 - (resid ** 2).sum() / ((test[target] - test[target].mean()) ** 2).sum())


def preview(d: dict) -> pd.DataFrame:
    """Предварительная проверка гипотезы H0 линейной моделью: обучение на переходах до 2024/25, проверка на последнем.

    Это ещё не эксперимент (нет подбора и ДИ), а ориентир: есть ли вообще сигнал в достижениях сверх GPA.
    """
    rows = []
    for rules in RULES:
        p = year_panel(d, rules)
        t = p[p.delta_true.notna()].copy()
        last = t.year.max()
        train, test = t[t.year < last], t[t.year == last]
        b0 = float((test.true_igpa_next - test.true_igpa).abs().mean())
        sets = {"B0: IGPA не меняется": None, "B1: только GPA": ["gpa"],
                "GPA и текущий IGPA": ["gpa", "true_igpa"],
                "GPA, IGPA и достижения": ["gpa", "true_igpa", "true_iros", "true_ssci", "n_research", "n_one_time",
                                           "n_permanent"]}
        for name, cols in sets.items():
            mae, r2 = (b0, np.nan) if cols is None else _ols_mae(train, test, cols, "true_igpa_next")
            rows.append({"rules": rules, "model": name, "mae": mae, "r2": r2, "n_test": len(test)})
    return pd.DataFrame(rows)


def saturation(d: dict) -> dict:
    """Как часто срабатывает предел «5 лучших в типе» и потолок 100 баллов – источник нелинейности."""
    rec = d["records_true"]
    per = rec.groupby(["student_id", "year", "category"]).size()
    over5 = per[per > 5]
    one_time = per[[BLOCK[c] != "permanent" for c in per.index.get_level_values("category")]]
    return {"student_year_categories": len(per), "over_5": len(over5), "over_5_share": len(over5) / len(per),
            "max_in_category": int(per.max()), "share_one_time_ge3": float((one_time >= 3).mean()),
            "student_years_affected": over5.reset_index()[["student_id", "year"]].drop_duplicates().shape[0]}


def approval(d: dict) -> dict:
    asu, ap = d["records_asu"], d["approvals"]
    delay = (asu.entered_at - asu.event_date).dt.days
    decided = asu[asu.decision.isin(["approved", "rejected"])]
    decision_days = (decided.decided_at - decided.entered_at).dt.days
    rejected_by_error = asu[asu.decision != "draft"].groupby(
        asu.gt_error.replace("", "без ошибки")).decision.apply(lambda s: (s == "rejected").mean())
    return {"entry_delay_median": float(delay.median()), "entry_delay_p90": float(delay.quantile(.9)),
            "decision_days_median": float(decision_days.median()), "decision_days_p90": float(decision_days.quantile(.9)),
            "rejected_by_error": rejected_by_error.to_dict(), "states_now": asu.state_now.value_counts(normalize=True).to_dict()}


def real_scenario(d: dict) -> pd.DataFrame:
    """Кто есть в АСУ на «сегодня» в двух сценариях, по группам студентов."""
    snap_main = d["snapshots_year"].query("partial")
    snap_real = d["snapshots_real"]
    st = d["students"].set_index("student_id").level

    def group(s):
        lvl = s.student_id.map(st)
        return np.where(lvl == "bachelor", "bachelor_" + s.year_of_study.astype(str), "master_" + s.year_of_study.astype(str))

    def share(s, col):
        return (s[col] > 0).groupby(group(s)).mean()

    main = share(snap_main, "obs_n")
    real = share(snap_real, "obs_n")
    counts = pd.Series(group(snap_real)).value_counts()
    return pd.DataFrame({"main": main, "real": real, "students": counts}).fillna(0).sort_index()


def recovery(d: dict) -> pd.DataFrame:
    """Видны ли в данных заложенные эффекты: научная активность у сильных и перегрузка SSCI против GPA следующего семестра.

    Сырые различия средних, без поправок: проверка того, что сигнал есть и модели есть что искать.
    """
    sem = d["gpa_semester"].sort_values(["student_id", "year", "semester"])
    sem["order"] = sem.year * 2 + sem.semester
    sem["gpa_next"] = sem.groupby("student_id").gpa.shift(-1)
    rec = d["records_true"].assign(block=lambda r: r.category.map(BLOCK))
    cnt = rec[rec.block != "permanent"].pivot_table(index=["student_id", "year", "semester"], columns="block",
                                                    values="record_id", aggfunc="count", fill_value=0).reset_index()
    s = sem.merge(cnt, on=["student_id", "year", "semester"], how="left").fillna({"research": 0, "one_time": 0})
    s = s.merge(d["latent"][["student_id", "a"]], on="student_id").dropna(subset=["gpa_next"])
    s["change"] = s.gpa_next - s.gpa
    strong = s[s.a > 0.5]
    rows = [
        {"effect": "research_to_gpa", "group": "a > 0,5, научных ≥ 1", "n": int((strong.research >= 1).sum()),
         "change": strong[strong.research >= 1].change.mean()},
        {"effect": "research_to_gpa", "group": "a > 0,5, научных 0", "n": int((strong.research == 0).sum()),
         "change": strong[strong.research == 0].change.mean()},
        {"effect": "social_load_to_gpa", "group": "разовых SSCI > 3", "n": int((s.one_time > 3).sum()),
         "change": s[s.one_time > 3].change.mean()},
        {"effect": "social_load_to_gpa", "group": "разовых SSCI ≤ 3", "n": int((s.one_time <= 3).sum()),
         "change": s[s.one_time <= 3].change.mean()},
    ]
    return pd.DataFrame(rows)
