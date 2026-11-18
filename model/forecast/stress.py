"""Стресс-тест смены правила с изменением поведения (план доработки статьи, 19.11.2026).

Арифметическая переносимость (серия S8): правило расчёта меняется (Положение → EduScore), поведение студентов
прежнее – гибриду достаточно сменить калькулятор. Поведенческая: студенты подстраиваются под новое правило.
Сценарии: в учебном году 2025/26 (цель последней проверки) у студентов на 30% больше (а) разовых SSCI-записей,
(б) записей всех типов – к случайным 30% таких записей года добавлены дубли (новый record_id, та же дата и
уровень) в истинном слое и в АСУ; срез 2025 года по EduScore пересчитан. Признаки 2024 года и обучающие годы
не меняются.

Сравнение на последней проверке, слой АСУ, цель – IGPA 2025/26 по EduScore в исходном и сдвинутых сценариях:
B0; CatBoost и Stack, обученные по Положению, с переносом прогноза изменения на текущий IGPA по EduScore; они
же, переобученные по EduScore (ориентир, недостижим сразу после смены правила); IGPA-Hybrid с калькулятором
EduScore без переобучения; IGPA-Hybrid с поправкой частот сдвинутых типов ×1,3 (если сдвиг поведения известен
заранее, например из пилотного семестра).
"""

import time
from pathlib import Path

import numpy as np
import pandas as pd

from generator.common import load_config
from generator.snapshots import gpa_tables, snapshots
from igpa import CATEGORIES, Block, load_rules

from . import hybrid
from . import protocol as P
from .features import build, transitions

LAYER = "obs"
SHIFT_YEAR = P.FINAL + 1     # учебный год цели последней проверки
SHARE = 0.3
BASE = "исходное поведение"
ONE_TIME = [c.code for c in CATEGORIES if c.block is Block.ONE_TIME]
ALL = [c.code for c in CATEGORIES]
SCENARIOS = {"+30% разовых SSCI": ONE_TIME, "+30% записей всех типов": ALL}


def _new_ids(ids: pd.Series, n: int, start) -> np.ndarray:
    if pd.api.types.is_numeric_dtype(ids):
        return np.arange(n) + int(start) + 1
    return np.array([f"stress-{i}" for i in range(n)], dtype=object)


def shifted(d: dict, codes=ONE_TIME, share: float = SHARE, seed: int = 0) -> tuple[dict, dict]:
    """Копия данных: +share записей типов codes в году SHIFT_YEAR (дубли в истине и в АСУ) и пересчёт среза."""
    rng = np.random.default_rng(seed)
    true, asu = d["records_true"], d["records_asu"]
    pool = true[(true.year == SHIFT_YEAR) & true.category.isin(codes)]
    picked = pool.sample(int(round(share * len(pool))), random_state=int(rng.integers(1 << 31)))
    new_true = picked.copy()
    new_true["record_id"] = _new_ids(true.record_id, len(picked), true.record_id.max() if len(true) else 0)
    mapping = dict(zip(picked.record_id, new_true.record_id))
    dup = asu[asu.true_record_id.isin(mapping)].copy()
    dup["true_record_id"] = dup.true_record_id.map(mapping)
    dup["record_id"] = _new_ids(asu.record_id, len(dup), asu.record_id.max() if len(asu) else 0)
    out = {**d, "records_true": pd.concat([true, new_true], ignore_index=True),
           "records_asu": pd.concat([asu, dup], ignore_index=True)}
    sem, year = gpa_tables(d["courses"])
    snap = snapshots(d["enrollment"], sem, year, {"true": out["records_true"], "obs": out["records_asu"]},
                     load_config(), load_rules("eduscore"), years=[SHIFT_YEAR])
    table = d["snapshots_year_eduscore"].copy().set_index(["student_id", "year"])
    snap = snap.set_index(["student_id", "year"])
    cols = [c for c in snap.columns if c in table.columns and c not in ("part", "date", "partial")]
    table.update(snap[cols])
    out["snapshots_year_eduscore"] = table.reset_index()
    return out, {"added_true": len(new_true), "added_asu": len(dup), "pool": len(pool)}


def run(d: dict, results: Path):
    out = results / "stress"
    out.mkdir(parents=True, exist_ok=True)
    preds = pd.concat([pd.read_parquet(results / run / "predictions.parquet") for run in ("models", "hybrid")])
    preds = preds[preds.layer == LAYER]

    def pick(rules, model):
        return preds[(preds.rules == rules) & (preds.model == model)].drop_duplicates("student_id").set_index("student_id")

    hybrid.prepare(d)   # обучающие годы в сдвиге не меняются: компоненты те же
    panel, features = build(d, "eduscore", LAYER)
    data = transitions(panel)
    train, test = data[data.year < P.FINAL], data[data.year == P.FINAL]
    ids = test.student_id.to_numpy()

    igpa_b = test.set_index("student_id").igpa.loc[ids]
    common = {"B0 (IGPA по EduScore не изменится)": igpa_b.to_numpy()}
    for m in ("CatBoost", "Stack"):
        a, b = pick("default", m).loc[ids], pick("eduscore", m).loc[ids]
        common[f"{m}, обучен по Положению, перенос изменения"] = (igpa_b + (a.pred - a.igpa)).to_numpy()
        common[f"{m}, переобучен по EduScore (ориентир)"] = b.pred.to_numpy()
    common["IGPA-Hybrid, калькулятор EduScore"] = hybrid.HybridModel().fit(train, features).predict(test)

    targets = {BASE: test.set_index("student_id").igpa_next.loc[ids].to_numpy()}
    corrected, infos = {}, []
    for scenario, codes in SCENARIOS.items():
        d_shift, info = shifted(d, codes)
        infos.append({"scenario": scenario, **info})
        st = transitions(build(d_shift, "eduscore", LAYER)[0])
        targets[scenario] = st[st.year == P.FINAL].set_index("student_id").igpa_next.loc[ids].to_numpy()
        corrected[scenario] = hybrid.HybridModel(rate_scale={c: 1 + SHARE for c in codes}).fit(train, features).predict(test)
        print(f"{time.strftime('%H:%M:%S')} {scenario}: {info}", flush=True)

    rows = []
    for scenario, y in targets.items():
        # поправка частот сценария X проверяется на исходном поведении (цена ошибочной поправки) и на самом X
        variants = {**common, **{f"IGPA-Hybrid, калькулятор EduScore, частоты ×1,3 ({k})": v
                                 for k, v in corrected.items() if scenario in (BASE, k)}}
        for name, pred in variants.items():
            lo, hi = P.mae_ci(y, pred)
            rows.append({"scenario": scenario, "variant": name, "n": len(y), "mae": float(np.abs(y - pred).mean()),
                         "mae_lo": lo, "mae_hi": hi, "bias": float(np.mean(pred - y)),
                         "target_mean": float(np.mean(y))})
    table = pd.DataFrame(rows)
    table.to_csv(out / "stress.csv", index=False)
    pd.DataFrame(infos).to_csv(out / "shift.csv", index=False)
    with pd.option_context("display.width", 220, "display.max_columns", 20, "display.max_colwidth", 80):
        print(table.round(4).to_string(index=False))
