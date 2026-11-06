import argparse
import json
from pathlib import Path

import pandas as pd

from . import evaluate
from .baselines import B0, B1
from .features import GROUPS, group_features, load
from . import hybrid
from .models import CatBoostModel, ForestModel, MeanModel, RidgeModel, StackModel
from .report import write_report

S0 = group_features("grades", "context")
S1 = group_features("grades", "context", "achievements", "asu")
MODELS = {
    "B0": B0, "B1": B1,
    "Ridge": RidgeModel, "RF": ForestModel, "CatBoost": CatBoostModel,
    "Stack": StackModel, "Mean": MeanModel,
    "CatBoost-level": lambda: CatBoostModel(target="level"),
    "Hybrid": hybrid.HybridModel,
    # серии на CatBoost: S0 только оценки, S1 + достижения, S2 всё (с динамикой), S3 – всё без одной группы;
    # параметры подбираются один раз на полном наборе (S2) и общие для всех вариантов
    "S0": lambda: CatBoostModel(use=S0, shared=True),
    "S1": lambda: CatBoostModel(use=S1, shared=True),
    "S2": lambda: CatBoostModel(),
    **{f"S3-{g}": (lambda g=g: CatBoostModel(use=group_features(without=(g,)), shared=True)) for g in GROUPS},
}
RUNS = {
    "baselines": "B0,B1",
    "models": "B0,B1,Ridge,RF,CatBoost,Stack,Mean,CatBoost-level",
    "series": "B0,S0,S1,S2," + ",".join(f"S3-{g}" for g in GROUPS),
    "hybrid": "B0,Hybrid",   # CatBoost и стекинг не переобучаются: их прогнозы берутся из прогона models
}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="forecast", description="Модели прогноза IGPA стенда IgpaLab")
    parser.add_argument("--version", default="v1")
    parser.add_argument("--data", default="/repo/data/synthetic")
    parser.add_argument("--name", default="baselines", help="прогон: " + ", ".join(RUNS) + ", recsys")
    parser.add_argument("--models", help="свой список моделей через запятую, из: " + ", ".join(MODELS))
    parser.add_argument("--disjoint", action="store_true", help="контроль: студенты проверки не входят в обучение")
    args = parser.parse_args(argv)

    d = load(Path(args.data) / args.version)
    if args.name == "recsys":
        from . import study
        study.run(d, pd.read_parquet(Path(args.data) / args.version / "latent.parquet"),
                  Path("results") / args.version / "recsys")
        return
    hybrid.prepare(d)
    models = {m: MODELS[m] for m in (args.models or RUNS[args.name]).split(",")}
    folds, preds = evaluate.run(d, models, disjoint=args.disjoint)
    out = Path("results") / args.version / (args.name + ("_disjoint" if args.disjoint else ""))
    s8 = None
    if args.name == "hybrid":
        # прямые модели шага 5 не переобучаем: их прогнозы на той же проверке берём из прогона models
        done = pd.read_parquet(out.parent / "models" / "predictions.parquet")
        reuse = done[done.model.isin(["CatBoost", "Stack"]) & ~done.model.isin(preds.model.unique())]
        preds = pd.concat([preds, reuse], ignore_index=True)
        assert not preds.duplicated(["rules", "layer", "model", "student_id"]).any()
        s8 = evaluate.rule_change(preds)
        out.mkdir(parents=True, exist_ok=True)
        s8.to_csv(out / "rule_change.csv", index=False)
    summary = evaluate.summary(preds)
    out.mkdir(parents=True, exist_ok=True)
    folds.to_csv(out / "folds.csv", index=False)
    preds.to_parquet(out / "predictions.parquet", index=False)
    summary.to_csv(out / "summary.csv", index=False)
    reference = next((m for m in ("CatBoost", "S2") if m in set(preds.model)), None)
    versus = evaluate.summary(preds, reference=reference) if reference else None
    if versus is not None:
        versus.to_csv(out / f"summary_vs_{reference.lower()}.csv", index=False)
    (out / "report.md").write_text(write_report(folds, summary, args, versus, reference, s8), encoding="utf-8")
    (out / "args.json").write_text(json.dumps(vars(args), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{out}: {len(models)} моделей, {len(folds)} строк метрик")
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(summary.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
