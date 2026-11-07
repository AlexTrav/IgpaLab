import datetime as dt
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).parent
TEMPLATES = HERE.parent / "example"


def _merge(base: dict, extra: dict) -> dict:
    """Вложенное слияние: словари сливаются по ключам, остальное заменяется."""
    out = dict(base)
    for k, v in extra.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load_config(path: str | Path | None = None, **overrides) -> dict:
    """Конфиг генератора и структура университета; overrides (students, seed, version) перекрывают YAML.

    Файл с ключом base – надстройка: перекрывает только указанные параметры базового конфига (путь от папки файла).
    """
    path = Path(path or HERE / "config.yaml")
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    if "base" in cfg:
        cfg = _merge(load_config(path.parent / cfg.pop("base")), cfg)
        cfg.pop("university")
    cfg.update({k: v for k, v in overrides.items() if v is not None})
    cfg["university"] = yaml.safe_load((HERE / "university.yaml").read_text(encoding="utf-8"))
    return cfg


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


def academic_year(day: dt.date) -> int:
    """Учебный год по дате: 2026 означает 2026/2027."""
    return day.year if day.month >= 9 else day.year - 1


def on(year: int, month_day: str) -> dt.date:
    """Дата внутри учебного года year: сентябрь–декабрь – того же года, январь–август – следующего."""
    month, day = map(int, month_day.split("-"))
    return dt.date(year if month >= 9 else year + 1, month, day)


def year_label(year: int) -> str:
    return f"{year}/{year + 1}"
