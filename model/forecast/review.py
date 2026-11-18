"""Доработки по рецензии (17.11.2026) и плану доработки статьи (19.11.2026): метрики вне основных серий.

Считается на последней проверке (2024/25 → 2025/26), слой АСУ, оба правила, по уже сохранённым прогнозам
прогонов models, hybrid и extra. Заново разыгрывается только IGPA-Hybrid – для коридора 10–90%, conformal
и порога «выявить 80% снижений» (у гибрида он подбирается здесь, на пробной модели без последнего года).

intervals    – коридор 10–90% гибрида по всем проверочным годам (покрытие с ДИ, средняя и медианная ширина)
               против split conformal (2023 и 2024: в 2022 году валидационного года нет); по группам – 2024;
risk         – раннее предупреждение при двух порогах, выбранных на валидации: по F1 и «выявить ≥ 80% снижений»;
               матрица ошибок, precision, recall, ложные предупреждения на одно верное, доля предупреждений,
               PR-AUC с ДИ, Brier, калибровка (ECE, сдвиг и наклон логистической перекалибровки);
calibration  – кривая калибровки по 10 равным группам прогноза (csv и рисунок);
pairs        – парные разности MAE между моделями с 95% ДИ, относительным улучшением, dz и Уилкоксоном (Холм);
subgroups    – качество по уровню, курсу, факультету, языку, форме, наличию достижений и размеру программы;
thresholds   – устойчивость ранжирования к порогу снижения 0,05 / 0,1 / 0,2 / 0,3;
errors       – распределение ошибок; sizes – объём выборки по проверкам.
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
SUBGROUP_MODELS = ["B0", "Ridge", "CatBoost", "Stack", "Hybrid"]
CURVE_MODELS = ["Ridge", "CatBoost", "Stack", "Hybrid"]
THRESHOLDS = (0.05, 0.1, 0.2, 0.3)
SURFACE, INK, INK_2 = "#fcfcfb", "#0b0b0b", "#52514e"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]


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


def _bins(p, bins: int = 10):
    return pd.qcut(pd.Series(np.asarray(p, float)).rank(method="first"), bins, labels=False).to_numpy()


def ece(y, p, bins: int = 10) -> float:
    """Ожидаемая ошибка калибровки по 10 равным по численности группам прогноза."""
    g = pd.DataFrame({"p": p, "y": y}).groupby(_bins(p, bins))
    return float((g.size() / len(y) * (g.p.mean() - g.y.mean()).abs()).sum())


def calibration_curve(y, p, bins: int = 10) -> pd.DataFrame:
    """Средний прогноз и наблюдаемая доля снижений в каждой из 10 равных групп прогноза."""
    g = pd.DataFrame({"p": np.asarray(p, float), "y": np.asarray(y, float)}).groupby(_bins(p, bins))
    return pd.DataFrame({"bin": np.arange(bins), "n": g.size().to_numpy(), "mean_pred": g.p.mean().to_numpy(),
                         "observed": g.y.mean().to_numpy()})


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
            "fp_per_tp": fp / tp if tp else np.nan,
            "specificity": tn / (tn + fp) if tn + fp else np.nan,
            "f1": 2 * precision * recall / (precision + recall) if precision and recall else 0.0,
            "roc_auc": roc_auc_score(y, score), "pr_auc": average_precision_score(y, score),
            "pr_auc_lo": pr_lo, "pr_auc_hi": pr_hi, "mean_pred": float(score.mean()),
            "brier": brier_score_loss(y, score), "ece": ece(y, score), **calibration(y, score)}


def paired(y, a, b) -> dict:
    """Разность MAE (a − b) с ДИ, относительная разность к MAE b, dz по парным абсолютным ошибкам, p Уилкоксона."""
    y = np.asarray(y, float)
    ea, eb = np.abs(y - np.asarray(a, float)), np.abs(y - np.asarray(b, float))
    d = ea - eb
    lo, hi = P.diff_ci(y, a, b)
    return {"mae_a": float(ea.mean()), "mae_b": float(eb.mean()), "diff": float(d.mean()), "diff_lo": lo,
            "diff_hi": hi, "rel": float(d.mean() / eb.mean()) if eb.mean() > 0 else np.nan,
            "dz": float(d.mean() / d.std()) if d.std() > 0 else 0.0, "p": P.wilcoxon(y, a, b)}


def coverage(y, lo, hi) -> dict:
    inside = ((np.asarray(y) >= lo) & (np.asarray(y) <= hi)).astype(float)
    c_lo, c_hi = P.bootstrap(inside, lambda i: inside[i].mean())
    width = np.asarray(hi) - np.asarray(lo)
    return {"n": len(inside), "coverage": float(inside.mean()), "cov_lo": c_lo, "cov_hi": c_hi,
            "width": float(np.mean(width)), "width_median": float(np.median(width))}


def conformal(residuals, q=(0.1, 0.9)) -> tuple[float, float]:
    """Split conformal по остаткам валидации: квантили с поправкой на конечную выборку (ceil((n+1)·α)/n)."""
    r = np.sort(np.asarray(residuals, float))
    n = len(r)
    lo = r[max(int(np.floor((n + 1) * q[0])) - 1, 0)]
    hi = r[min(int(np.ceil((n + 1) * q[1])) - 1, n - 1)]
    return float(lo), float(hi)


def small_programs(students: pd.DataFrame) -> tuple[set, float]:
    """Малые программы – нижняя четверть по числу студентов программы."""
    size = students.groupby("program").student_id.nunique()
    q1 = float(size.quantile(0.25))
    return set(size[size < q1].index), q1


def _attrs(d: dict) -> pd.DataFrame:
    """Признаки студентов проверочного года для подгрупп."""
    panel, _ = build(d, "default", LAYER)
    t = transitions(panel)
    t = t[t.year == P.FINAL]
    small, q1 = small_programs(d["students"])
    a = t[["student_id", *GROUPS]].merge(d["students"][["student_id", "program"]], on="student_id")
    a["program_size"] = np.where(a.program.isin(small), f"малая (< {q1:.0f} студентов)", "остальные")
    return a.drop(columns="program")


def _predictions(results: Path) -> pd.DataFrame:
    parts = [pd.read_parquet(results / run / "predictions.parquet") for run in ("models", "hybrid", "extra")
             if (results / run / "predictions.parquet").exists()]
    p = pd.concat(parts, ignore_index=True)
    p = p[p.layer == LAYER].drop_duplicates(["rules", "model", "student_id"]).reset_index(drop=True)
    if "threshold80" not in p:
        p["threshold80"] = np.nan
    return p


def _intervals(d: dict, out: Path) -> tuple[dict, list]:
    """Коридор гибрида по всем проверочным годам против split conformal; порог 80% гибрида; пороги по розыгрышам."""
    hybrid.prepare(d)
    rows, cov_groups, thr_rows, thr80 = [], [], [], {}
    for rules in RULES:
        panel, features = build(d, rules, LAYER)
        data = transitions(panel)
        for year, train, test in P.folds(data):
            fit_part, val = P.inner_split(train)
            y, igpa = test.igpa_next.to_numpy(), test.igpa.to_numpy()
            log(f"{rules} {year}: гибрид на всей обучающей части")
            sims = hybrid.HybridModel().fit(train, features)._simulate(test)
            mean = sims.mean(axis=1)
            lo, hi = np.quantile(sims, 0.1, axis=1), np.quantile(sims, 0.9, axis=1)
            rows.append({"rules": rules, "year": year, "method": "IGPA-Hybrid 10–90%", **coverage(y, lo, hi)})
            c_lo = c_hi = None
            if train.year.nunique() > 1:   # есть отдельный валидационный год: остатки для conformal и порог 80%
                log(f"{rules} {year}: гибрид без последнего года обучающей части")
                probe = hybrid.HybridModel().fit(fit_part, features)
                r_val = val.igpa_next.to_numpy() - probe.predict(val)
                c_lo, c_hi = conformal(r_val)
                rows.append({"rules": rules, "year": year, "method": "split conformal 10–90%",
                             **coverage(y, mean + c_lo, mean + c_hi)})
                if year == P.FINAL:
                    thr80[rules] = P.recall_threshold(val.risk.astype(int), probe.risk(val), 0.8)
            if year != P.FINAL:
                continue
            t = test.reset_index(drop=True)   # признаки групп уже в проверочной таблице; позиции совпадают с y и sims
            for col in GROUPS:
                for value, idx in t.groupby(col).indices.items():
                    row = {"rules": rules, "group": col, "value": str(value), "n": len(idx),
                           "hybrid": float(((y[idx] >= lo[idx]) & (y[idx] <= hi[idx])).mean())}
                    if c_lo is not None:
                        row["conformal"] = float(((y[idx] >= mean[idx] + c_lo) & (y[idx] <= mean[idx] + c_hi)).mean())
                    cov_groups.append(row)
            for thr in THRESHOLDS:
                yy = ((y - igpa) <= -thr).astype(int)
                score = (sims <= igpa[:, None] - thr).mean(axis=1)
                thr_rows.append({"rules": rules, "model": "Hybrid", "score": "simulated probability", "t": thr,
                                 "prevalence": yy.mean(), "roc_auc": roc_auc_score(yy, score),
                                 "pr_auc": average_precision_score(yy, score)})
    pd.DataFrame(rows).to_csv(out / "intervals.csv", index=False)
    pd.DataFrame(cov_groups).to_csv(out / "intervals_groups.csv", index=False)
    log("коридоры по годам")
    return thr80, thr_rows


def _calibration_figure(curves: pd.DataFrame, path: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
                         "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                         "grid.color": "#e6e5e0", "axes.axisbelow": True, "font.size": 10, "axes.titlesize": 11,
                         "axes.titleweight": "bold", "axes.titlelocation": "left", "legend.frameon": False,
                         "savefig.dpi": 200, "savefig.bbox": "tight", "text.color": INK, "axes.labelcolor": INK_2,
                         "xtick.color": INK_2, "ytick.color": INK_2})
    names = {"default": "Положение 2025", "eduscore": "EduScore"}
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.8), sharey=True)
    for ax, rules in zip(axes, RULES):
        top = float(curves[curves.rules == rules][["mean_pred", "observed"]].max().max()) * 1.05
        ax.plot([0, top], [0, top], color=INK_2, linewidth=1, linestyle="--", label="идеальная калибровка")
        for model, color in zip(CURVE_MODELS, SERIES):
            c = curves[(curves.rules == rules) & (curves.model == model)]
            ax.plot(c.mean_pred, c.observed, color=color, linewidth=2, marker="o", markersize=4,
                    label="IGPA-Hybrid" if model == "Hybrid" else model)
        ax.set_title(names[rules])
        ax.set_xlabel("прогноз вероятности снижения")
        ax.set_xlim(0, top)
        ax.set_ylim(0, top)
    axes[0].set_ylabel("наблюдаемая доля снижений")
    axes[1].legend(loc="upper left", fontsize=8)
    fig.savefig(path)
    plt.close(fig)


def run(d: dict, results: Path):
    out = results / "review"
    out.mkdir(parents=True, exist_ok=True)
    preds = _predictions(results)
    attrs = _attrs(d)
    models = [m for m in preds.model.unique() if m != "CatBoost-level"]
    log(f"модели: {', '.join(models)}")

    # 1. коридоры гибрида и его порог 80% (самая долгая часть: розыгрыши)
    thr80, thr_rows = _intervals(d, out)
    for rules, t in thr80.items():
        preds.loc[(preds.model == "Hybrid") & (preds.rules == rules), "threshold80"] = t

    # 2. метрики риска при двух порогах и кривая калибровки
    rows, curves = [], []
    for (rules, model), g in preds.groupby(["rules", "model"], sort=False):
        if model not in models or not g.score.notna().all():
            continue
        for kind, col in (("F1", "threshold"), ("recall80", "threshold80")):
            if pd.notna(g[col].iloc[0]):
                rows.append({"rules": rules, "model": model, "rule": kind,
                             **risk_metrics(g.risk, g.score, g[col].iloc[0])})
        curves.append(calibration_curve(g.risk, g.score).assign(rules=rules, model=model))
    pd.DataFrame(rows).to_csv(out / "risk.csv", index=False)
    curves = pd.concat(curves, ignore_index=True)
    curves.to_csv(out / "calibration_curve.csv", index=False)
    _calibration_figure(curves, out / "fig_calibration.png")
    log("метрики риска и калибровка")

    # 3. парные сравнения: все пары основных моделей и каждая модель против B0
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

    # 4. подгруппы: точность, ДИ MAE, ранжирование и предупреждения при обоих порогах
    rows = []
    sub = preds[preds.model.isin(SUBGROUP_MODELS)].merge(attrs, on="student_id")
    sub["achievements"] = np.where(sub.active == 1, "есть достижения", "нет достижений")
    for (rules, model), g in sub.groupby(["rules", "model"]):
        b0 = preds[(preds.rules == rules) & (preds.model == "B0")].set_index("student_id").pred
        for col in [*GROUPS, "achievements", "program_size"]:
            for value, s in g.groupby(col):
                err, ref = np.abs(s.y - s.pred), np.abs(s.y - b0.loc[s.student_id].to_numpy())
                lo, hi = P.mae_ci(s.y, s.pred)
                row = {"rules": rules, "model": model, "group": col, "value": str(value), "n": len(s),
                       "mae": float(err.mean()), "mae_lo": lo, "mae_hi": hi,
                       "gain": float(1 - err.mean() / ref.mean()), "prevalence": float(s.risk.mean())}
                if s.score.notna().all():
                    yy, sc = s.risk.astype(int).to_numpy(), s.score.to_numpy()
                    both = 0 < yy.sum() < len(yy)
                    row.update({"roc_auc": roc_auc_score(yy, sc) if both else np.nan,
                                "pr_auc": average_precision_score(yy, sc) if both else np.nan,
                                "brier": brier_score_loss(yy, sc), "mean_pred": float(sc.mean())})
                    for kind, c in (("f1", "threshold"), ("r80", "threshold80")):
                        if pd.notna(s[c].iloc[0]):
                            alert = sc >= s[c].iloc[0]
                            row[f"alert_rate_{kind}"] = float(alert.mean())
                            row[f"recall_{kind}"] = float((alert & (yy == 1)).sum() / max(yy.sum(), 1))
                            row[f"precision_{kind}"] = float((alert & (yy == 1)).sum() / alert.sum()) if alert.any() else np.nan
                rows.append(row)
    pd.DataFrame(rows).to_csv(out / "subgroups.csv", index=False)
    log("подгруппы")

    # 5. порог снижения: ранжирование по прогнозу изменения IGPA (прямые модели); гибрид – по розыгрышам (выше)
    rows = []
    for (rules, model), g in preds[preds.model.isin(["B1", "B2", "Ridge", "CatBoost", "Stack"])].groupby(["rules", "model"]):
        score = -(g.pred - g.igpa).to_numpy()
        for t in THRESHOLDS:
            y = ((g.y - g.igpa) <= -t).astype(int).to_numpy()
            rows.append({"rules": rules, "model": model, "score": "predicted change", "t": t,
                         "prevalence": y.mean(), "roc_auc": roc_auc_score(y, score),
                         "pr_auc": average_precision_score(y, score)})
    pd.DataFrame(rows + thr_rows).to_csv(out / "thresholds.csv", index=False)

    # 6. распределение ошибок
    rows = []
    for (rules, model), g in preds[preds.model.isin(["B0", "B2", "Stack", "Hybrid"])].groupby(["rules", "model"]):
        e = (g.pred - g.y).to_numpy()
        a = np.abs(e)
        rows.append({"rules": rules, "model": model, "bias": e.mean(), "mae": a.mean(),
                     **{f"abs_q{int(q * 100)}": np.quantile(a, q) for q in (0.5, 0.75, 0.9, 0.95, 0.99)},
                     "share_over_0.2": (a > 0.2).mean(), "share_over_0.5": (a > 0.5).mean()})
    pd.DataFrame(rows).to_csv(out / "errors.csv", index=False)

    # 7. объём выборки по проверкам (правила не влияют на число переходов)
    rows = []
    for rules in RULES:
        panel, _ = build(d, rules, LAYER)
        data = transitions(panel)
        for year, train, test in P.folds(data):
            rows.append({"rules": rules, "test_year": f"{year}/{(year + 1) % 100:02d} → {year + 1}/{(year + 2) % 100:02d}",
                         "train_transitions": len(train), "train_students": train.student_id.nunique(),
                         "test_transitions": len(test), "decline_share": float(test.risk.mean())})
    pd.DataFrame(rows).to_csv(out / "sizes.csv", index=False)
    log(f"готово: {out}")
