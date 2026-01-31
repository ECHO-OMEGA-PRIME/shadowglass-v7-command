"""
SEMANTIC NORMALIZATION DICTIONARY
Tax Intelligence Engine v1.1.1

==============================================================================
GOVERNANCE NOTICE:
Semantic normalization is a preprocessing layer.
It must remain deterministic.
Do not attach probabilistic models to this stage.
No vector inference. No embeddings. No auto-learning.
==============================================================================

This module provides a frozen, immutable mapping of semantic equivalents
for tax terminology normalization. All mappings are manually curated and
reviewed for accuracy.

Architecture Position:
    RAW QUERY
        ↓
    SEMANTIC NORMALIZATION (this layer - deterministic)
        ↓
    HASH
        ↓
    DOCTRINE MATCH

Author: ECHO OMEGA PRIME
Authority: 11.0 SOVEREIGN
"""

from typing import Dict, Tuple, List
from dataclasses import dataclass
import re


# ============================================================================
# FROZEN SEMANTIC MAP
# ============================================================================
# Rules:
#   - All keys are lowercase
#   - All keys have normalized spacing (single spaces)
#   - Immutable at runtime
#   - No auto-learning
#   - No vector inference
#   - No external calls
#
# Sort order: Applied by phrase length descending to prevent partial-token
# replacement bugs (e.g., "comp" rewriting inside "compensation")
# ============================================================================

SEMANTIC_MAP: Dict[str, str] = {
    # -------------------------------------------------------------------------
    # Reasonable Compensation Variants
    # -------------------------------------------------------------------------
    "reasonable comp": "reasonable compensation",
    "reasonable compen": "reasonable compensation",
    "reas comp": "reasonable compensation",
    "reas compensation": "reasonable compensation",

    # -------------------------------------------------------------------------
    # S-Corporation Variants
    # -------------------------------------------------------------------------
    "s corp": "s-corp",
    "s corporation": "s-corp",
    "s-corporation": "s-corp",
    "scorp": "s-corp",
    "sub s": "s-corp",
    "subchapter s": "s-corp",
    "sub chapter s": "s-corp",
    "subchapter s corporation": "s-corp",

    # -------------------------------------------------------------------------
    # C-Corporation Variants
    # -------------------------------------------------------------------------
    "c corp": "c-corp",
    "c corporation": "c-corp",
    "c-corporation": "c-corp",
    "ccorp": "c-corp",
    "regular corporation": "c-corp",

    # -------------------------------------------------------------------------
    # Home Office Variants
    # -------------------------------------------------------------------------
    "work from home deduction": "home office deduction",
    "work from home": "home office",
    "wfh deduction": "home office deduction",
    "wfh": "home office",
    "home office expense": "home office deduction",
    "home office expenses": "home office deduction",
    "working from home": "home office",

    # -------------------------------------------------------------------------
    # Self-Employment Variants
    # -------------------------------------------------------------------------
    "self employment tax": "self-employment tax",
    "self employment": "self-employment",
    "se tax": "self-employment tax",
    "schedule se": "self-employment tax",
    "sch se": "self-employment tax",

    # -------------------------------------------------------------------------
    # Depreciation Variants
    # -------------------------------------------------------------------------
    "depreciation recap": "depreciation recapture",
    "deprec recapture": "depreciation recapture",
    "deprec recap": "depreciation recapture",
    "section 1245 recapture": "depreciation recapture",
    "section 1250 recapture": "depreciation recapture",
    "1245 recapture": "depreciation recapture",
    "1250 recapture": "depreciation recapture",

    # -------------------------------------------------------------------------
    # Qualified Business Income Variants
    # -------------------------------------------------------------------------
    "qbi deduction": "qualified business income deduction",
    "qbi": "qualified business income",
    "section 199a": "qualified business income deduction",
    "199a deduction": "qualified business income deduction",
    "199a": "qualified business income",

    # -------------------------------------------------------------------------
    # Independent Contractor Variants
    # -------------------------------------------------------------------------
    "independent contractor": "independent contractor classification",
    "ic classification": "independent contractor classification",
    "1099 worker": "independent contractor classification",
    "1099 contractor": "independent contractor classification",
    "gig worker": "independent contractor classification",

    # -------------------------------------------------------------------------
    # Partnership Variants
    # -------------------------------------------------------------------------
    "k-1": "schedule k-1",
    "k1": "schedule k-1",
    "partner k-1": "schedule k-1",
    "partnership k-1": "schedule k-1",

    # -------------------------------------------------------------------------
    # Retirement Plan Variants
    # -------------------------------------------------------------------------
    "401k": "401(k)",
    "401 k": "401(k)",
    "403b": "403(b)",
    "403 b": "403(b)",
    "457b": "457(b)",
    "457 b": "457(b)",
    "ira": "individual retirement account",
    "roth ira": "roth individual retirement account",
    "sep ira": "sep individual retirement account",
    "simple ira": "simple individual retirement account",

    # -------------------------------------------------------------------------
    # Form Number Variants
    # -------------------------------------------------------------------------
    "form 1040": "1040",
    "form 1120": "1120",
    "form 1120s": "1120-s",
    "form 1120-s": "1120-s",
    "form 1065": "1065",
    "form 990": "990",
    "form 941": "941",
    "form 940": "940",
    "form w-2": "w-2",
    "form w2": "w-2",
    "form 1099": "1099",
    "form 1099-nec": "1099-nec",
    "form 1099-misc": "1099-misc",

    # -------------------------------------------------------------------------
    # Tax Year/Period Variants
    # -------------------------------------------------------------------------
    "tax yr": "tax year",
    "fiscal yr": "fiscal year",
    "fy": "fiscal year",
    "ty": "tax year",

    # -------------------------------------------------------------------------
    # IRS/Authority Variants
    # -------------------------------------------------------------------------
    "internal revenue service": "irs",
    "revenue service": "irs",
    "treasury regulations": "treasury regulation",
    "treas reg": "treasury regulation",
    "treas. reg.": "treasury regulation",
    "treas. reg": "treasury regulation",
    "treasury reg": "treasury regulation",
    "irc section": "section",
    "irc sec": "section",
    "irc sec.": "section",

    # -------------------------------------------------------------------------
    # Common Abbreviations
    # -------------------------------------------------------------------------
    "amt": "alternative minimum tax",
    "nol": "net operating loss",
    "agi": "adjusted gross income",
    "magi": "modified adjusted gross income",
    "ltcg": "long-term capital gain",
    "stcg": "short-term capital gain",
    "fmv": "fair market value",
    "fbt": "fringe benefit tax",
    "eitc": "earned income tax credit",
    "ctc": "child tax credit",

    # -------------------------------------------------------------------------
    # Entity Type Variants
    # -------------------------------------------------------------------------
    "llc": "limited liability company",
    "l.l.c.": "limited liability company",
    "l.l.c": "limited liability company",
    "sole prop": "sole proprietorship",
    "sole proprietor": "sole proprietorship",
    "sp": "sole proprietorship",
    "gp": "general partnership",
    "lp": "limited partnership",
    "llp": "limited liability partnership",
    "pllc": "professional limited liability company",
}


# ============================================================================
# FROZEN - DO NOT MODIFY AT RUNTIME
# ============================================================================

# Pre-compute sorted keys by length (longest first) for safe replacement
_SORTED_KEYS: Tuple[str, ...] = tuple(
    sorted(SEMANTIC_MAP.keys(), key=len, reverse=True)
)


@dataclass(frozen=True)
class NormalizationResult:
    """Immutable result of semantic normalization."""
    original: str
    normalized: str
    variants_detected: Tuple[str, ...]
    was_modified: bool

    def __hash__(self):
        return hash((self.original, self.normalized, self.variants_detected, self.was_modified))


def normalize_semantics(query: str) -> NormalizationResult:
    """
    Deterministic semantic normalization.

    Execution Order (MUST NOT CHANGE):
        1. Lowercase
        2. Whitespace collapse
        3. Semantic replacement (longest phrases first, word-boundary aware)

    ===========================================================================
    GOVERNANCE NOTICE:
    This function is a preprocessing layer. It must remain deterministic.
    Do not attach probabilistic models to this stage.
    ===========================================================================

    Args:
        query: Raw input query

    Returns:
        NormalizationResult with original, normalized, and detected variants
    """
    # Step 1: Lowercase
    working = query.lower()

    # Step 2: Whitespace collapse (tabs, newlines, multiple spaces → single space)
    working = re.sub(r'\s+', ' ', working).strip()

    # Track what we found
    original = working
    detected_variants: List[str] = []

    # Step 3: Semantic replacement - LONGEST PHRASES FIRST
    # This prevents partial-token chaos (e.g., "comp" inside "compensation")
    # Use word-boundary matching to ensure we don't match mid-word
    for phrase in _SORTED_KEYS:
        replacement = SEMANTIC_MAP[phrase]

        # Skip if phrase equals replacement (would be redundant)
        if phrase == replacement:
            continue

        # Skip entries where the phrase is a non-prefix substring of replacement
        # This prevents idempotency issues EXCEPT for legitimate prefix expansions
        # e.g., "reasonable comp" → "reasonable compensation" is OK (prefix)
        # but "compen" inside "compensation" would be bad (non-prefix)
        if phrase in replacement and not replacement.startswith(phrase):
            continue

        # Use word-boundary regex for safe replacement
        # \b ensures we match whole words/phrases, not substrings
        pattern = r'\b' + re.escape(phrase) + r'\b'
        if re.search(pattern, working):
            detected_variants.append(phrase)
            working = re.sub(pattern, replacement, working)

    return NormalizationResult(
        original=original,
        normalized=working,
        variants_detected=tuple(detected_variants),
        was_modified=len(detected_variants) > 0
    )


def get_semantic_map() -> Dict[str, str]:
    """Return a copy of the semantic map for inspection. Original is immutable."""
    return dict(SEMANTIC_MAP)


def get_sorted_keys() -> Tuple[str, ...]:
    """Return the pre-sorted keys (longest first) for inspection."""
    return _SORTED_KEYS


# ============================================================================
# INTEGRITY VERIFICATION
# ============================================================================

def verify_dictionary_integrity() -> bool:
    """
    Verify the semantic dictionary has no circular references or conflicts.

    Returns:
        True if integrity check passes

    Raises:
        ValueError if integrity check fails
    """
    # Check 1: No key equals its value
    for key, value in SEMANTIC_MAP.items():
        if key == value:
            raise ValueError(f"Redundant mapping: '{key}' → '{value}'")

    # Check 2: No circular references (A→B and B→A)
    for key, value in SEMANTIC_MAP.items():
        if value in SEMANTIC_MAP and SEMANTIC_MAP[value] == key:
            raise ValueError(f"Circular reference: '{key}' ↔ '{value}'")

    # Check 3: All keys are lowercase and normalized
    for key in SEMANTIC_MAP.keys():
        normalized = re.sub(r'\s+', ' ', key.lower()).strip()
        if key != normalized:
            raise ValueError(f"Key not normalized: '{key}' should be '{normalized}'")

    return True


# Run integrity check on import
verify_dictionary_integrity()
