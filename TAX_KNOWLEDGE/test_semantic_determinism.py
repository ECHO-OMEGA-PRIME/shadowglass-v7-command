"""
SEMANTIC DETERMINISM TEST SUITE
Tax Intelligence Engine v1.2.0

Validates that semantic normalization preserves hash stability.

MANDATORY BEFORE DEPLOYMENT:
If any test fails, deployment MUST be blocked.

Author: ECHO OMEGA PRIME
Authority: 11.0 SOVEREIGN
"""

import sys
sys.path.insert(0, "O:/ECHO_OMEGA_PRIME/TAX_KNOWLEDGE")

import requests
import hashlib
import re
from typing import List, Tuple, Dict
from dataclasses import dataclass

from semantic_dictionary import normalize_semantics, NormalizationResult

BASE_URL = "http://localhost:8391"


@dataclass
class TestResult:
    test_name: str
    passed: bool
    details: str
    evidence: Dict = None


class SemanticDeterminismTest:
    """Verify semantic normalization preserves hash stability."""

    def __init__(self):
        self.results: List[TestResult] = []
        self.failures: List[TestResult] = []

    def query(self, question: str) -> Dict:
        """Execute query and return response."""
        try:
            resp = requests.post(
                f"{BASE_URL}/tax/query",
                json={"question": question, "mode": "fast"},
                timeout=30
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def compute_local_hash(self, query: str, topic_key: str = "", candidates: List[str] = None) -> str:
        """Compute determinism hash locally for verification."""
        if candidates is None:
            candidates = []
        # Normalize exactly as engine does
        query_normalized = re.sub(r'\s+', ' ', query.lower().strip())
        candidate_keys = sorted(candidates)
        hash_input = f"{query_normalized}|{topic_key}|{','.join(candidate_keys)}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def log(self, test_name: str, passed: bool, details: str, evidence: Dict = None):
        result = TestResult(test_name, passed, details, evidence)
        self.results.append(result)
        if not passed:
            self.failures.append(result)
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {test_name}")
        if details and not passed:
            print(f"       {details}")

    # =========================================================================
    # TEST 1: Hash Stability Across Semantic Variants
    # =========================================================================
    def test_hash_stability(self):
        """Semantic variants MUST produce identical hashes after normalization."""
        print("\n=== TEST 1: Hash Stability Across Semantic Variants ===")

        # Each group should normalize to the same form and produce identical hashes
        test_groups = [
            # Reasonable Compensation
            (
                "reasonable_comp",
                [
                    "reasonable compensation s-corp",
                    "reasonable comp s corp",
                    "reasonable comp s-corp",
                    "reasonable compensation s corp",
                    "reas comp scorp",
                ],
                "reasonable compensation s-corp"  # Expected normalized form
            ),
            # Home Office
            (
                "home_office",
                [
                    "home office deduction",
                    "work from home deduction",
                    "wfh deduction",
                    "home office expense",
                ],
                "home office deduction"
            ),
            # Self-Employment Tax
            (
                "se_tax",
                [
                    "self-employment tax",
                    "self employment tax",
                    "se tax",
                    "schedule se",
                ],
                "self-employment tax"
            ),
            # Depreciation Recapture
            (
                "depreciation",
                [
                    "depreciation recapture",
                    "depreciation recap",
                    "1245 recapture",
                    "section 1245 recapture",
                ],
                "depreciation recapture"
            ),
            # QBI
            (
                "qbi",
                [
                    "qualified business income deduction",
                    "qbi deduction",
                    "section 199a",
                    "199a deduction",
                ],
                "qualified business income deduction"
            ),
        ]

        for group_name, variants, expected_normalized in test_groups:
            normalized_forms = []
            for variant in variants:
                result = normalize_semantics(variant)
                normalized_forms.append(result.normalized)

            # Check all normalize to same form
            unique_forms = set(normalized_forms)

            if len(unique_forms) == 1:
                self.log(f"semantic_{group_name}", True, f"All variants → '{list(unique_forms)[0]}'")
            else:
                self.log(
                    f"semantic_{group_name}",
                    False,
                    f"Variants normalized inconsistently",
                    {"variants": variants, "normalized_forms": normalized_forms}
                )

    # =========================================================================
    # TEST 2: API Hash Consistency
    # =========================================================================
    def test_api_hash_consistency(self):
        """Semantic variants MUST return identical hashes from the API."""
        print("\n=== TEST 2: API Hash Consistency ===")

        # Test pairs that should produce identical hashes
        test_pairs = [
            ("reasonable compensation s-corp", "reasonable comp s corp"),
            ("home office deduction", "work from home deduction"),
            ("self-employment tax", "se tax"),
            ("depreciation recapture", "1245 recapture"),
        ]

        for query_a, query_b in test_pairs:
            result_a = self.query(query_a)
            result_b = self.query(query_b)

            if "error" in result_a or "error" in result_b:
                self.log(
                    f"api_hash_{query_a[:20]}",
                    False,
                    f"Query failed",
                    {"a": result_a.get("error"), "b": result_b.get("error")}
                )
                continue

            hash_a = result_a.get("determinism_hash")
            hash_b = result_b.get("determinism_hash")

            if hash_a == hash_b:
                self.log(f"api_hash_{query_a[:20]}", True, f"Both return hash: {hash_a}")
            else:
                self.log(
                    f"api_hash_{query_a[:20]}",
                    False,
                    f"Hash mismatch: '{hash_a}' vs '{hash_b}'",
                    {"query_a": query_a, "query_b": query_b, "hash_a": hash_a, "hash_b": hash_b}
                )

    # =========================================================================
    # TEST 3: Normalization Idempotency
    # =========================================================================
    def test_idempotency(self):
        """Normalizing twice should produce identical results."""
        print("\n=== TEST 3: Normalization Idempotency ===")

        test_queries = [
            "reasonable comp s corp",
            "work from home deduction",
            "se tax on llc income",
            "qbi deduction for scorp",
        ]

        for query in test_queries:
            result_1 = normalize_semantics(query)
            result_2 = normalize_semantics(result_1.normalized)

            if result_1.normalized == result_2.normalized:
                self.log(f"idempotent_{query[:20]}", True, "Double normalization stable")
            else:
                self.log(
                    f"idempotent_{query[:20]}",
                    False,
                    f"Not idempotent: '{result_1.normalized}' → '{result_2.normalized}'"
                )

    # =========================================================================
    # TEST 4: No Partial Token Corruption
    # =========================================================================
    def test_no_partial_token_corruption(self):
        """Ensure short patterns don't corrupt longer words."""
        print("\n=== TEST 4: No Partial Token Corruption ===")

        # These should NOT have their internal tokens replaced
        test_cases = [
            ("compensation analysis", "compensation analysis"),  # "comp" shouldn't affect "compensation"
            ("corporate tax", "corporate tax"),  # "corp" shouldn't corrupt "corporate"
            ("comprehensive review", "comprehensive review"),  # "comp" again
            ("incorporate business", "incorporate business"),  # "corp" inside "incorporate"
        ]

        for input_query, expected_output in test_cases:
            result = normalize_semantics(input_query)

            if result.normalized == expected_output:
                self.log(f"no_corruption_{input_query[:20]}", True, "No partial token corruption")
            else:
                self.log(
                    f"no_corruption_{input_query[:20]}",
                    False,
                    f"Corrupted: '{input_query}' → '{result.normalized}' (expected '{expected_output}')"
                )

    # =========================================================================
    # TEST 5: Whitespace Invariance
    # =========================================================================
    def test_whitespace_invariance(self):
        """Different whitespace should normalize identically."""
        print("\n=== TEST 5: Whitespace Invariance ===")

        base_queries = [
            "reasonable compensation",
            "home office deduction",
            "self-employment tax",
        ]

        for base in base_queries:
            variants = [
                base,
                f"  {base}  ",
                base.replace(" ", "  "),
                base.replace(" ", "\t"),
                f"\n{base}\n",
            ]

            normalized_forms = [normalize_semantics(v).normalized for v in variants]
            unique_forms = set(normalized_forms)

            if len(unique_forms) == 1:
                self.log(f"whitespace_{base[:20]}", True, f"All whitespace variants → '{list(unique_forms)[0]}'")
            else:
                self.log(
                    f"whitespace_{base[:20]}",
                    False,
                    f"Whitespace variants differ",
                    {"forms": normalized_forms}
                )

    # =========================================================================
    # TEST 6: Case Invariance
    # =========================================================================
    def test_case_invariance(self):
        """Different cases should normalize identically."""
        print("\n=== TEST 6: Case Invariance ===")

        base_queries = [
            "Reasonable Compensation",
            "HOME OFFICE DEDUCTION",
            "Self-Employment Tax",
        ]

        for base in base_queries:
            variants = [
                base.lower(),
                base.upper(),
                base.title(),
                base.swapcase(),
            ]

            normalized_forms = [normalize_semantics(v).normalized for v in variants]
            unique_forms = set(normalized_forms)

            if len(unique_forms) == 1:
                self.log(f"case_{base[:20]}", True, f"All case variants → '{list(unique_forms)[0]}'")
            else:
                self.log(
                    f"case_{base[:20]}",
                    False,
                    f"Case variants differ",
                    {"forms": normalized_forms}
                )

    # =========================================================================
    # TEST 7: Dictionary Integrity
    # =========================================================================
    def test_dictionary_integrity(self):
        """Verify dictionary has no circular references or conflicts."""
        print("\n=== TEST 7: Dictionary Integrity ===")

        from semantic_dictionary import verify_dictionary_integrity

        try:
            verify_dictionary_integrity()
            self.log("dictionary_integrity", True, "No circular references or conflicts")
        except ValueError as e:
            self.log("dictionary_integrity", False, str(e))

    # =========================================================================
    # RUN ALL TESTS
    # =========================================================================
    def run_all(self) -> bool:
        """Run all determinism tests."""
        print("=" * 70)
        print("SEMANTIC DETERMINISM TEST SUITE")
        print("Tax Intelligence Engine v1.1.1")
        print("=" * 70)

        self.test_hash_stability()
        self.test_api_hash_consistency()
        self.test_idempotency()
        self.test_no_partial_token_corruption()
        self.test_whitespace_invariance()
        self.test_case_invariance()
        self.test_dictionary_integrity()

        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)

        print(f"Tests Passed: {passed}/{total}")

        if self.failures:
            print(f"\nFAILURES ({len(self.failures)}):")
            for f in self.failures:
                print(f"  - {f.test_name}: {f.details}")
            print("\n" + "=" * 70)
            print("DEPLOYMENT BLOCKED - Hash stability not verified")
            print("=" * 70)
            return False
        else:
            print("\n" + "=" * 70)
            print("ALL TESTS PASSED - Semantic normalization is deterministic")
            print("DEPLOYMENT APPROVED")
            print("=" * 70)
            return True


if __name__ == "__main__":
    tester = SemanticDeterminismTest()
    success = tester.run_all()
    sys.exit(0 if success else 1)
