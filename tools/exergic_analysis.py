#!/usr/bin/env python3
"""Reproducible calculator for the ECL formal Exergism analysis layer.

This tool performs mechanical calculations only. It does not assign ECL
R/S/U/N outcomes and does not validate the underlying evidence.
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
ALL_VARS = POSITIVE + PENALTY + ("D_p",)
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
        "pc",
        "pr",
        "pe",
        "a1",
        "a2",
        "a3",
        "a4",
        "a5",
        "b1",
        "b2",
        "b3",
        "b4",
        "b5",
        "b6",
        "lambda",
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
    return out


def scalar_scores(values: dict[str, float], p: dict[str, float]) -> dict[str, float]:
    P = values["P"]
    A = values["A"]
    V = values["V_ep"]
    L = values["L"]
    O = values["O"]
    U = values["U"]
    C = values["C"]
    S = values["S"]
    R = values["R"]
    E = values["Ecol"]
    D = values["D_p"]

    ex_b = (P * A * V * L * O * U) ** (1.0 / 6.0)
    pen = p["pc"] * (C ** p["qC"]) + p["pr"] * R + p["pe"] * E
    ex_r = ex_b / (1.0 + pen)
    e_i = D * (
        p["a1"] * (A * V)
        + p["a2"] * (L * O * U)
        - p["a3"] * (S ** p["qS"])
        - p["a4"] * (C ** p["qC"])
        - p["a5"] * E
    )
    x_h = ((P * O * A * U) ** (1.0 / 4.0)) / (1.0 + pen)
    b_0 = (
        p["b1"] * ex_b
        + p["b2"] * L
        - p["b3"] * (C ** p["qC"])
        - p["b4"] * (S ** p["qS"])
        - p["b5"] * R
        - p["b6"] * E
    )
    return {
        "Ex_b": ex_b,
        "Pen": pen,
        "Ex_r": ex_r,
        "E_i": e_i,
        "X_h": x_h,
        "B_0": b_0,
    }


def project(intervals: dict[str, dict[str, float]], side: str) -> dict[str, float]:
    return {name: interval[side] for name, interval in intervals.items()}


def conservative_bounds(
    intervals: dict[str, dict[str, float]], p: dict[str, float]
) -> dict[str, dict[str, float]]:
    central = scalar_scores(project(intervals, "central"), p)

    # Formula-aware conservative bounds. These are epistemic envelopes, not
    # probability intervals.
    low_pos_high_pen = {
        **{name: intervals[name]["low"] for name in POSITIVE},
        "C": intervals["C"]["high"],
        "S": intervals["S"]["high"],
        "R": intervals["R"]["high"],
        "Ecol": intervals["Ecol"]["high"],
        "D_p": intervals["D_p"]["high"],
    }
    high_pos_low_pen = {
        **{name: intervals[name]["high"] for name in POSITIVE},
        "C": intervals["C"]["low"],
        "S": intervals["S"]["low"],
        "R": intervals["R"]["low"],
        "Ecol": intervals["Ecol"]["low"],
        "D_p": intervals["D_p"]["high"],
    }

    low_scores = scalar_scores(low_pos_high_pen, p)
    high_scores = scalar_scores(high_pos_low_pen, p)

    # E_i is multiplied by D_p and can cross zero. Evaluate D_p endpoints too.
    e_candidates = []
    b_candidates = []
    for capacity_side in ("low", "high"):
        for penalty_side in ("low", "high"):
            for d_side in ("low", "high"):
                vals = {
                    **{
                        name: intervals[name][capacity_side]
                        for name in POSITIVE
                    },
                    **{
                        name: intervals[name][penalty_side]
                        for name in PENALTY
                    },
                    "D_p": intervals["D_p"][d_side],
                }
                scores = scalar_scores(vals, p)
                e_candidates.append(scores["E_i"])
                b_candidates.append(scores["B_0"])

    bounds: dict[str, dict[str, float]] = {}
    for key in ("Ex_b", "Pen", "Ex_r", "X_h"):
        if key == "Pen":
            low = scalar_scores(
                {
                    **{
                        name: intervals[name]["central"]
                        for name in POSITIVE
                    },
                    "C": intervals["C"]["low"],
                    "S": intervals["S"]["central"],
                    "R": intervals["R"]["low"],
                    "Ecol": intervals["Ecol"]["low"],
                    "D_p": intervals["D_p"]["central"],
                },
                p,
            )[key]
            high = scalar_scores(
                {
                    **{
                        name: intervals[name]["central"]
                        for name in POSITIVE
                    },
                    "C": intervals["C"]["high"],
                    "S": intervals["S"]["central"],
                    "R": intervals["R"]["high"],
                    "Ecol": intervals["Ecol"]["high"],
                    "D_p": intervals["D_p"]["central"],
                },
                p,
            )[key]
        else:
            low = low_scores[key]
            high = high_scores[key]
        bounds[key] = {
            "low": min(low, high),
            "central": central[key],
            "high": max(low, high),
        }

    bounds["E_i"] = {
        "low": min(e_candidates),
        "central": central["E_i"],
        "high": max(e_candidates),
    }
    bounds["B_0"] = {
        "low": min(b_candidates),
        "central": central["B_0"],
        "high": max(b_candidates),
    }
    return bounds


def temporal_scores(
    snapshots: Any, p: dict[str, float]
) -> dict[str, dict[str, float]] | None:
    if snapshots is None:
        return None
    if not isinstance(snapshots, list) or not snapshots:
        raise InputError("temporal must be a non-empty array when supplied")

    totals = {
        "low": [0.0, 0.0],
        "central": [0.0, 0.0],
        "high": [0.0, 0.0],
    }
    for index, snapshot in enumerate(snapshots):
        if not isinstance(snapshot, dict):
            raise InputError(f"temporal[{index}] must be an object")
        t = number(snapshot.get("t"), f"temporal[{index}].t")
        if t < 0:
            raise InputError(f"temporal[{index}].t must be >= 0")
        gamma = unit(snapshot.get("gamma"), f"temporal[{index}].gamma")
        delta = unit(snapshot.get("delta"), f"temporal[{index}].delta")
        raw_vars = snapshot.get("variables")
        if not isinstance(raw_vars, dict):
            raise InputError(f"temporal[{index}].variables must be an object")
        intervals = {
            name: validate_interval(
                raw_vars.get(name), f"temporal[{index}].variables.{name}"
            )
            for name in ALL_VARS
        }
        decay = math.exp(-p["lambda"] * t)

        for side in ("low", "central", "high"):
            values = project(intervals, side)
            ex_b = scalar_scores(values, p)["Ex_b"]
            benefit = (
                ex_b + values["O"] + values["A"] * values["V_ep"]
            ) * decay * gamma
            destruction = (
                values["S"] + values["Ecol"] + values["C"]
            ) * decay * delta
            totals[side][0] += benefit
            totals[side][1] += destruction

    b_low = totals["low"][0]
    b_c = totals["central"][0]
    b_high = totals["high"][0]
    d_low = totals["low"][1]
    d_c = totals["central"][1]
    d_high = totals["high"][1]
    return {
        "B_acc": {"low": b_low, "central": b_c, "high": b_high},
        "D_acc": {"low": d_low, "central": d_c, "high": d_high},
        "N_t": {
            "low": b_low - d_high,
            "central": b_c - d_c,
            "high": b_high - d_low,
        },
    }


def calculate(
    assessment: dict[str, Any], profile: dict[str, Any]
) -> dict[str, Any]:
    state = assessment.get("scoring_status")
    if state not in SCORING_STATES:
        raise InputError(
            "assessment.scoring_status must be one of: "
            + ", ".join(sorted(SCORING_STATES))
        )

    result: dict[str, Any] = {
        "assessment_id": assessment.get("assessment_id"),
        "entity": assessment.get("entity"),
        "object": assessment.get("object"),
        "scoring_status": state,
        "profile": profile.get("name"),
        "profile_status": profile.get("status"),
        "legal_effect": "none",
        "tier_mapping": "forbidden",
    }

    if state != "scorable":
        result["reason"] = assessment.get("reason")
        result["scores"] = None
        result["temporal"] = None
        return result

    raw_vars = assessment.get("variables")
    if not isinstance(raw_vars, dict):
        raise InputError(
            "assessment.variables must be an object for scorable assessments"
        )

    intervals = {
        name: validate_interval(
            raw_vars.get(name), f"assessment.variables.{name}"
        )
        for name in ALL_VARS
    }
    p = validate_profile(profile)
    result["scores"] = conservative_bounds(intervals, p)
    result["temporal"] = temporal_scores(assessment.get("temporal"), p)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("assessment", type=Path)
    parser.add_argument(
        "--profile",
        type=Path,
        default=Path("exergism/profiles/reference-balanced-v2.json"),
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

    json.dump(
        result,
        sys.stdout,
        indent=2 if args.pretty else None,
        sort_keys=True,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
