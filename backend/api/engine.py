"""Расчёты API на сохранённых артефактах (model/artifacts/<версия>): IGPA, прогноз, объяснение, советы, данные стенда."""

import json
import os
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, CatBoostRegressor, Pool
from sklearn.neighbors import NearestNeighbors

from igpa import CATEGORIES, CATEGORY_BY_CODE, STATUS_BY_CODE, Block, Record, calculate, igpa_parts, load_rules, statuses

from . import texts as T

ARTIFACTS = Path(os.environ.get("ARTIFACTS", "/app/artifacts"))
RULES = ("default", "eduscore", "percentile")
CODES = [c.code for c in CATEGORIES]
LEVEL = {s.code: i for b in (Block.RESEARCH, Block.ONE_TIME) for i, s in enumerate(statuses(b))}
LEVEL["SSCI_PERMANENT"] = 0
SAMPLES = 300
SEED = 20261107


class Engine:
    def __init__(self, folder: Path = ARTIFACTS):
        self.folder = folder
        self.meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
        self.rules = {name: load_rules(name) for name in RULES}
        self.light = {r: self._pair(f"light_{r}") for r in RULES}
        self.full = {r: self._pair(f"full_{r}") for r in RULES}
        h = self.meta["hybrid"]
        self.h_gpa = CatBoostRegressor().load_model(str(folder / "hybrid_gpa.cbm"))
        self.h_rates = {c: CatBoostRegressor().load_model(str(folder / f"hybrid_rate_{c}.cbm")) for c in h["rates"]}
        self.h_levels = {c: pd.Series(v) for c, v in h["global_levels"].items()}
        self.h_residuals = np.array(h["gpa_residuals"])
        feas = np.load(folder / "feasibility.npz")
        fmeta = json.loads((folder / "feasibility.json").read_text(encoding="utf-8"))
        self.actions = [tuple(a) for a in fmeta["actions"]]
        self.profile_cols, self.k, self.smoothing = fmeta["profile"], fmeta["neighbours"], fmeta["smoothing"]
        self.f_mean, self.f_scale, self.f_hit, self.f_prior = feas["mean"], feas["scale"], feas["hit"], feas["prior"]
        self.nn = NearestNeighbors(n_neighbors=self.k).fit((feas["profile"] - self.f_mean) / self.f_scale)
        self.students = pd.read_parquet(folder / "stand_students.parquet")
        self.history = pd.read_parquet(folder / "stand_history.parquet")
        self.enrollment = pd.read_parquet(folder / "stand_enrollment.parquet")
        self.records = pd.read_parquet(folder / "stand_records.parquet")
        self.backtest = pd.read_parquet(folder / "stand_backtest.parquet")
        self.forecast = {r: pd.read_parquet(folder / f"stand_forecast_{r}.parquet") for r in RULES}
        self.research = json.loads((folder / "research.json").read_text(encoding="utf-8"))
        self._components = {}

    def _pair(self, name):
        reg = CatBoostRegressor().load_model(str(self.folder / f"{name}_delta.cbm"))
        clf = CatBoostClassifier().load_model(str(self.folder / f"{name}_risk.cbm"))
        return reg, clf

    # IGPA по калькулятору

    def components(self, items: tuple, rules: str) -> tuple[float, float]:
        key = (rules, items)
        if key not in self._components:
            r = calculate([Record(c, s) for c, s in items], 0.0, self.rules[rules])
            self._components[key] = (r.iros, r.ssci)
        return self._components[key]

    def igpa(self, gpa: float, items, rules: str) -> float:
        return sum(igpa_parts(min(4.0, gpa), *self.components(tuple(sorted(items)), rules), self.rules[rules]))

    def calc(self, gpa: float, items: list[tuple], rules: str, lang: str) -> dict:
        r = calculate([Record(c, s) for c, s in items], gpa, self.rules[rules])
        return {
            "rules": rules, "rules_name": T.RULES[rules][lang], "igpa": r.igpa, "gpa": gpa, "iros": r.iros,
            "ssci": r.ssci, "gpa_part": r.gpa_part, "iros_part": r.iros_part, "ssci_part": r.ssci_part,
            "categories": [{"code": c, "name": T.category_name(c, lang), "points": s.points, "counted": s.counted,
                            "contribution": s.contribution, "profile": CATEGORY_BY_CODE[c].profile.value}
                           for c, s in r.categories.items() if s.counted or s.points],
            "flags": [{"index": f.index, "kind": f.kind.value} for f in r.flags],
        }

    def quick(self, gpa: float, iros: float, ssci: float, lang: str) -> list[dict]:
        out = []
        for name in RULES:
            parts = igpa_parts(gpa, iros, ssci, self.rules[name])
            out.append({"rules": name, "rules_name": T.RULES[name][lang], "igpa": sum(parts),
                        "gpa_part": parts[0], "iros_part": parts[1], "ssci_part": parts[2]})
        return out

    # «Мой портфель»

    def light_row(self, inp: dict, items: list[tuple], rules: str) -> pd.DataFrame:
        """Признаки облегчённой модели из ручного ввода (тот же смысл, что при обучении на слое АСУ)."""
        r = calculate([Record(c, s) for c, s in items], inp["gpa"], self.rules[rules])
        blocks = {"research": 0, "one_time": 0, "permanent": 0}
        counts = dict.fromkeys(CODES, 0)
        for c, _ in items:
            counts[c] += 1
            blocks[CATEGORY_BY_CODE[c].block.value] += 1
        prev = inp.get("gpa_prev")
        row = {"gpa": inp["gpa"], "gpa_prev": np.nan if prev is None else prev,
               "gpa_trend": np.nan if prev is None else inp["gpa"] - prev, "has_history": int(prev is not None),
               "year_of_study": inp["year_of_study"], "master": int(inp["level"] != "bachelor"), "level": inp["level"],
               "n_research": blocks["research"], "n_one_time": blocks["one_time"], "n_permanent": blocks["permanent"],
               "iros": r.iros, "ssci": r.ssci, "igpa": r.igpa, **{f"cnt_{c}": counts[c] for c in CODES}}
        return pd.DataFrame([row])

    @staticmethod
    def _X(frame: pd.DataFrame, features: list[str], cats: list[str]) -> pd.DataFrame:
        X = frame[features].copy()
        for c in cats:
            X[c] = X[c].astype(str)
        return X

    def hybrid(self, inp: dict, items: list[tuple], rules: str) -> dict:
        """IGPA-Hybrid: розыгрыши GPA и записей следующего года, IGPA каждого – калькулятором по правилам."""
        h = self.meta["hybrid"]
        frame = self.light_row(inp, items, "default")
        X = self._X(frame, h["features"], h["cats"])
        rng = np.random.default_rng(SEED)
        gpa = np.clip(inp["gpa"] + self.h_gpa.predict(X)[0] + rng.choice(self.h_residuals, SAMPLES), 0, 4)
        own = pd.Series([s for _, s in items]).groupby([c for c, _ in items]).value_counts() if items else None
        draws = []
        for code in CODES:
            model = self.h_rates.get(code)
            rate = 0.0 if model is None else float(model.predict(X, prediction_type="Exponent")[0])
            n = rng.poisson(rate, SAMPLES)
            if n.max() == 0:
                draws.append(None)
                continue
            probs = self.h_levels[code] * h["prior"]
            if own is not None and code in own.index.get_level_values(0):
                probs = probs.add(own[code], fill_value=0)
            probs = probs / probs.sum()
            draws.append((n, rng.choice(probs.index.to_numpy(), (SAMPLES, n.max()), p=probs.to_numpy())))
        igpa, iros, ssci = np.empty(SAMPLES), np.empty(SAMPLES), np.empty(SAMPLES)
        for s in range(SAMPLES):
            rec = tuple(sorted((CODES[j], st) for j, d in enumerate(draws) if d is not None for st in d[1][s, :d[0][s]]))
            iros[s], ssci[s] = self.components(rec, rules)
            igpa[s] = sum(igpa_parts(gpa[s], iros[s], ssci[s], self.rules[rules]))
        now = frame.igpa.iloc[0] if rules == "default" else self.igpa(inp["gpa"], items, rules)
        return {"mean": float(igpa.mean()), "p10": float(np.quantile(igpa, 0.1)), "p90": float(np.quantile(igpa, 0.9)),
                "risk": float((igpa <= now - 0.1).mean()), "gpa": float(gpa.mean()), "iros": float(iros.mean()),
                "ssci": float(ssci.mean())}

    def explain(self, frame: pd.DataFrame, rules: str, lang: str, top: int = 6) -> list[dict]:
        """SHAP облегчённой модели изменения IGPA: что тянет прогноз вверх и вниз."""
        meta = self.meta["light"][rules]
        X = self._X(frame, meta["features"], meta["cats"])
        values = self.light[rules][0].get_feature_importance(Pool(X, cat_features=meta["cats"]), type="ShapValues")[0, :-1]
        order = np.argsort(-np.abs(values))[:top]
        return [{"feature": meta["features"][j], "name": T.feature_name(meta["features"][j], lang),
                 "value": float(values[j])} for j in order if abs(values[j]) > 1e-6]

    def advise(self, inp: dict, items: list[tuple], rules: str, lang: str, top: int = 3) -> list[dict]:
        """Советы: точный прирост по калькулятору × реалистичность по похожим студентам."""
        blocks = {"research": 0, "one_time": 0, "permanent": 0}
        for c, _ in items:
            blocks[CATEGORY_BY_CODE[c].block.value] += 1
        prev = inp.get("gpa_prev")
        profile = {"gpa": inp["gpa"], "gpa_trend": 0.0 if prev is None else inp["gpa"] - prev,
                   "n_research": blocks["research"], "n_one_time": blocks["one_time"],
                   "n_permanent": blocks["permanent"], "year_of_study": inp["year_of_study"],
                   "master": int(inp["level"] != "bachelor")}
        x = (np.array([[profile[c] for c in self.profile_cols]]) - self.f_mean) / self.f_scale
        idx = self.nn.kneighbors(x, return_distance=False)[0]
        feas = (self.f_hit[idx].sum(axis=0) + self.smoothing * self.f_prior) / (self.k + self.smoothing)
        base = self.igpa(inp["gpa"], items, rules)
        gains = []
        for kind, code, value in self.actions:
            if kind == "gpa":
                gains.append(self.igpa(inp["gpa"] + value, items, rules) - base)
            else:
                gains.append(self.igpa(inp["gpa"], list(items) + [(code, value)], rules) - base)
        gains = np.array(gains)
        expected = gains * feas
        out = []
        for j in [j for j in np.argsort(-expected) if gains[j] > 1e-9][:top]:
            kind, code, value = self.actions[j]
            out.append({"kind": kind, "category": code if kind == "record" else None,
                        "status": value if kind == "record" else None, "gpa_step": value if kind == "gpa" else None,
                        "gain": float(gains[j]), "feasibility": float(feas[j]), "expected": float(expected[j]),
                        "igpa_after": float(base + gains[j]),
                        "text": T.advice(kind, lang, gains[j], base + gains[j], feas[j], code,
                                         value if kind == "record" else None, value if kind == "gpa" else None)})
        return out

    def portfolio(self, inp: dict, lang: str) -> dict:
        items = [(r["category"], r["status"]) for r in inp["records"]]
        rules = inp["rules"]
        now = self.calc(inp["gpa"], items, rules, lang)
        frame = self.light_row(inp, items, rules)
        meta = self.meta["light"][rules]
        reg, clf = self.light[rules]
        X = self._X(frame, meta["features"], meta["cats"])
        catboost = {"pred": float(frame.igpa.iloc[0] + reg.predict(X)[0]), "risk": float(clf.predict_proba(X)[0, 1])}
        catboost["p10"] = catboost["pred"] + meta["residual_q"]["0.1"]
        catboost["p90"] = catboost["pred"] + meta["residual_q"]["0.9"]
        return {"now": now, "forecast": self.hybrid(inp, items, rules), "catboost": catboost,
                "explanation": self.explain(frame, rules, lang), "advice": self.advise(inp, items, rules, lang)}

    # «Студент со стенда»

    def search(self, query: str, faculty: str | None, level: str | None, current: bool, limit: int, offset: int):
        s = self.students
        if current:
            s = s[s.student_id.isin(self.enrollment.query("outcome == 'current'").student_id)]
        if query:
            q = query.lower()
            s = s[s.fio.str.lower().str.contains(q) | s.student_id.str.lower().str.contains(q)
                  | s.program.str.lower().str.contains(q)]
        if faculty:
            s = s[s.faculty == faculty]
        if level:
            s = s[s.level == level]
        return len(s), s.iloc[offset:offset + limit].to_dict("records")

    def student(self, sid: str, rules: str, lang: str) -> dict | None:
        st = self.students[self.students.student_id == sid]
        if st.empty:
            return None
        hist = self.history[(self.history.student_id == sid) & (self.history.rules == rules)].sort_values("year")
        enr = self.enrollment[self.enrollment.student_id == sid].sort_values("year")
        recs = self.records[self.records.student_id == sid].sort_values("event_date")
        back = self.backtest[(self.backtest.student_id == sid) & (self.backtest.rules == rules)]
        fc = self.forecast[rules]
        fc = fc[fc.student_id == sid]
        forecast = None
        if not fc.empty:
            r = fc.iloc[0]
            forecast = {"igpa_now": r.igpa_now, "pred": r.pred, "p10": r.p10, "p90": r.p90, "risk": r.risk,
                        "factors": [{"feature": r[f"shap{k}_feature"], "name": T.feature_name(r[f"shap{k}_feature"], lang),
                                     "value": float(r[f"shap{k}_value"])} for k in range(5)]}
        return {
            "student": st.iloc[0].to_dict(),
            "history": hist.drop(columns=["student_id", "rules"]).to_dict("records"),
            "enrollment": enr.drop(columns="student_id").to_dict("records"),
            "records": [{**r, "category_name": T.category_name(r["category"], lang),
                         "status_name": T.status_name(r["status"], lang), "event_date": str(r["event_date"])[:10]}
                        for r in recs.drop(columns="student_id").to_dict("records")],
            "backtest": back.drop(columns=["student_id", "rules"]).to_dict("records"),
            "forecast": forecast,
        }

    def meta_info(self, lang: str) -> dict:
        return {
            "categories": [{"code": c.code, "column": c.column, "block": c.block.value, "profile": c.profile.value,
                            "name": T.category_name(c.code, lang), "asu_title": c.asu_title,
                            "statuses": [s.code for s in statuses(c.block)]} for c in CATEGORIES],
            "statuses": [{"code": s.code, "family": s.family.value, "name": T.status_name(s.code, lang)}
                         for s in STATUS_BY_CODE.values()],
            "rules": [{"code": r, "name": T.RULES[r][lang], "note": T.RULE_NOTES[r][lang]} for r in RULES],
            "faculties": sorted(self.students.faculty.unique()),
            "levels": ["bachelor", "master_research", "master_profile"],
            "current_year": self.meta["current_year"],
        }


@lru_cache(maxsize=1)
def engine() -> Engine:
    return Engine()
