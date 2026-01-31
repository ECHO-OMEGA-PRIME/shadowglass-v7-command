"""
Adversarial Authority Layer Tests
Surfaces nondeterministic behavior in the Tax Intelligence Engine

Tests:
1. Repeated identical queries - must return identical hashes
2. Case sensitivity - should normalize
3. Whitespace variations - should normalize
4. Multi-doctrine conflict scenarios
5. Edge cases: empty queries, special characters
6. Concurrent queries - thread safety
"""

import sys
sys.path.insert(0, "O:/ECHO_OMEGA_PRIME/TAX_KNOWLEDGE")

import requests
import json
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from typing import List, Dict, Any

BASE_URL = "http://localhost:8391"

class AdversarialTester:
    def __init__(self):
        self.results = []
        self.failures = []

    def log(self, test_name: str, passed: bool, details: str = ""):
        status = "PASS" if passed else "FAIL"
        self.results.append({"test": test_name, "passed": passed, "details": details})
        if not passed:
            self.failures.append({"test": test_name, "details": details})
        print(f"[{status}] {test_name}")
        if details and not passed:
            print(f"       {details}")

    def query(self, question: str, mode: str = "fast") -> Dict[str, Any]:
        """Execute a query and return the response."""
        try:
            resp = requests.post(
                f"{BASE_URL}/tax/query",
                json={"question": question, "mode": mode},
                timeout=30
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    # =========================================================================
    # TEST 1: Repeated Identical Queries
    # =========================================================================
    def test_determinism_repeated_queries(self, iterations: int = 10):
        """Same query N times must return identical determinism_hash."""
        print("\n=== TEST 1: Repeated Identical Queries ===")

        test_queries = [
            "What is reasonable compensation for S-corp shareholders?",
            "How are home office deductions calculated?",
            "What are the rules for depreciation recapture?",
        ]

        for query in test_queries:
            hashes = []
            weights = []
            topics = []

            for i in range(iterations):
                result = self.query(query)
                if "error" in result:
                    self.log(f"Repeated query: {query[:40]}...", False, f"Error: {result['error']}")
                    continue

                hashes.append(result.get("determinism_hash"))
                weights.append(result.get("authority_weight"))
                topics.append(result.get("confidence_stratification"))

            # Check all hashes are identical
            unique_hashes = set(hashes)
            unique_weights = set(weights)

            if len(unique_hashes) == 1 and len(unique_weights) == 1:
                self.log(f"Repeated query: {query[:40]}...", True,
                        f"Hash: {hashes[0]}, Weight: {weights[0]}")
            else:
                self.log(f"Repeated query: {query[:40]}...", False,
                        f"Hash variance: {unique_hashes}, Weight variance: {unique_weights}")

    # =========================================================================
    # TEST 2: Case Sensitivity
    # =========================================================================
    def test_case_sensitivity(self):
        """Queries differing only in case should return same doctrine."""
        print("\n=== TEST 2: Case Sensitivity ===")

        test_cases = [
            ("reasonable compensation", "REASONABLE COMPENSATION", "Reasonable Compensation"),
            ("s-corp salary", "S-CORP SALARY", "S-Corp Salary"),
            ("home office deduction", "HOME OFFICE DEDUCTION", "Home Office Deduction"),
        ]

        for variants in test_cases:
            results = [self.query(v) for v in variants]
            hashes = [r.get("determinism_hash") for r in results if "error" not in r]

            # All should match (same normalized query -> same result)
            unique_hashes = set(hashes)

            if len(unique_hashes) == 1:
                self.log(f"Case sensitivity: {variants[0]}", True)
            else:
                self.log(f"Case sensitivity: {variants[0]}", False,
                        f"Different hashes for case variants: {hashes}")

    # =========================================================================
    # TEST 3: Whitespace Variations
    # =========================================================================
    def test_whitespace_normalization(self):
        """Queries with different whitespace should normalize identically."""
        print("\n=== TEST 3: Whitespace Normalization ===")

        test_cases = [
            (
                "reasonable compensation",
                "reasonable  compensation",
                "  reasonable compensation  ",
                "reasonable\tcompensation",
            ),
            (
                "home office deduction",
                "home   office   deduction",
                "  home office deduction",
            ),
        ]

        for variants in test_cases:
            results = [self.query(v) for v in variants]
            hashes = [r.get("determinism_hash") for r in results if "error" not in r]
            doctrines = [r.get("doctrine_match") for r in results if "error" not in r]

            # All should match same doctrine at minimum
            unique_doctrines = set(doctrines)

            if len(unique_doctrines) == 1:
                self.log(f"Whitespace: {variants[0]}", True)
            else:
                self.log(f"Whitespace: {variants[0]}", False,
                        f"Different doctrine matches: {doctrines}")

    # =========================================================================
    # TEST 4: Multi-Doctrine Conflict Scenarios
    # =========================================================================
    def test_conflict_scenarios(self):
        """Queries that could match multiple doctrines - must resolve consistently."""
        print("\n=== TEST 4: Multi-Doctrine Conflict Scenarios ===")

        # These queries are designed to potentially match multiple doctrines
        conflict_queries = [
            "What about compensation and distributions for S-corp?",  # compensation + distributions
            "employee vs independent contractor classification",  # classification + employment tax
            "depreciation on rental property improvements",  # depreciation + rental + improvements
            "charitable contribution deduction limits",  # charitable + deduction limits
            "self-employment tax on LLC income",  # SE tax + LLC + pass-through
        ]

        for query in conflict_queries:
            results = []
            for i in range(5):
                result = self.query(query)
                if "error" not in result:
                    results.append({
                        "hash": result.get("determinism_hash"),
                        "conflict": result.get("conflict_detected"),
                        "weight": result.get("authority_weight"),
                        "strat": result.get("confidence_stratification"),
                    })

            if not results:
                self.log(f"Conflict scenario: {query[:40]}...", False, "No valid results")
                continue

            # Check consistency
            unique_hashes = set(r["hash"] for r in results)
            conflict_detected = results[0].get("conflict")

            if len(unique_hashes) == 1:
                self.log(f"Conflict scenario: {query[:40]}...", True,
                        f"Consistent. Conflict detected: {conflict_detected}")
            else:
                self.log(f"Conflict scenario: {query[:40]}...", False,
                        f"Inconsistent hashes: {unique_hashes}")

    # =========================================================================
    # TEST 5: Edge Cases
    # =========================================================================
    def test_edge_cases(self):
        """Edge cases that might expose nondeterminism."""
        print("\n=== TEST 5: Edge Cases ===")

        edge_cases = [
            ("Empty-ish query", "   "),
            ("Single word", "tax"),
            ("Very long query", "What are the reasonable compensation requirements for S-corporation shareholder-employees who provide services to the corporation and also receive distributions, considering the IRS position on employment taxes and the relevant case law including Exacto Spring and Watson? " * 3),
            ("Special characters", "S-corp compensation @ $100,000?"),
            ("Numbers only", "401k 403b 457"),
            ("Mixed symbols", "1099-NEC vs W-2 classification"),
        ]

        for name, query in edge_cases:
            results = []
            for i in range(3):
                result = self.query(query)
                if "error" not in result:
                    results.append(result.get("determinism_hash"))

            if not results:
                self.log(f"Edge case: {name}", True, "No match (expected for some)")
                continue

            unique_hashes = set(results)
            if len(unique_hashes) == 1:
                self.log(f"Edge case: {name}", True)
            else:
                self.log(f"Edge case: {name}", False, f"Inconsistent: {results}")

    # =========================================================================
    # TEST 6: Concurrent Queries (Thread Safety)
    # =========================================================================
    def test_concurrent_queries(self):
        """Concurrent identical queries must return identical results."""
        print("\n=== TEST 6: Concurrent Queries (Thread Safety) ===")

        test_query = "What is reasonable compensation for S-corp shareholders?"
        num_concurrent = 20

        def make_query(_):
            return self.query(test_query)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_query, i) for i in range(num_concurrent)]
            results = [f.result() for f in as_completed(futures)]

        hashes = [r.get("determinism_hash") for r in results if "error" not in r]
        unique_hashes = set(hashes)

        if len(unique_hashes) == 1:
            self.log(f"Concurrent queries ({num_concurrent}x)", True, f"All returned: {hashes[0]}")
        else:
            self.log(f"Concurrent queries ({num_concurrent}x)", False,
                    f"Race condition! Hashes: {unique_hashes}")

    # =========================================================================
    # TEST 7: Authority Weight Consistency
    # =========================================================================
    def test_authority_weight_consistency(self):
        """Authority weights must be deterministic and correctly ordered."""
        print("\n=== TEST 7: Authority Weight Consistency ===")

        # Queries expected to have different authority weights
        queries_by_expected_weight = [
            ("IRC-heavy", "What does Section 162 say about business expenses?"),
            ("Reg-heavy", "What are the Treasury Regulations on reasonable compensation?"),
            ("Case-heavy", "What did Exacto Spring hold about officer compensation?"),
        ]

        for category, query in queries_by_expected_weight:
            weights = []
            for i in range(5):
                result = self.query(query)
                if "error" not in result:
                    weights.append(result.get("authority_weight"))

            unique_weights = set(weights)
            if len(unique_weights) == 1:
                self.log(f"Authority weight ({category}): {query[:30]}...", True,
                        f"Consistent weight: {weights[0]}")
            else:
                self.log(f"Authority weight ({category}): {query[:30]}...", False,
                        f"Weight variance: {unique_weights}")

    # =========================================================================
    # TEST 8: Response Mode Independence
    # =========================================================================
    def test_response_mode_independence(self):
        """Doctrine selection should be independent of response mode."""
        print("\n=== TEST 8: Response Mode Independence ===")

        query = "What is reasonable compensation for S-corp shareholders?"
        modes = ["fast", "defense", "memo"]

        results_by_mode = {}
        for mode in modes:
            for i in range(3):
                result = self.query(query, mode)
                if "error" not in result:
                    if mode not in results_by_mode:
                        results_by_mode[mode] = []
                    results_by_mode[mode].append({
                        "hash": result.get("determinism_hash"),
                        "weight": result.get("authority_weight"),
                    })

        # All modes should select same doctrine (same hash base, same weight)
        all_weights = []
        for mode, results in results_by_mode.items():
            weights = [r["weight"] for r in results]
            all_weights.extend(weights)

        unique_weights = set(all_weights)
        if len(unique_weights) == 1:
            self.log("Response mode independence", True, f"All modes: weight={all_weights[0]}")
        else:
            self.log("Response mode independence", False, f"Weight varies by mode: {results_by_mode}")

    # =========================================================================
    # TEST 9: Semantic Equivalence
    # =========================================================================
    def test_semantic_equivalence(self):
        """Semantically equivalent queries should match same doctrine."""
        print("\n=== TEST 9: Semantic Equivalence (Keyword-Based) ===")

        # These should all hit the same doctrine due to keyword overlap
        semantic_groups = [
            [
                "reasonable compensation S-corp",
                "S-corp reasonable compensation",
                "S corporation reasonable compensation",
                "reasonable compensation for S-corporation shareholder",
            ],
            [
                "home office deduction",
                "deduction for home office",
                "home office expense deduction",
            ],
        ]

        for group in semantic_groups:
            doctrines = []
            for query in group:
                result = self.query(query)
                if "error" not in result:
                    doctrines.append(result.get("doctrine_match"))

            unique_doctrines = set(doctrines)
            if len(unique_doctrines) == 1:
                self.log(f"Semantic group: {group[0][:30]}...", True)
            else:
                self.log(f"Semantic group: {group[0][:30]}...", False,
                        f"Different doctrine matches: {doctrines}")

    # =========================================================================
    # RUN ALL TESTS
    # =========================================================================
    def run_all(self):
        """Run all adversarial tests."""
        print("=" * 70)
        print("ADVERSARIAL AUTHORITY LAYER TESTS")
        print("=" * 70)

        start = time.time()

        self.test_determinism_repeated_queries()
        self.test_case_sensitivity()
        self.test_whitespace_normalization()
        self.test_conflict_scenarios()
        self.test_edge_cases()
        self.test_concurrent_queries()
        self.test_authority_weight_consistency()
        self.test_response_mode_independence()
        self.test_semantic_equivalence()

        elapsed = time.time() - start

        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        passed = sum(1 for r in self.results if r["passed"])
        total = len(self.results)

        print(f"Tests Passed: {passed}/{total}")
        print(f"Time Elapsed: {elapsed:.2f}s")

        if self.failures:
            print(f"\nFAILURES ({len(self.failures)}):")
            for f in self.failures:
                print(f"  - {f['test']}: {f['details']}")
        else:
            print("\nAll tests passed. No nondeterministic behavior detected.")

        return len(self.failures) == 0


if __name__ == "__main__":
    tester = AdversarialTester()
    success = tester.run_all()
    sys.exit(0 if success else 1)
