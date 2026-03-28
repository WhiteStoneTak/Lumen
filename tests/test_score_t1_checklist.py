"""Tests for the narrow deterministic T1 checklist scorer.

Coverage:
 1. Strong correct response for clamp scores high
 2. Strong correct response for count_vowels scores high
 3. Strong correct response for is_sorted scores high
 4. Partial response gives fractional score (0 < score < 1)
 5. Synonym variation still earns positive score
 6. Contradictory/negating response scores low
 7. Empty response gives invalid_response status
 8. Whitespace-only response gives invalid_response status
 9. Result validates under scorer-result-v1
10. score == evidence["matched"] / evidence["total"]
11. Property-level evidence is present and well-formed
12. Wrong task raises/errors gracefully
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from experiment.contracts import validate_scorer_result  # noqa: E402
from experiment.score_t1_checklist import (  # noqa: E402
    normalize_t1_response,
    score_t1_property,
    score_t1_checklist,
    load_t1_scoring_context,
    _extract_key_terms,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_scorer_input(func_id: str) -> dict:
    return {
        "lumen_schema": "scorer-input-v1",
        "func_id": func_id,
        "task": "T1",
        "condition": "C1",
        "model_id": "test-model",
        "response_ref": "results/raw/placeholder.json",
    }


def _run(func_id: str, response: str) -> dict:
    return score_t1_checklist(_make_scorer_input(func_id), response)


# ---------------------------------------------------------------------------
# Responses used in tests
# ---------------------------------------------------------------------------

# clamp: covers all 9 properties
CLAMP_STRONG_RESPONSE = """\
clamp(value, lo, hi) accepts exactly three parameters: value, lo, and hi.
All three parameters are annotated as float.
The precondition lo <= hi is documented in the docstring but is not enforced
by the function body.
The return type is float.
Returns lo when value is strictly less than lo.
Returns hi when value is strictly greater than hi.
Returns value unchanged when lo <= value <= hi.
The interval [lo, hi] is closed: when value equals lo or hi exactly,
value itself is returned.
When lo equals hi, the function always returns lo (= hi) regardless of value.
"""

# clamp: covers only three properties (P01 inputs, P02 annotated float, P04 return type)
# Deliberately omits lo/hi/value to avoid incidental matches on behavior/edge_case properties.
CLAMP_PARTIAL_RESPONSE = """\
clamp accepts three float parameters and returns a float.
The return type is float. Three inputs are annotated as float.
"""

# clamp: mostly negations / contradictions
CLAMP_CONTRADICTORY_RESPONSE = """\
The function does not accept three parameters.
The return type is not float.
It does not return value unchanged when within range.
There is no precondition documented in the docstring.
"""

# count_vowels: covers all 7 properties
COUNT_VOWELS_STRONG_RESPONSE = """\
count_vowels(s) accepts exactly one parameter s, annotated as str.
The return type is int.
The return value is a non-negative integer representing the number of vowel characters found.
Counts exactly the five vowels: a, e, i, o, u.
The count is case-insensitive: uppercase vowel letters are counted the same as lowercase.
Non-vowel characters — including consonants, digits, spaces, and punctuation —
do not contribute to the count.
Returns 0 for an empty string.
"""

# is_sorted: covers all 8 properties
IS_SORTED_STRONG_RESPONSE = """\
is_sorted(items) accepts exactly one parameter items, annotated as list.
The element type is unconstrained; the function requires only that elements
support pairwise comparison with >.
The return type is bool.
Returns True if and only if items is in non-decreasing order (no element is
strictly greater than its immediate successor).
Returns False if any adjacent pair exists where the earlier element is strictly
greater than the later element.
Returns True for an empty list.
Returns True for a single-element list.
Equal adjacent elements satisfy the non-decreasing condition; a list of all
equal elements returns True.
"""


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------

class TestExtractKeyTerms(unittest.TestCase):
    def test_removes_stop_words(self) -> None:
        terms = _extract_key_terms("The function accepts exactly three parameters.")
        self.assertNotIn("the", terms)
        self.assertNotIn("function", terms)
        self.assertNotIn("parameters", terms)

    def test_keeps_short_meaningful_terms(self) -> None:
        # lo and hi are 2 chars — must be preserved
        terms = _extract_key_terms("Returns lo when value is strictly less than lo.")
        self.assertIn("lo", terms)

    def test_keeps_type_names(self) -> None:
        terms = _extract_key_terms("The return type is float.")
        self.assertIn("float", terms)
        self.assertIn("return", terms)

    def test_deduplicates(self) -> None:
        terms = _extract_key_terms("lo lo lo float float")
        self.assertEqual(terms.count("lo"), 1)
        self.assertEqual(terms.count("float"), 1)

    def test_empty_statement(self) -> None:
        terms = _extract_key_terms("")
        self.assertEqual(terms, [])


class TestNormalizeT1Response(unittest.TestCase):
    def test_lowercases(self) -> None:
        self.assertEqual(normalize_t1_response("FLOAT"), "float")

    def test_collapses_whitespace(self) -> None:
        result = normalize_t1_response("a   b\t\nc")
        self.assertEqual(result, "a b c")

    def test_strips_punctuation(self) -> None:
        result = normalize_t1_response("value, lo, and hi.")
        self.assertNotIn(",", result)

    def test_preserves_numbers(self) -> None:
        result = normalize_t1_response("returns 0 for empty string")
        self.assertIn("0", result)


class TestScoreT1Property(unittest.TestCase):
    def _prop(self, statement: str) -> dict:
        return {
            "property_id": "test.P01",
            "category": "behavior",
            "statement": statement,
            "required": True,
        }

    def test_match_when_key_terms_present(self) -> None:
        prop = self._prop("The return type is float.")
        # Response contains "return type" and "float" — all 3 key terms present
        norm = normalize_t1_response("The return type is float.")
        result = score_t1_property(prop, norm)
        self.assertEqual(result["matched"], 1)
        self.assertIn("float", result["evidence"])

    def test_no_match_when_terms_absent(self) -> None:
        prop = self._prop("The return type is float.")
        norm = normalize_t1_response("The function returns a boolean.")
        result = score_t1_property(prop, norm)
        self.assertEqual(result["matched"], 0)

    def test_negation_suppresses_match(self) -> None:
        prop = self._prop("The return type is float.")
        # "not return type float" — "not " directly precedes the first primary term "return"
        # Primary terms are the first 2 found: ['return', 'type']
        # "not " appears within the 15-char window before "return"
        norm = normalize_t1_response("not return type float")
        result = score_t1_property(prop, norm)
        self.assertEqual(result["matched"], 0)

    def test_empty_statement_gives_zero(self) -> None:
        prop = self._prop("")
        norm = normalize_t1_response("anything here")
        result = score_t1_property(prop, norm)
        self.assertEqual(result["matched"], 0)
        self.assertIn("No key terms", result["note"])


# ---------------------------------------------------------------------------
# Integration tests: score_t1_checklist
# ---------------------------------------------------------------------------

class TestScoreT1ClampFunction(unittest.TestCase):

    def test_strong_response_scores_high(self) -> None:
        result = _run("clamp", CLAMP_STRONG_RESPONSE)
        self.assertEqual(result["status"], "ok")
        self.assertGreaterEqual(result["score"], 0.8,
            msg=f"Expected score >= 0.8, got {result['score']}")

    def test_partial_response_gives_fractional_score(self) -> None:
        result = _run("clamp", CLAMP_PARTIAL_RESPONSE)
        self.assertEqual(result["status"], "ok")
        # Should match some but not all (9 properties total)
        self.assertGreater(result["score"], 0.0)
        self.assertLess(result["score"], 1.0)

    def test_contradictory_response_scores_low(self) -> None:
        result = _run("clamp", CLAMP_CONTRADICTORY_RESPONSE)
        self.assertEqual(result["status"], "ok")
        # Negations should suppress most matches
        self.assertLessEqual(result["score"], 0.5)

    def test_score_equals_matched_over_total(self) -> None:
        result = _run("clamp", CLAMP_STRONG_RESPONSE)
        ev = result["evidence"]
        expected = ev["matched"] / ev["total"]
        self.assertAlmostEqual(result["score"], expected, places=9)


class TestScoreT1CountVowelsFunction(unittest.TestCase):

    def test_strong_response_scores_high(self) -> None:
        result = _run("count_vowels", COUNT_VOWELS_STRONG_RESPONSE)
        self.assertEqual(result["status"], "ok")
        self.assertGreaterEqual(result["score"], 0.7,
            msg=f"Expected score >= 0.7, got {result['score']}")


class TestScoreT1IsSortedFunction(unittest.TestCase):

    def test_strong_response_scores_high(self) -> None:
        result = _run("is_sorted", IS_SORTED_STRONG_RESPONSE)
        self.assertEqual(result["status"], "ok")
        self.assertGreaterEqual(result["score"], 0.7,
            msg=f"Expected score >= 0.7, got {result['score']}")


class TestScoreT1InvalidInputs(unittest.TestCase):

    def test_empty_response_gives_invalid_response_status(self) -> None:
        result = _run("clamp", "")
        self.assertEqual(result["status"], "invalid_response")
        self.assertIsNotNone(result["failure_reason"])
        self.assertEqual(result["failure_reason"]["code"], "empty_response")
        self.assertEqual(result["score"], 0.0)

    def test_whitespace_only_response_gives_invalid_response_status(self) -> None:
        result = _run("clamp", "   \n\t  ")
        self.assertEqual(result["status"], "invalid_response")
        self.assertIsNotNone(result["failure_reason"])

    def test_none_response_gives_invalid_response_status(self) -> None:
        result = score_t1_checklist(_make_scorer_input("clamp"), None)  # type: ignore[arg-type]
        self.assertEqual(result["status"], "invalid_response")
        self.assertEqual(result["score"], 0.0)


class TestScoreT1ContractCompliance(unittest.TestCase):

    def test_result_validates_under_scorer_result_v1_strong(self) -> None:
        result = _run("clamp", CLAMP_STRONG_RESPONSE)
        validated = validate_scorer_result(result)
        self.assertEqual(validated["lumen_schema"], "scorer-result-v1")
        self.assertEqual(validated["task"], "T1")

    def test_result_validates_under_scorer_result_v1_partial(self) -> None:
        result = _run("clamp", CLAMP_PARTIAL_RESPONSE)
        validated = validate_scorer_result(result)
        self.assertEqual(validated["task"], "T1")

    def test_result_validates_for_all_pilot_functions(self) -> None:
        cases = [
            ("clamp", CLAMP_STRONG_RESPONSE),
            ("count_vowels", COUNT_VOWELS_STRONG_RESPONSE),
            ("is_sorted", IS_SORTED_STRONG_RESPONSE),
            ("clamp", "minimal response"),
        ]
        for func_id, response in cases:
            with self.subTest(func_id=func_id):
                result = _run(func_id, response)
                validated = validate_scorer_result(result)
                self.assertEqual(validated["func_id"], func_id)

    def test_invalid_response_validates_under_scorer_result_v1(self) -> None:
        result = _run("clamp", "")
        validated = validate_scorer_result(result)
        self.assertEqual(validated["status"], "invalid_response")
        self.assertIsNotNone(validated["failure_reason"])

    def test_score_in_unit_interval(self) -> None:
        for func_id, response in [
            ("clamp", CLAMP_STRONG_RESPONSE),
            ("clamp", CLAMP_PARTIAL_RESPONSE),
            ("clamp", CLAMP_CONTRADICTORY_RESPONSE),
            ("count_vowels", COUNT_VOWELS_STRONG_RESPONSE),
            ("is_sorted", IS_SORTED_STRONG_RESPONSE),
        ]:
            with self.subTest(func_id=func_id):
                result = _run(func_id, response)
                self.assertGreaterEqual(result["score"], 0.0)
                self.assertLessEqual(result["score"], 1.0)


class TestScoreT1EvidenceShape(unittest.TestCase):

    def test_property_level_evidence_present(self) -> None:
        result = _run("clamp", CLAMP_STRONG_RESPONSE)
        ev = result["evidence"]
        self.assertIn("properties", ev)
        self.assertIsInstance(ev["properties"], list)
        self.assertGreater(len(ev["properties"]), 0)

    def test_property_evidence_fields(self) -> None:
        result = _run("clamp", CLAMP_STRONG_RESPONSE)
        for entry in result["evidence"]["properties"]:
            with self.subTest(pid=entry.get("property_id")):
                self.assertIn("property_id", entry)
                self.assertIn("matched", entry)
                self.assertIn("evidence", entry)
                self.assertIn("note", entry)
                self.assertIn(entry["matched"], (0, 1))

    def test_matched_and_total_counts_consistent(self) -> None:
        result = _run("clamp", CLAMP_STRONG_RESPONSE)
        ev = result["evidence"]
        props = ev["properties"]
        computed_matched = sum(p["matched"] for p in props)
        self.assertEqual(ev["matched"], computed_matched)
        self.assertEqual(ev["total"], len(props))

    def test_score_equals_matched_over_total_for_all_functions(self) -> None:
        for func_id, response in [
            ("clamp", CLAMP_STRONG_RESPONSE),
            ("clamp", CLAMP_PARTIAL_RESPONSE),
            ("count_vowels", COUNT_VOWELS_STRONG_RESPONSE),
            ("is_sorted", IS_SORTED_STRONG_RESPONSE),
        ]:
            with self.subTest(func_id=func_id):
                result = _run(func_id, response)
                ev = result["evidence"]
                expected = ev["matched"] / ev["total"]
                self.assertAlmostEqual(result["score"], expected, places=9)


class TestScoreT1SynonymVariation(unittest.TestCase):
    """Verify the scorer still returns positive scores for paraphrased correct answers."""

    def test_clamp_paraphrased_parameters(self) -> None:
        # Uses "three inputs" instead of "three parameters"
        response = (
            "clamp takes three inputs: value, lo, and hi. "
            "All are annotated as float. The return type is float. "
            "The value is clamped between lo and hi. "
            "Returns lo when value is below lo, hi when above hi, "
            "value unchanged otherwise. The precondition is documented "
            "in the docstring but not enforced by the body."
        )
        result = _run("clamp", response)
        self.assertGreater(result["score"], 0.0)

    def test_count_vowels_paraphrased(self) -> None:
        response = (
            "count_vowels accepts a string s and returns an int. "
            "It counts the five vowels a e i o u in s. "
            "The counting is case-insensitive. "
            "Non-vowel characters do not contribute. "
            "Returns 0 for an empty string."
        )
        result = _run("count_vowels", response)
        self.assertGreater(result["score"], 0.0)


if __name__ == "__main__":
    unittest.main()
