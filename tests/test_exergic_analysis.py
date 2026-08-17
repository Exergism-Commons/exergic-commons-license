import importlib.util
import math
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "exergic_analysis.py"
SPEC = importlib.util.spec_from_file_location("exergic_analysis", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


PROFILE = {
    "name": "upstream-transition-v0.1.0-test",
    "status": "test-only",
    "context": "transicion",
    "upstream_release": "v0.1.0",
    "pc": 0.40,
    "pr": 0.30,
    "pe": 0.30,
    "qC": 2.0,
    "qS": 2.0,
    "S_crit": 0.85,
    "C_crit": 0.80,
    "a1": 0.22,
    "a2": 0.18,
    "a3": 0.22,
    "a4": 0.16,
    "a5": 0.12,
    "b1": 0.28,
    "b2": 0.12,
    "b3": 0.16,
    "b4": 0.16,
    "b5": 0.14,
    "b6": 0.14,
    "m1": 0.25,
    "m2": 0.20,
    "m3": 0.20,
    "m4": 0.20,
    "m5": 0.15,
    "r1": 0.50,
    "r2": 0.30,
    "r3": 0.20,
}


def interval(value, spread=0.0):
    return {
        "low": max(0.0, value - spread),
        "central": value,
        "high": min(1.0, value + spread),
    }


def assessment(include_advanced=True, **overrides):
    central = {
        "P": 0.8,
        "A": 0.4,
        "V_ep": 0.5,
        "L": 0.3,
        "O": 0.4,
        "U": 0.6,
        "C": 0.9,
        "S": 0.9,
        "R": 0.7,
        "Ecol": 0.2,
        "D_p": 1.0,
    }
    if include_advanced:
        central.update({"D_a": 0.8, "I": 0.7, "Lz": 0.8, "G": 0.6, "Rj": 0.75})
    central.update(overrides)
    fixed = {"D_p"}
    return {
        "assessment_id": "TEST",
        "entity": "Test entity",
        "object": "Test object",
        "scoring_status": "scorable",
        "variables": {
            name: interval(value, 0.05 if name not in fixed else 0.0)
            for name, value in central.items()
        },
    }


class ExergicAnalysisTests(unittest.TestCase):
    def test_canonical_static_formulas_match_direct_calculation(self):
        item = assessment()
        result = MODULE.calculate(item, PROFILE)
        central_values = {name: raw["central"] for name, raw in item["variables"].items()}
        direct = MODULE.scalar_scores(central_values, MODULE.validate_profile(PROFILE))
        for key, expected in direct.items():
            self.assertTrue(
                math.isclose(result["scores"][key]["central"], expected, rel_tol=1e-12),
                key,
            )
        self.assertEqual(result["formal_completeness"], "canonical-static-complete")

    def test_atrocity_penalty_and_adjusted_ethics_match_upstream_formula(self):
        item = assessment()
        result = MODULE.calculate(item, PROFILE)["scores"]
        values = {name: raw["central"] for name, raw in item["variables"].items()}
        expected_patr = (
            0.50 * max(0.0, values["S"] - 0.85) ** 2
            + 0.30 * max(0.0, values["C"] - 0.80) ** 2
            + 0.20 * values["Rj"]
        )
        self.assertTrue(math.isclose(result["P_atr"]["central"], expected_patr, rel_tol=1e-12))
        self.assertTrue(
            math.isclose(
                result["E_i_adj"]["central"],
                result["E_i"]["central"] - expected_patr,
                rel_tol=1e-12,
            )
        )

    def test_moral_imputation_matches_upstream_formula(self):
        item = assessment()
        result = MODULE.calculate(item, PROFILE)["scores"]["M_f"]["central"]
        v = {name: raw["central"] for name, raw in item["variables"].items()}
        expected = v["D_p"] * v["D_a"] * (
            0.25 * v["I"] + 0.20 * v["Lz"] + 0.20 * v["G"] + 0.20 * v["C"] + 0.15 * v["S"]
        )
        self.assertTrue(math.isclose(result, expected, rel_tol=1e-12))

    def test_bounds_contain_central_value(self):
        result = MODULE.calculate(assessment(), PROFILE)
        for metric in result["scores"].values():
            self.assertLessEqual(metric["low"], metric["central"])
            self.assertLessEqual(metric["central"], metric["high"])

    def test_more_capture_reduces_relative_exergy(self):
        lower = MODULE.calculate(assessment(C=0.2), PROFILE)["scores"]["Ex_r"]["central"]
        higher = MODULE.calculate(assessment(C=0.9), PROFILE)["scores"]["Ex_r"]["central"]
        self.assertGreater(lower, higher)

    def test_core_only_assessment_is_not_falsely_called_complete(self):
        result = MODULE.calculate(assessment(include_advanced=False), PROFILE)
        self.assertEqual(result["formal_completeness"], "core-only")
        self.assertEqual(set(result["missing_canonical_variables"]), set(MODULE.ADVANCED_VARS))
        self.assertNotIn("P_atr", result["scores"])
        self.assertNotIn("M_f", result["scores"])

    def test_partial_advanced_variables_are_rejected(self):
        item = assessment(include_advanced=False)
        item["variables"]["Rj"] = interval(0.5)
        with self.assertRaises(MODULE.InputError):
            MODULE.calculate(item, PROFILE)

    def test_temporal_formula_includes_liberation_atrocity_and_irreversibility(self):
        item = assessment()
        temporal_vars = {
            name: interval(raw["central"])
            for name, raw in item["variables"].items()
            if name in MODULE.CORE_VARS or name == "Rj"
        }
        item["temporal"] = {
            "lambda": 0.1,
            "snapshots": [
                {
                    "t": 0,
                    "gamma": 0.8,
                    "delta": 0.9,
                    "irreversibility": 0.5,
                    "variables": temporal_vars,
                }
            ],
        }
        out = MODULE.calculate(item, PROFILE)["temporal"]
        self.assertIsNotNone(out)
        v = {name: raw["central"] for name, raw in temporal_vars.items()}
        p = MODULE.validate_profile(PROFILE)
        base = MODULE.scalar_scores(v, p)
        patr = (
            p["r1"] * max(0.0, v["S"] - p["S_crit"]) ** 2
            + p["r2"] * max(0.0, v["C"] - p["C_crit"]) ** 2
            + p["r3"] * v["Rj"]
        )
        expected_b = (base["Ex_b"] + v["O"] + v["A"] * v["V_ep"] + v["L"]) * 0.8
        expected_d = (v["S"] ** p["qS"] + v["Ecol"] + v["C"] ** p["qC"] + patr) * 0.9 * 1.5
        self.assertTrue(math.isclose(out["B_acc"]["central"], expected_b, rel_tol=1e-12))
        self.assertTrue(math.isclose(out["D_acc"]["central"], expected_d, rel_tol=1e-12))
        self.assertTrue(math.isclose(out["N_t"]["central"], expected_b - expected_d, rel_tol=1e-12))

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

    def test_invalid_interval_is_rejected(self):
        item = assessment()
        item["variables"]["A"] = {"low": 0.8, "central": 0.5, "high": 0.9}
        with self.assertRaises(MODULE.InputError):
            MODULE.calculate(item, PROFILE)

    def test_transition_profile_ambiguity_is_preserved_not_normalized(self):
        self.assertTrue(
            math.isclose(sum(PROFILE[f"a{i}"] for i in range(1, 6)), 0.90, rel_tol=1e-12)
        )


if __name__ == "__main__":
    unittest.main()
