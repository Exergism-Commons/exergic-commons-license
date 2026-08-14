import importlib.util
import json
import math
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "exergic_analysis.py"
SPEC = importlib.util.spec_from_file_location("exergic_analysis", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


PROFILE = {
    "name": "test-profile",
    "status": "test-only",
    "pc": 1 / 3,
    "pr": 1 / 3,
    "pe": 1 / 3,
    "qC": 1.0,
    "qS": 1.0,
    "a1": 0.5,
    "a2": 0.5,
    "a3": 1 / 3,
    "a4": 1 / 3,
    "a5": 1 / 3,
    "b1": 0.5,
    "b2": 0.5,
    "b3": 0.25,
    "b4": 0.25,
    "b5": 0.25,
    "b6": 0.25,
    "lambda": 0.1,
}


def interval(value, spread=0.0):
    return {
        "low": max(0.0, value - spread),
        "central": value,
        "high": min(1.0, value + spread),
    }


def assessment(**overrides):
    central = {
        "P": 0.8,
        "A": 0.4,
        "V_ep": 0.5,
        "L": 0.3,
        "O": 0.4,
        "U": 0.6,
        "C": 0.7,
        "S": 0.6,
        "R": 0.7,
        "Ecol": 0.2,
        "D_p": 1.0,
    }
    central.update(overrides)
    return {
        "assessment_id": "TEST",
        "entity": "Test entity",
        "object": "Test object",
        "scoring_status": "scorable",
        "variables": {name: interval(value, 0.05 if name != "D_p" else 0.0) for name, value in central.items()},
    }


class ExergicAnalysisTests(unittest.TestCase):
    def test_formula_matches_direct_central_calculation(self):
        item = assessment()
        result = MODULE.calculate(item, PROFILE)
        central_values = {name: raw["central"] for name, raw in item["variables"].items()}
        direct = MODULE.scalar_scores(central_values, MODULE.validate_profile(PROFILE))
        for key, expected in direct.items():
            self.assertTrue(math.isclose(result["scores"][key]["central"], expected, rel_tol=1e-12))

    def test_bounds_contain_central_value(self):
        result = MODULE.calculate(assessment(), PROFILE)
        for metric in result["scores"].values():
            self.assertLessEqual(metric["low"], metric["central"])
            self.assertLessEqual(metric["central"], metric["high"])

    def test_more_capture_reduces_relative_exergy(self):
        lower = MODULE.calculate(assessment(C=0.2), PROFILE)["scores"]["Ex_r"]["central"]
        higher = MODULE.calculate(assessment(C=0.9), PROFILE)["scores"]["Ex_r"]["central"]
        self.assertGreater(lower, higher)

    def test_more_autonomy_increases_base_exergy(self):
        lower = MODULE.calculate(assessment(A=0.2), PROFILE)["scores"]["Ex_b"]["central"]
        higher = MODULE.calculate(assessment(A=0.8), PROFILE)["scores"]["Ex_b"]["central"]
        self.assertLess(lower, higher)

    def test_insufficient_evidence_is_not_scored(self):
        result = MODULE.calculate(
            {
                "assessment_id": "U",
                "entity": "Unknown",
                "object": "Undefined",
                "scoring_status": "insufficient_evidence",
                "reason": "No defined object",
            },
            PROFILE,
        )
        self.assertIsNone(result["scores"])
        self.assertEqual(result["tier_mapping"], "forbidden")

    def test_not_applicable_is_not_scored(self):
        result = MODULE.calculate(
            {
                "assessment_id": "N",
                "entity": "No object",
                "object": "None",
                "scoring_status": "not_applicable",
                "reason": "No current object",
            },
            PROFILE,
        )
        self.assertIsNone(result["scores"])

    def test_invalid_interval_is_rejected(self):
        item = assessment()
        item["variables"]["A"] = {"low": 0.8, "central": 0.5, "high": 0.9}
        with self.assertRaises(MODULE.InputError):
            MODULE.calculate(item, PROFILE)


if __name__ == "__main__":
    unittest.main()
