"""Истинная история студентов: оценки, перевод с курса на курс и достижения (что было на самом деле, до АСУ)."""

import datetime as dt

import numpy as np
import pandas as pd

from igpa import CATEGORY_BY_CODE, Block, categories, statuses

from .common import academic_year, on, sigmoid

RESEARCH = [c.code for c in categories(block=Block.RESEARCH)]
ONE_TIME = [c.code for c in categories(block=Block.ONE_TIME)]
PERMANENT = [c.code for c in categories(block=Block.PERMANENT)]
LEVEL_STATUS = {block: np.array([s.code for s in statuses(block)], dtype=object)
                for block in (Block.RESEARCH, Block.ONE_TIME)}

WAITING, ACTIVE, GRADUATED, EXPELLED, DROPOUT = range(5)


def simulate(students: pd.DataFrame, latent: pd.DataFrame, cfg: dict, rng: np.random.Generator) -> dict:
    """Таблицы истории: records_true, courses, enrollment, motivation."""
    return _Simulation(students, latent, cfg, rng).run()


class _Simulation:
    def __init__(self, students, latent, cfg, rng):
        self.cfg, self.rng = cfg, rng
        self.act = cfg["activity"]
        self.now = cfg["now"]
        self.n = n = len(students)
        self.students = students
        self.intake = students.intake_year.to_numpy()
        self.level = students.level.to_numpy()
        self.master = self.level != "bachelor"
        self.duration = np.array([cfg["levels"][lv]["years"] for lv in self.level])
        self.a, self.r, self.s, self.rep = (latent[c].to_numpy() for c in ("a", "r", "s", "rep"))
        self.m = latent.m0.to_numpy().copy()
        self.athlete = latent.athlete.to_numpy()

        self.state = np.full(n, WAITING)
        self.yos = np.zeros(n, dtype=int)
        self.exp = {code: np.zeros(n) for code in CATEGORY_BY_CODE}
        self.had = {code: np.zeros(n, dtype=bool) for code in PERMANENT}
        self.prev_research, self.prev_social = np.zeros(n), np.zeros(n)
        self.credits, self.points, self.earned = np.zeros(n), np.zeros(n), np.zeros(n)
        self.records, self.courses, self.enrollment, self.motivation = [], [], [], []

    def active(self) -> np.ndarray:
        return np.flatnonzero(self.state == ACTIVE)

    def run(self) -> dict:
        for year in range(self.cfg["first_intake"], academic_year(self.now) + 1):
            self._start_year(year)
            self._permanent(year)
            complete = True
            for semester, name in ((1, "fall"), (2, "spring")):
                start, end = (on(year, d) for d in self.act["windows"][name])
                if start > self.now:
                    complete = False
                    break
                self._activity(year, semester, start, min(end, self.now), (end - start).days + 1)
                if on(year, self.act["sessions"][name]) <= self.now:
                    self._grades(year, semester)
                else:
                    complete = False
                self.prev_research, self.prev_social = self.cur_research, self.cur_social
            if complete:
                self._finish_year(year)
            else:
                self._current_year(year)
        return self._frames()

    def _start_year(self, year):
        new = self.intake == year
        self.state[new], self.yos[new] = ACTIVE, 1
        old = (self.state == ACTIVE) & ~new
        mot = self.cfg["latent"]["motivation"]
        self.m[old] = mot["keep"] * self.m[old] + mot["noise"] * self.rng.standard_normal(old.sum())
        self.m[old & (self.rng.random(self.n) < mot["shock_p"])] += mot["shock"]
        idx = self.active()
        self.motivation.append(pd.DataFrame({"student": idx, "year": year, "m": self.m[idx]}))
        self.year_credits, self.year_points = np.zeros(self.n), np.zeros(self.n)
        self.cur_perm = {code: np.zeros(self.n, dtype=bool) for code in PERMANENT}

    def _permanent(self, year):
        start, end = (on(year, d) for d in self.act["windows"]["permanent"])
        if start > self.now:
            return
        idx = self.active()
        traits = {"a": self.a[idx], "r": self.r[idx], "s": self.s[idx], "m": self.m[idx]}
        for code in PERMANENT:
            p = self.act["permanent"][code]
            logit = (p["base"] + sum(p.get(t, 0) * v for t, v in traits.items())
                     + p.get("keep", 0) * self.had[code][idx]
                     + p.get("after_org", 0) * self.had["SSCI_STUDENT_ORG"][idx]
                     + self.act["permanent_master"] * self.master[idx])
            joined = self.rng.random(idx.size) < sigmoid(logit)
            self.cur_perm[code][idx] = joined
            self._add(code, idx, joined.astype(int), year, 1, start, min(end, self.now))
            self.exp[code][idx] += joined

    def _activity(self, year, semester, start, end, full_days):
        idx = self.active()
        frac = ((end - start).days + 1) / full_days   # текущий семестр прожит частично
        a, r, s, m = self.a[idx], self.r[idx], self.s[idx], self.m[idx]
        yos, master, level = self.yos[idx], self.master[idx], self.level[idx]
        rng, counts = self.rng, {}

        rc = self.act["research_coef"]
        lin = rc["trait"] * r + rc["motivation"] * m + rc["year"] * (yos - 1) + rc["master"] * master
        for code, base in self.act["research"].items():
            lam = base * np.exp(lin + rc["experience"] * np.log1p(self.exp[code][idx])) * frac
            if code == "IROS_PUBLICATION":
                lam = lam + self.act["publication_per_talk"] * counts["IROS_TALK"]
            counts[code] = rng.poisson(lam)
        intern = self.act["internship"]
        lam = np.select([(level == "master_research") & (yos == 2), level == "master_profile"],
                        [intern["master_research"], intern["master_profile"]], 0.0) * frac
        counts["IROS_INTERNSHIP"] = rng.poisson(np.where(self.exp["IROS_INTERNSHIP"][idx] >= 2, 0, lam))
        pz = self.act["prize"]
        counts["IROS_PRIZE"] = rng.binomial(counts["IROS_EVENT"] + counts["IROS_TALK"],
                                            sigmoid(pz["base"] + pz["r"] * r + pz["a"] * a + pz["m"] * m))

        sc = self.act["social_coef"]
        lin = (sc["trait"] * s + sc["motivation"] * m + sc["peak"] * (yos - sc["peak_year"]) ** 2
               + sc["master"] * master)
        for code, base in self.act["social"].items():
            counts[code] = rng.poisson(base * np.exp(lin + sc["experience"] * np.log1p(self.exp[code][idx])) * frac)
        sport = self.act["sport"]
        counts["SSCI_SPORT"] = rng.poisson(np.where(self.athlete[idx], sport["athlete"], sport["other"]) * frac)
        ip = self.act["intellectual_prize"]
        counts["SSCI_INTELLECTUAL_PRIZE"] = rng.binomial(counts["SSCI_INTELLECTUAL"],
                                                         sigmoid(ip["base"] + ip["a"] * a + ip["s"] * s))

        for code in RESEARCH + ONE_TIME:
            self._add(code, idx, counts[code], year, semester, start, end)
            self.exp[code][idx] += counts[code]
        self.cur_research, self.cur_social = np.zeros(self.n), np.zeros(self.n)
        self.cur_research[idx] = sum(counts[c] for c in RESEARCH)
        self.cur_social[idx] = sum(counts[c] for c in ONE_TIME)

    def _add(self, code, idx, counts, year, semester, start: dt.date, end: dt.date):
        rec = np.repeat(idx, counts)
        if rec.size == 0:
            return
        days = self.rng.integers(0, (end - start).days + 1, rec.size)
        block = CATEGORY_BY_CODE[code].block
        status = (np.full(rec.size, "SSCI_PERMANENT", dtype=object) if block is Block.PERMANENT
                  else self._level(code, block, rec))
        self.records.append(pd.DataFrame({
            "student": rec, "year": year, "semester": semester, "year_of_study": self.yos[rec],
            "category": code, "status": status,
            "event_date": np.datetime64(start, "D") + days.astype("timedelta64[D]"),
        }))

    def _level(self, code, block, rec) -> np.ndarray:
        """Уровень мероприятия: порядковая логит-модель от склонности, опыта, курса и уровня обучения."""
        lv, c = self.act["level"], self.act["level"]["coef"]
        trait = self.r[rec] if block is Block.RESEARCH else self.s[rec]
        experience = sum(self.exp[k][rec] for k in (RESEARCH if block is Block.RESEARCH else ONE_TIME))
        x = (c["trait"] * trait + c["experience"] * np.log1p(experience) + c["year"] * (self.yos[rec] - 1)
             + c["master"] * self.master[rec] + lv["shift"].get(code, 0) + self.rng.logistic(size=rec.size))
        cuts = lv["cut_research"] if block is Block.RESEARCH else lv["cut_one_time"]
        return LEVEL_STATUS[block][np.searchsorted(cuts, x)]

    def _grades(self, year, semester):
        g, e, rng = self.cfg["grades"], self.cfg["effects"], self.rng
        idx = self.active()
        k = idx.size
        sizes = list(g["courses"])
        width = max(len(v) for v in g["courses"].values())
        patterns = np.zeros((len(sizes), width))
        for i, size in enumerate(sizes):
            patterns[i, :len(g["courses"][size])] = g["courses"][size]
        credits = patterns[rng.choice(len(sizes), k, p=[g["courses_p"][size] for size in sizes])]

        a = self.a[idx]
        mean = (np.where(self.master[idx], g["base"]["master"], g["base"]["bachelor"]) + g["ability"] * a
                + g["motivation"] * self.m[idx] + g["growth"] * (self.yos[idx] - 1))
        mean += np.where(a > e["research_to_gpa_min_a"],
                         e["research_to_gpa"] * np.minimum(self.prev_research[idx], e["research_to_gpa_cap"]), 0)
        mean += e["social_load_to_gpa"] * np.maximum(self.prev_social[idx] - e["social_load_free"], 0)
        score = (mean[:, None] + g["semester_noise"] * rng.standard_normal((k, 1))
                 + g["difficulty"] * rng.standard_normal((k, width)) + g["course_noise"] * rng.standard_normal((k, width)))
        score = np.clip(np.rint(score), 0, 100)

        scale = g["scale"][::-1]   # по возрастанию нижней границы
        pos = np.searchsorted([b for b, _, _ in scale], score, side="right") - 1
        letter = np.array([x for _, x, _ in scale], dtype=object)[pos]
        points = np.array([p for _, _, p in scale])[pos]

        rows, cols = np.nonzero(credits > 0)
        self.courses.append(pd.DataFrame({
            "student": idx[rows], "year": year, "semester": semester, "course": cols + 1,
            "credits": credits[rows, cols].astype(int), "score": score[rows, cols].astype(int),
            "letter": letter[rows, cols], "points": points[rows, cols],
        }))
        sum_c, sum_cp = credits.sum(1), (credits * points).sum(1)
        self.credits[idx] += sum_c
        self.points[idx] += sum_cp
        self.earned[idx] += (credits * (score >= g["pass_score"])).sum(1)
        self.year_credits[idx] += sum_c
        self.year_points[idx] += sum_cp

    def _finish_year(self, year):
        """Конец учебного года: выпуск, перевод по накопленным кредитам и переводному GPA, повторный курс, уход."""
        g, rng = self.cfg["grades"], self.rng
        idx = self.active()
        k = idx.size
        gpa_year = self.year_points[idx] / self.year_credits[idx]
        gpa_cum = self.points[idx] / self.credits[idx]
        yos, level = self.yos[idx], self.level[idx]
        final = yos >= self.duration[idx]
        fail = np.zeros(k, dtype=bool)
        for lv, rules in g["transfer"].items():
            for course, (credits, gpa) in rules.items():
                sel = ~final & (level == lv) & (yos == int(course))
                fail |= sel & ((self.earned[idx] < credits) | (gpa_cum < gpa))
        repeat = fail & (rng.random(k) < g["repeat_p"])
        d = g["dropout"]
        drop = ~final & ~fail & (rng.random(k) < sigmoid(d["base"] + d["gpa"] * (gpa_year - 2.5)))

        outcome = np.full(k, "promoted", dtype=object)
        outcome[final], outcome[fail], outcome[repeat], outcome[drop] = "graduated", "expelled", "repeat", "dropout"
        self.enrollment.append(pd.DataFrame({
            "student": idx, "year": year, "year_of_study": yos, "outcome": outcome,
            "gpa_year": gpa_year, "gpa_cum": gpa_cum, "credits_earned": self.earned[idx],
        }))
        self.state[idx[final]] = GRADUATED
        self.state[idx[outcome == "expelled"]] = EXPELLED
        self.state[idx[drop]] = DROPOUT
        self.yos[idx[outcome == "promoted"]] += 1
        self.had = self.cur_perm

    def _current_year(self, year):
        idx = self.active()
        with np.errstate(invalid="ignore", divide="ignore"):
            gpa_cum = np.where(self.credits[idx] > 0, self.points[idx] / self.credits[idx], np.nan)
        self.enrollment.append(pd.DataFrame({
            "student": idx, "year": year, "year_of_study": self.yos[idx], "outcome": "current",
            "gpa_year": np.nan, "gpa_cum": gpa_cum, "credits_earned": self.earned[idx],
        }))

    def _frames(self) -> dict:
        ids = self.students.student_id.to_numpy()

        def finish(parts, sort):
            df = pd.concat(parts, ignore_index=True).sort_values(sort, kind="stable").reset_index(drop=True)
            df.insert(0, "student_id", ids[df.pop("student")])
            return df

        records = finish(self.records, ["event_date", "student"])
        records.insert(0, "record_id", [f"R{i:07d}" for i in range(1, len(records) + 1)])
        records["title"] = self._titles(records)
        return {
            "records_true": records,
            "courses": finish(self.courses, ["student", "year", "semester", "course"]),
            "enrollment": finish(self.enrollment, ["student", "year"]),
            "motivation": finish(self.motivation, ["student", "year"]),
        }

    def _titles(self, records: pd.DataFrame) -> list[str]:
        """Наименование записи, как его пишет студент: шаблон типа + тема факультета или вымышленное событие."""
        uni = self.cfg["university"]
        topics = {f["name"]: f["topics"] for f in uni["faculties"]}
        faculty = records.student_id.map(self.students.set_index("student_id").faculty)
        u = self.rng.random((len(records), 2))
        fill = uni["fill"]
        titles = []
        for (code, fac), (u1, u2) in zip(zip(records.category, faculty), u):
            patterns = uni["titles"][code]
            pattern = patterns[int(u1 * len(patterns))]
            values = {key: options[int(u2 * len(options))] for key, options in fill.items()}
            values["t"] = topics[fac][int(u2 * len(topics[fac]))]
            titles.append(pattern.format(**values))
        return titles
