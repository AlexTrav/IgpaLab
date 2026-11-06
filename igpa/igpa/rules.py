"""Правила расчёта IGPA: веса, баллы и режимы. Загружаются из YAML: готовый набор из presets/ или свой файл."""

import math
from dataclasses import dataclass, replace
from importlib import resources
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

import yaml

from .catalog import CATEGORY_BY_CODE, STATUS_BY_CODE, Block, categories

PRESETS = ("default", "eduscore")
METHODS = ("category", "eduscore")
SSCI_BLOCKS = ("mean", "sum_clip")
FOREIGN_STATUS = ("map", "reject")


@dataclass(frozen=True)
class Rules:
    version: str
    weight_gpa: float
    weight_iros: float
    weight_ssci: float
    scale: float
    method: str
    top_n: int
    category_cap: float
    ssci_blocks: str
    foreign_status: str
    only_approved: bool
    points: Mapping[str, float]
    category_weights: Mapping[str, float]
    max_count: Mapping[Block, int]
    status_map: Mapping[Block, Mapping[str, str]]

    def __post_init__(self):
        # словари замораживаются, чтобы правила нельзя было поменять мимо with_changes и проверки
        freeze = lambda d: MappingProxyType(dict(d))
        object.__setattr__(self, "points", freeze(self.points))
        object.__setattr__(self, "category_weights", freeze(self.category_weights))
        object.__setattr__(self, "max_count", freeze({Block(k): v for k, v in self.max_count.items()}))
        object.__setattr__(self, "status_map",
                           freeze({Block(k): freeze(v) for k, v in self.status_map.items()}))
        self._validate()

    def _validate(self):
        _check(self.method in METHODS, f"method: {self.method!r}, ожидается одно из {METHODS}")
        _check(self.ssci_blocks in SSCI_BLOCKS, f"ssci_blocks: {self.ssci_blocks!r}, ожидается одно из {SSCI_BLOCKS}")
        _check(self.foreign_status in FOREIGN_STATUS,
               f"foreign_status: {self.foreign_status!r}, ожидается одно из {FOREIGN_STATUS}")
        weights = (self.weight_gpa, self.weight_iros, self.weight_ssci)
        _check(min(weights) >= 0 and math.isclose(sum(weights), 1.0), f"веса GPA, iROS, SSCI {weights}: сумма должна быть 1")
        _check(self.scale > 0 and self.top_n >= 1 and self.category_cap > 0, "scale, top_n, category_cap должны быть > 0")
        _check(set(self.points) == set(STATUS_BY_CODE), "points: нужны баллы ровно для 9 статусов АСУ")
        _check(min(self.points.values()) > 0, "points: баллы должны быть > 0")
        _check(set(self.category_weights) == set(CATEGORY_BY_CODE), "category_weights: нужны веса ровно для 16 типов АСУ")
        _check(min(self.category_weights.values()) >= 0, "category_weights: веса не могут быть отрицательными")
        for block in Block:
            total = sum(self.category_weights[c.code] for c in categories(block=block))
            _check(total > 0, f"category_weights: в блоке {block.value} все веса нулевые")
        _check(set(self.max_count) == set(Block) and min(self.max_count.values()) >= 1,
               "max_count: нужно значение >= 1 для каждого блока")
        for block, mapping in self.status_map.items():
            for src, dst in mapping.items():
                _check(src in STATUS_BY_CODE and dst in STATUS_BY_CODE, f"status_map.{block.value}: неизвестный статус")
                _check(STATUS_BY_CODE[src].family is not block, f"status_map.{block.value}: {src} уже статус этого блока")
                _check(STATUS_BY_CODE[dst].family is block, f"status_map.{block.value}: {dst} не статус этого блока")

    def block_weight(self, code: str) -> float:
        """Вес типа в методе category: доля в сумме весов его блока, по блоку в сумме 1 (п. 3.7)."""
        block = CATEGORY_BY_CODE[code].block
        total = sum(self.category_weights[c.code] for c in categories(block=block))
        return self.category_weights[code] / total

    def with_changes(self, **changes) -> "Rules":
        return replace(self, **changes)


def _check(condition: bool, message: str):
    if not condition:
        raise ValueError(f"Правила IGPA: {message}")


def load_rules(source: str | Path = "default") -> Rules:
    """Правила из набора presets/<имя>.yaml или из своего YAML-файла."""
    if isinstance(source, str) and source in PRESETS:
        text = resources.files(__package__).joinpath("presets", f"{source}.yaml").read_text(encoding="utf-8")
    else:
        text = Path(source).read_text(encoding="utf-8")
    raw = yaml.safe_load(text)
    weights = raw.pop("weights")
    return Rules(weight_gpa=weights["gpa"], weight_iros=weights["iros"], weight_ssci=weights["ssci"],
                 status_map=raw.pop("status_map") or {}, **raw)
