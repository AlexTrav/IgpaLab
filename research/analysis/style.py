"""Оформление рисунков: эталонная палитра dataviz (светлая поверхность, для статьи и сайта) и подписи ru/en."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SURFACE = "#fcfcfb"
INK, INK_2, INK_3 = "#0b0b0b", "#52514e", "#8a8984"
GRID = "#e6e5e0"
# категориальные слоты 1–3 проходят проверку различимости для всех пар (в том числе при дальтонизме)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
DIVERGING = ("#2a78d6", "#f0efec", "#e34948")   # синий – отрицательные, красный – положительные
SEQUENTIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]


def setup():
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.edgecolor": INK_3, "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
        "text.color": INK, "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
        "lines.linewidth": 2, "legend.frameon": False, "figure.dpi": 110, "savefig.dpi": 200,
        "savefig.bbox": "tight",
    })


LABELS = {
    "ru": {
        "gpa_part": "0,5·GPA", "iros_part": "1,4·iROS", "ssci_part": "0,6·SSCI",
        "rule_default": "Буквально по Положению", "rule_eduscore": "Схема EduScore",
        "f1_title": "Из чего складывается IGPA", "f1_x": "Средний вклад в IGPA (шкала 0–4)",
        "f2_title": "Распределение IGPA при двух правилах нормировки", "f2_x": "IGPA за учебный год",
        "f2_y": "Студенто-лет", "f3_title": "Что видно в АСУ", "f3_y": "Доля студенто-лет",
        "f3_none": "Достижений не было", "f3_hidden": "Были, в АСУ нет", "f3_part": "В АСУ часть",
        "f3_full": "В АСУ все",
        "f4_title": "IGPA соседних лет", "f4_x": "IGPA в году t", "f4_y": "IGPA в году t+1",
        "f4_diag": "без изменений", "f4_risk": "снижение на 0,1 и больше",
        "f5_title": "Связь признаков года t с изменением IGPA к году t+1",
        "f5_x": "Ранговая корреляция Спирмена",
        "f6_title": "Сценарий «как в жизни»: у кого есть записи в АСУ", "f6_y": "Доля студентов с записями",
        "f6_main": "Раздел работает с 2021 года", "f6_real": "Раздел открыт 01.09.2026",
    },
    "en": {
        "gpa_part": "0.5·GPA", "iros_part": "1.4·iROS", "ssci_part": "0.6·SSCI",
        "rule_default": "Literal regulation", "rule_eduscore": "EduScore scheme",
        "f1_title": "What IGPA is made of", "f1_x": "Mean contribution to IGPA (0–4 scale)",
        "f2_title": "IGPA distribution under two normalization rules", "f2_x": "IGPA per academic year",
        "f2_y": "Student-years", "f3_title": "What the university system sees", "f3_y": "Share of student-years",
        "f3_none": "No achievements", "f3_hidden": "Achievements, none recorded", "f3_part": "Some recorded",
        "f3_full": "All recorded",
        "f4_title": "IGPA in consecutive years", "f4_x": "IGPA in year t", "f4_y": "IGPA in year t+1",
        "f4_diag": "no change", "f4_risk": "drop of 0.1 or more",
        "f5_title": "Year-t features vs IGPA change to year t+1",
        "f5_x": "Spearman rank correlation",
        "f6_title": "Real-life scenario: who has records in the system", "f6_y": "Share of students with records",
        "f6_main": "Section live since 2021", "f6_real": "Section opened 1 Sep 2026",
    },
}

FEATURES = {
    "ru": {"gpa": "GPA года", "gpa_trend": "Изменение GPA за год", "gpa_cum_prev": "Накопленный GPA",
           "iros": "iROS", "ssci": "SSCI", "n_research": "Научных достижений", "n_one_time": "Разовых SSCI",
           "n_permanent": "Постоянных проектов", "year_of_study": "Курс", "master": "Магистрант",
           "obs_share": "Доля внесённого в АСУ"},
    "en": {"gpa": "Year GPA", "gpa_trend": "GPA change over year", "gpa_cum_prev": "Cumulative GPA",
           "iros": "iROS", "ssci": "SSCI", "n_research": "Research achievements", "n_one_time": "One-time SSCI",
           "n_permanent": "Permanent projects", "year_of_study": "Year of study", "master": "Master's student",
           "obs_share": "Share recorded in system"},
}

GROUPS = {
    "ru": {"bachelor_1": "Бакалавры 1 курс", "bachelor_2": "Бакалавры 2 курс", "bachelor_3": "Бакалавры 3 курс",
           "bachelor_4": "Бакалавры 4 курс", "master_1": "Магистранты 1 год", "master_2": "Магистранты 2 год"},
    "en": {"bachelor_1": "Bachelor yr 1", "bachelor_2": "Bachelor yr 2", "bachelor_3": "Bachelor yr 3",
           "bachelor_4": "Bachelor yr 4", "master_1": "Master yr 1", "master_2": "Master yr 2"},
}
