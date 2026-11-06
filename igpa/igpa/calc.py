"""Расчёт iROS, SSCI и IGPA по записям достижений одного студента за один период.

Период (учебный год, семестр, всё обучение) выбирает вызывающий код: сюда передаются уже отобранные записи.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping

from .catalog import CATEGORIES, CATEGORY_BY_CODE, STATUS_BY_CODE, Block, Profile, categories, statuses
from .rules import Rules, load_rules


@dataclass(frozen=True)
class Record:
    """Запись профиля АСУ: тип мероприятия, статус (уровень) и согласована ли она."""
    category: str
    status: str
    approved: bool = True


class FlagKind(str, Enum):
    NOT_APPROVED = "not_approved"        # запись не согласована
    NO_RULE = "no_rule"                  # у типа нулевой вес: в этих правилах он не считается
    STATUS_MAPPED = "status_mapped"      # статус чужой карты сопоставлен со своим
    STATUS_MISMATCH = "status_mismatch"  # статус не подходит типу, запись не учтена
    OVER_LIMIT = "over_limit"            # сверх предела учитываемых достижений


@dataclass(frozen=True)
class Flag:
    index: int  # номер записи во входном списке
    kind: FlagKind


@dataclass(frozen=True)
class CategoryScore:
    code: str
    points: float        # сумма баллов учтённых записей
    counted: int         # сколько записей учтено
    contribution: float  # вклад в iROS или SSCI (в долях от 1)


@dataclass(frozen=True)
class IgpaResult:
    gpa: float
    iros: float
    ssci: float
    igpa: float
    gpa_part: float
    iros_part: float
    ssci_part: float
    categories: Mapping[str, CategoryScore]
    flags: tuple[Flag, ...]
    rules_version: str


@dataclass(frozen=True)
class _Scored:
    index: int
    category: str
    status: str
    points: float


def igpa_parts(gpa: float, iros: float, ssci: float, rules: Rules) -> tuple[float, float, float]:
    """Вклады GPA, iROS и SSCI в IGPA (п. 5.4, шкала задаётся rules.scale)."""
    return (rules.weight_gpa * gpa,
            rules.weight_iros * iros * rules.scale,
            rules.weight_ssci * ssci * rules.scale)


def igpa_value(gpa: float, iros: float, ssci: float, rules: Rules | None = None) -> float:
    return sum(igpa_parts(gpa, iros, ssci, rules or load_rules()))


def calculate(records: Iterable[Record], gpa: float, rules: Rules | None = None) -> IgpaResult:
    rules = rules or load_rules()
    if not 0 <= gpa <= 4:
        raise ValueError(f"GPA {gpa} вне шкалы от 0 до 4")
    flags: list[Flag] = []
    scored = _resolve(list(records), rules, flags)
    if rules.method == "category":
        per_category = _by_category(scored, rules, flags)
    else:
        per_category = _by_direction(scored, rules, flags)

    per_category = _apply_ceiling(per_category, Profile.IROS, rules.ceiling_iros)
    per_category = _apply_ceiling(per_category, Profile.SSCI, rules.ceiling_ssci)
    iros = sum(per_category[c.code].contribution for c in categories(profile=Profile.IROS))
    ssci = sum(per_category[c.code].contribution for c in categories(profile=Profile.SSCI))
    parts = igpa_parts(gpa, iros, ssci, rules)
    return IgpaResult(gpa=gpa, iros=iros, ssci=ssci, igpa=sum(parts),
                      gpa_part=parts[0], iros_part=parts[1], ssci_part=parts[2],
                      categories=per_category, flags=tuple(sorted(flags, key=lambda f: f.index)),
                      rules_version=rules.version)


def _apply_ceiling(per_category: dict, profile: Profile, ceiling: float) -> dict:
    """Потолок нормировки: значение направления делится на ceiling и обрезается до 1; вклады типов – в той же пропорции."""
    if ceiling >= 1:
        return per_category
    codes = [c.code for c in categories(profile=profile)]
    total = sum(per_category[c].contribution for c in codes)
    if total == 0:
        return per_category
    factor = min(1.0, total / ceiling) / total
    out = dict(per_category)
    for code in codes:
        s = out[code]
        out[code] = CategoryScore(s.code, s.points, s.counted, s.contribution * factor)
    return out


def _resolve(records: list[Record], rules: Rules, flags: list[Flag]) -> list[_Scored]:
    scored = []
    for index, record in enumerate(records):
        category = CATEGORY_BY_CODE.get(record.category)
        status = STATUS_BY_CODE.get(record.status)
        if category is None or status is None:
            raise ValueError(f"запись {index}: неизвестный тип {record.category!r} или статус {record.status!r}")
        if rules.only_approved and not record.approved:
            flags.append(Flag(index, FlagKind.NOT_APPROVED))
            continue
        if rules.category_weights[category.code] == 0:
            flags.append(Flag(index, FlagKind.NO_RULE))
            continue
        status_code = status.code
        if status.family is not category.block:
            mapped = rules.status_map.get(category.block, {}).get(status.code)
            if rules.foreign_status == "reject" or mapped is None:
                flags.append(Flag(index, FlagKind.STATUS_MISMATCH))
                continue
            flags.append(Flag(index, FlagKind.STATUS_MAPPED))
            status_code = mapped
        scored.append(_Scored(index, category.code, status_code, rules.points[status_code]))
    return scored


def _by_category(scored: list[_Scored], rules: Rules, flags: list[Flag]) -> dict[str, CategoryScore]:
    """Метод Положения: в каждом типе до top_n лучших записей, доля от category_cap, веса блока в сумме 1."""
    grouped = defaultdict(list)
    for s in scored:
        grouped[s.category].append(s)

    result, block_total = {}, Counter()
    for category in CATEGORIES:
        total, counted = 0.0, 0
        for rank, s in enumerate(sorted(grouped[category.code], key=lambda s: -s.points)):
            if rank >= rules.top_n or total >= rules.category_cap:
                flags.append(Flag(s.index, FlagKind.OVER_LIMIT))
                continue
            total += s.points
            counted += 1
        contribution = rules.block_weight(category.code) * min(total, rules.category_cap) / rules.category_cap
        result[category.code] = CategoryScore(category.code, total, counted, contribution)
        block_total[category.block] += contribution

    # SSCI собирается из двух частей, у каждой веса в сумме 1
    one_time, permanent = block_total[Block.ONE_TIME], block_total[Block.PERMANENT]
    if rules.ssci_blocks == "mean":
        factor = 0.5
    else:
        factor = 1.0 if one_time + permanent <= 1 else 1 / (one_time + permanent)
    for category in categories(profile=Profile.SSCI):
        r = result[category.code]
        result[category.code] = CategoryScore(r.code, r.points, r.counted, r.contribution * factor)
    return result


def _by_direction(scored: list[_Scored], rules: Rules, flags: list[Flag]) -> dict[str, CategoryScore]:
    """Метод EduScore: эффективный балл = баллы × вес, top_n лучших по направлению, деление на максимум."""
    points, counted, contribution = Counter(), Counter(), Counter()
    for profile in Profile:
        per_key, effective = Counter(), []
        for s in (s for s in scored if CATEGORY_BY_CODE[s.category].profile is profile):
            key = (s.category, s.status)
            if per_key[key] >= rules.max_count[CATEGORY_BY_CODE[s.category].block]:
                flags.append(Flag(s.index, FlagKind.OVER_LIMIT))
                continue
            per_key[key] += 1
            effective.append((s.points * rules.category_weights[s.category], s))
        effective.sort(key=lambda e: -e[0])
        maximum = eduscore_max(rules, profile)
        for rank, (value, s) in enumerate(effective):
            if rank >= rules.top_n:
                flags.append(Flag(s.index, FlagKind.OVER_LIMIT))
                continue
            points[s.category] += s.points
            counted[s.category] += 1
            contribution[s.category] += value / maximum
    return {c.code: CategoryScore(c.code, float(points[c.code]), counted[c.code], contribution[c.code])
            for c in CATEGORIES}


def eduscore_max(rules: Rules, profile: Profile) -> float:
    """Максимум суммы top_n эффективных баллов по направлению с учётом max_count (computeMaxPossible в EduScore)."""
    values = []
    for category in categories(profile=profile):
        weight = rules.category_weights[category.code]
        repeats = min(rules.max_count[category.block], rules.top_n)
        for status in statuses(category.block):
            values += [rules.points[status.code] * weight] * repeats
    values.sort(reverse=True)
    return sum(values[:rules.top_n])
