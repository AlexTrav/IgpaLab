"""Перенос на новую группу (план доработки статьи, 19.11.2026): обучение без группы, проверка на ней.

Последняя проверка (2024/25 → 2025/26), слой АСУ, оба правила. Сценарии: обучение без одного факультета →
проверка на этом факультете (все три факультета по очереди) и обучение только на бакалавриате → проверка на
магистратуре; обучение без малых программ (нижняя четверть по числу студентов) → проверка на них. Новый набор
поступления – первокурсники проверочного года: в обучении их нет по построению (подгруппа «курс 1» в review).
Ориентир – та же модель, обученная на всех студентах (обычный протокол). Холодный старт по студентам (обучение
без студентов проверки) – отдельный прогон models --disjoint.
"""

import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from . import protocol as P
from .baselines import B0
from .features import RULES, build, transitions
from .models import CatBoostModel, RidgeModel
from .review import small_programs

LAYER = "obs"
MODELS = {"B0": B0, "Ridge": RidgeModel, "CatBoost": CatBoostModel}


def scenarios(train: pd.DataFrame, test: pd.DataFrame, small: set | None = None):
    """(название, обучающая часть без группы, проверка только на группе)."""
    for faculty in sorted(test.faculty.unique()):
        yield f"без факультета: {faculty}", train[train.faculty != faculty], test[test.faculty == faculty]
    yield "бакалавриат → магистратура", train[train.level == "bachelor"], test[test.level != "bachelor"]
    if small:
        yield "без малых программ", train[~train.program.isin(small)], test[test.program.isin(small)]


def _risk(y, score) -> dict:
    if score is None:
        return {}
    y = np.asarray(y, int)
    return {"roc_auc": roc_auc_score(y, score), "pr_auc": average_precision_score(y, score)}


def run(d: dict, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for rules in RULES:
        panel, features = build(d, rules, LAYER)
        data = transitions(panel)
        data = data.merge(d["students"][["student_id", "program"]], on="student_id")
        train, test = data[data.year < P.FINAL], data[data.year == P.FINAL]
        full = {name: factory().fit(train, features) for name, factory in MODELS.items()}
        for scenario, tr, te in scenarios(train, test, small_programs(d["students"])[0]):
            y = te.igpa_next.to_numpy()
            ref_b0 = np.abs(y - te.igpa.to_numpy()).mean()
            for name, factory in MODELS.items():
                model = factory().fit(tr, features)
                pred, base = model.predict(te), full[name].predict(te)
                lo, hi = P.mae_ci(y, pred)
                d_lo, d_hi = P.diff_ci(y, pred, base)
                mae, mae_full = float(np.abs(y - pred).mean()), float(np.abs(y - base).mean())
                row = {"rules": rules, "scenario": scenario, "model": name, "train": len(tr), "test": len(te),
                       "mae": mae, "mae_lo": lo, "mae_hi": hi, "mae_full": mae_full,
                       "diff_vs_full": mae - mae_full, "diff_lo": d_lo, "diff_hi": d_hi,
                       "gain_vs_b0": 1 - mae / ref_b0, "gain_vs_b0_full": 1 - mae_full / ref_b0}
                row.update({k: v for k, v in _risk(te.risk, model.risk(te)).items()})
                row.update({f"{k}_full": v for k, v in _risk(te.risk, full[name].risk(te)).items()})
                rows.append(row)
                print(f"{time.strftime('%H:%M:%S')} {rules} {scenario}: {name}", flush=True)
    table = pd.DataFrame(rows)
    table.to_csv(out / "transfer.csv", index=False)
    with pd.option_context("display.width", 220, "display.max_columns", 20):
        print(table[["rules", "scenario", "model", "test", "mae", "mae_full", "gain_vs_b0", "gain_vs_b0_full",
                     "roc_auc", "roc_auc_full"]].round(4).to_string(index=False))
