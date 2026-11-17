"""Доработки по рецензии статьи (17.11.2026): метрики, которых не было в основных сериях.

Всё считается на последней проверке (2024/25 → 2025/26), слой АСУ, оба правила, по уже сохранённым прогнозам
прогонов models, hybrid и extra. Заново разыгрывается только IGPA-Hybrid – для коридора 10–90% и conformal.

risk        – метрики раннего предупреждения при пороге, выбранном на валидации: матрица ошибок, precision,
              recall, specificity, F1, PR-AUC с ДИ, Brier, калибровка (ECE, сдвиг и наклон логистической
              перекалибровки);
pairs       – парные разности MAE между моделями с 95% ДИ, размером эффекта (dz) и Уилкоксоном с поправкой Холма;
subgroups   – качество по уровню, курсу, факультету, языку и форме обучения, худшая группа;
thresholds  – устойчивость ранжирования к порогу снижения 0,05 / 0,1 / 0,2 / 0,3;
errors      – распределение ошибок; sizes – объём выборки по проверкам;
intervals   – коридор 10–90% гибрида (покрытие с ДИ, ширина, по группам) против split conformal.
"""

import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from . import hybrid
from . import protocol as P
from .features import build, transitions

LAYER = "obs"
RULES = ("default", "eduscore")
MAIN = ["Ridge", "RF", "CatBoost", "Stack", "Mean", "Hybrid"]
GROUPS = ["level", "year_of_study", "faculty", "language", "form"]
THRESHOLDS = (0.05, 0.1, 0.2, 0.3)


def log(msg):
    print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)


# --- калибровка: логистическая перекалибровка y ~ a + b·logit(p) методом Ньютона ---
def _logit(p):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def calibration(y, p) -> dict:
    """Сдвиг (calibration-in-the-large: a при b = 1) и наклон (b при свободном a); идеал – 0 и 1."""
    y, o = np.asarray(y, float), _logit(p)
    a = 0.0
    for _ in range(50):                     # только сдвиг, наклон закреплён на 1
        mu = 1 / (1 + np.exp(-(a + o)))
        a += (y - mu).sum() / max((mu * (1 - mu)).sum(), 1e-9)
    beta = np.zeros(2)
    X = np.column_stack([np.ones_like(o), o])
    for _ in range(100):                    # сдвиг и наклон вместе (IRLS)
        mu = 1 / (1 + np.exp(-X @ beta))
        w = mu * (1 - mu)
        step = np.linalg.solve(X.T @ (X * w[:, None]) + 1e-9 * np.eye(2), X.T @ (y - mu))
        beta += step
        if np.abs(step).max() < 1e-10:
            break
    return {"cal_intercept": float(a), "cal_slope": float(beta[1])}


def ece(y, p, bins: int = 10) -> float:
    """Ожидаемая ошибка калибровки по 10 равным по численности группам прогноза."""
    q = pd.qcut(pd.Series(np.asarray(p, float)).rank(method="first"), bins, labels=False)
    g = pd.DataFrame({"p": p, "y": y}).groupby(q)
    return float((g.size() / len(y) * (g.p.mean() - g.y.mean()).abs()).sum())


def risk_metrics(y, score, threshold) -> dict:
    y, score = np.asarray(y, int), np.asarray(score, float)
    alert = score >= threshold
    tp, fp = int((alert & (y == 1)).sum()), int((alert & (y == 0)).sum())
    fn, tn = int((~alert & (y == 1)).sum()), int((~alert & (y == 0)).sum())
    precision = tp / (tp + fp) if tp + fp else np.nan
    recall = tp / (tp + fn) if tp + fn else np.nan
    pr_lo, pr_hi = P.bootstrap(np.arange(len(y)), lambda i: average_precision_score(y[i], score[i])
                               if 0 < y[i].sum() < len(i) else np.nan)
    return {"n": len(y), "prevalence": float(y.mean()), "threshold": float(threshold), "tp": tp, "fp": fp,
            "fn": fn, "tn": tn, "alert_rate": float(alert.mean()), "precision": precision, "recall": recall,
            "specificity": tn / (tn + fp) if tn + fp else np.nan,
            "f1": 2 * precision * recall / (precision + recall) if precision and recall else 0.0,
            "roc_auc": roc_auc_score(y, score), "pr_auc": average_precision_score(y, score),
            "pr_auc_lo": pr_lo, "pr_auc_hi": pr_hi, "mean_pred": float(score.mean()),
            "brier": brier_score_loss(y, score), "ece": ece(y, score), **calibration(y, score)}


def paired(y, a, b) -> dict:
    """Разность MAE (a − b) с ДИ, размер эффекта dz по парным абсолютным ошибкам, p Уилкоксона."""
    y = np.asarray(y, float)
    d = np.abs(y - np.asarray(a, float)) - np.abs(y - np.asarray(b, float))
    lo, hi = P.diff_ci(y, a, b)
    return {"diff": float(d.mean()), "diff_lo": lo, "diff_hi": hi,
            "dz": float(d.mean() / d.std()) if d.std() > 0 else 0.0, "p": P.wilcoxon(y, a, b)}


def coverage(y, lo, hi) -> dict:
    inside = ((np.asarray(y) >= lo) & (np.asarray(y) <= hi)).astype(float)
    c_lo, c_hi = P.bootstrap(inside, lambda i: inside[i].mean())
    return {"coverage": float(inside.mean()), "cov_lo": c_lo, "cov_hi": c_hi,
            "width": float(np.mean(np.asarray(hi) - np.asarray(lo)))}


def conformal(residuals, q=(0.1, 0.9)) -> tuple[float, float]:
    """Split conformal по остаткам валидации: квантили с поправкой на конечную выборку (ceil((n+1)·α)/n)."""
    r = np.sort(np.asarray(residuals, float))
    n = len(r)
    lo = r[max(int(np.floor((n + 1) * q[0])) - 1, 0)]
    hi = r[min(int(np.ceil((n + 1) * q[1])) - 1, n - 1)]
    return float(lo), float(hi)


def _attrs(d: dict) -> pd.DataFrame:
    """Признаки студентов проверочного года для подгрупп."""
    panel, _ = build(d, "default", LAYER)
    t = transitions(panel)
    t = t[t.year == P.FINAL]
    return t[["student_id", *GROUPS]].copy()


def _predictions(results: Path) -> pd.DataFrame:
    parts = [pd.read_parquet(results / run / "predictions.parquet") for run in ("models", "hybrid", "extra")
             if (results / run / "predictions.parquet").exists()]
    p = pd.concat(parts, ignore_index=True)
    p = p[p.layer == LAYER].drop_duplicates(["rules", "model", "student_id"])
    return p


def run(d: dict, results: Path):
    out = results / "review"
    out.mkdir(parents=True, exist_ok=True)
    preds = _predictions(results)
    attrs = _attrs(d)
    models = [m for m in preds.model.unique() if m != "CatBoost-level"]
    log(f"модели: {', '.join(models)}")

    # 1. метрики риска
    rows = []
    for (rules, model), g in preds.groupby(["rules", "model"], sort=False):
        if model in models and g.score.notna().all():
            rows.append({"rules": rules, "model": model, **risk_metrics(g.risk, g.score, g.threshold.iloc[0])})
    pd.DataFrame(rows).to_csv(out / "risk.csv", index=False)
    log("метрики риска")

    # 2. парные сравнения: все пары основных моделей и каждая модель против B0
    rows, pvals = [], {}
    for rules, g in preds.groupby("rules", sort=False):
        w = g.pivot(index="student_id", columns="model", values="pred")
        y = g[g.model == "B0"].set_index("student_id").y.loc[w.index]
        names = [m for m in MAIN if m in w]
        pairs = [(a, b) for i, a in enumerate(names) for b in names[i + 1:]]
        pairs += [(m, "B0") for m in models if m != "B0" and m in w]
        for a, b in pairs:
            r = {"rules": rules, "a": a, "b": b, **paired(y, w[a], w[b])}
            rows.append(r)
            pvals[f"{rules}|{a}|{b}"] = r["p"]
    adj = P.holm(pvals)
    pairs_df = pd.DataFrame(rows)
    pairs_df["p_holm"] = [adj[f"{r.rules}|{r.a}|{r.b}"] for r in pairs_df.itertuples()]
    pairs_df.to_csv(out / "pairs.csv", index=False)
    log("парные сравнения")

    # 3. подгруппы
    rows = []
    for (rules, model), g in preds[preds.model.isin(["B0", "Stack", "Hybrid", "CatBoost"])].groupby(["rules", "model"]):
        g = g.merge(attrs, on="student_id")
        b0 = preds[(preds.rules == rules) & (preds.model == "B0")].set_index("student_id").pred
        for col in GROUPS:
            for value, s in g.groupby(col):
                err, ref = np.abs(s.y - s.pred), np.abs(s.y - b0.loc[s.student_id].to_numpy())
                row = {"rules": rules, "model": model, "group": col, "value": str(value), "n": len(s),
                       "mae": float(err.mean()), "gain": float(1 - err.mean() / ref.mean()),
                       "prevalence": float(s.risk.mean())}
                if s.score.notna().all():
                    yy = s.risk.astype(int)
                    row.update({"roc_auc": roc_auc_score(yy, s.score) if 0 < yy.sum() < len(yy) else np.nan,
                                "mean_pred": float(s.score.mean()),
                                "alert_rate": float((s.score >= s.threshold.iloc[0]).mean()),
                                "recall": float(((s.score >= s.threshold.iloc[0]) & (yy == 1)).sum() / max(yy.sum(), 1))})
                rows.append(row)
    pd.DataFrame(rows).to_csv(out / "subgroups.csv", index=False)
    log("подгруппы")

    # 4. порог снижения: ранжирование по прогнозу изменения IGPA (прямые модели) и по розыгрышам (гибрид, ниже)
    rows = []
    for (rules, model), g in preds[preds.model.isin(["B1", "B2", "Ridge", "CatBoost", "Stack"])].groupby(["rules", "model"]):
        score = -(g.pred - g.igpa).to_numpy()
        for t in THRESHOLDS:
            y = ((g.y - g.igpa) <= -t).astype(int).to_numpy()
            rows.append({"rules": rules, "model": model, "score": "predicted change", "t": t,
                         "prevalence": y.mean(), "roc_auc": roc_auc_score(y, score),
                         "pr_auc": average_precision_score(y, score)})
    thr_rows = rows

    # 5. распределение ошибок
    rows = []
    for (rules, model), g in preds[preds.model.isin(["B0", "B2", "Stack", "Hybrid"])].groupby(["rules", "model"]):
        e = (g.pred - g.y).to_numpy()
        a = np.abs(e)
        rows.append({"rules": rules, "model": model, "bias": e.mean(), "mae": a.mean(),
                     **{f"abs_q{int(q * 100)}": np.quantile(a, q) for q in (0.5, 0.75, 0.9, 0.95, 0.99)},
                     "share_over_0.2": (a > 0.2).mean(), "share_over_0.5": (a > 0.5).mean()})
    pd.DataFrame(rows).to_csv(out / "errors.csv", index=False)

    # 6. объём выборки по проверкам (правила не влияют на число переходов)
    rows = []
    for rules in RULES:
        panel, _ = build(d, rules, LAYER)
        data = transitions(panel)
        for year, train, test in P.folds(data):
            rows.append({"rules": rules, "test_year": f"{year}/{(year + 1) % 100:02d} → {year + 1}/{(year + 2) % 100:02d}",
                         "train_transitions": len(train), "train_students": train.student_id.nunique(),
                         "test_transitions": len(test), "decline_share": float(test.risk.mean())})
    pd.DataFrame(rows).to_csv(out / "sizes.csv", index=False)
    log("ошибки и объём выборки")

    # 7. коридор гибрида против split conformal + порог по розыгрышам
    hybrid.prepare(d)
    rows, cov_groups = [], []
    for rules in RULES:
        panel, features = build(d, rules, LAYER)
        data = transitions(panel)
        train, test = data[data.year < P.FINAL], data[data.year == P.FINAL]
        fit_part, val = P.inner_split(train)
        log(f"{rules}: гибрид на обучающей части без последнего года (остатки для conformal)")
        probe = hybrid.HybridModel().fit(fit_part, features)
        r_val = val.igpa_next.to_numpy() - probe.predict(val)
        log(f"{rules}: гибрид на всей обучающей части")
        model = hybrid.HybridModel().fit(train, features)
        sims = model._simulate(test)
        y, mean = test.igpa_next.to_numpy(), sims.mean(axis=1)
        lo, hi = np.quantile(sims, 0.1, axis=1), np.quantile(sims, 0.9, axis=1)
        c_lo, c_hi = conformal(r_val)
        rows.append({"rules": rules, "method": "IGPA-Hybrid 10–90%", **coverage(y, lo, hi)})
        rows.append({"rules": rules, "method": "split conformal 10–90%", **coverage(y, mean + c_lo, mean + c_hi)})
        t = test.reset_index(drop=True)   # признаки групп уже в проверочной таблице; позиции совпадают с y и sims
        for col in GROUPS:
            for value, idx in t.groupby(col).indices.items():
                cov_groups.append({"rules": rules, "group": col, "value": str(value), "n": len(idx),
                                   "hybrid": float(((y[idx] >= lo[idx]) & (y[idx] <= hi[idx])).mean()),
                                   "conformal": float(((y[idx] >= mean[idx] + c_lo) & (y[idx] <= mean[idx] + c_hi)).mean())})
        for thr in THRESHOLDS:
            yy = ((y - test.igpa.to_numpy()) <= -thr).astype(int)
            score = (sims <= test.igpa.to_numpy()[:, None] - thr).mean(axis=1)
            thr_rows.append({"rules": rules, "model": "Hybrid", "score": "simulated probability", "t": thr,
                             "prevalence": yy.mean(), "roc_auc": roc_auc_score(yy, score),
                             "pr_auc": average_precision_score(yy, score)})
    pd.DataFrame(rows).to_csv(out / "intervals.csv", index=False)
    pd.DataFrame(cov_groups).to_csv(out / "intervals_groups.csv", index=False)
    pd.DataFrame(thr_rows).to_csv(out / "thresholds.csv", index=False)
    log(f"готово: {out}")
