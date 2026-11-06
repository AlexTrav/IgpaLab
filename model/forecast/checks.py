"""Доработки после шага 8: проверки, которых не было в основных сериях.

light – облегчённые модели сайта (ручной ввод) по полному протоколу: точность, ранжирование риска, честность
коридоров «10–90%» (доля реальных исходов внутри) и калибровка вероятности риска.
"""

import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

from generator.common import load_config
from generator.snapshots import gpa_tables, snapshots
from igpa import load_rules

from . import hybrid
from . import protocol as P
from .export import CNT, LIGHT, RULES3, _with_counts
from .features import build, transitions
from .models import CatBoostModel


def log(msg):
    print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)


def add_percentile(d: dict):
    if "snapshots_year_percentile" not in d:
        sem, year = gpa_tables(d["courses"])
        d["snapshots_year_percentile"] = snapshots(d["enrollment"], sem, year,
                                                   {"true": d["records_true"], "obs": d["records_asu"]},
                                                   load_config(), load_rules("percentile"))


class LightHybrid(hybrid.HybridModel):
    """Гибрид на признаках ручного ввода; отдаёт и розыгрыши, чтобы проверить коридор."""

    def fit(self, train, features):
        return super().fit(train, [f for f in LIGHT if f not in CNT])

    def band(self, test, q=(0.1, 0.9)):
        sims = self._simulate(test)
        return np.quantile(sims, q[0], axis=1), np.quantile(sims, q[1], axis=1)


def _calibration_gap(y, p, bins=10):
    q = pd.qcut(pd.Series(p).rank(method="first"), bins, labels=False)
    g = pd.DataFrame({"p": p, "y": y}).groupby(q).mean()
    return float((g.p - g.y).abs().mean())


def light(d: dict, out: Path):
    add_percentile(d)
    hybrid.prepare(d)
    rows = []
    for rules in RULES3:
        panel, features = build(d, rules, "obs")
        data = transitions(_with_counts(panel))
        for year, train, test in P.folds(data):
            y, risk = test.igpa_next.to_numpy(), test.risk.astype(int).to_numpy()
            rows.append({"rules": rules, "year": year, "model": "B0", **P.regression(y, test.igpa)})
            cat = CatBoostModel(use=LIGHT).fit(train, features + CNT)
            fit_part, val = P.inner_split(train)
            probe = CatBoostModel(use=LIGHT).fit(fit_part, features + CNT)
            resid = val.igpa_next.to_numpy() - probe.predict(val)
            pred, score = cat.predict(test), cat.risk(test)
            lo, hi = pred + np.quantile(resid, 0.1), pred + np.quantile(resid, 0.9)
            rows.append(_row(rules, year, "CatBoost облегчённый", y, pred, risk, score, lo, hi))
            hyb = LightHybrid().fit(train, features)
            pred, score = hyb.predict(test), hyb.risk(test)
            lo, hi = hyb.band(test)
            rows.append(_row(rules, year, "Hybrid облегчённый", y, pred, risk, score, lo, hi))
            log(f"{rules} проверка {year} готова")
    res = pd.DataFrame(rows)
    out.mkdir(parents=True, exist_ok=True)
    res.to_csv(out / "light.csv", index=False)
    return res


def _row(rules, year, model, y, pred, risk, score, lo, hi):
    return {"rules": rules, "year": year, "model": model, **P.regression(y, pred),
            "roc_auc": roc_auc_score(risk, score), "brier": brier_score_loss(risk, score),
            "calibration_gap": _calibration_gap(risk, score), "risk_mean_pred": float(np.mean(score)),
            "risk_observed": float(np.mean(risk)), "coverage_80": float(np.mean((y >= lo) & (y <= hi))),
            "band_width": float(np.mean(hi - lo))}


# пункт 2: кривая обучения

SIZES = (250, 500, 1000, 2500, 5000)
TEST_STUDENTS = 1000


def learning(d: dict, out: Path):
    """Качество от числа студентов в обучении: проверка на 1000 студентах, которых нет в обучении (переходы 2024),
    обучение на переходах до 2024 из случайной подвыборки остальных; малые объёмы повторяются трижды."""
    from .models import RidgeModel
    rng = np.random.default_rng(0)
    rows = []
    for rules in ("default", "eduscore"):
        panel, features = build(d, rules, "obs")
        data = transitions(panel)
        final = data[data.year == P.FINAL]
        test_ids = set(rng.choice(final.student_id.unique(), TEST_STUDENTS, replace=False))
        test = final[final.student_id.isin(test_ids)]
        pool = data[(data.year < P.FINAL) & ~data.student_id.isin(test_ids)]
        students = pool.student_id.unique()
        sizes = [s for s in SIZES if s < len(students)] + [len(students)]
        y, risk = test.igpa_next.to_numpy(), test.risk.astype(int).to_numpy()
        rows.append({"rules": rules, "students": 0, "rep": 0, "model": "B0", "train_rows": 0,
                     **P.regression(y, test.igpa)})
        for n in sizes:
            for rep in range(3 if n <= 1000 else 1):
                ids = rng.choice(students, n, replace=False)
                train = pool[pool.student_id.isin(ids)]
                for name, cls in (("Ridge", RidgeModel), ("CatBoost", CatBoostModel)):
                    m = cls().fit(train, features)
                    rows.append({"rules": rules, "students": n, "rep": rep, "model": name, "train_rows": len(train),
                                 **P.regression(y, m.predict(test)), "roc_auc": roc_auc_score(risk, m.risk(test))})
                log(f"{rules}: {n} студентов, повтор {rep} готов")
    res = pd.DataFrame(rows)
    out.mkdir(parents=True, exist_ok=True)
    res.to_csv(out / "learning.csv", index=False)
    return res


# пункт 3: сценарии реальных данных

def _template_features():
    """Что есть в выгрузке IGPA (общие баллы и баллы по 16 типам) плюс GPA года и прошлые выгрузки."""
    from igpa import CATEGORIES
    return ["gpa", "gpa_prev", "gpa_trend", "has_history", "year_of_study", "master", "level", "faculty", "form",
            "language", "iros", "ssci", "igpa", "iros_prev", "ssci_prev", "igpa_prev", "igpa_trend",
            *[f"pts_{c.code}" for c in CATEGORIES]]


def scenarios(d: dict, out: Path):
    """Сценарий B: только колонки выгрузки IGPA (баллы по 16 типам, общий балл) и GPA года, без записей, дат и
    согласований. Сценарий «малые данные»: только магистранты; вся история против одного года истории."""
    from .models import RidgeModel
    template = _template_features()
    rows = []
    for rules in ("default", "eduscore"):
        panel, features = build(d, rules, "obs")
        data = transitions(panel)
        train, test = data[data.year < P.FINAL], data[data.year == P.FINAL]
        y, risk = test.igpa_next.to_numpy(), test.risk.astype(int).to_numpy()
        rows.append({"rules": rules, "scenario": "все данные", "model": "B0", "n_train": len(train), "n_test": len(test),
                     **P.regression(y, test.igpa)})
        for scenario, use in (("все данные", None), ("только выгрузка АСУ и GPA", template)):
            for name, cls in (("Ridge", RidgeModel), ("CatBoost", CatBoostModel)):
                m = cls(use=use).fit(train, features)
                rows.append({"rules": rules, "scenario": scenario, "model": name, "n_train": len(train),
                             "n_test": len(test), **P.regression(y, m.predict(test)),
                             "roc_auc": roc_auc_score(risk, m.risk(test))})
        masters = data[data.level != "bachelor"]
        mtest = masters[masters.year == P.FINAL]
        my, mrisk = mtest.igpa_next.to_numpy(), mtest.risk.astype(int).to_numpy()
        rows.append({"rules": rules, "scenario": "магистранты", "model": "B0", "n_test": len(mtest),
                     **P.regression(my, mtest.igpa)})
        for scenario, train_m in (("магистранты, вся история", masters[masters.year < P.FINAL]),
                                  ("магистранты, один год истории", masters[masters.year == P.FINAL - 1])):
            for name, cls in (("Ridge", RidgeModel), ("CatBoost", CatBoostModel)):
                m = cls().fit(train_m, features)
                rows.append({"rules": rules, "scenario": scenario, "model": name, "n_train": len(train_m),
                             "n_test": len(mtest), **P.regression(my, m.predict(mtest)),
                             "roc_auc": roc_auc_score(mrisk, m.risk(mtest))})
        log(f"{rules}: сценарии готовы")
    res = pd.DataFrame(rows)
    out.mkdir(parents=True, exist_ok=True)
    res.to_csv(out / "scenarios.csv", index=False)
    return res


# пункт 4: семестровый горизонт

def semester(d: dict, out: Path):
    """IGPA следующего семестра: срезы на конец осени и весны (достижения копятся внутри учебного года, GPA семестра).

    Наивные прогнозы: «не изменится» и сезонный «как в том же семестре год назад» (осенью портфель года начинается
    заново, поэтому простое «не изменится» здесь слабое).
    """
    from igpa import CATEGORIES
    from .models import RidgeModel
    sem = pd.read_parquet(Path("/repo/data/synthetic") / "v1" / "snapshots_semester.parquet")
    sem = sem[~sem.partial]
    st = d["students"][["student_id", "level", "faculty", "form", "language"]]
    rows = []
    for layer in ("true", "obs"):
        cols = {f"{layer}_iros": "iros", f"{layer}_ssci": "ssci", f"{layer}_igpa": "igpa",
                **{f"{layer}_pts_{c.code}": f"pts_{c.code}" for c in CATEGORIES}}
        p = sem[["student_id", "year", "part", "year_of_study", "gpa", *cols]].rename(columns=cols)
        p["t"] = p.year * 2 + (p.part == "spring").astype(int)
        p["spring"] = (p.part == "spring").astype(int)
        for lag, name in ((1, "prev"), (2, "lastyear")):
            prev = p[["student_id", "t", "gpa", "igpa", "iros", "ssci"]].assign(t=p.t + lag)
            p = p.merge(prev.rename(columns={c: f"{c}_{name}" for c in ("gpa", "igpa", "iros", "ssci")}),
                        on=["student_id", "t"], how="left")
        p["gpa_trend"] = p.gpa - p.gpa_prev
        p["igpa_trend"] = p.igpa - p.igpa_prev
        nxt = p[["student_id", "t", "igpa", "igpa_lastyear"]].assign(t=p.t - 1).rename(
            columns={"igpa": "igpa_next", "igpa_lastyear": "seasonal"})
        p = p.merge(nxt, on=["student_id", "t"], how="left").merge(st, on="student_id")
        p["master"] = (p.level != "bachelor").astype(int)
        p = p[p.igpa_next.notna()].reset_index(drop=True)
        p["delta"] = p.igpa_next - p.igpa
        p["risk"] = (p.delta <= -0.1).astype(float)
        p["year"] = p.t // 2
        features = ["gpa", "gpa_prev", "gpa_trend", "gpa_lastyear", "iros", "ssci", "igpa", "igpa_prev", "igpa_trend",
                    "igpa_lastyear", "iros_lastyear", "ssci_lastyear", "spring", "year_of_study", "master", "level",
                    "faculty", "form", "language", *[f"pts_{c.code}" for c in CATEGORIES]]
        train, test = p[p.year < P.FINAL], p[p.year == P.FINAL]
        y, risk = test.igpa_next.to_numpy(), test.risk.astype(int).to_numpy()
        seasonal = test.seasonal.fillna(test.igpa).to_numpy()
        for part in ("all", "fall", "spring"):
            mask = np.ones(len(test), bool) if part == "all" else (test.spring == (part == "spring")).to_numpy()
            rows.append({"layer": layer, "start": part, "model": "B0 не изменится", **P.regression(y[mask], test.igpa[mask])})
            rows.append({"layer": layer, "start": part, "model": "B0 сезонный", **P.regression(y[mask], seasonal[mask])})
        for name, cls in (("Ridge", RidgeModel), ("CatBoost", CatBoostModel)):
            m = cls().fit(train, features)
            pred, score = m.predict(test), m.risk(test)
            for part in ("all", "fall", "spring"):
                mask = np.ones(len(test), bool) if part == "all" else (test.spring == (part == "spring")).to_numpy()
                rows.append({"layer": layer, "start": part, "model": name, **P.regression(y[mask], pred[mask]),
                             "roc_auc": roc_auc_score(risk[mask], score[mask])})
        log(f"семестры {layer}: готово")
    res = pd.DataFrame(rows)
    out.mkdir(parents=True, exist_ok=True)
    res.to_csv(out / "semester.csv", index=False)
    return res


# пункт 5: открытые данные (серия S5)

def open_uci(d: dict, out: Path):
    """UCI Student Performance (Cortez, Silva 2008): прогноз итоговой оценки G3 по оценкам G1, G2 и прочему.

    Тот же вопрос, что в серии S1 на стенде: дают ли внеучебная активность и социальные признаки прирост сверх
    оценок. Пол и возраст не используются. Перекрёстная проверка 5 × 3 (времени в наборе нет).
    """
    from catboost import CatBoostRegressor
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import RidgeCV
    from sklearn.model_selection import RepeatedKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    folder = Path("/repo/data/open/uci")
    grades = ["G1", "G2", "failures", "absences", "studytime"]
    activity = ["activities", "goout", "freetime", "higher", "romantic", "internet", "schoolsup", "famsup", "paid",
                "famrel", "Dalc", "Walc", "health", "traveltime"]
    rows = []
    for subject, name in (("mat", "математика"), ("por", "португальский")):
        df = pd.read_csv(folder / f"student-{subject}.csv", sep=";")
        y = df.G3.to_numpy(float)
        for setname, cols in (("оценки", grades), ("оценки и активность", grades + activity)):
            X = pd.get_dummies(df[cols], drop_first=True, dtype=float)
            errs = {"B0: G3 = G2": [], "Ridge": [], "RF": [], "CatBoost": []}
            for tr, te in RepeatedKFold(n_splits=5, n_repeats=3, random_state=0).split(X):
                errs["B0: G3 = G2"].append(np.abs(y[te] - df.G2.to_numpy(float)[te]).mean())
                models = {"Ridge": make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 12))),
                          "RF": RandomForestRegressor(500, min_samples_leaf=5, n_jobs=-1, random_state=0),
                          "CatBoost": CatBoostRegressor(depth=4, iterations=600, learning_rate=0.03, verbose=False,
                                                        random_seed=0, thread_count=-1, allow_writing_files=False)}
                for mname, m in models.items():
                    m.fit(X.iloc[tr], y[tr])
                    errs[mname].append(np.abs(y[te] - m.predict(X.iloc[te])).mean())
            for mname, e in errs.items():
                rows.append({"subject": name, "n": len(df), "features": setname, "model": mname,
                             "mae": float(np.mean(e)), "mae_sd": float(np.std(e))})
        log(f"UCI {name}: готово")
    res = pd.DataFrame(rows)
    out.mkdir(parents=True, exist_ok=True)
    res.to_csv(out / "open_uci.csv", index=False)
    return res
