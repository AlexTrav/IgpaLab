import pandas as pd

from generator.common import load_config
from generator.pipeline import generate

TABLES = ("students", "records_true", "records_asu", "approvals", "snapshots_year")


def test_same_seed_same_data():
    first, second = (generate(load_config(students=150)) for _ in range(2))
    for name in TABLES:
        pd.testing.assert_frame_equal(first[name], second[name])


def test_other_seed_other_data():
    a = generate(load_config(students=150))
    b = generate(load_config(students=150, seed=7))
    assert not a["records_true"][["student_id", "category"]].equals(b["records_true"][["student_id", "category"]])
