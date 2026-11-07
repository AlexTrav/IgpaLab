"""Финальное обучение для сайта и сохранение артефактов для API (шаг 8).

Все модели учатся на слое АСУ (согласованные записи): так работает и ручной ввод портфеля, и будущая реальная выгрузка.
- облегчённые CatBoost (изменение IGPA и риск) на признаках ручного ввода, по трём правилам; проверка против полной модели;
- компоненты IGPA-Hybrid на тех же признаках (от правил не зависят);
- данные для реалистичности советов (профили и исходы студентов обучающих лет);
- режим «Студент со стенда»: полные CatBoost по трём правилам, прогноз на 2026/27 с коридором и SHAP, прогноз
  против факта на 2025/26 из экспериментов шагов 5–6, история по годам.
"""

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import Pool

from generator.asu import state_at
from generator.common import load_config, on
from generator.snapshots import gpa_tables, snapshots
from igpa import CATEGORIES, load_rules

from . import hybrid
from . import protocol as P
from . import recommend as R
from .features import build, transitions
from .models import CatBoostModel

RULES3 = ("default", "eduscore", "percentile")
CODES = [c.code for c in CATEGORIES]
CNT = [f"cnt_{c}" for c in CODES]
LIGHT = ["gpa", "gpa_prev", "gpa_trend", "has_history", "year_of_study", "master", "level",
         "n_research", "n_one_time", "n_permanent", "iros", "ssci", "igpa", *CNT]
CURRENT = 2025   # последний завершённый учебный год: прогноз на 2026/27


def log(msg):
    print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)


def _with_counts(frame: pd.DataFrame) -> pd.DataFrame:
    counts = hybrid._counts("obs")
    out = frame.join(counts, on=["student_id", "year"])
    out[CNT] = out[CNT].fillna(0)
    return out


def _save_catboost(model: CatBoostModel, folder: Path, name: str, residuals: np.ndarray | None = None) -> dict:
    model.reg.save_model(str(folder / f"{name}_delta.cbm"))
    model.clf.save_model(str(folder / f"{name}_risk.cbm"))
    meta = {"features": model.features, "cats": model.cats, "params": model.params}
    if residuals is not None:
        meta["residual_q"] = {str(q): float(np.quantile(residuals, q)) for q in (0.1, 0.25, 0.5, 0.75, 0.9)}
    return meta


def run(d: dict, out: Path, results: Path):
    out.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    sem, year = gpa_tables(d["courses"])
    d["snapshots_year_percentile"] = snapshots(d["enrollment"], sem, year,
                                               {"true": d["records_true"], "obs": d["records_asu"]}, cfg,
                                               load_rules("percentile"))
    hybrid.prepare(d)
    log("подготовка данных готова")
    meta, light_eval = {"light": {}, "full": {}, "current_year": CURRENT}, []

    for rules in RULES3:
        panel, features = build(d, rules, "obs")
        panel = _with_counts(panel)
        data = transitions(panel)
        train, test = data[data.year < P.FINAL], data[data.year == P.FINAL]
        # проверка: облегчённая против полной на последней проверке
        light = CatBoostModel(use=LIGHT).fit(train, features + CNT)
        full = CatBoostModel().fit(train, features)
        for name, m in (("Облегчённая", light), ("Полная", full)):
            pred, score = m.predict(test), m.risk(test)
            light_eval.append({"rules": rules, "model": name, **P.regression(test.igpa_next, pred),
                               "roc_auc": P.classification(test.risk.astype(int), score, 0.5)["roc_auc"]})
        light_eval.append({"rules": rules, "model": "B0", **P.regression(test.igpa_next, test.igpa), "roc_auc": np.nan})
        log(f"{rules}: проверка облегчённой модели готова")

        # финальные модели на всех переходах
        light = CatBoostModel(use=LIGHT).fit(data, features + CNT)
        fit_part, val = P.inner_split(data)
        residuals = val.igpa_next.to_numpy() - CatBoostModel(use=LIGHT).fit(fit_part, features + CNT).predict(val)
        meta["light"][rules] = _save_catboost(light, out, f"light_{rules}", residuals)
        full = CatBoostModel().fit(data, features)
        residuals = val.igpa_next.to_numpy() - CatBoostModel().fit(fit_part, features).predict(val)
        meta["full"][rules] = _save_catboost(full, out, f"full_{rules}", residuals)
        _stand_forecast(d, panel, full, rules, out, residuals)
        log(f"{rules}: финальные модели и прогноз стенда готовы")

    pd.DataFrame(light_eval).to_csv(out / "light_eval.csv", index=False)
    panel, features = build(d, "default", "obs")
    data = transitions(_with_counts(panel))
    _export_hybrid(data, features, out, meta)
    log("компоненты гибрида готовы")
    _export_feasibility(data, out)
    log("данные реалистичности готовы")
    _export_stand(d, out, results)
    _export_research(results, out)
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
    log(f"{out}: артефакты готовы")


def _export_hybrid(data: pd.DataFrame, features: list[str], out: Path, meta: dict):
    comp = hybrid._Components("obs", data, [f for f in LIGHT if f not in CNT])   # число записей по типам добавит сам
    comp.gpa.save_model(str(out / "hybrid_gpa.cbm"))
    rates = {}
    for code, model in comp.rates.items():
        if model is not None:
            model.save_model(str(out / f"hybrid_rate_{code}.cbm"))
            rates[code] = True
    meta["hybrid"] = {"features": comp.features, "cats": comp.cats, "rates": sorted(rates),
                      "gpa_residuals": comp.gpa_residuals.tolist(),
                      "global_levels": {c: s.to_dict() for c, s in comp.global_levels.items()},
                      "prior": hybrid.PRIOR}


def _export_feasibility(data: pd.DataFrame, out: Path):
    portfolio = R.Portfolio(hybrid._RECORDS["obs"], load_rules())
    feas = R.Feasibility(data, portfolio)
    np.savez_compressed(out / "feasibility.npz", profile=data[R.PROFILE].fillna(0).to_numpy(float), hit=feas.hit,
                        prior=feas.prior, delta=feas.delta, mean=feas.scaler.mean_, scale=feas.scaler.scale_)
    (out / "feasibility.json").write_text(json.dumps({"profile": R.PROFILE, "actions": R.actions(),
                                                      "neighbours": R.NEIGHBOURS, "smoothing": R.SMOOTHING},
                                                     ensure_ascii=False), encoding="utf-8")


def _stand_forecast(d, panel, full: CatBoostModel, rules: str, out: Path, residuals: np.ndarray):
    """Прогноз на 2026/27 для студентов, которые учатся сейчас, с коридором и пятью главными SHAP-вкладами."""
    current = set(d["enrollment"].query("outcome == 'current'").student_id)
    rows = panel[(panel.year == CURRENT) & panel.student_id.isin(current)].reset_index(drop=True)
    pred, risk = full.predict(rows), full.risk(rows)
    shap = full.reg.get_feature_importance(Pool(full._X(rows), cat_features=full.cats), type="ShapValues")[:, :-1]
    top = np.argsort(-np.abs(shap), axis=1)[:, :5]
    lo, hi = np.quantile(residuals, [0.1, 0.9])
    pd.DataFrame({
        "student_id": rows.student_id, "rules": rules, "igpa_now": rows.igpa, "pred": pred,
        "p10": pred + lo, "p90": pred + hi, "risk": risk,
        **{f"shap{k}_feature": [full.features[j] for j in top[:, k]] for k in range(5)},
        **{f"shap{k}_value": shap[np.arange(len(rows)), top[:, k]] for k in range(5)},
    }).to_parquet(out / f"stand_forecast_{rules}.parquet", index=False)


def _export_stand(d: dict, out: Path, results: Path):
    """Студенты, история по годам при трёх правилах, записи АСУ, прогноз против факта из экспериментов."""
    d["students"].to_parquet(out / "stand_students.parquet", index=False)
    keep = ["student_id", "year", "year_of_study", "gpa", "true_iros", "true_ssci", "true_igpa", "obs_iros",
            "obs_ssci", "obs_igpa", "obs_n", "true_n"]
    parts = []
    for rules in RULES3:
        snap = d["snapshots_year"] if rules == "default" else d[f"snapshots_year_{rules}"]
        parts.append(snap[keep].assign(rules=rules))
    hist = pd.concat(parts, ignore_index=True)
    hist.to_parquet(out / "stand_history.parquet", index=False)
    enr = d["enrollment"][["student_id", "year", "year_of_study", "outcome", "gpa_year", "gpa_cum"]]
    enr.to_parquet(out / "stand_enrollment.parquet", index=False)
    asu = d["records_asu"]
    rows = []
    for year, recs in asu.groupby("year"):
        day = min(on(year, "06-30"), load_config()["now"])
        recs = recs[recs.event_date <= pd.Timestamp(day)].copy()
        recs["state"] = state_at(recs, day)
        rows.append(recs[recs.state.notna()])
    asu = pd.concat(rows)[["student_id", "year", "category", "status", "title", "event_date", "state"]]
    asu.to_parquet(out / "stand_records.parquet", index=False)
    models = pd.read_parquet(results / "models" / "predictions.parquet")
    hyb = pd.read_parquet(results / "hybrid" / "predictions.parquet")
    pred = pd.concat([models[models.model.isin(["B0", "CatBoost", "Stack"])], hyb[hyb.model == "Hybrid"]])
    pred = pred[pred.layer == "obs"][["rules", "model", "student_id", "year", "y", "igpa", "pred", "score", "risk"]]
    pred.to_parquet(out / "stand_backtest.parquet", index=False)


def _export_research(results: Path, out: Path):
    """Сводка результатов исследования для страниц сайта (числа, без пересчёта)."""
    bundle = {}
    for name in ("baselines", "models", "series", "hybrid"):
        bundle[name] = pd.read_csv(results / name / "summary.csv").to_dict("records")
    bundle["rule_change"] = pd.read_csv(results / "hybrid" / "rule_change.csv").to_dict("records")
    rec = results / "recsys"
    bundle["normalization"] = pd.read_csv(rec / "normalization.csv").to_dict("records")
    follow = pd.read_parquet(rec / "follow.parquet")
    bundle["recommendations"] = (follow.groupby(["rules", "strategy"]).agg(
        claimed=("claimed", "mean"), realized=("realized", "mean"), expected=("expected_realized", "mean"),
        feasibility=("feasibility", "mean")).reset_index().to_dict("records"))
    bundle["feasibility_quality"] = pd.read_csv(rec / "feasibility_quality.csv").to_dict("records")
    bundle["recovery"] = pd.read_csv(rec / "recovery.csv").to_dict("records")
    shap = pd.read_csv(rec / "shap_global.csv")
    bundle["shap"] = shap[shap.layer == "obs"].to_dict("records")
    bundle["light_eval"] = pd.read_csv(out / "light_eval.csv").to_dict("records")
    bundle.update(_checks(results))
    (out / "research.json").write_text(json.dumps(bundle, ensure_ascii=False, default=float), encoding="utf-8")


def _checks(results: Path) -> dict:
    """Итоги семи доработок после шага 8 (checks.py и контроль models --disjoint); чего нет – пропускается."""
    checks, out = results / "checks", {}
    files = {"check_light": checks / "light.csv", "check_scenarios": checks / "scenarios.csv",
             "check_semester": checks / "semester.csv", "check_open_uci": checks / "open_uci.csv",
             "robust_data": checks / "robust_data.csv", "robust_models": checks / "robust_models.csv",
             "robust_recsys": checks / "robust_recsys.csv", "disjoint": results / "models_disjoint" / "summary.csv"}
    for name, path in files.items():
        if path.exists():
            out[name] = pd.read_csv(path).to_dict("records")
    learning = [pd.read_csv(p).assign(version=p.parent.parent.name)
                for p in (checks / "learning.csv", results.parent / "v1-12k" / "checks" / "learning.csv") if p.exists()]
    if learning:
        out["check_learning"] = pd.concat(learning, ignore_index=True).to_dict("records")
    return out


def research_only(out: Path, results: Path):
    """Пересобрать только research.json (без обучения моделей): после новых проверок."""
    _export_research(results, out)
    log(f"{out / 'research.json'}: обновлён")
