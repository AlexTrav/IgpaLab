"""Отчёт анализа данных в Markdown: числа и таблицы; выводы для моделей – в docs/research.md."""

import pandas as pd

from . import eda

GROUP_NAMES = {"none": "достижений не было", "hidden": "были, в АСУ нет ни одного", "part": "в АСУ часть",
               "full": "в АСУ все"}
RULE_NAMES = {"default": "буквально по Положению", "eduscore": "схема EduScore"}


def num(x, d=3):
    return "–" if pd.isna(x) else f"{x:.{d}f}".replace(".", ",")


def pct(x):
    return "–" if pd.isna(x) else f"{100 * x:.1f}%".replace(".", ",")


def table(header, rows):
    return ["| " + " | ".join(header) + " |", "|" + " --- |" * len(header),
            *["| " + " | ".join(str(v) for v in r) + " |" for r in rows], ""]


def build(d: dict, version: str) -> tuple[str, dict]:
    ov, comp, compl = eda.overview(d), eda.components(d), eda.completeness(d)
    dyn, assoc, prev = eda.dynamics(d), eda.associations(d), eda.preview(d)
    sat, appr, real, rec = eda.saturation(d), eda.approval(d), eda.real_scenario(d), eda.recovery(d)

    out = [f"# Анализ данных: версия {version}", "",
           "Отчёт собирается командой `make -C research report`. Рисунки: `figures/ru` (сайт) и `figures/en` (статья).", ""]
    out += ["## Объём", ""] + table(["Показатель", "Значение"], [
        ["Студентов", ov["students"]], ["Студенто-лет (завершённые годы)", ov["student_years"]],
        ["Переходов «год → следующий год»", ov["transitions"]],
        *[[f"Переходов из {y}/{y + 1}", n] for y, n in ov["transitions_by_year"].items()],
    ])

    out += ["## Состав IGPA при двух правилах (рисунки 1 и 2)", ""]
    out += table(["Правила", "Слой", "GPA", "iROS ср.", "iROS 90%", "iROS = 0", "SSCI ср.", "SSCI = 0", "IGPA ср.",
                  "IGPA ст. откл.", "Не объясняет GPA"],
                 [[RULE_NAMES[r.rules], "истина" if r.layer == "true" else "АСУ", num(r.gpa_mean, 2), num(r.iros_mean),
                   num(r.iros_p90), pct(r.iros_zero), num(r.ssci_mean), pct(r.ssci_zero), num(r.igpa_mean, 2),
                   num(r.igpa_sd), pct(r.achievement_share)] for r in comp.itertuples()])
    out += ["«Не объясняет GPA» – 1 − r²(GPA, IGPA): доля разброса IGPA, которую даёт не успеваемость.", ""]

    out += ["## Что видно в АСУ (рисунок 3)", ""]
    out += table(["Группа студенто-лет", "Доля"], [[GROUP_NAMES[k], pct(v)] for k, v in compl["groups"].items()])
    out += table(["Показатель", "Смещение АСУ − истина", "Корреляция АСУ и истины"],
                 [[k, num(compl["bias"][k]), num(compl["corr"][k])] for k in ("iros", "ssci", "igpa")])
    out += ["Доля внесённого по квартилям склонности вносить (скрытое свойство rep, только стенд): "
            + ", ".join(f"{q} {pct(v)}" for q, v in compl["entered_by_rep"].items()) + ".", ""]
    out += table(["Тип", "Внесено в АСУ"], [[c, pct(v)] for c, v in compl["entered_by_category"].items()])

    out += ["## Динамика год к году (рисунок 4)", ""]
    out += table(["Правила", "Переходов", "r GPA", "r iROS", "r SSCI", "r IGPA", "r IGPA по АСУ", "Среднее ΔIGPA",
                  "Ст. откл. ΔIGPA", "MAE наивного B0", "Риск (истина)", "Риск (АСУ)", "Совпадение риска"],
                 [[RULE_NAMES[r.rules], r.n, num(r.r_gpa, 2), num(r.r_true_iros, 2), num(r.r_true_ssci, 2),
                   num(r.r_true_igpa, 2), num(r.r_obs_igpa, 2), num(r.delta_mean), num(r.delta_sd), num(r.b0_mae),
                   pct(r.risk_true), pct(r.risk_obs), pct(r.risk_agree)] for r in dyn.itertuples()])

    out += ["## Связь признаков с будущим IGPA (рисунок 5)", "", "Ранговая корреляция Спирмена, правила по Положению.", ""]
    out += table(["Признак года t", "n", "с IGPA t+1", "с ΔIGPA", "с риском снижения"],
                 [[r.feature, r.n, num(r.igpa_next, 2), num(r.delta, 2), num(r.risk, 2)] for r in assoc.itertuples()])

    out += ["## Предварительная проверка H0", "",
            "Линейная модель, обучение на переходах до предпоследнего, проверка на последнем. Без подбора и интервалов: "
            "это ориентир, а не результат эксперимента.", ""]
    out += table(["Правила", "Модель", "MAE", "R²", "Тест"],
                 [[RULE_NAMES[r.rules], r.model, num(r.mae, 4), num(r.r2), r.n_test] for r in prev.itertuples()])

    out += ["## Предел «5 лучших в типе»", ""] + table(["Показатель", "Значение"], [
        ["Пар «студент, год, тип» с записями", sat["student_year_categories"]],
        ["Из них больше 5 записей", f"{sat['over_5']} ({pct(sat['over_5_share'])})"],
        ["Студенто-лет, где предел сработал", sat["student_years_affected"]],
        ["Максимум записей в типе за год", sat["max_in_category"]],
        ["Разовые типы: 3 и больше записей за год", pct(sat["share_one_time_ge3"])],
    ])

    out += ["## Согласование", ""] + table(["Показатель", "Значение"], [
        ["Внесение после события, медиана дней", num(appr["entry_delay_median"], 0)],
        ["Внесение после события, 90% дней", num(appr["entry_delay_p90"], 0)],
        ["Решение после внесения, медиана дней", num(appr["decision_days_median"], 0)],
        ["Решение после внесения, 90% дней", num(appr["decision_days_p90"], 0)],
        *[[f"Отклонено: {k}", pct(v)] for k, v in appr["rejected_by_error"].items()],
    ])

    out += ["## Сценарий «как в жизни» на «сегодня» (рисунок 6)", ""]
    out += table(["Группа", "Студентов", "С записями: раздел с 2021", "С записями: раздел с 01.09.2026"],
                 [[g, int(r.students), pct(r.main), pct(r.real)] for g, r in real.iterrows()])

    out += ["## Заложенные эффекты видны в сырых данных", "",
            "Изменение GPA к следующему семестру; сырые средние без поправок (a – скрытое свойство, только стенд).", ""]
    out += table(["Эффект", "Группа", "n", "Среднее изменение GPA"],
                 [[r.effect, r.group, r.n, num(r.change)] for r in rec.itertuples()])

    numbers = {"overview": ov, "components": comp.to_dict("records"), "completeness": {k: v for k, v in compl.items()
               if k in ("groups", "bias", "corr", "entered_by_rep")}, "dynamics": dyn.to_dict("records"),
               "preview": prev.to_dict("records"), "saturation": sat}
    return "\n".join(out), numbers
