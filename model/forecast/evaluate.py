"""Прогон моделей по протоколу: 2 правила × 2 слоя × 3 проверочных года, итог по последнему году с ДИ и тестами."""

from typing import Callable

import numpy as np
import pandas as pd

from . import protocol as P
from .features import LAYERS, RULES, build, transitions

Factory = Callable[[], object]


def run(d: dict, models: dict[str, Factory], disjoint: bool = False,
        settings: list[tuple[str, str]] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Метрики по всем проверкам и прогнозы последней проверки.

    Порог риска выбирается так: модель учится на обучающей части без последнего года, порог берётся по F1
    на этом последнем году, затем модель переобучается на всей обучающей части.
    """
    rows, preds = [], []
    for rules, layer in settings or [(r, l) for r in RULES for l in LAYERS]:
        panel, features = build(d, rules, layer)
        data = transitions(panel)
        for year, train, test in P.folds(data, disjoint=disjoint):
            fit_part, val = P.inner_split(train)
            for name, factory in models.items():
                threshold = None
                probe = factory().fit(fit_part, features)
                val_score = probe.risk(val)
                if val_score is not None:
                    threshold = P.best_threshold(val.risk.astype(int), val_score)
                model = factory().fit(train, features)
                pred, score = model.predict(test), model.risk(test)
                for group, mask in (("all", np.ones(len(test), bool)), ("active", test.active.to_numpy() == 1)):
                    row = {"rules": rules, "layer": layer, "year": year, "model": name, "group": group,
                           "n": int(mask.sum()), **P.regression(test.igpa_next[mask], pred[mask])}
                    if score is not None:
                        row.update(P.classification(test.risk[mask].astype(int), score[mask], threshold))
                    rows.append(row)
                if year == P.FINAL:
                    preds.append(pd.DataFrame({
                        "rules": rules, "layer": layer, "model": name, "student_id": test.student_id.to_numpy(),
                        "year": year, "y": test.igpa_next.to_numpy(), "igpa": test.igpa.to_numpy(),
                        "risk": test.risk.to_numpy(), "active": test.active.to_numpy(), "pred": pred,
                        "score": np.full(len(test), np.nan) if score is None else score,
                        "threshold": np.nan if threshold is None else threshold}))
    return pd.DataFrame(rows), pd.concat(preds, ignore_index=True)


def summary(preds: pd.DataFrame, reference: str = "B0") -> pd.DataFrame:
    """Последняя проверка: MAE с 95% ДИ, разность с B0 с ДИ, Уилкоксон (Холм по всем сравнениям), ROC-AUC с ДИ."""
    rows, pvalues = [], {}
    for (rules, layer), g in preds.groupby(["rules", "layer"], sort=False):
        ref = g[g.model == reference].set_index("student_id")
        for name, m in g.groupby("model", sort=False):
            m = m.set_index("student_id").loc[ref.index]
            lo, hi = P.mae_ci(m.y, m.pred)
            row = {"rules": rules, "layer": layer, "model": name, "n": len(m),
                   "mae": float(np.abs(m.y - m.pred).mean()), "mae_lo": lo, "mae_hi": hi}
            if name != reference:
                row["diff_lo"], row["diff_hi"] = P.diff_ci(m.y, m.pred, ref.pred)
                row["gain"] = 1 - row["mae"] / float(np.abs(ref.y - ref.pred).mean())
                pvalues[(rules, layer, name)] = P.wilcoxon(m.y, m.pred, ref.pred)
            if m.score.notna().all():
                row["roc_auc"] = P.classification(m.risk.astype(int), m.score, m.threshold.iloc[0])["roc_auc"]
                row["auc_lo"], row["auc_hi"] = P.auc_ci(m.risk.astype(int), m.score)
            rows.append(row)
    out = pd.DataFrame(rows)
    adjusted = P.holm({"|".join(k): v for k, v in pvalues.items()})
    out["p_holm"] = ["|".join((r.rules, r.layer, r.model)) for r in out.itertuples()]
    out["p_holm"] = out.p_holm.map(adjusted)
    return out
