"""Шаг 7: объяснения SHAP, восстановление заложенных эффектов, серия S7 (нормировка), проверка рекомендаций на стенде."""

import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from catboost import CatBoostRegressor, Pool  # noqa: E402

from generator.common import load_config  # noqa: E402
from generator.snapshots import gpa_tables, snapshots  # noqa: E402
from igpa import CATEGORY_BY_CODE, STATUS_BY_CODE, load_rules  # noqa: E402

from . import recommend as R  # noqa: E402
from .features import CATEGORICAL, build, transitions  # noqa: E402
from .hybrid import RULE_DEPENDENT  # noqa: E402
from .models import SEED, CatBoostModel  # noqa: E402
from .protocol import FINAL  # noqa: E402

RULES3 = ("default", "eduscore", "percentile")
SURFACE, INK, INK_2 = "#fcfcfb", "#0b0b0b", "#52514e"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
TXT = {
    "ru": {"default": "Положение", "eduscore": "Схема EduScore", "percentile": "Положение с потолком 95%",
           "shap_title": "Что влияет на прогноз риска снижения IGPA", "shap_x": "Средний |SHAP| (вклад в логит риска)",
           "rec_title": "Ожидаемый прирост IGPA от первого совета", "rec_y": "Прирост × реалистичность",
           "norm_title": "Сколько разброса IGPA дают достижения", "norm_y": "Доля разброса IGPA не от GPA"},
    "en": {"default": "Regulation", "eduscore": "EduScore scheme", "percentile": "Regulation, 95% ceiling",
           "shap_title": "What drives the predicted risk of an IGPA drop", "shap_x": "Mean |SHAP| (risk log-odds)",
           "rec_title": "Expected IGPA gain from the top advice", "rec_y": "Gain × feasibility",
           "norm_title": "How much IGPA variance achievements carry", "norm_y": "Share of IGPA variance not from GPA"},
}
STRATEGY_EN = {"Наша: прирост × реалистичность": "Ours: gain × feasibility", "Только прирост по формуле": "Formula gain only",
               "Самое частое достижение": "Most common achievement", "Случайное действие": "Random action"}


def log(msg: str):
    print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)


def normalization(d: dict) -> pd.DataFrame:
    """Серия S7: те же студенты и записи, три правила нормировки; состав IGPA, доля достижений, доля снижения."""
    cfg = load_config()
    sem, year = gpa_tables(d["courses"])
    rows = []
    for name in RULES3:
        snap = snapshots(d["enrollment"], sem, year, {"true": d["records_true"], "obs": d["records_asu"]}, cfg,
                         load_rules(name))
        s = snap[~snap.partial]
        wide = s.pivot(index="student_id", columns="year", values="true_igpa")
        drops = np.concatenate([(wide[y + 1] - wide[y]).dropna() for y in wide.columns[:-1]])
        for layer in ("true", "obs"):
            rows.append({"rules": name, "layer": layer, "iros_mean": s[f"{layer}_iros"].mean(),
                         "ssci_mean": s[f"{layer}_ssci"].mean(), "igpa_mean": s[f"{layer}_igpa"].mean(),
                         "igpa_sd": s[f"{layer}_igpa"].std(),
                         "achievement_share": 1 - np.corrcoef(s.gpa, s[f"{layer}_igpa"])[0, 1] ** 2,
                         "iros_full_share": (s[f"{layer}_iros"] >= 0.999).mean(),
                         "risk_share": float((drops <= -0.1).mean()) if layer == "true" else np.nan})
        log(f"S7: правила {name} посчитаны")
    return pd.DataFrame(rows)


def shap_global(d: dict) -> tuple[pd.DataFrame, dict]:
    """SHAP CatBoost (обучение на годах до последней проверки) для изменения IGPA и риска во всех постановках."""
    rows, per_student = [], {}
    for rules in ("default", "eduscore"):
        for layer in ("true", "obs"):
            panel, features = build(d, rules, layer)
            data = transitions(panel)
            train, test = data[data.year < FINAL], data[data.year == FINAL]
            model = CatBoostModel().fit(train, features)
            X = model._X(test)
            pool = Pool(X, cat_features=model.cats)
            for task, booster in (("delta", model.reg), ("risk", model.clf)):
                values = booster.get_feature_importance(pool, type="ShapValues")[:, :-1]
                imp = np.abs(values).mean(axis=0)
                rows += [{"rules": rules, "layer": layer, "task": task, "feature": f, "mean_abs_shap": v}
                         for f, v in zip(model.features, imp)]
                if layer == "obs":
                    per_student[(rules, task)] = pd.DataFrame(values, columns=model.features).assign(
                        student_id=test.student_id.to_numpy())
            log(f"SHAP: {rules}/{layer} готов")
    return pd.DataFrame(rows), per_student


def recovery(d: dict, latent: pd.DataFrame) -> pd.DataFrame:
    """Находит ли SHAP заложенные в генератор эффекты на GPA следующего года (только стенд: известна истина)."""
    panel, features = build(d, "default", "true")
    feats = [f for f in features if f not in RULE_DEPENDENT and not f.startswith("pts_")]
    data = transitions(panel)
    train, test = data[data.year < FINAL], data[data.year == FINAL]
    cats = [c for c in CATEGORICAL if c in feats]

    def X(f):
        out = f[feats].copy()
        for c in cats:
            out[c] = out[c].astype(str)
        return out
    model = CatBoostRegressor(depth=6, learning_rate=0.05, iterations=800, random_seed=SEED, verbose=False,
                              thread_count=-1, allow_writing_files=False, cat_features=cats)
    model.fit(X(train), train.gpa_next - train.gpa)
    shap = pd.DataFrame(model.get_feature_importance(Pool(X(test), cat_features=cats), type="ShapValues")[:, :-1],
                        columns=feats)
    a = test.student_id.map(latent.set_index("student_id").a).to_numpy()
    strong, research, social = a > 0.5, test.n_research.to_numpy(), test.n_one_time.to_numpy()
    rows = [
        {"effect": "научные достижения → GPA (у сильных)", "group": "a > 0,5, научных ≥ 1",
         "n": int((strong & (research >= 1)).sum()), "mean_shap": shap.n_research[strong & (research >= 1)].mean()},
        {"effect": "научные достижения → GPA (у сильных)", "group": "a > 0,5, научных 0",
         "n": int((strong & (research == 0)).sum()), "mean_shap": shap.n_research[strong & (research == 0)].mean()},
        {"effect": "перегрузка разовыми SSCI → GPA", "group": "разовых > 3",
         "n": int((social > 3).sum()), "mean_shap": shap.n_one_time[social > 3].mean()},
        {"effect": "перегрузка разовыми SSCI → GPA", "group": "разовых ≤ 3",
         "n": int((social <= 3).sum()), "mean_shap": shap.n_one_time[social <= 3].mean()},
    ]
    return pd.DataFrame(rows)


def recommendations(d: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """По трём правилам: проверка следования совету, качество реалистичности, топ-1 действий, примеры советов."""
    follow_rows, quality_rows, top_rows, examples = [], [], [], []
    for name in RULES3:
        rules = load_rules(name)
        panel, _ = build(d, "default", "true")    # портфель и GPA от правил не зависят; IGPA пересчитывается по name
        data = transitions(panel)
        train, test = data[data.year < FINAL], data[data.year == FINAL]
        portfolio = R.Portfolio(d["records_true"], rules)
        feas = R.Feasibility(train, portfolio)
        f = R.follow(test, portfolio, feas).assign(rules=name)
        follow_rows.append(f)
        q = R.feasibility_quality(test, portfolio, feas)
        quality_rows.append({"rules": name, **q})
        rec = R.recommend(test, portfolio, feas).assign(rules=name)
        top = rec[rec["rank"] == 1]
        label = np.where(top.kind == "gpa", "GPA +" + top.gpa_step.astype(str),
                         top.category.fillna("") + " / " + top.status.fillna(""))
        top_rows.append(pd.Series(label).value_counts(normalize=True).head(5).rename_axis("action")
                        .reset_index(name="share").assign(rules=name))
        examples.append(rec)
        log(f"Рекомендации: правила {name} готовы")
    return (pd.concat(follow_rows), pd.DataFrame(quality_rows), pd.concat(top_rows), pd.concat(examples))


def action_name(category, status, step) -> str:
    if category is None or (isinstance(category, float) and np.isnan(category)):
        return f"GPA +{step:.1f}".replace(".", ",")
    return f"{CATEGORY_BY_CODE[category].name} ({STATUS_BY_CODE[status].asu_name})"


def advice_text(row, lang: str = "ru") -> str:
    """Шаблон текста совета: числа даёт расчёт, текст их только формулирует."""
    pct = round(100 * row.feasibility)
    if lang == "en":
        what = f"raise GPA by {row.gpa_step:.1f}" if row.kind == "gpa" else f"add {row.category} ({row.status})"
        return f"If you {what}, IGPA rises by {row.gain:.3f} to {row.igpa_now + row.gain:.2f}; {pct}% of similar students manage this."
    comma = lambda v, d: f"{v:.{d}f}".replace(".", ",")
    what = (f"поднимете GPA на {comma(row.gpa_step, 1)}" if row.kind == "gpa"
            else f"добавите «{action_name(row.category, row.status, None)}»")
    return (f"Если {what}, IGPA вырастет на {comma(row.gain, 3)} до {comma(row.igpa_now + row.gain, 2)}; "
            f"у похожих студентов так получается в {pct}% случаев.")


def _setup():
    plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
                         "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                         "grid.color": "#e6e5e0", "axes.axisbelow": True, "font.size": 10, "axes.titlesize": 11,
                         "axes.titleweight": "bold", "axes.titlelocation": "left", "legend.frameon": False,
                         "savefig.dpi": 200, "savefig.bbox": "tight", "text.color": INK, "axes.labelcolor": INK_2,
                         "xtick.color": INK_2, "ytick.color": INK_2})


def _two_lines(label: str) -> str:
    words = label.split(" ")
    half = (len(words) + 1) // 2
    return " ".join(words[:half]) + "\n" + " ".join(words[half:])


def _pretty_action(label: str) -> str:
    """«CATEGORY / STATUS» или «GPA +0.2» – в человеческое название."""
    if label.startswith("GPA"):
        return label.replace(".", ",")
    code, status = label.split(" / ")
    return action_name(code, status, None)


def rerender(out: Path):
    """Пересобрать рисунки и отчёт из сохранённых результатов, без пересчёта."""
    norm = pd.read_csv(out / "normalization.csv")
    shap = pd.read_csv(out / "shap_global.csv")
    rec = pd.read_csv(out / "recovery.csv")
    follow = pd.read_parquet(out / "follow.parquet")
    quality = pd.read_csv(out / "feasibility_quality.csv")
    top = pd.read_csv(out / "top_actions.csv")
    examples = pd.read_parquet(out / "recommendations.parquet")
    figures(shap, follow, norm, out, FEATURE_NAMES)
    (out / "report.md").write_text(report(norm, shap, rec, follow, quality, top, examples), encoding="utf-8")


def figures(shap: pd.DataFrame, follow: pd.DataFrame, norm: pd.DataFrame, out: Path, feature_names: dict):
    _setup()
    for lang, T in TXT.items():
        folder = out / "figures" / lang
        folder.mkdir(parents=True, exist_ok=True)
        dec = (lambda v: f"{v:.2f}".replace(".", ",")) if lang == "ru" else (lambda v: f"{v:.2f}")

        s = shap[(shap.rules == "default") & (shap.layer == "obs") & (shap.task == "risk")].nlargest(12, "mean_abs_shap")
        fig, ax = plt.subplots(figsize=(7.2, 4))
        names = [feature_names[lang].get(f, f) for f in s.feature][::-1]
        ax.barh(names, s.mean_abs_shap[::-1], color=SERIES[0], height=0.6, edgecolor=SURFACE, linewidth=2)
        for y, v in enumerate(s.mean_abs_shap[::-1]):
            ax.text(v, y, " " + dec(v), va="center", color=INK_2, fontsize=8)
        ax.set_title(T["shap_title"])
        ax.set_xlabel(T["shap_x"])
        ax.grid(axis="y", visible=False)
        if lang == "ru":
            ax.xaxis.set_major_formatter(lambda v, _: f"{v:.2f}".replace(".", ","))
        fig.savefig(folder / "fig7_shap_risk.png")
        plt.close(fig)

        # честная метрика: прирост, если совет выполнен, × доля похожих студентов, кому это удаётся
        g = follow.groupby(["rules", "strategy"], sort=False).expected_realized.mean().unstack(0)[list(RULES3)]
        fig, ax = plt.subplots(figsize=(7.2, 3.6))
        x = np.arange(len(g))
        for k, (rules, color) in enumerate(zip(RULES3, SERIES)):
            ax.bar(x + (k - 1) * 0.26, g[rules], width=0.26, color=color, label=T[rules], edgecolor=SURFACE, linewidth=2)
        labels = g.index if lang == "ru" else [STRATEGY_EN[s] for s in g.index]
        ax.set_xticks(x, [_two_lines(lbl) for lbl in labels], fontsize=8)
        ax.set_ylabel(T["rec_y"])
        ax.set_title(T["rec_title"])
        ax.grid(axis="x", visible=False)
        if lang == "ru":
            ax.yaxis.set_major_formatter(lambda v, _: f"{v:.3f}".replace(".", ","))
        ax.legend(ncol=3, loc="upper left", bbox_to_anchor=(0, -0.3))
        fig.savefig(folder / "fig8_recommendations.png")
        plt.close(fig)

        n = norm[norm.layer == "true"].set_index("rules").loc[list(RULES3)]
        fig, ax = plt.subplots(figsize=(7.2, 2.6))
        ax.barh([T[r] for r in n.index][::-1], n.achievement_share[::-1], color=SERIES[0], height=0.55,
                edgecolor=SURFACE, linewidth=2)
        for y, v in enumerate(n.achievement_share[::-1]):
            ax.text(v + 0.01, y, f"{100 * v:.0f}%", va="center", color=INK)
        ax.set_xlim(0, 1)
        ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
        ax.set_title(T["norm_title"])
        ax.set_xlabel(T["norm_y"])
        ax.grid(axis="y", visible=False)
        fig.savefig(folder / "fig9_normalization.png")
        plt.close(fig)


FEATURE_NAMES = {
    "ru": {"gpa": "GPA года", "gpa_fall": "GPA осеннего семестра", "gpa_spring": "GPA весеннего семестра",
           "sem_trend": "Весна минус осень", "gpa_cum": "Накопленный GPA", "gpa_prev": "GPA прошлого года",
           "gpa_trend": "Изменение GPA за год", "fx_count": "Оценок FX и F", "min_score": "Минимальный балл",
           "low_count": "Баллов ниже 65", "failed_credits": "Несданные кредиты", "iros": "iROS", "ssci": "SSCI",
           "igpa": "IGPA года", "iros_prev": "iROS прошлого года", "ssci_prev": "SSCI прошлого года",
           "igpa_prev": "IGPA прошлого года", "igpa_trend": "Изменение IGPA за год",
           "n_research": "Научных записей", "n_one_time": "Разовых SSCI", "n_permanent": "Постоянных проектов",
           "n_research_prev": "Научных записей в прошлом году", "n_one_time_prev": "Разовых SSCI в прошлом году",
           "n_permanent_prev": "Постоянных проектов в прошлом году", "asu_records": "Записей в АСУ",
           "asu_has_records": "Есть записи в АСУ", "asu_delay": "Задержка внесения",
           "asu_rejected_share": "Доля отклонённых", "asu_pending_share": "Доля ожидающих",
           "year_of_study": "Курс", "master": "Магистрант", "has_history": "Есть прошлый год", "level": "Уровень",
           "faculty": "Факультет", "form": "Форма обучения", "language": "Язык обучения",
           **{f"pts_{c}": f"Баллы: {cat.name}" for c, cat in CATEGORY_BY_CODE.items()}},
    "en": {"gpa": "Year GPA", "gpa_fall": "Fall GPA", "gpa_spring": "Spring GPA", "sem_trend": "Spring minus fall",
           "gpa_cum": "Cumulative GPA", "gpa_prev": "Previous-year GPA", "gpa_trend": "GPA change over year",
           "fx_count": "FX and F grades", "min_score": "Lowest score", "low_count": "Scores below 65",
           "failed_credits": "Failed credits", "iros": "iROS", "ssci": "SSCI", "igpa": "Year IGPA",
           "iros_prev": "Previous iROS", "ssci_prev": "Previous SSCI", "igpa_prev": "Previous IGPA",
           "igpa_trend": "IGPA change over year", "n_research": "Research records", "n_one_time": "One-time SSCI",
           "n_permanent": "Permanent projects", "n_research_prev": "Previous research records",
           "n_one_time_prev": "Previous one-time SSCI", "n_permanent_prev": "Previous permanent projects",
           "asu_records": "Records in system", "asu_has_records": "Has records in system",
           "asu_delay": "Entry delay", "asu_rejected_share": "Rejected share", "asu_pending_share": "Pending share",
           "year_of_study": "Year of study", "master": "Master's student", "has_history": "Has previous year",
           "level": "Level", "faculty": "Faculty", "form": "Study form", "language": "Language",
           **{f"pts_{c}": f"Points: {c}" for c in CATEGORY_BY_CODE}},
}


def run(d: dict, latent: pd.DataFrame, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    norm = normalization(d)
    norm.to_csv(out / "normalization.csv", index=False)
    shap, per_student = shap_global(d)
    shap.to_csv(out / "shap_global.csv", index=False)
    for (rules, task), values in per_student.items():
        values.to_parquet(out / f"shap_{rules}_{task}.parquet", index=False)
    rec = recovery(d, latent)
    rec.to_csv(out / "recovery.csv", index=False)
    log("Восстановление эффектов готово")
    follow, quality, top, examples = recommendations(d)
    follow.to_parquet(out / "follow.parquet", index=False)
    quality.to_csv(out / "feasibility_quality.csv", index=False)
    top.to_csv(out / "top_actions.csv", index=False)
    examples.to_parquet(out / "recommendations.parquet", index=False)
    figures(shap, follow, norm, out, FEATURE_NAMES)
    (out / "report.md").write_text(report(norm, shap, rec, follow, quality, top, examples), encoding="utf-8")
    log(f"{out}: отчёт и рисунки готовы")


def report(norm, shap, rec, follow, quality, top, examples) -> str:
    def num(x, k=3):
        return "–" if pd.isna(x) else f"{x:.{k}f}".replace(".", ",")

    def pct(x):
        return "–" if pd.isna(x) else f"{100 * x:.1f}%".replace(".", ",")

    def table(header, rows):
        return ["| " + " | ".join(header) + " |", "|" + " --- |" * len(header),
                *["| " + " | ".join(str(v) for v in r) + " |" for r in rows], ""]

    T = TXT["ru"]
    out = ["# Шаг 7: объяснения, рекомендации, нормировка", "",
           "Отчёт собирается командой `make -C model recsys`. Рисунки: `figures/ru`, `figures/en`.", ""]
    out += ["## Серия S7: три правила нормировки (рисунок 9)", "",
            "Те же студенты и записи. «Положение с потолком 95%»: 100% iROS или SSCI у студента на уровне лучших 5% вуза.", ""]
    out += table(["Правила", "Слой", "iROS ср.", "SSCI ср.", "IGPA ср.", "IGPA ст. откл.", "Доля разброса от достижений",
                  "iROS = 1", "Снижение ≥ 0,1"],
                 [[T[r.rules], "истина" if r.layer == "true" else "АСУ", num(r.iros_mean), num(r.ssci_mean),
                   num(r.igpa_mean, 2), num(r.igpa_sd), pct(r.achievement_share), pct(r.iros_full_share),
                   pct(r.risk_share)] for r in norm.itertuples()])

    out += ["## SHAP: главные признаки (рисунок 7)", "", "Средний |SHAP| на последней проверке, слой АСУ.", ""]
    for rules in ("default", "eduscore"):
        for task in ("delta", "risk"):
            s = shap[(shap.rules == rules) & (shap.layer == "obs") & (shap.task == task)].nlargest(8, "mean_abs_shap")
            out += [f"{T[rules]}, {'изменение IGPA' if task == 'delta' else 'риск снижения'}: "
                    + "; ".join(f"{FEATURE_NAMES['ru'].get(f, f)} {num(v)}" for f, v in zip(s.feature, s.mean_abs_shap)), ""]

    out += ["## Восстановление заложенных эффектов", "",
            "SHAP модели изменения GPA к следующему году (истина, правила не важны). Знак должен совпасть с генератором: "
            "научная активность у сильных студентов повышает GPA, перегрузка разовыми SSCI снижает.", ""]
    out += table(["Эффект", "Группа", "n", "Средний SHAP признака"],
                 [[r.effect, r.group, r.n, num(r.mean_shap, 4)] for r in rec.itertuples()])

    out += ["## Рекомендации: проверка следованием (рисунок 8)", "",
            "Студент последней проверки выполняет одно действие; реальный прирост – на его фактическом портфеле и GPA "
            "следующего года. «С учётом реалистичности» – прирост × доля похожих студентов, кому это удаётся.", ""]
    g = follow.groupby(["rules", "strategy"], sort=False).agg(
        claimed=("claimed", "mean"), realized=("realized", "mean"), expected=("expected_realized", "mean"),
        positive=("realized", lambda s: (s > 1e-9).mean()), feas=("feasibility", "mean")).reset_index()
    out += table(["Правила", "Стратегия", "Заявленный прирост", "Реальный прирост", "Доля с приростом",
                  "Реалистичность", "С учётом реалистичности"],
                 [[T[r.rules], r.strategy, num(r.claimed, 4), num(r.realized, 4), pct(r.positive), pct(r.feas),
                   num(r.expected, 4)] for r in g.itertuples()])
    out += ["Качество реалистичности (предсказывает ли она, что студент действительно получит достижение):", ""]
    out += table(["Правила", "ROC-AUC", "Средняя реалистичность", "Фактическая доля"],
                 [[T[r.rules], num(r.auc_records), pct(r.mean_feasibility), pct(r.observed_rate)]
                  for r in quality.itertuples()])
    out += ["## Что чаще всего советуется первым", ""]
    out += table(["Правила", "Действие", "Доля студентов"], [[T[r.rules], _pretty_action(r.action), pct(r.share)] for r in top.itertuples()])
    first = examples[examples.rules == "default"]
    first = first[first.student_id == first.student_id.iloc[0]]
    out += ["## Пример советов (Положение, один студент)", ""]
    out += [f"- {advice_text(r)}" for r in first.itertuples()] + [""]
    return "\n".join(out)
