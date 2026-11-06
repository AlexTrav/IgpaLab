"""API стенда IgpaLab: расчёт IGPA, прогноз, объяснения и советы, студенты стенда, результаты исследования."""

import math
import os
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from igpa import CATEGORY_BY_CODE, STATUS_BY_CODE

from .engine import RULES, engine

Lang = Literal["ru", "kk", "en"]
Rules = Literal["default", "eduscore", "percentile"]
Level = Literal["bachelor", "master_research", "master_profile"]


@asynccontextmanager
async def lifespan(_: FastAPI):
    engine()   # модели загружаются один раз при старте, а не на первом запросе
    yield


app = FastAPI(title="IgpaLab API", version="1.0", lifespan=lifespan,
              description="Лабораторный стенд прогнозирования интегрального GPA. Данные синтетические.")
app.add_middleware(CORSMiddleware, allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
                   allow_methods=["GET", "POST"], allow_headers=["*"])


class RecordIn(BaseModel):
    category: str
    status: str

    @field_validator("category")
    @classmethod
    def known_category(cls, v):
        if v not in CATEGORY_BY_CODE:
            raise ValueError(f"неизвестный тип {v}")
        return v

    @field_validator("status")
    @classmethod
    def known_status(cls, v):
        if v not in STATUS_BY_CODE:
            raise ValueError(f"неизвестный статус {v}")
        return v


class CalcIn(BaseModel):
    gpa: float = Field(ge=0, le=4)
    records: list[RecordIn] = Field(default_factory=list, max_length=200)
    rules: Rules = "default"
    lang: Lang = "ru"


class QuickIn(BaseModel):
    gpa: float = Field(ge=0, le=4)
    iros: float = Field(ge=0, le=1)
    ssci: float = Field(ge=0, le=1)
    lang: Lang = "ru"


class PortfolioIn(CalcIn):
    gpa_prev: float | None = Field(default=None, ge=0, le=4)
    year_of_study: int = Field(ge=1, le=4)
    level: Level = "bachelor"


def clean(obj):
    """NaN и бесконечности – в null, numpy-типы – в обычные числа."""
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if hasattr(obj, "item"):
        obj = obj.item()
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    return obj


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/meta")
def meta(lang: Lang = "ru"):
    return clean(engine().meta_info(lang))


@app.post("/api/calc")
def calc(body: CalcIn):
    return clean(engine().calc(body.gpa, [(r.category, r.status) for r in body.records], body.rules, body.lang))


@app.post("/api/quick")
def quick(body: QuickIn):
    return clean(engine().quick(body.gpa, body.iros, body.ssci, body.lang))


@app.post("/api/portfolio")
def portfolio(body: PortfolioIn):
    if body.level == "master_profile" and body.year_of_study > 1 or body.level == "master_research" and body.year_of_study > 2:
        raise HTTPException(422, "курс больше длительности программы")
    return clean(engine().portfolio(body.model_dump(), body.lang))


@app.get("/api/students")
def students(q: str = "", faculty: str | None = None, level: Level | None = None, current: bool = True,
             limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
    total, items = engine().search(q, faculty, level, current, limit, offset)
    return clean({"total": total, "items": items})


@app.get("/api/students/{student_id}")
def student(student_id: str, rules: Rules = "default", lang: Lang = "ru"):
    found = engine().student(student_id, rules, lang)
    if found is None:
        raise HTTPException(404, "студент не найден")
    return clean(found)


@app.get("/api/research")
def research():
    return clean(engine().research)


@app.get("/api/rules")
def rules():
    return list(RULES)
