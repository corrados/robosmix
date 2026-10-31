from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from robosmix.domain.mix_plan import (
    MAX_EQ_BANDS,
    MIX_PLAN_SCHEMA_VERSION,
    Compressor,
    EqBand,
    Limiter,
    MasterMix,
    MixPlan,
    MixTarget,
    TrackMix,
)
from robosmix.errors import PlanValidationError


def _plan_dict() -> dict[str, Any]:
    return {
        "schema_version": MIX_PLAN_SCHEMA_VERSION,
        "flavor": "powerful",
        "target": {
            "genre": "rock",
            "reference_recipe": "dominant guitars and fat drums",
            "integrated_lufs": -11.0,
            "true_peak_db": -1.0,
        },
        "tracks": {
            "track-1": {
                "gain_db": -3.5,
                "pan": 0.25,
                "high_pass_hz": 30.0,
                "eq": [
                    {"freq_hz": 80.0, "gain_db": 2.0, "q": 0.8},
                    {"freq_hz": 3_000.0, "gain_db": -1.5, "q": 1.2},
                ],
                "compressor": {
                    "threshold_db": -18.0,
                    "ratio": 3.0,
                    "attack_ms": 10.0,
                    "release_ms": 120.0,
                },
                "saturation": 0.1,
                "reverb_send": 0.05,
            }
        },
        "master": {
            "eq": [{"freq_hz": 120.0, "gain_db": -1.0, "q": 0.7}],
            "compressor": None,
            "limiter": {"ceiling_db": -1.0},
            "stereo_width": 1.1,
        },
        "rationale": "Keep the drums forward and the guitars controlled.",
    }


def test_valid_plan_round_trips_through_dict() -> None:
    data = _plan_dict()
    plan = MixPlan.from_dict(data)

    assert plan.schema_version == MIX_PLAN_SCHEMA_VERSION
    assert plan.flavor == "powerful"
    assert plan.target.genre == "rock"
    assert plan.tracks["track-1"].high_pass_hz == 30.0
    assert plan.tracks["track-1"].compressor is not None
    assert plan.master.limiter.ceiling_db == -1.0
    assert plan.to_dict() == data


def test_plan_model_is_immutable() -> None:
    plan = MixPlan.from_dict(_plan_dict())

    with pytest.raises(TypeError):
        plan.tracks["track-2"] = TrackMix()  # type: ignore[index]


def test_master_only_plan_is_allowed() -> None:
    data = _plan_dict()
    data["tracks"] = {}

    plan = MixPlan.from_dict(data)

    assert plan.tracks == {}


def test_plan_validates_track_ids() -> None:
    plan = MixPlan.from_dict(_plan_dict())

    plan.validate_track_ids(["track-1", "track-2"])
    with pytest.raises(PlanValidationError, match="unknown track id"):
        plan.validate_track_ids(["track-2"])


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("flavor",), "", "flavor"),
        (("schema_version",), 2, "schema_version"),
        (("target", "genre"), "", "target.genre"),
        (("target", "integrated_lufs"), -4.0, "target.integrated_lufs"),
        (("target", "true_peak_db"), 0.0, "target.true_peak_db"),
        (("tracks", "track-1", "gain_db"), 13.0, "gain_db"),
        (("tracks", "track-1", "pan"), -1.1, "pan"),
        (("tracks", "track-1", "high_pass_hz"), 10.0, "high_pass_hz"),
        (("tracks", "track-1", "saturation"), 1.1, "saturation"),
        (("tracks", "track-1", "reverb_send"), 0.6, "reverb_send"),
        (("tracks", "track-1", "eq"), [{"freq_hz": 80.0, "gain_db": 13.0}], "gain_db"),
        (("tracks", "track-1", "eq"), [{"freq_hz": 10.0, "gain_db": 1.0}], "freq_hz"),
        (("tracks", "track-1", "eq"), [{"freq_hz": 80.0, "gain_db": 1.0, "q": 11.0}], "q"),
        (
            ("tracks", "track-1", "compressor"),
            {"threshold_db": -18.0, "ratio": 11.0, "attack_ms": 10.0, "release_ms": 120.0},
            "ratio",
        ),
        (
            ("tracks", "track-1", "compressor"),
            {"threshold_db": -18.0, "ratio": 3.0, "attack_ms": 0.5, "release_ms": 120.0},
            "attack_ms",
        ),
        (
            ("tracks", "track-1", "compressor"),
            {"threshold_db": -18.0, "ratio": 3.0, "attack_ms": 10.0, "release_ms": 1_100.0},
            "release_ms",
        ),
        (("master", "stereo_width"), 2.1, "stereo_width"),
        (("master", "limiter", "ceiling_db"), -0.05, "ceiling_db"),
    ],
)
def test_rejects_out_of_range_values(path: tuple[str, ...], value: object, message: str) -> None:
    data = _plan_dict()
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    with pytest.raises(PlanValidationError, match=message):
        MixPlan.from_dict(data)


def test_rejects_limiter_ceiling_above_target_true_peak() -> None:
    data = _plan_dict()
    data["master"]["limiter"]["ceiling_db"] = -0.5

    with pytest.raises(PlanValidationError, match="must not exceed the target true peak"):
        MixPlan.from_dict(data)


def test_rejects_too_many_eq_bands() -> None:
    data = _plan_dict()
    data["tracks"]["track-1"]["eq"] = [
        {"freq_hz": 100.0 + index, "gain_db": 0.0, "q": 1.0} for index in range(MAX_EQ_BANDS + 1)
    ]

    with pytest.raises(PlanValidationError, match="at most"):
        MixPlan.from_dict(data)


def test_rejects_unknown_fields() -> None:
    data = _plan_dict()
    data["unexpected"] = True

    with pytest.raises(PlanValidationError, match="unknown field"):
        MixPlan.from_dict(data)


def test_rejects_unknown_nested_fields() -> None:
    data = _plan_dict()
    data["tracks"]["track-1"]["unexpected"] = True

    with pytest.raises(PlanValidationError, match="unknown field"):
        MixPlan.from_dict(data)


def test_rejects_missing_required_fields() -> None:
    data = _plan_dict()
    del data["flavor"]

    with pytest.raises(PlanValidationError, match="plan.flavor: is required"):
        MixPlan.from_dict(data)


@pytest.mark.parametrize("value", [True, "0.5", None])
def test_rejects_non_numeric_values(value: object) -> None:
    data = _plan_dict()
    data["tracks"]["track-1"]["gain_db"] = value

    with pytest.raises(PlanValidationError, match="must be a number"):
        MixPlan.from_dict(data)


def test_rejects_invalid_track_keys() -> None:
    data = _plan_dict()
    data["tracks"]["bad key"] = deepcopy(data["tracks"]["track-1"])

    with pytest.raises(PlanValidationError, match="stable track identifier"):
        MixPlan.from_dict(data)


def test_direct_construction_validates_values() -> None:
    with pytest.raises(PlanValidationError, match="gain_db"):
        TrackMix(gain_db=100.0)
    with pytest.raises(PlanValidationError, match="ceiling_db"):
        Limiter(ceiling_db=0.0)
    with pytest.raises(PlanValidationError, match="freq_hz"):
        EqBand(freq_hz=0.0, gain_db=0.0)
    with pytest.raises(PlanValidationError, match="ratio"):
        Compressor(threshold_db=-18.0, ratio=20.0, attack_ms=10.0, release_ms=120.0)
    with pytest.raises(PlanValidationError, match="target.genre"):
        MixTarget(genre="", reference_recipe="", integrated_lufs=-14.0, true_peak_db=-1.0)
    with pytest.raises(PlanValidationError, match="master"):
        MixPlan(
            flavor="test",
            target=MixTarget(
                genre="pop", reference_recipe="", integrated_lufs=-14.0, true_peak_db=-1.0
            ),
            tracks={},
            master=None,  # type: ignore[arg-type]
            rationale="test",
        )
    with pytest.raises(PlanValidationError, match="schema_version"):
        MixPlan(
            flavor="test",
            target=MixTarget(
                genre="pop", reference_recipe="", integrated_lufs=-14.0, true_peak_db=-1.0
            ),
            tracks={},
            master=MasterMix(),
            rationale="test",
            schema_version=2,
        )
