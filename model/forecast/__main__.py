import argparse
import json
from pathlib import Path

import pandas as pd

from . import evaluate
from .baselines import B0, B1
from .features import load
from .report import write_report

MODELS = {"B0": B0, "B1": B1}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="forecast", description="Модели прогноза IGPA стенда IgpaLab")
    parser.add_argument("--version", default="v1")
    parser.add_argument("--data", default="/repo/data/synthetic")
    parser.add_argument("--models", default=",".join(MODELS), help="через запятую, из: " + ", ".join(MODELS))
    parser.add_argument("--name", default="baselines", help="имя прогона: results/<версия>/<имя>")
    parser.add_argument("--disjoint", action="store_true", help="контроль: студенты проверки не входят в обучение")
    args = parser.parse_args(argv)

    d = load(Path(args.data) / args.version)
    models = {m: MODELS[m] for m in args.models.split(",")}
    folds, preds = evaluate.run(d, models, disjoint=args.disjoint)
    summary = evaluate.summary(preds)
    out = Path("results") / args.version / (args.name + ("_disjoint" if args.disjoint else ""))
    out.mkdir(parents=True, exist_ok=True)
    folds.to_csv(out / "folds.csv", index=False)
    preds.to_parquet(out / "predictions.parquet", index=False)
    summary.to_csv(out / "summary.csv", index=False)
    (out / "report.md").write_text(write_report(folds, summary, args), encoding="utf-8")
    (out / "args.json").write_text(json.dumps(vars(args), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{out}: {len(models)} моделей, {len(folds)} строк метрик")
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(summary.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
