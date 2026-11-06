import shutil
from importlib import resources

import pytest

from igpa import Block, categories, load_rules, statuses


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_default_preset(rules):
    assert rules.method == "category"
    assert (rules.weight_gpa, rules.weight_iros, rules.weight_ssci) == (0.5, 0.35, 0.15)
    assert rules.top_n == 5 and rules.scale == 4


def test_points_follow_regulation(rules):
    assert [rules.points[s.code] for s in statuses(Block.RESEARCH)] == [10, 14, 18, 20]
    assert [rules.points[s.code] for s in statuses(Block.ONE_TIME)] == [10, 15, 15, 20]
    assert rules.points["SSCI_PERMANENT"] == 100


def test_regulation_weights_kept(rules):
    w = rules.category_weights
    assert (w["IROS_EVENT"], w["IROS_PRIZE"], w["IROS_PUBLICATION"], w["IROS_PROJECT"]) == (0.2, 0.2, 0.3, 0.3)
    assert all(w[c.code] == 0.2 for c in categories(block=Block.ONE_TIME))
    assert (w["SSCI_IMAGE_PROJECT"], w["SSCI_STUDENT_ORG"], w["SSCI_UNIVERSITY_IMAGE"]) == (0.2, 0.4, 0.4)


@pytest.mark.parametrize("block", list(Block))
def test_block_weights_sum_to_one(rules, block):
    assert sum(rules.block_weight(c.code) for c in categories(block=block)) == pytest.approx(1)


def test_eduscore_preset_has_no_new_types():
    rules = load_rules("eduscore")
    assert rules.method == "eduscore"
    assert [code for code, w in rules.category_weights.items() if w == 0] == [
        "IROS_TALK", "IROS_INTERNSHIP", "SSCI_LEADERSHIP", "SSCI_UNIT_VOLUNTEER"]


def test_load_from_file(tmp_path):
    source = resources.files("igpa").joinpath("presets", "default.yaml")
    target = tmp_path / "my.yaml"
    with resources.as_file(source) as path:
        shutil.copy(path, target)
    assert load_rules(target).version == load_rules().version


@pytest.mark.parametrize("changes", [
    {"method": "magic"},
    {"ssci_blocks": "max"},
    {"foreign_status": "guess"},
    {"weight_gpa": 0.6},
    {"top_n": 0},
    {"points": {"IROS_OVPO": 10}},
    {"category_weights": {"IROS_EVENT": 1}},
    {"status_map": {"research": {"SSCI_UNIVERSITY": "SSCI_REPUBLIC"}}},
    {"max_count": {"research": 5}},
])
def test_invalid_rules_rejected(rules, changes):
    with pytest.raises(ValueError):
        rules.with_changes(**changes)


def test_zero_weights_in_whole_block_rejected(rules):
    weights = {**rules.category_weights, **{c.code: 0 for c in categories(block=Block.PERMANENT)}}
    with pytest.raises(ValueError):
        rules.with_changes(category_weights=weights)


def test_rules_are_immutable(rules):
    with pytest.raises(TypeError):
        rules.points["IROS_OVPO"] = 100
