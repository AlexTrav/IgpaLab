"""Отчёт прогона моделей в Markdown."""

import pandas as pd

RULES = {"default": "Положение", "eduscore": "EduScore"}
LAYERS = {"true": "истина", "obs": "АСУ"}


def num(x, d=4):
    return "–" if pd.isna(x) else f"{x:.{d}f}".replace(".", ",")


def pct(x):
    return "–" if pd.isna(x) else f"{100 * x:+.1f}%".replace(".", ",")


def _table(header, rows):
    return ["| " + " | ".join(header) + " |", "|" + " --- |" * len(header),
            *["| " + " | ".join(str(v) for v in r) + " |" for r in rows], ""]


def write_report(folds: pd.DataFrame, summary: pd.DataFrame, args, versus: pd.DataFrame | None = None,
                 reference: str | None = None) -> str:
    out = [f"# Прогон «{args.name}» на версии {args.version}" + (" (студенты проверки не в обучении)" if args.disjoint else ""),
           "", "Задача A – IGPA года t+1, задача B – снижение на 0,1 и больше. Правила: Положение или EduScore; слой: "
           "истина стенда или данные АСУ.", ""]

    out += ["## Последняя проверка (переходы 2024/25 → 2025/26)", "",
            "MAE с 95% ДИ (бутстреп по студентам); выигрыш – доля снижения MAE относительно B0; "
            "ДИ разности MAE с B0 (ниже нуля – лучше B0); p – Уилкоксон по парным ошибкам с поправкой Холма.", ""]
    out += _table(["Правила", "Слой", "Модель", "MAE", "95% ДИ", "Выигрыш к B0", "ДИ разности", "p (Холм)",
                   "ROC-AUC", "95% ДИ"],
                  [[RULES[r.rules], LAYERS[r.layer], r.model, num(r.mae), f"{num(r.mae_lo)}–{num(r.mae_hi)}",
                    pct(getattr(r, "gain", float("nan"))),
                    "–" if pd.isna(getattr(r, "diff_lo", float("nan"))) else f"{num(r.diff_lo)}…{num(r.diff_hi)}",
                    num(r.p_holm, 3), num(getattr(r, "roc_auc", float("nan")), 3),
                    "–" if pd.isna(getattr(r, "auc_lo", float("nan"))) else f"{num(r.auc_lo, 3)}–{num(r.auc_hi, 3)}"]
                   for r in summary.itertuples()])

    if versus is not None:
        title = "лучшей одиночной моделью CatBoost" if reference == "CatBoost" else "полным набором признаков S2"
        out += [f"## Сравнение с {title}", "",
                f"Разность MAE модели и {reference} с 95% ДИ (ниже нуля – лучше {reference}), p – Уилкоксон с поправкой Холма.", ""]
        out += _table(["Правила", "Слой", "Модель", "MAE", f"Выигрыш к {reference}", "ДИ разности", "p (Холм)"],
                      [[RULES[r.rules], LAYERS[r.layer], r.model, num(r.mae), pct(r.gain),
                        f"{num(r.diff_lo)}…{num(r.diff_hi)}", num(r.p_holm, 3)]
                       for r in versus.itertuples() if r.model != reference])

    out += ["## Все проверки: среднее по трём годам", ""]
    agg = folds.groupby(["rules", "layer", "model", "group"], sort=False).mean(numeric_only=True).reset_index()
    cols = [c for c in ("mae", "rmse", "r2", "roc_auc", "pr_auc", "f1") if c in agg]
    out += _table(["Правила", "Слой", "Модель", "Студенты", *[c.upper() for c in cols]],
                  [[RULES[r["rules"]], LAYERS[r["layer"]], r["model"], "все" if r["group"] == "all" else "активные",
                    *[num(r[c], 4 if c in ("mae", "rmse") else 3) for c in cols]] for _, r in agg.iterrows()])

    out += ["## По годам проверки (все студенты)", ""]
    allg = folds[folds.group == "all"]
    out += _table(["Правила", "Слой", "Год t", "Модель", "n", "MAE", "R²", "ROC-AUC", "PR-AUC", "F1", "Доля риска"],
                  [[RULES[r.rules], LAYERS[r.layer], r.year, r.model, r.n, num(r.mae), num(r.r2, 3),
                    num(getattr(r, "roc_auc", float("nan")), 3), num(getattr(r, "pr_auc", float("nan")), 3),
                    num(getattr(r, "f1", float("nan")), 3), num(getattr(r, "prevalence", float("nan")), 3)]
                   for r in allg.itertuples()])
    return "\n".join(out)
