"""Сборка версии датасета: население, история, два слоя АСУ, срезы; запись на диск."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from igpa import load_rules

from .asu import observe
from .common import academic_year
from .export import write_asu, write_tables
from .passport import passport
from .population import make_students
from .simulate import simulate
from .snapshots import gpa_tables, snapshots


def generate(cfg: dict) -> dict[str, pd.DataFrame]:
    """Вся версия датасета в памяти. Потоки случайных чисел у этапов свои: правка одного не сдвигает другие."""
    rng_population, rng_history, rng_asu, rng_real = map(np.random.default_rng,
                                                        np.random.SeedSequence(cfg["seed"]).spawn(4))
    students, latent = make_students(cfg, rng_population)
    history = simulate(students, latent, cfg, rng_history)
    records, enrollment = history["records_true"], history["enrollment"]
    asu, approvals = observe(records, students, enrollment, latent, cfg, rng_asu, cfg["asu_launch"])
    asu_real, approvals_real = observe(records, students, enrollment, latent, cfg, rng_real, cfg["real_launch"],
                                       shift=cfg["asu"]["real_shift"])

    rules = load_rules(cfg["rules"])
    sem_gpa, year_gpa = gpa_tables(history["courses"])
    layers = {"true": records, "obs": asu}
    current = academic_year(cfg["now"])
    past = [y for y in enrollment.year.unique() if y < current]
    semester = pd.concat([snapshots(enrollment, sem_gpa, year_gpa, layers, cfg, rules, part="fall"),
                          snapshots(enrollment, sem_gpa, year_gpa, layers, cfg, rules, part="spring", years=past)],
                         ignore_index=True)
    alternatives = {f"snapshots_year_{name}": snapshots(enrollment, sem_gpa, year_gpa, layers, cfg, load_rules(name))
                    for name in cfg["rules_alt"]}
    return {
        "students": students, "latent": latent, **history,
        "gpa_semester": sem_gpa, "gpa_year": year_gpa,
        "records_asu": asu, "approvals": approvals,
        "records_asu_real": asu_real, "approvals_real": approvals_real,
        "snapshots_year": snapshots(enrollment, sem_gpa, year_gpa, layers, cfg, rules),
        "snapshots_semester": semester.sort_values(["student_id", "year", "part"], kind="stable", ignore_index=True),
        "snapshots_real": snapshots(enrollment, sem_gpa, year_gpa, {"obs": asu_real}, cfg, rules, years=[current]),
        **alternatives,
    }


def ground_truth(data: dict, cfg: dict) -> str:
    latent = data["latent"][["a", "r", "s", "m0", "rep"]]
    return json.dumps({
        "version": cfg["version"], "seed": cfg["seed"], "students": cfg["students"],
        "config": {k: v for k, v in cfg.items() if k != "university"},
        "university": cfg["university"],
        "latent_corr_realized": np.corrcoef(latent.to_numpy().T).round(3).tolist(),
    }, ensure_ascii=False, indent=2, default=str)


def write_version(out: Path, data: dict, cfg: dict):
    write_tables(out, data)
    write_asu(out, data, cfg)
    (out / "ground_truth.json").write_text(ground_truth(data, cfg), encoding="utf-8")
    (out / "passport.md").write_text(passport(data, cfg), encoding="utf-8")
