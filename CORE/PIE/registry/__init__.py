"""
PROGRAMMING INTELLIGENCE ENGINE - Registry Module

Immutable authority classification registry.
Sources are classified once and recorded permanently.

System Class: ISOLATED_REASONING_ENGINE
Governance Tier: ZERO
"""

from .authority_registry import (
    AuthorityRegistry,
    AuthorityRecord,
    SourceType,
    SourceTypeWeight,
    ClassificationEvidence,
)

__all__ = [
    "AuthorityRegistry",
    "AuthorityRecord",
    "SourceType",
    "SourceTypeWeight",
    "ClassificationEvidence",
]
