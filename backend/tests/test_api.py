import pytest
from fastapi.testclient import TestClient

from api.main import app
from igpa import Record, calculate, load_rules

client = TestClient(app)
PORTFOLIO = {
    "gpa": 3.1, "gpa_prev": 2.9, "year_of_study": 2, "level": "bachelor",
    "records": [{"category": "IROS_EVENT", "status": "IROS_OVPO"}, {"category": "IROS_EVENT", "status": "IROS_REP_CITY"},
                {"category": "SSCI_VOLUNTEER", "status": "SSCI_UNIVERSITY"}],
}


def test_health_and_meta():
    assert client.get("/api/health").json() == {"status": "ok"}
    meta = client.get("/api/meta", params={"lang": "kk"}).json()
    assert len(meta["categories"]) == 16 and len(meta["statuses"]) == 9 and len(meta["rules"]) == 3
    assert meta["categories"][0]["name"] == "Ғылыми іс-шараларға қатысу немесе ұйымдастыру"


@pytest.mark.parametrize("rules", ["default", "eduscore", "percentile"])
def test_calc_matches_calculator(rules):
    body = {"gpa": 3.1, "records": PORTFOLIO["records"], "rules": rules}
    got = client.post("/api/calc", json=body).json()
    expected = calculate([Record(r["category"], r["status"]) for r in body["records"]], 3.1, load_rules(rules))
    assert got["igpa"] == pytest.approx(expected.igpa)
    assert got["gpa_part"] + got["iros_part"] + got["ssci_part"] == pytest.approx(got["igpa"])


def test_quick():
    got = client.post("/api/quick", json={"gpa": 3.9, "iros": 0.69, "ssci": 0.10}).json()
    default = next(r for r in got if r["rules"] == "default")
    assert default["igpa"] == pytest.approx(2.976)   # экран EduScore


@pytest.mark.parametrize("lang", ["ru", "kk", "en"])
def test_portfolio(lang):
    got = client.post("/api/portfolio", json={**PORTFOLIO, "lang": lang}).json()
    f = got["forecast"]
    assert 0 <= f["p10"] <= f["mean"] <= f["p90"] <= 4 and 0 <= f["risk"] <= 1
    assert 0 <= got["catboost"]["risk"] <= 1
    assert got["explanation"] and got["advice"]
    for a in got["advice"]:
        assert a["gain"] > 0 and 0 < a["feasibility"] < 1 and a["text"]
    assert [a["expected"] for a in got["advice"]] == sorted((a["expected"] for a in got["advice"]), reverse=True)


def test_advice_gain_is_exact():
    got = client.post("/api/portfolio", json=PORTFOLIO).json()
    rules = load_rules()
    records = [Record(r["category"], r["status"]) for r in PORTFOLIO["records"]]
    for a in got["advice"]:
        if a["kind"] == "record":
            after = calculate(records + [Record(a["category"], a["status"])], PORTFOLIO["gpa"], rules).igpa
        else:
            after = calculate(records, min(4, PORTFOLIO["gpa"] + a["gpa_step"]), rules).igpa
        assert a["igpa_after"] == pytest.approx(after)


@pytest.mark.parametrize("rules", ["default", "eduscore", "percentile"])
def test_advice_are_different_steps(rules):
    # портфель со скриншота: низкий GPA, где «GPA +0,1» и «GPA +0,2» оба попадали в тройку
    body = {"gpa": 1.45, "gpa_prev": 2.63, "year_of_study": 3, "level": "bachelor", "rules": rules,
            "records": [{"category": "IROS_EVENT", "status": "IROS_OVPO"}] * 2}
    for portfolio in (body, {**PORTFOLIO, "rules": rules}):
        advice = client.post("/api/portfolio", json=portfolio).json()["advice"]
        keys = ["gpa" if a["kind"] == "gpa" else a["category"] for a in advice]
        assert len(advice) == 3 and len(set(keys)) == 3


def test_portfolio_validation():
    assert client.post("/api/portfolio", json={**PORTFOLIO, "gpa": 4.5}).status_code == 422
    assert client.post("/api/portfolio", json={**PORTFOLIO, "records": [{"category": "X", "status": "IROS_OVPO"}]}).status_code == 422
    assert client.post("/api/portfolio", json={**PORTFOLIO, "level": "master_profile"}).status_code == 422


def test_students():
    page = client.get("/api/students", params={"limit": 5}).json()
    assert page["total"] > 1000 and len(page["items"]) == 5
    sid = page["items"][0]["student_id"]
    one = client.get(f"/api/students/{sid}", params={"rules": "eduscore", "lang": "en"}).json()
    assert one["student"]["student_id"] == sid and one["history"]
    assert one["forecast"] is None or 0 <= one["forecast"]["risk"] <= 1
    assert client.get("/api/students/NOPE").status_code == 404


def test_research():
    r = client.get("/api/research").json()
    assert {"models", "series", "hybrid", "rule_change", "normalization", "recommendations", "light_eval"} <= set(r)


def test_research_checks_and_feature_names():
    r = client.get("/api/research?lang=kk").json()
    assert {"check_light", "check_learning", "check_scenarios", "robust_models", "disjoint"} <= set(r)
    assert r["feature_names"]["gpa_trend"] != "gpa_trend"   # названия признаков на языке запроса
