#!/usr/bin/env python3
"""Reproducible ECL application calculator for canonical Exergism v0.1.0.

The formulas implemented here are an ECL application of the formal model pinned
in ``exergism/upstream.json``. The calculator is diagnostic only: it never maps
scores to ECL R/S/U/N outcomes and never substitutes for evidence or exact
license-criterion review.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

POSITIVE = ("P", "A", "V_ep", "L", "O", "U")
PENALTY = ("C", "S", "R", "Ecol")
CORE_VARS = POSITIVE + PENALTY + ("D_p",)
ADVANCED_VARS = ("D_a", "I", "Lz", "G", "Rj")
SCORING_STATES = {"scorable", "insufficient_evidence", "not_applicable"}


class InputError(ValueError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise InputError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise InputError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise InputError(f"{path} must contain a JSON object")
    return data


def number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputError(f"{label} must be numeric")
    value = float(value)
    if not math.isfinite(value):
        raise InputError(f"{label} must be finite")
    return value


def unit(value: Any, label: str) -> float:
    value = number(value, label)
    if not 0.0 <= value <= 1.0:
        raise InputError(f"{label} must be in [0, 1]")
    return value


def validate_interval(raw: Any, label: str) -> dict[str, float]:
    if not isinstance(raw, dict):
        raise InputError(f"{label} must be an object with low/central/high")
    interval = {
        "low": unit(raw.get("low"), f"{label}.low"),
        "central": unit(raw.get("central"), f"{label}.central"),
        "high": unit(raw.get("high"), f"{label}.high"),
    }
    if not interval["low"] <= interval["central"] <= interval["high"]:
        raise InputError(f"{label} must satisfy low <= central <= high")
    return interval


def validate_profile(profile: dict[str, Any]) -> dict[str, float]:
    required_nonnegative = (
        "pc", "pr", "pe",
        "a1", "a2", "a3", "a4", "a5",
        "b1", "b2", "b3", "b4", "b5", "b6",
        "m1", "m2", "m3", "m4", "m5",
        "r1", "r2", "r3",
    )
    out: dict[str, float] = {}
    for key in required_nonnegative:
        out[key] = number(profile.get(key), f"profile.{key}")
        if out[key] < 0:
            raise InputError(f"profile.{key} must be >= 0")
    for key in ("qC", "qS"):
        out[key] = number(profile.get(key), f"profile.{key}")
        if out[key] <= 0:
            raise InputError(f"profile.{key} must be > 0")
    for key in ("S_crit", "C_crit"):
        out[key] = unit(profile.get(key), f"profile.{key}")
    if "lambda" in profile:
        out["lambda"] = number(profile["lambda"], "profile.lambda")
        if out["lambda"] < 0:
            raise InputError("profile.lambda must be >= 0")
    return out


def scalar_scores(values: dict[str, float], p: dict[str, float]) -> dict[str, float]:
    P, A, V, L, O, U = (values[name] for name in POSITIVE)
    C, S, R, E = (values[name] for name in PENALTY)
    D = values["D_p"]

    ex_b = (P * A * V * L * O * U) ** (1.0 / 6.0)
    pen = p["pc"] * C**p["qC"] + p["pr"] * R + p["pe"] * E
    ex_r = ex_b / (1.0 + pen)
    e_i = D * (
        p["a1"] * (A * V)
        + p["a2"] * (L * O * U)
        - p["a3"] * S**p["qS"]
        - p["a4"] * C**p["qC"]
        - p["a5"] * E
    )
    x_h = ((P * O * A * U) ** (1.0 / 4.0)) / (1.0 + pen)
    b_0 = (
        p["b1"] * ex_b
        + p["b2"] * L
        - p["b3"] * C**p["qC"]
        - p["b4"] * S**p["qS"]
        - p["b5"] * R
        - p["b6"] * E
    )
    result = {
        "Ex_b": ex_b,
        "Pen": pen,
        "Ex_r": ex_r,
        "E_i": e_i,
        "X_h": x_h,
        "B_0": b_0,
    }

    if all(name in values for name in ADVANCED_VARS):
        p_atr = (
            p["r1"] * max(0.0, S - p["S_crit"]) ** 2
            + p["r2"] * max(0.0, C - p["C_crit"]) ** 2
            + p["r3"] * values["Rj"]
        )
        m_f = D * values["D_a"] * (
            p["m1"] * values["I"]
            + p["m2"] * values["Lz"]
            + p["m3"] * values["G"]
            + p["m4"] * C
            + p["m5"] * S
        )
        result.update(
            {
                "P_atr": p_atr,
                "E_i_adj": e_i - p_atr,
                "M_f": m_f,
            }
        )
    return result


def project(intervals: dict[str, dict[str, float]], side: str) -> dict[str, float]:
    return {name: interval[side] for name, interval in intervals.items()}


def _core_extremes(
    intervals: dict[str, dict[str, float]], p: dict[str, float]
) -> dict[str, dict[str, float]]:
    central = scalar_scores(project(intervals, "central"), p)
    low_values = {
        **{name: intervals[name]["low"] for name in POSITIVE},
        "C": intervals["C"]["high"],
        "S": intervals["S"]["high"],
        "R": intervals["R"]["high"],
        "Ecol": intervals["Ecol"]["high"],
        "D_p": intervals["D_p"]["central"],
    }
    high_values = {
        **{name: intervals[name]["high"] for name in POSITIVE},
        "C": intervals["C"]["low"],
        "S": intervals["S"]["low"],
        "R": intervals["R"]["low"],
        "Ecol": intervals["Ecol"]["low"],
        "D_p": intervals["D_p"]["central"],
    }
    low_scores = scalar_scores(low_values, p)
    high_scores = scalar_scores(high_values, p)

    bounds: dict[str, dict[str, float]] = {}
    for key in ("Ex_b", "Ex_r", "X_h", "B_0"):
        bounds[key] = {
            "low": low_scores[key],
            "central": central[key],
            "high": high_scores[key],
        }

    pen_low = scalar_scores(
        {**project(intervals, "central"), "C": intervals["C"]["low"], "R": intervals["R"]["low"], "Ecol": intervals["Ecol"]["low"]},
        p,
    )["Pen"]
    pen_high = scalar_scores(
        {**project(intervals, "central"), "C": intervals["C"]["high"], "R": intervals["R"]["high"], "Ecol": intervals["Ecol"]["high"]},
        p,
    )["Pen"]
    bounds["Pen"] = {"low": pen_low, "central": central["Pen"], "high": pen_high}

    e_candidates = []
    for capacity_side, penalty_side, d_side in (
        ("low", "high", "low"),
        ("low", "high", "high"),
        ("high", "low", "low"),
        ("high", "low", "high"),
    ):
        values = {
            **{name: intervals[name][capacity_side] for name in POSITIVE},
            **{name: intervals[name][penalty_side] for name in PENALTY},
            "D_p": intervals["D_p"][d_side],
        }
        e_candidates.append(scalar_scores(values, p)["E_i"])
    bounds["E_i"] = {
        "low": min(e_candidates),
        "central": central["E_i"],
        "high": max(e_candidates),
    }
    return bounds


def conservative_bounds(
    intervals: dict[str, dict[str, float]], p: dict[str, float]
) -> dict[str, dict[str, float]]:
    bounds = _core_extremes({name: intervals[name] for name in CORE_VARS}, p)
    if not all(name in intervals for name in ADVANCED_VARS):
        return bounds

    central_values = project(intervals, "central")
    central = scalar_scores(central_values, p)
    p_atr_low = scalar_scores(
        {**central_values, "S": intervals["S"]["low"], "C": intervals["C"]["low"], "Rj": intervals["Rj"]["low"]},
        p,
    )["P_atr"]
    p_atr_high = scalar_scores(
        {**central_values, "S": intervals["S"]["high"], "C": intervals["C"]["high"], "Rj": intervals["Rj"]["high"]},
        p,
    )["P_atr"]
    bounds["P_atr"] = {"low": p_atr_low, "central": central["P_atr"], "high": p_atr_high}

    low_e = bounds["E_i"]["low"] - p_atr_high
    high_e = bounds["E_i"]["high"] - p_atr_low
    bounds["E_i_adj"] = {"low": low_e, "central": central["E_i_adj"], "high": high_e}

    mf_low_values = {name: intervals[name]["low"] for name in intervals}
    mf_high_values = {name: intervals[name]["high"] for name in intervals}
    mf_low = scalar_scores(mf_low_values, p)["M_f"]
    mf_high = scalar_scores(mf_high_values, p)["M_f"]
    bounds["M_f"] = {"low": mf_low, "central": central["M_f"], "high": mf_high}
    return bounds


def temporal_scores(raw: Any, p: dict[str, float]) -> dict[str, dict[str, float]] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise InputError("temporal must be an object with lambda and snapshots")
    decay_lambda = number(raw.get("lambda"), "temporal.lambda")
    if decay_lambda < 0:
        raise InputError("temporal.lambda must be >= 0")
    snapshots = raw.get("snapshots")
    if not isinstance(snapshots, list) or not snapshots:
        raise InputError("temporal.snapshots must be a non-empty array")

    benefit_totals = {side: 0.0 for side in ("low", "central", "high")}
    damage_totals = {side: 0.0 for side in ("low", "central", "high")}
    for index, snapshot in enumerate(snapshots):
        if not isinstance(snapshot, dict):
            raise InputError(f"temporal.snapshots[{index}] must be an object")
        t = number(snapshot.get("t"), f"temporal.snapshots[{index}].t")
        if t < 0:
            raise InputError(f"temporal.snapshots[{index}].t must be >= 0")
        gamma = unit(snapshot.get("gamma"), f"temporal.snapshots[{index}].gamma")
        delta = unit(snapshot.get("delta"), f"temporal.snapshots[{index}].delta")
        irr = unit(snapshot.get("irreversibility"), f"temporal.snapshots[{index}].irreversibility")
        raw_vars = snapshot.get("variables")
        if not isinstance(raw_vars, dict):
            raise InputError(f"temporal.snapshots[{index}].variables must be an object")
        required = CORE_VARS + ("Rj",)
        intervals = {
            name: validate_interval(raw_vars.get(name), f"temporal.snapshots[{index}].variables.{name}")
            for name in required
        }
        decay = math.exp(-decay_lambda * t)
        for side in ("low", "central", "high"):
            values = project(intervals, side)
            base = scalar_scores(values, p)
            p_atr = (
                p["r1"] * max(0.0, values["S"] - p["S_crit"]) ** 2
                + p["r2"] * max(0.0, values["C"] - p["C_crit"]) ** 2
                + p["r3"] * values["Rj"]
            )
            benefit_totals[side] += (
                base["Ex_b"] + values["O"] + values["A"] * values["V_ep"] + values["L"]
            ) * decay * gamma
            damage_totals[side] += (
                values["S"] ** p["qS"]
                + values["Ecol"]
                + values["C"] ** p["qC"]
                + p_atr
            ) * decay * delta * (1.0 + irr)

    return {
        "B_acc": {
            "low": benefit_totals["low"],
            "central": benefit_totals["central"],
            "high": benefit_totals["high"],
        },
        "D_acc": {
            "low": damage_totals["low"],
            "central": damage_totals["central"],
            "high": damage_totals["high"],
        },
        "N_t": {
            "low": benefit_totals["low"] - damage_totals["high"],
            "central": benefit_totals["central"] - damage_totals["central"],
            "high": benefit_totals["high"] - damage_totals["low"],
        },
    }


def calculate(assessment: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    state = assessment.get("scoring_status")
    if state not in SCORING_STATES:
        raise InputError(
            "assessment.scoring_status must be one of: " + ", ".join(sorted(SCORING_STATES))
        )
    p = validate_profile(profile)
    result: dict[str, Any] = {
        "assessment_id": assessment.get("assessment_id"),
        "entity": assessment.get("entity"),
        "object": assessment.get("object"),
        "scoring_status": state,
        "profile": profile.get("name"),
        "profile_status": profile.get("status"),
        "context": profile.get("context"),
        "upstream_release": profile.get("upstream_release"),
        "legal_effect": "none",
        "tier_mapping": "forbidden",
    }
    if state != "scorable":
        result.update({"reason": assessment.get("reason"), "scores": None, "temporal": None})
        return result

    raw_vars = assessment.get("variables")
    if not isinstance(raw_vars, dict):
        raise InputError("assessment.variables must be an object for scorable assessments")
    intervals = {
        name: validate_interval(raw_vars.get(name), f"assessment.variables.{name}")
        for name in CORE_VARS
    }
    advanced_present = [name for name in ADVANCED_VARS if name in raw_vars]
    if advanced_present and len(advanced_present) != len(ADVANCED_VARS):
        missing = sorted(set(ADVANCED_VARS) - set(advanced_present))
        raise InputError(
            "advanced Exergism variables must be supplied as a complete set; missing: "
            + ", ".join(missing)
        )
    if len(advanced_present) == len(ADVANCED_VARS):
        intervals.update(
            {
                name: validate_interval(raw_vars.get(name), f"assessment.variables.{name}")
                for name in ADVANCED_VARS
            }
        )
        result["formal_completeness"] = "canonical-static-complete"
        result["missing_canonical_variables"] = []
    else:
        result["formal_completeness"] = "core-only"
        result["missing_canonical_variables"] = list(ADVANCED_VARS)

    result["scores"] = conservative_bounds(intervals, p)
    result["temporal"] = temporal_scores(assessment.get("temporal"), p)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("assessment", type=Path)
    parser.add_argument(
        "--profile",
        type=Path,
        required=True,
        help="Explicit pinned Exergism context profile; no context is guessed.",
    )
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    try:
        assessment = load_json(args.assessment)
        profile = load_json(args.profile)
        result = calculate(assessment, profile)
    except InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    json.dump(result, sys.stdout, indent=2 if args.pretty else None, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
