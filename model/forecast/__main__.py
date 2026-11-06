import argparse
import json
from pathlib import Path

import pandas as pd

from . import evaluate
from .baselines import B0, B1
from .features import GROUPS, group_features, load
from .models import CatBoostModel, ForestModel, MeanModel, RidgeModel, StackModel
from .report import write_report

S0 = group_features("grades", "context")
S1 = group_features("grades", "context", "achievements", "asu")
MODELS = {
    "B0": B0, "B1": B1,
    "Ridge": RidgeModel, "RF": ForestModel, "CatBoost": CatBoostModel,
    "Stack": StackModel, "Mean": MeanModel,
    "CatBoost-level": lambda: CatBoostModel(target="level"),
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
}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="forecast", description="Модели прогноза IGPA стенда IgpaLab")
    parser.add_argument("--version", default="v1")
    parser.add_argument("--data", default="/repo/data/synthetic")
    parser.add_argument("--name", default="baselines", help="прогон: " + ", ".join(RUNS))
    parser.add_argument("--models", help="свой список моделей через запятую, из: " + ", ".join(MODELS))
    parser.add_argument("--disjoint", action="store_true", help="контроль: студенты проверки не входят в обучение")
    args = parser.parse_args(argv)

    d = load(Path(args.data) / args.version)
    models = {m: MODELS[m] for m in (args.models or RUNS[args.name]).split(",")}
    folds, preds = evaluate.run(d, models, disjoint=args.disjoint)
    summary = evaluate.summary(preds)
    out = Path("results") / args.version / (args.name + ("_disjoint" if args.disjoint else ""))
    out.mkdir(parents=True, exist_ok=True)
    folds.to_csv(out / "folds.csv", index=False)
    preds.to_parquet(out / "predictions.parquet", index=False)
    summary.to_csv(out / "summary.csv", index=False)
    reference = next((m for m in ("CatBoost", "S2") if m in models), None)
    versus = evaluate.summary(preds, reference=reference) if reference else None
    if versus is not None:
        versus.to_csv(out / f"summary_vs_{reference.lower()}.csv", index=False)
    (out / "report.md").write_text(write_report(folds, summary, args, versus, reference), encoding="utf-8")
    (out / "args.json").write_text(json.dumps(vars(args), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{out}: {len(models)} моделей, {len(folds)} строк метрик")
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(summary.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
