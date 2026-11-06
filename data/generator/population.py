"""Студенты: уровень, когорта, факультет, ОП, форма и язык обучения, скрытые свойства."""

import numpy as np
import pandas as pd

LEVELS = ("bachelor", "master_research", "master_profile")


def program_table(university: dict) -> pd.DataFrame:
    """Все ОП с вероятностью выбора: вес факультета × доля ОП внутри факультета (отдельно бакалавриат и магистратура)."""
    rows = []
    for faculty in university["faculties"]:
        for group in ("bachelor", "master"):
            weights = {(school["name"], program): w
                       for school in faculty["schools"] for program, w in (school[group] or {}).items()}
            total = sum(weights.values())
            rows += [dict(group=group, faculty=faculty["name"], school=school, program=program,
                          weight=faculty["weight"] * w / total) for (school, program), w in weights.items()]
    return pd.DataFrame(rows)


def make_students(cfg: dict, rng: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Таблица студентов (то, что знает АСУ) и их скрытые свойства (истина стенда, в признаки не идёт)."""
    n = cfg["students"]
    intake = np.sort(rng.integers(cfg["first_intake"], cfg["last_intake"] + 1, n))
    level = rng.choice(LEVELS, n, p=[cfg["levels"][lv]["share"] for lv in LEVELS])
    group = np.where(level == "bachelor", "bachelor", "master")

    programs = program_table(cfg["university"])
    faculty, school, program, language, form = (np.empty(n, dtype=object) for _ in range(5))
    for g in ("bachelor", "master"):
        mask = group == g
        table = programs[programs.group == g]
        pick = rng.choice(len(table), mask.sum(), p=(table.weight / table.weight.sum()).to_numpy())
        faculty[mask] = table.faculty.to_numpy()[pick]
        school[mask] = table.school.to_numpy()[pick]
        program[mask] = table.program.to_numpy()[pick]
        for column, options in ((language, cfg["language"][g]), (form, cfg["form"][g])):
            column[mask] = rng.choice(list(options), mask.sum(), p=list(options.values()))

    lat = cfg["latent"]
    z = rng.multivariate_normal(np.zeros(len(lat["names"])), np.array(lat["corr"]), n)
    traits = dict(zip(lat["names"], z.T))
    for lv, shift in lat["level_shift"].items():
        for name, value in shift.items():
            traits[name][level == lv] += value
    for fac in cfg["university"]["faculties"]:
        for name, value in fac["shift"].items():
            traits[name][faculty == fac["name"]] += value
    athlete = rng.random(n) < np.clip(lat["athlete"]["base"] + lat["athlete"]["s"] * traits["s"], 0, 1)

    number = np.arange(1, n + 1)
    students = pd.DataFrame({
        "student_id": [f"S{i:06d}" for i in number],
        "fio": [f"Студент {i:06d}" for i in number],
        "faculty": faculty, "school": school, "program": program, "level": level,
        "intake_year": intake, "form": form, "language": language,
    })
    latent = pd.DataFrame({"student_id": students.student_id, "a": traits["a"], "r": traits["r"], "s": traits["s"],
                           "m0": traits["m"], "rep": traits["rep"], "athlete": athlete})
    return students, latent
