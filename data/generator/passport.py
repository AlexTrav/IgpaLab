"""Паспорт данных версии: состав, распределения, полнота АСУ, доля снижения IGPA."""

import pandas as pd

from igpa import CATEGORIES, CATEGORY_BY_CODE, STATUS_BY_CODE

from .common import year_label

LEVEL_NAMES = {"bachelor": "Бакалавриат", "master_research": "Магистратура научно-педагогическая",
               "master_profile": "Магистратура профильная"}
OUTCOMES = {"promoted": "переведён", "repeat": "повторный курс", "graduated": "выпущен", "expelled": "отчислен",
            "dropout": "ушёл сам", "current": "учится сейчас"}


def num(x, digits: int = 2) -> str:
    return "–" if pd.isna(x) else f"{x:.{digits}f}".replace(".", ",")


def pct(x) -> str:
    return "–" if pd.isna(x) else f"{100 * x:.1f}%".replace(".", ",")


def table(header: list[str], rows: list[list]) -> list[str]:
    return ["| " + " | ".join(header) + " |", "|" + " --- |" * len(header),
            *["| " + " | ".join(str(v) for v in row) + " |" for row in rows], ""]


def passport(data: dict, cfg: dict) -> str:
    students, enrollment = data["students"], data["enrollment"]
    true, asu, real = data["records_true"], data["records_asu"], data["records_asu_real"]
    snap = data["snapshots_year"]
    done = snap[~snap.partial]
    out = [f"# Паспорт данных {cfg['version']}", "",
           "Синтетические данные стенда IgpaLab: реальных студентов здесь нет. Допущения и заложенные эффекты: "
           "`ground_truth.json`, обоснование: `docs/data.md`.", ""]

    out += ["## Параметры", ""] + table(["Параметр", "Значение"], [
        ["Seed", cfg["seed"]], ["Студентов", len(students)],
        ["Когорты", f"{cfg['first_intake']}–{cfg['last_intake']}"], ["«Сегодня»", cfg["now"]],
        ["Запуск раздела IGPA: основной слой", cfg["asu_launch"]],
        ["Запуск раздела IGPA: сценарий «как в жизни»", cfg["real_launch"]],
        ["Правила расчёта IGPA (igpa)", cfg["rules"]],
    ])

    out += ["## Студенты", ""]
    by_level = students.level.value_counts()
    out += table(["Уровень", "Студентов", "Доля"],
                 [[LEVEL_NAMES[k], v, pct(v / len(students))] for k, v in by_level.items()])
    by_fac = students.groupby(["faculty", "level"]).size().unstack(fill_value=0)
    out += table(["Факультет", *[LEVEL_NAMES[c] for c in by_fac.columns]],
                 [[f, *row] for f, row in zip(by_fac.index, by_fac.to_numpy().tolist())])
    flow = enrollment.groupby(["year", "outcome"]).size().unstack(fill_value=0)
    cols = [c for c in OUTCOMES if c in flow.columns]
    out += ["Движение по учебным годам (строка: сколько студентов училось в году и чем год закончился):", ""]
    out += table(["Год", "Учились", *[OUTCOMES[c] for c in cols]],
                 [[year_label(y), int(flow.loc[y].sum()), *[int(flow.loc[y, c]) for c in cols]] for y in flow.index])

    out += ["## GPA по учебным годам", ""]
    g = data["gpa_year"].groupby("year").gpa
    out += table(["Год", "Студентов", "Среднее", "Ст. откл.", "10%", "Медиана", "90%"],
                 [[year_label(y), len(s), num(s.mean()), num(s.std()), num(s.quantile(.1)), num(s.median()),
                   num(s.quantile(.9))] for y, s in g])

    out += ["## Достижения", "",
            "Истинные – что было на самом деле; в АСУ – внесённые в основном слое (с ошибками и дублями).", ""]
    asu_counts = asu.category.value_counts()
    real_counts = real.category.value_counts()
    true_counts = true.category.value_counts()
    rows = []
    for c in CATEGORIES:
        levels = true[true.category == c.code].status.value_counts(normalize=True)
        top = ", ".join(f"{STATUS_BY_CODE[s].asu_name} {pct(v)}" for s, v in levels.head(2).items())
        rows.append([c.column, c.name, int(true_counts.get(c.code, 0)), int(asu_counts.get(c.code, 0)),
                     int(real_counts.get(c.code, 0)), top])
    out += table(["Кол.", "Тип", "Истинных", "В АСУ", "В АСУ «как в жизни»", "Чаще всего"], rows)
    per_year = true.groupby(["student_id", "year"]).size()
    out += [f"Записей на студента в год (у кого есть хотя бы одна): {num(per_year.mean())}; "
            f"студентов-лет без единого достижения: {pct(1 - len(per_year) / len(enrollment))}.", ""]

    out += ["## Полнота и качество АСУ (основной слой)", ""]
    original = asu[asu.gt_error != "duplicate"]
    out += table(["Показатель", "Значение"], [
        ["Доля истинных достижений, внесённых в АСУ", pct(original.true_record_id.nunique() / len(true))],
        ["Ошибка типа (похожий тип)", pct(asu.gt_error.str.contains("wrong_category").mean())],
        ["Статус «чужой» карты", pct(asu.gt_error.str.contains("foreign_status").mean())],
        ["Дубли", pct((asu.gt_error == "duplicate").mean())],
        *[[f"Статус записей на «сегодня»: {k}", pct(v)] for k, v in asu.state_now.value_counts(normalize=True).items()],
    ])

    out += ["## Срезы на конец учебного года", "",
            "Достижения за учебный год, IGPA с годовым GPA. «Нет в АСУ» – доля студентов с нулём согласованных записей.", ""]
    rows = []
    for y, s in done.groupby("year"):
        rows.append([year_label(y), len(s), num(s.true_iros.mean()), num(s.obs_iros.mean()), num(s.true_ssci.mean()),
                     num(s.obs_ssci.mean()), num(s.true_igpa.mean()), num(s.obs_igpa.mean()), pct((s.obs_approved == 0).mean())])
    out += table(["Год", "Студентов", "iROS ист.", "iROS АСУ", "SSCI ист.", "SSCI АСУ", "IGPA ист.", "IGPA АСУ",
                  "Нет в АСУ"], rows)

    out += ["## Правила расчёта меняют вес достижений", "",
            "Те же данные, истинный слой, все завершённые годы. Доля дисперсии IGPA от достижений: "
            "1 − дисперсия(0,5·GPA) / дисперсия(IGPA), грубая оценка без учёта ковариации.", ""]
    rows = []
    for name in [cfg["rules"], *cfg["rules_alt"]]:
        s = done if name == cfg["rules"] else data[f"snapshots_year_{name}"].query("not partial")
        share = 1 - (0.5 * s.gpa).var() / s.true_igpa.var()
        rows.append([name, num(s.true_iros.mean()), num(s.true_iros.quantile(.9)), num(s.true_ssci.mean()),
                     num(s.true_igpa.mean()), num(s.true_igpa.std()), pct(share)])
    out += table(["Правила", "iROS среднее", "iROS 90%", "SSCI среднее", "IGPA среднее", "IGPA ст. откл.",
                  "Доля от достижений"], rows)

    out += ["## Снижение IGPA (задача B)", "", "Доля студентов, у которых IGPA следующего года ниже на 0,1 и больше.", ""]
    rows = []
    for layer, name in (("true", "истинный"), ("obs", "по АСУ")):
        wide = done.pivot(index="student_id", columns="year", values=f"{layer}_igpa")
        for y in wide.columns[:-1]:
            delta = (wide[y + 1] - wide[y]).dropna()
            rows.append([name, f"{year_label(y)} → {year_label(y + 1)}", len(delta), pct((delta <= -0.1).mean()),
                         num(delta.mean(), 3)])
    out += table(["IGPA", "Переход", "Студентов", "Снижение ≥ 0,1", "Среднее изменение"], rows)

    out += ["## Сценарий «как в жизни»", "",
            f"Раздел IGPA открыт {cfg['real_launch']}, прошлое вносят задним числом. На «сегодня» в АСУ "
            f"{len(real)} записей от {real.student_id.nunique()} студентов; в текущем учебном году "
            f"{int((real.year == real.year.max()).sum())} записей.", ""]
    perm = true[true.category.map(lambda c: CATEGORY_BY_CODE[c].block.value) == "permanent"]
    out += [f"Справочно: постоянных проектов (U–Y) в истинной истории {len(perm)}.", ""]
    return "\n".join(out)
