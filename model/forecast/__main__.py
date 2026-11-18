import argparse
import json
from pathlib import Path

import pandas as pd

from . import evaluate
from .baselines import B0, B1, Cohort, Drift, ENet, Huber, Lin
from .features import GROUPS, group_features, load
from . import hybrid
from .models import CatBoostModel, ForestModel, MeanModel, RidgeModel, StackModel
from .report import write_report

S0 = group_features("grades", "context")
S1 = group_features("grades", "context", "achievements", "asu")
MODELS = {
    "B0": B0, "B1": B1, "B2": Drift, "B3": Lin, "B4": ENet, "B5": hybrid.ComponentPlugIn, "B6": Cohort,
    "Huber": Huber,
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
    "extra": "B0,B2,B3,B4,B5,B6,Huber",   # базовые уровни B2–B6 по плану доработки статьи и Huber
}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="forecast", description="Модели прогноза IGPA стенда IgpaLab")
    parser.add_argument("--version", default="v1")
    parser.add_argument("--data", default="/repo/data/synthetic")
    parser.add_argument("--name", default="baselines", help="прогон: " + ", ".join(RUNS) + ", review, transfer, stress, advice, recsys, export")
    parser.add_argument("--models", help="свой список моделей через запятую, из: " + ", ".join(MODELS))
    parser.add_argument("--disjoint", action="store_true", help="контроль: студенты проверки не входят в обучение")
    args = parser.parse_args(argv)

    if args.name == "export-research":   # только research.json для сайта, модели не трогаются
        from . import export
        export.research_only(Path("artifacts") / args.version, Path("results") / args.version)
        return
    d = load(Path(args.data) / args.version)
    if args.name.startswith("check-"):
        from . import checks
        d["_dir"] = Path(args.data) / args.version   # папка версии: проверкам нужны и таблицы вне features.TABLES
        getattr(checks, args.name[6:].replace("-", "_"))(d, Path("results") / args.version / "checks")
        return
    if args.name == "export":
        from . import export
        export.run(d, Path("artifacts") / args.version, Path("results") / args.version)
        return
    if args.name == "review":   # метрики по рецензии статьи на сохранённых прогнозах: results/v1/review
        from . import review
        review.run(d, Path("results") / args.version)
        return
    if args.name == "transfer":   # перенос: без факультета, бакалавриат → магистратура: results/v1/transfer
        from . import transfer
        transfer.run(d, Path("results") / args.version / "transfer")
        return
    if args.name == "hybrid-refresh":   # после нового прогона models: S8 и сводка hybrid с новыми CatBoost и Stack
        out = Path("results") / args.version / "hybrid"
        old = pd.read_parquet(out / "predictions.parquet")
        done = pd.read_parquet(out.parent / "models" / "predictions.parquet")
        preds = pd.concat([old[~old.model.isin(["CatBoost", "Stack"])],
                           done[done.model.isin(["CatBoost", "Stack"])]], ignore_index=True)
        assert not preds.duplicated(["rules", "layer", "model", "student_id"]).any()
        s8 = evaluate.rule_change(preds)
        summary = evaluate.summary(preds)
        versus = evaluate.summary(preds, reference="CatBoost")
        folds = pd.read_csv(out / "folds.csv")
        preds.to_parquet(out / "predictions.parquet", index=False)
        s8.to_csv(out / "rule_change.csv", index=False)
        summary.to_csv(out / "summary.csv", index=False)
        versus.to_csv(out / "summary_vs_catboost.csv", index=False)
        args.name = "hybrid"
        (out / "report.md").write_text(write_report(folds, summary, args, versus, "CatBoost", s8), encoding="utf-8")
        print(s8.round(4).to_string(index=False))
        return
    if args.name == "stress":   # смена правила + изменение поведения (+30% разовых SSCI): results/v1/stress
        from . import stress
        stress.run(d, Path("results") / args.version)
        return
    if args.name == "advice":   # ретроспективная оценка советов: results/v1/advice
        from . import advice
        advice.run(d, Path("results") / args.version / "advice")
        return
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
