"""Ретроспективная оценка советов (план доработки статьи, 19.11.2026), слой истины, последняя проверка.

Для каждой стратегии: арифметический прирост при условии выполнения, пересчитанный на фактическом портфеле
года t+1, умноженный на оценённую вероятность наблюдения действия (expected_realized), с 95% ДИ и парной
разностью с нашей стратегией; доля студентов, реально сделавших рекомендованное действие (did); покрытие
(прирост > 0 и вероятность ≥ 10%); regret против лучшего доступного действия, выбранного задним числом по той
же метрике; разбивка по типам действий (GPA, iROS, SSCI). Это проверка в синтетическом сценарии, не причинная оценка эффекта совета:
поправка на отбор (IPW, doubly robust) вынесена в дальнейшую работу.
"""

import time
from pathlib import Path

import numpy as np
import pandas as pd

from igpa import load_rules

from . import protocol as P
from . import recommend as R
from .features import build, transitions

RULES3 = ("default", "eduscore", "percentile")
OURS = "Наша: прирост × реалистичность"


def _ci(values) -> tuple[float, float, float]:
    v = np.asarray(values, float)
    lo, hi = P.bootstrap(v, lambda i: v[i].mean())
    return float(v.mean()), lo, hi


def summarize(f: pd.DataFrame) -> tuple[list, list]:
    """Сводка по стратегиям и по типам действий для одного правила."""
    ours = f[f.strategy == OURS].set_index("student_id")
    rows, kinds = [], []
    for strategy, g in f.groupby("strategy", sort=False):
        g = g.set_index("student_id").loc[ours.index]
        exp, exp_lo, exp_hi = _ci(g.expected_realized)
        real, real_lo, real_hi = _ci(g.realized)
        did, did_lo, did_hi = _ci(g.did)
        diff, diff_lo, diff_hi = _ci(ours.expected_realized - g.expected_realized)
        rows.append({"strategy": strategy, "n": len(g),
                     "expected_realized": exp, "expected_lo": exp_lo, "expected_hi": exp_hi,
                     "ours_minus_this": diff, "diff_lo": diff_lo, "diff_hi": diff_hi,
                     "realized": real, "realized_lo": real_lo, "realized_hi": real_hi,
                     "did": did, "did_lo": did_lo, "did_hi": did_hi,
                     "realized_if_did": float(g.realized[g.did].mean()) if g.did.any() else np.nan,
                     "mean_feasibility": float(g.feasibility.mean()), "covered": float(g.covered.mean()),
                     "oracle": float(g.oracle.mean()), "regret": float(g.regret.mean()),
                     "regret_share": float(g.regret.mean() / g.oracle.mean()) if g.oracle.mean() > 0 else np.nan,
                     "advice_is_best": float((g.regret <= 1e-12).mean())})
        for kind, k in g.groupby("kind"):
            kinds.append({"strategy": strategy, "kind": kind, "share": len(k) / len(g), "n": len(k),
                          "did": float(k.did.mean()), "realized": float(k.realized.mean()),
                          "feasibility": float(k.feasibility.mean()),
                          "expected_realized": float(k.expected_realized.mean())})
    return rows, kinds


def run(d: dict, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    panel, _ = build(d, "default", "true")   # портфель и GPA от правил не зависят; IGPA пересчитывается по правилам
    data = transitions(panel)
    train, test = data[data.year < P.FINAL], data[data.year == P.FINAL]
    rows, kinds, follows = [], [], []
    for name in RULES3:
        portfolio = R.Portfolio(d["records_true"], load_rules(name))
        f = R.follow(test, portfolio, R.Feasibility(train, portfolio))
        follows.append(f.assign(rules=name))
        r, k = summarize(f)
        coverable = float(f[f.strategy == OURS].coverable.mean())
        rows += [{"rules": name, "students_coverable": coverable, **x} for x in r]
        kinds += [{"rules": name, **x} for x in k]
        print(f"{time.strftime('%H:%M:%S')} советы: правила {name}", flush=True)
    pd.concat(follows).to_parquet(out / "follow.parquet", index=False)
    table = pd.DataFrame(rows)
    table.to_csv(out / "strategies.csv", index=False)
    pd.DataFrame(kinds).to_csv(out / "by_kind.csv", index=False)
    with pd.option_context("display.width", 220, "display.max_columns", 20):
        print(table[["rules", "strategy", "expected_realized", "expected_lo", "expected_hi", "did", "covered",
                     "regret", "regret_share", "advice_is_best"]].round(4).to_string(index=False))
