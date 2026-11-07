"""Названия на трёх языках и шаблоны советов. Русские названия типов и статусов – из справочника igpa (АСУ).

Казахские термины сверены 07.11.2026: ЖЖОКБҰ – как в приказах МНВО (adilet.zan.kz), «волонтерлік» – как в законе
«Волонтерлік қызмет туралы» № 42-VI. В шаблонах советов падежные окончания после чисел не используются
(их форма зависит от произношения числа): «IGPA 2,05 мәніне дейін өседі (+0,233)».
"""

from igpa import CATEGORY_BY_CODE, STATUS_BY_CODE

LANGS = ("ru", "kk", "en")

CATEGORY = {
    "kk": {
        "IROS_EVENT": "Ғылыми іс-шараларға қатысу немесе ұйымдастыру",
        "IROS_TALK": "Баяндамамен сөйлеу",
        "IROS_PUBLICATION": "Жарияланымдар мен нәтижелер",
        "IROS_PROJECT": "Ғылыми жобалар мен стартаптарға қатысу",
        "IROS_INTERNSHIP": "Ғылыми тағылымдама",
        "IROS_PRIZE": "Ғылыми байқаулардағы жүлделі орын",
        "SSCI_VOLUNTEER": "Волонтерлік қозғалысқа қатысу",
        "SSCI_INTELLECTUAL": "Зияткерлік және дебаттық іс-шараларға қатысу",
        "SSCI_INTELLECTUAL_PRIZE": "Зияткерлік және дебаттық іс-шаралардағы жетістіктер",
        "SSCI_SPORT": "Спорттағы жетістіктер",
        "SSCI_SOCIAL_PROJECT": "Шығармашылық және әлеуметтік жобаларды ұйымдастыру",
        "SSCI_IMAGE_PROJECT": "Имидждік жобаларға қатысу",
        "SSCI_STUDENT_ORG": "Студенттік ұйымға мүшелік, топ старостасы",
        "SSCI_LEADERSHIP": "Студенттік ұйымға жетекшілік ету",
        "SSCI_UNIVERSITY_IMAGE": "Университет имиджіне үлес",
        "SSCI_UNIT_VOLUNTEER": "Құрылымдық бөлімшелердегі волонтерлік",
    },
    "en": {
        "IROS_EVENT": "Taking part in or organizing research events",
        "IROS_TALK": "Conference talk",
        "IROS_PUBLICATION": "Publications and results",
        "IROS_PROJECT": "Research projects and startups",
        "IROS_INTERNSHIP": "Research internship",
        "IROS_PRIZE": "Prize in research competitions",
        "SSCI_VOLUNTEER": "Volunteering",
        "SSCI_INTELLECTUAL": "Intellectual and debate events",
        "SSCI_INTELLECTUAL_PRIZE": "Awards in intellectual and debate events",
        "SSCI_SPORT": "Sports achievements",
        "SSCI_SOCIAL_PROJECT": "Organizing creative and social projects",
        "SSCI_IMAGE_PROJECT": "University image projects",
        "SSCI_STUDENT_ORG": "Student organization member, group head",
        "SSCI_LEADERSHIP": "Leading a student organization",
        "SSCI_UNIVERSITY_IMAGE": "Contribution to university image",
        "SSCI_UNIT_VOLUNTEER": "Volunteering in university units",
    },
}

STATUS = {
    "kk": {
        "IROS_OVPO": "ЖЖОКБҰ (университет)",
        "IROS_REP_CITY": "Республикалық, қалалық",
        "IROS_INT_RK": "Қазақстан Республикасындағы халықаралық",
        "IROS_INT_ABROAD": "Халықаралық, шетелде",
        "SSCI_UNIVERSITY": "Университеттік",
        "SSCI_CITY_REGION": "Қалалық, өңірлік",
        "SSCI_REPUBLIC": "Республикалық",
        "SSCI_INTERNATIONAL": "Халықаралық",
        "SSCI_PERMANENT": "Тұрақты жүзеге асырылатын университеттік жобалар аясында (жыл бойы)",
    },
    "en": {
        "IROS_OVPO": "University (HEI)",
        "IROS_REP_CITY": "National, city",
        "IROS_INT_RK": "International in Kazakhstan",
        "IROS_INT_ABROAD": "International, abroad",
        "SSCI_UNIVERSITY": "University",
        "SSCI_CITY_REGION": "City, regional",
        "SSCI_REPUBLIC": "National",
        "SSCI_INTERNATIONAL": "International",
        "SSCI_PERMANENT": "Ongoing university projects (whole year)",
    },
}

RULES = {
    "default": {"ru": "Положение", "kk": "Ереже", "en": "Regulation"},
    "eduscore": {"ru": "Схема EduScore", "kk": "EduScore схемасы", "en": "EduScore scheme"},
    "percentile": {"ru": "Лучшие 5% = 100%", "kk": "Үздік 5% = 100%", "en": "Top 5% = 100%"},
}

RULE_NOTES = {
    "default": {"ru": "Буквально по Положению «Туран»: 5 лучших записей в каждом типе, доля от 100 баллов.",
                "kk": "«Тұран» Ережесі бойынша: әр түрде ең жақсы 5 жазба, 100 балдан үлес.",
                "en": "Literal Turan regulation: best 5 records per type, share of 100 points."},
    "eduscore": {"ru": "Как в EduScore: 5 лучших записей по всему направлению, деление на максимум.",
                 "kk": "EduScore сияқты: бағыт бойынша ең жақсы 5 жазба, максимумға бөлу.",
                 "en": "As in EduScore: best 5 records across the area, divided by the maximum."},
    "percentile": {"ru": "Положение, но 100% iROS или SSCI получает студент на уровне лучших 5% вуза.",
                   "kk": "Ереже, бірақ iROS немесе SSCI 100% университеттің үздік 5% деңгейіндегі студентке беріледі.",
                   "en": "Regulation, but 100% iROS or SSCI goes to a student at the university's top 5% level."},
}

FEATURE = {
    "ru": {"gpa": "GPA года", "gpa_prev": "GPA прошлого года", "gpa_trend": "Изменение GPA за год",
           "has_history": "Есть прошлый год", "year_of_study": "Курс", "master": "Магистрант", "level": "Уровень",
           "n_research": "Научных записей", "n_one_time": "Разовых SSCI", "n_permanent": "Постоянных проектов",
           "iros": "iROS", "ssci": "SSCI", "igpa": "IGPA года", "gpa_fall": "GPA осеннего семестра",
           "gpa_spring": "GPA весеннего семестра", "sem_trend": "Весна минус осень", "gpa_cum": "Накопленный GPA",
           "fx_count": "Оценок FX и F", "min_score": "Минимальный балл", "low_count": "Баллов ниже 65",
           "failed_credits": "Несданные кредиты", "iros_prev": "iROS прошлого года", "ssci_prev": "SSCI прошлого года",
           "igpa_prev": "IGPA прошлого года", "igpa_trend": "Изменение IGPA за год",
           "n_research_prev": "Научных записей в прошлом году", "n_one_time_prev": "Разовых SSCI в прошлом году",
           "n_permanent_prev": "Постоянных проектов в прошлом году", "asu_records": "Записей в АСУ",
           "asu_has_records": "Есть записи в АСУ", "asu_delay": "Задержка внесения",
           "asu_rejected_share": "Доля отклонённых", "asu_pending_share": "Доля ожидающих",
           "faculty": "Факультет", "form": "Форма обучения", "language": "Язык обучения"},
    "kk": {"gpa": "Жылдық GPA", "gpa_prev": "Өткен жылғы GPA", "gpa_trend": "GPA-ның жылдық өзгерісі",
           "has_history": "Өткен жыл бар", "year_of_study": "Курс", "master": "Магистрант", "level": "Деңгей",
           "n_research": "Ғылыми жазбалар саны", "n_one_time": "Бір реттік SSCI саны",
           "n_permanent": "Тұрақты жобалар саны", "iros": "iROS", "ssci": "SSCI", "igpa": "Жылдық IGPA",
           "gpa_fall": "Күзгі семестр GPA", "gpa_spring": "Көктемгі семестр GPA", "sem_trend": "Көктем минус күз",
           "gpa_cum": "Жинақталған GPA", "fx_count": "FX және F бағалары", "min_score": "Ең төмен балл",
           "low_count": "65-тен төмен балдар", "failed_credits": "Тапсырылмаған кредиттер",
           "iros_prev": "Өткен жылғы iROS", "ssci_prev": "Өткен жылғы SSCI", "igpa_prev": "Өткен жылғы IGPA",
           "igpa_trend": "IGPA-ның жылдық өзгерісі", "n_research_prev": "Өткен жылғы ғылыми жазбалар",
           "n_one_time_prev": "Өткен жылғы бір реттік SSCI", "n_permanent_prev": "Өткен жылғы тұрақты жобалар",
           "asu_records": "АБЖ-дағы жазбалар", "asu_has_records": "АБЖ-да жазба бар",
           "asu_delay": "Енгізу кешігуі", "asu_rejected_share": "Қабылданбағандар үлесі",
           "asu_pending_share": "Күтудегілер үлесі", "faculty": "Факультет", "form": "Оқу нысаны",
           "language": "Оқу тілі"},
    "en": {"gpa": "Year GPA", "gpa_prev": "Previous-year GPA", "gpa_trend": "GPA change over year",
           "has_history": "Has previous year", "year_of_study": "Year of study", "master": "Master's student",
           "level": "Level", "n_research": "Research records", "n_one_time": "One-time SSCI",
           "n_permanent": "Permanent projects", "iros": "iROS", "ssci": "SSCI", "igpa": "Year IGPA",
           "gpa_fall": "Fall GPA", "gpa_spring": "Spring GPA", "sem_trend": "Spring minus fall",
           "gpa_cum": "Cumulative GPA", "fx_count": "FX and F grades", "min_score": "Lowest score",
           "low_count": "Scores below 65", "failed_credits": "Failed credits", "iros_prev": "Previous iROS",
           "ssci_prev": "Previous SSCI", "igpa_prev": "Previous IGPA", "igpa_trend": "IGPA change over year",
           "n_research_prev": "Previous research records", "n_one_time_prev": "Previous one-time SSCI",
           "n_permanent_prev": "Previous permanent projects", "asu_records": "Records in system",
           "asu_has_records": "Has records in system", "asu_delay": "Entry delay",
           "asu_rejected_share": "Rejected share", "asu_pending_share": "Pending share", "faculty": "Faculty",
           "form": "Study form", "language": "Language"},
}

POINTS_PREFIX = {"ru": "Баллы", "kk": "Балдар", "en": "Points"}
COUNT_PREFIX = {"ru": "Записей", "kk": "Жазбалар", "en": "Records"}


def category_name(code: str, lang: str) -> str:
    return CATEGORY_BY_CODE[code].name if lang == "ru" else CATEGORY[lang][code]


def status_name(code: str, lang: str) -> str:
    return STATUS_BY_CODE[code].asu_name if lang == "ru" else STATUS[lang][code]


def feature_name(feature: str, lang: str) -> str:
    if feature.startswith("pts_"):
        return f"{POINTS_PREFIX[lang]}: {category_name(feature[4:], lang)}"
    if feature.startswith("cnt_"):
        return f"{COUNT_PREFIX[lang]}: {category_name(feature[4:], lang)}"
    return FEATURE[lang].get(feature, feature)


def number(value: float, lang: str, digits: int = 2) -> str:
    text = f"{value:.{digits}f}"
    return text if lang == "en" else text.replace(".", ",")


def advice(kind: str, lang: str, gain: float, new: float, feasibility: float, category: str | None = None,
           status: str | None = None, step: float | None = None) -> str:
    """Текст совета: числа даёт расчёт, шаблон их только формулирует."""
    g, n, p = number(gain, lang, 3), number(new, lang, 2), round(100 * feasibility)
    if kind == "gpa":
        s = number(step, lang, 1)
        head = {"ru": f"Если поднимете GPA на {s}, IGPA вырастет на {g} (до {n}).",
                "kk": f"GPA-ны {s} балға көтерсеңіз, IGPA {n} мәніне дейін өседі (+{g}).",
                "en": f"Raise GPA by {s} and IGPA grows by {g} (to {n})."}[lang]
    else:
        c, st = category_name(category, lang), status_name(status, lang)
        head = {"ru": f"Если добавите «{c}» ({st}), IGPA вырастет на {g} (до {n}).",
                "kk": f"«{c}» ({st}) қоссаңыз, IGPA {n} мәніне дейін өседі (+{g}).",
                "en": f"Add “{c}” ({st}) and IGPA grows by {g} (to {n})."}[lang]
    tail = {"ru": f"Так получается у {p}% похожих студентов.",
            "kk": f"Ұқсас студенттердің {p} пайызы бұған қол жеткізеді.",
            "en": f"{p}% of similar students achieve this."}[lang]
    return f"{head} {tail}"
