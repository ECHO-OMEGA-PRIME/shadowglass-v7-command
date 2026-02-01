"""
PROGRAMMING INTELLIGENCE ENGINE - Authority Registry
IMMUTABLE SOURCE CLASSIFICATION REGISTRY

Every source is categorized by TYPE, not just vendor.
Classifications are immutable once assigned.
Conflicts are resolved deterministically: higher authority wins.

Source Types:
- SPEC: Official specifications (RFC, W3C, IEEE, ECMA)
- VENDOR_DOCS: Official vendor documentation
- RUNTIME_REALITY: Observed behavior from production systems
- DEPRECATION_NOTICE: Official deprecation announcements
- REFERENCE_IMPL: Reference implementations from maintainers
- FAILURE_NARRATIVE: Postmortems, outage reports, CVEs

System Class: ISOLATED_REASONING_ENGINE
Governance Tier: ZERO
Mutation: PROHIBITED after initial registration
"""

from enum import Enum, IntEnum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path
import hashlib
import json
import re
from loguru import logger


class SourceType(str, Enum):
    """
    Categorization of source documents by their institutional nature.
    This is orthogonal to vendor classification.
    """
    SPEC = "SPEC"                           # RFC, W3C, IEEE, ECMA specs
    VENDOR_DOCS = "VENDOR_DOCS"             # Official vendor documentation
    RUNTIME_REALITY = "RUNTIME_REALITY"     # Observed production behavior
    DEPRECATION_NOTICE = "DEPRECATION"      # Official deprecation announcements
    REFERENCE_IMPL = "REFERENCE_IMPL"       # Reference implementations
    FAILURE_NARRATIVE = "FAILURE_NARRATIVE" # Postmortems, CVEs, incident reports
    API_DEFINITION = "API_DEFINITION"       # OpenAPI, GraphQL schemas, IDL
    CHANGELOG = "CHANGELOG"                 # Release notes, changelogs
    TUTORIAL = "TUTORIAL"                   # Official guides (lower authority)
    COMMUNITY = "COMMUNITY"                 # Community content (lowest)


class SourceTypeWeight(IntEnum):
    """
    Authority weight modifier based on source type.
    Applied in addition to vendor tier weight.
    """
    SPEC = 50              # Specifications are highest authority
    API_DEFINITION = 45    # API definitions are near-spec authority
    VENDOR_DOCS = 40       # Official docs have high authority
    REFERENCE_IMPL = 35    # Reference impls demonstrate correct behavior
    DEPRECATION_NOTICE = 40 # Deprecation notices are authoritative
    RUNTIME_REALITY = 30   # Real behavior trumps docs sometimes
    FAILURE_NARRATIVE = 25 # Postmortems inform but are situational
    CHANGELOG = 20         # Changelogs are informative
    TUTORIAL = 15          # Tutorials can be outdated
    COMMUNITY = 10         # Community content needs verification


@dataclass(frozen=True)
class AuthorityRecord:
    """
    Immutable authority classification for a source.
    Once registered, cannot be mutated - only superseded.
    """
    record_id: str
    source_id: str
    source_type: SourceType
    authority_weight: int              # Combined vendor + type weight
    vendor: Optional[str]
    registered_at: datetime
    registered_by: str                 # System that registered this
    content_hash: str                  # Hash of content at registration
    evidence: Tuple[str, ...]          # Evidence for classification
    supersedes: Optional[str] = None   # Previous record if any

    def __hash__(self):
        return hash(self.record_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "source_id": self.source_id,
            "source_type": self.source_type.value,
            "authority_weight": self.authority_weight,
            "vendor": self.vendor,
            "registered_at": self.registered_at.isoformat(),
            "registered_by": self.registered_by,
            "content_hash": self.content_hash,
            "evidence": list(self.evidence),
            "supersedes": self.supersedes
        }


@dataclass
class ClassificationEvidence:
    """Evidence supporting a source type classification."""
    indicator: str                     # What was found
    pattern_matched: str               # Pattern that matched
    confidence: float                  # 0.0 to 1.0
    location: Optional[str] = None     # Where in content


class AuthorityRegistry:
    """
    IMMUTABLE AUTHORITY CLASSIFICATION REGISTRY

    Sources are classified once and recorded permanently.
    Updates create new records that supersede old ones.
    Conflict resolution is deterministic and auditable.
    """

    # Patterns for detecting source types
    SOURCE_TYPE_PATTERNS: Dict[SourceType, List[str]] = {
        SourceType.SPEC: [
            r"rfc\s*\d+",
            r"ietf\.org",
            r"w3\.org/(TR|Recommendation)",
            r"ecma-international\.org",
            r"ieee\.org/standard",
            r"iso\.org",
            r"(MUST|SHALL|SHOULD|MAY)\s+(?:NOT\s+)?[A-Z]",  # RFC 2119 keywords
            r"normative\s+reference",
            r"specification\s+version",
        ],
        SourceType.DEPRECATION_NOTICE: [
            r"deprecated\s+(since|in|as\s+of)",
            r"will\s+be\s+removed\s+in",
            r"scheduled\s+for\s+removal",
            r"end[- ]of[- ]life",
            r"no\s+longer\s+supported",
            r"sunset(ting|ted)?",
            r"migration\s+required",
            r"breaking\s+change",
        ],
        SourceType.FAILURE_NARRATIVE: [
            r"post[- ]?mortem",
            r"incident\s+report",
            r"outage\s+(report|summary)",
            r"root\s+cause\s+analysis",
            r"cve-\d{4}-\d+",
            r"security\s+advisory",
            r"vulnerability",
            r"lessons?\s+learned",
            r"what\s+went\s+wrong",
        ],
        SourceType.API_DEFINITION: [
            r"openapi:\s*['\"]?\d",
            r"swagger:\s*['\"]?\d",
            r"type\s+(Query|Mutation|Subscription)\s*\{",  # GraphQL
            r"service\s+\w+\s*\{",  # gRPC proto
            r"@api\s+",
            r"paths:\s*\n\s+/",
        ],
        SourceType.CHANGELOG: [
            r"(changelog|release\s*notes|what's\s*new)",
            r"##\s*\[\d+\.\d+",
            r"version\s+\d+\.\d+\.\d+",
            r"released?\s+(on\s+)?\d{4}",
            r"(added|changed|fixed|removed|deprecated):",
        ],
        SourceType.REFERENCE_IMPL: [
            r"reference\s+implementation",
            r"canonical\s+implementation",
            r"official\s+example",
            r"sample\s+code",
            r"(example|demo)\s+implementation",
        ],
        SourceType.TUTORIAL: [
            r"getting\s+started",
            r"quick\s+start",
            r"tutorial",
            r"how\s+to",
            r"step\s+\d+:",
            r"(first|next),?\s+(let's|we)",
        ],
    }

    # Vendor documentation URL patterns
    VENDOR_DOC_PATTERNS = [
        r"docs?\.(aws|google|microsoft|apple|mozilla|python|rust)",
        r"developer\.(apple|google|android|mozilla)\.com",
        r"learn\.microsoft\.com",
        r"cloud\.google\.com/docs",
        r"firebase\.google\.com/docs",
    ]

    def __init__(self, persist_path: Optional[Path] = None):
        self._records: Dict[str, AuthorityRecord] = {}
        self._by_source: Dict[str, List[str]] = {}  # source_id -> record_ids
        self._by_type: Dict[SourceType, Set[str]] = {t: set() for t in SourceType}
        self._superseded: Set[str] = set()  # record_ids that have been superseded
        self.persist_path = persist_path

        if persist_path and persist_path.exists():
            self._load_from_disk()

        logger.info("Authority Registry initialized (IMMUTABLE mode)")

    def classify_source(
        self,
        source_id: str,
        content: str,
        url: Optional[str] = None,
        metadata: Optional[Dict] = None,
        registrar: str = "PIE_AUTO"
    ) -> AuthorityRecord:
        """
        Classify a source and register it immutably.

        Returns the AuthorityRecord (existing or new).
        If source was previously classified, returns existing unless content changed.
        """
        content_hash = self._compute_hash(content)

        # Check for existing record with same content
        existing = self._find_current_record(source_id)
        if existing and existing.content_hash == content_hash:
            logger.debug(f"Returning existing classification for {source_id}")
            return existing

        # Classify the source
        source_type, evidence = self._determine_source_type(content, url)
        vendor = self._extract_vendor(url, metadata)
        authority_weight = self._compute_authority_weight(source_type, vendor)

        # Create immutable record
        record_id = f"auth_{source_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        record = AuthorityRecord(
            record_id=record_id,
            source_id=source_id,
            source_type=source_type,
            authority_weight=authority_weight,
            vendor=vendor,
            registered_at=datetime.now(),
            registered_by=registrar,
            content_hash=content_hash,
            evidence=tuple(e.indicator for e in evidence),
            supersedes=existing.record_id if existing else None
        )

        # Register (immutably)
        self._register_record(record, existing)

        logger.info(
            f"Classified source: {source_id} as {source_type.value} "
            f"(weight: {authority_weight}, vendor: {vendor})"
        )

        return record

    def _determine_source_type(
        self,
        content: str,
        url: Optional[str]
    ) -> Tuple[SourceType, List[ClassificationEvidence]]:
        """
        Determine source type from content and URL patterns.
        Returns (source_type, evidence_list).
        """
        evidence: List[ClassificationEvidence] = []
        type_scores: Dict[SourceType, float] = {t: 0.0 for t in SourceType}

        content_lower = content.lower()[:50000]  # First 50k chars

        # Check content patterns
        for source_type, patterns in self.SOURCE_TYPE_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, content_lower, re.IGNORECASE)
                if matches:
                    confidence = min(len(matches) * 0.15, 0.9)
                    type_scores[source_type] += confidence
                    evidence.append(ClassificationEvidence(
                        indicator=f"Pattern matched: {pattern}",
                        pattern_matched=pattern,
                        confidence=confidence,
                        location=f"{len(matches)} occurrences"
                    ))

        # Check URL for vendor docs
        if url:
            url_lower = url.lower()
            for pattern in self.VENDOR_DOC_PATTERNS:
                if re.search(pattern, url_lower):
                    type_scores[SourceType.VENDOR_DOCS] += 0.7
                    evidence.append(ClassificationEvidence(
                        indicator=f"Vendor docs URL: {pattern}",
                        pattern_matched=pattern,
                        confidence=0.7,
                        location=url
                    ))
                    break

        # Determine winner
        if not any(type_scores.values()):
            # Default to COMMUNITY if no patterns match
            return SourceType.COMMUNITY, [ClassificationEvidence(
                indicator="No patterns matched, defaulting to COMMUNITY",
                pattern_matched="",
                confidence=0.3
            )]

        winner = max(type_scores, key=lambda t: type_scores[t])
        return winner, evidence

    def _extract_vendor(
        self,
        url: Optional[str],
        metadata: Optional[Dict]
    ) -> Optional[str]:
        """Extract vendor from URL or metadata."""
        if metadata and "vendor" in metadata:
            return metadata["vendor"]

        if not url:
            return None

        vendor_patterns = {
            "google": r"(google|firebase|android|golang|go\.dev)",
            "apple": r"(apple|swift\.org|developer\.apple)",
            "microsoft": r"(microsoft|azure|typescript|dotnet)",
            "amazon": r"(aws|amazon)",
            "mozilla": r"(mozilla|mdn)",
            "python": r"(python\.org|docs\.python)",
            "rust": r"(rust-lang|crates\.io)",
            "kubernetes": r"kubernetes\.io",
            "docker": r"(docker\.com|docs\.docker)",
        }

        url_lower = url.lower()
        for vendor, pattern in vendor_patterns.items():
            if re.search(pattern, url_lower):
                return vendor

        return None

    def _compute_authority_weight(
        self,
        source_type: SourceType,
        vendor: Optional[str]
    ) -> int:
        """
        Compute combined authority weight from type and vendor.
        """
        type_weight = SourceTypeWeight[source_type.name].value

        # Vendor bonuses
        vendor_weights = {
            "google": 40,
            "apple": 40,
            "microsoft": 40,
            "amazon": 38,
            "python": 38,
            "rust": 36,
            "kubernetes": 34,
            "docker": 32,
            "mozilla": 30,
        }
        vendor_weight = vendor_weights.get(vendor, 15) if vendor else 10

        return type_weight + vendor_weight

    def _compute_hash(self, content: str) -> str:
        """Compute deterministic content hash."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

    def _find_current_record(self, source_id: str) -> Optional[AuthorityRecord]:
        """Find the current (non-superseded) record for a source."""
        record_ids = self._by_source.get(source_id, [])
        for rid in reversed(record_ids):  # Most recent first
            if rid not in self._superseded:
                return self._records.get(rid)
        return None

    def _register_record(
        self,
        record: AuthorityRecord,
        superseded: Optional[AuthorityRecord]
    ):
        """Register a record and mark superseded if applicable."""
        self._records[record.record_id] = record

        if record.source_id not in self._by_source:
            self._by_source[record.source_id] = []
        self._by_source[record.source_id].append(record.record_id)

        self._by_type[record.source_type].add(record.record_id)

        if superseded:
            self._superseded.add(superseded.record_id)

        # Persist if configured
        if self.persist_path:
            self._persist_to_disk()

    def get_record(self, source_id: str) -> Optional[AuthorityRecord]:
        """Get the current authority record for a source."""
        return self._find_current_record(source_id)

    def get_records_by_type(self, source_type: SourceType) -> List[AuthorityRecord]:
        """Get all current records of a specific type."""
        record_ids = self._by_type.get(source_type, set())
        return [
            self._records[rid] for rid in record_ids
            if rid not in self._superseded
        ]

    def resolve_conflict(
        self,
        records: List[AuthorityRecord]
    ) -> Tuple[AuthorityRecord, Dict[str, Any]]:
        """
        Resolve conflict between multiple authority records.
        DETERMINISTIC: Higher weight always wins.
        """
        if not records:
            raise ValueError("No records to resolve")

        if len(records) == 1:
            return records[0], {"conflict": False}

        # Sort by authority weight (descending)
        sorted_records = sorted(records, key=lambda r: r.authority_weight, reverse=True)
        winner = sorted_records[0]
        losers = sorted_records[1:]

        # Check for tie
        if len(sorted_records) > 1 and sorted_records[0].authority_weight == sorted_records[1].authority_weight:
            # Tie-breaker: Source type priority, then registration time
            type_priority = [
                SourceType.SPEC,
                SourceType.API_DEFINITION,
                SourceType.VENDOR_DOCS,
                SourceType.DEPRECATION_NOTICE,
                SourceType.REFERENCE_IMPL,
            ]
            for stype in type_priority:
                for r in sorted_records:
                    if r.source_type == stype:
                        winner = r
                        break
                if winner != sorted_records[0]:
                    break

        resolution = {
            "conflict": True,
            "resolution_method": "HIGHER_AUTHORITY_WINS",
            "winner": {
                "record_id": winner.record_id,
                "source_type": winner.source_type.value,
                "authority_weight": winner.authority_weight
            },
            "defeated": [
                {
                    "record_id": r.record_id,
                    "source_type": r.source_type.value,
                    "authority_weight": r.authority_weight,
                    "reason": f"Lower authority ({r.authority_weight} < {winner.authority_weight})"
                }
                for r in losers
            ]
        }

        return winner, resolution

    def get_audit_trail(self, source_id: str) -> List[Dict[str, Any]]:
        """Get full audit trail for a source's classifications."""
        record_ids = self._by_source.get(source_id, [])
        trail = []
        for rid in record_ids:
            record = self._records.get(rid)
            if record:
                entry = record.to_dict()
                entry["status"] = "SUPERSEDED" if rid in self._superseded else "CURRENT"
                trail.append(entry)
        return trail

    def _persist_to_disk(self):
        """Persist registry to disk."""
        if not self.persist_path:
            return

        data = {
            "records": {rid: r.to_dict() for rid, r in self._records.items()},
            "superseded": list(self._superseded),
            "persisted_at": datetime.now().isoformat()
        }

        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.persist_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_from_disk(self):
        """Load registry from disk."""
        if not self.persist_path or not self.persist_path.exists():
            return

        with open(self.persist_path) as f:
            data = json.load(f)

        for rid, rdata in data.get("records", {}).items():
            record = AuthorityRecord(
                record_id=rdata["record_id"],
                source_id=rdata["source_id"],
                source_type=SourceType(rdata["source_type"]),
                authority_weight=rdata["authority_weight"],
                vendor=rdata.get("vendor"),
                registered_at=datetime.fromisoformat(rdata["registered_at"]),
                registered_by=rdata["registered_by"],
                content_hash=rdata["content_hash"],
                evidence=tuple(rdata.get("evidence", [])),
                supersedes=rdata.get("supersedes")
            )
            self._records[rid] = record

            if record.source_id not in self._by_source:
                self._by_source[record.source_id] = []
            self._by_source[record.source_id].append(rid)
            self._by_type[record.source_type].add(rid)

        self._superseded = set(data.get("superseded", []))

        logger.info(f"Loaded {len(self._records)} authority records from disk")

    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_records": len(self._records),
            "current_records": len(self._records) - len(self._superseded),
            "superseded_records": len(self._superseded),
            "unique_sources": len(self._by_source),
            "by_type": {
                t.value: len([r for r in self._by_type[t] if r not in self._superseded])
                for t in SourceType
            }
        }


# Self-test assertions
def _self_test():
    """Validate registry functionality."""
    registry = AuthorityRegistry()

    # Test classification
    spec_content = "RFC 2119 defines MUST, SHALL, SHOULD keywords for specifications."
    record1 = registry.classify_source("test_rfc", spec_content, registrar="TEST")
    assert record1.source_type == SourceType.SPEC, "Should classify RFC as SPEC"

    # Test deprecation detection
    dep_content = "This API is deprecated since v2.0 and will be removed in v3.0."
    record2 = registry.classify_source("test_dep", dep_content, registrar="TEST")
    assert record2.source_type == SourceType.DEPRECATION_NOTICE, "Should detect deprecation"

    # Test conflict resolution
    winner, resolution = registry.resolve_conflict([record1, record2])
    assert winner.source_type == SourceType.SPEC, "SPEC should win over DEPRECATION"

    logger.info("Authority Registry self-test PASSED")


if __name__ == "__main__":
    _self_test()
