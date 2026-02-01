"""
PROGRAMMING INTELLIGENCE ENGINE - LAYER 4
Deterministic Engineering Doctrine Engine

Mirror the tax engine's determinism principles.
Identical query → identical conclusion.
No stochastic drift.

Attach:
- determinism hash
- authority weight
- confidence tier
- controlling source

Engineering decisions must be defensible.

System Class: ISOLATED_REASONING_ENGINE
Governance Tier: ZERO
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
import sqlite3
from loguru import logger

from ..engine.models import (
    EngineeringDoctrine,
    SourceReference,
    VersionMetadata,
    VersionStatus,
    ConfidenceTier,
    QueryResult
)
from .authority_hierarchy import AuthorityHierarchyEngine
from .version_awareness import VersionAwarenessEngine
from .semantic_graph import SemanticEngineeringGraph


@dataclass
class DoctrineQuery:
    """A query to the doctrine engine."""
    query_id: str
    query_text: str
    target_version: Optional[str] = None
    category_filter: Optional[str] = None
    authority_minimum: Optional[int] = None
    include_deprecated: bool = False
    require_deterministic: bool = True


@dataclass
class DeterminismProof:
    """Proof that a result is deterministic."""
    query_hash: str
    result_hash: str
    reasoning_hash: str
    timestamp: datetime
    inputs_frozen: Dict[str, str]


class DeterministicDoctrineEngine:
    """
    LAYER 4: Deterministic Engineering Doctrine Engine

    Identical query → identical conclusion.
    No stochastic drift.
    All decisions are defensible with full audit trail.

    REASONING_ISOLATION_PROTOCOL enforced:
    No OMNISCIENT memory calls during cognition.
    Observation only. Never interference.
    """

    def __init__(
        self,
        authority_engine: AuthorityHierarchyEngine,
        version_engine: VersionAwarenessEngine,
        semantic_graph: SemanticEngineeringGraph,
        db_path: Optional[Path] = None
    ):
        self.authority = authority_engine
        self.versions = version_engine
        self.graph = semantic_graph

        # Doctrine storage
        self.doctrines: Dict[str, EngineeringDoctrine] = {}
        self.doctrine_index: Dict[str, Set[str]] = {}  # category -> doctrine_ids
        self.tag_index: Dict[str, Set[str]] = {}  # tag -> doctrine_ids

        # Determinism tracking
        self.query_cache: Dict[str, QueryResult] = {}
        self.determinism_log: List[DeterminismProof] = []

        # Database for persistence
        self.db_path = db_path or Path(__file__).parent.parent / "doctrine" / "doctrines.db"
        self._init_database()

        logger.info("Deterministic Doctrine Engine initialized")
        logger.info("REASONING_ISOLATION_PROTOCOL: ACTIVE")

    def _init_database(self):
        """Initialize SQLite database for doctrine persistence."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS doctrines (
                doctrine_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT,
                authority_weight INTEGER,
                confidence_tier TEXT,
                determinism_hash TEXT,
                version_metadata TEXT,
                source_references TEXT,
                related_nodes TEXT,
                tags TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_log (
                query_id TEXT PRIMARY KEY,
                query_text TEXT NOT NULL,
                result_hash TEXT,
                determinism_hash TEXT,
                processed_at TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_category ON doctrines(category)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_authority ON doctrines(authority_weight)
        """)

        conn.commit()
        conn.close()

    def register_doctrine(
        self,
        doctrine: EngineeringDoctrine
    ) -> EngineeringDoctrine:
        """
        Register a doctrine in the engine.
        Computes determinism hash and authority weight.
        """
        # Compute authority weight from sources
        self.authority.compute_authority_weight(doctrine)

        # Compute determinism hash
        doctrine.compute_determinism_hash()

        # Store in memory
        self.doctrines[doctrine.doctrine_id] = doctrine

        # Index by category
        if doctrine.category:
            if doctrine.category not in self.doctrine_index:
                self.doctrine_index[doctrine.category] = set()
            self.doctrine_index[doctrine.category].add(doctrine.doctrine_id)

        # Index by tags
        for tag in doctrine.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = set()
            self.tag_index[tag].add(doctrine.doctrine_id)

        # Persist to database
        self._persist_doctrine(doctrine)

        logger.info(
            f"Doctrine registered: {doctrine.doctrine_id} | "
            f"Authority: {doctrine.authority_weight} | "
            f"Hash: {doctrine.determinism_hash[:16]}..."
        )

        return doctrine

    def _persist_doctrine(self, doctrine: EngineeringDoctrine):
        """Persist doctrine to database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO doctrines (
                doctrine_id, title, content, category, authority_weight,
                confidence_tier, determinism_hash, version_metadata,
                source_references, related_nodes, tags, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doctrine.doctrine_id,
            doctrine.title,
            doctrine.content,
            doctrine.category,
            doctrine.authority_weight,
            doctrine.confidence_tier.value,
            doctrine.determinism_hash,
            json.dumps(self._serialize_version_metadata(doctrine.version_metadata)),
            json.dumps([self._serialize_source(s) for s in doctrine.source_references]),
            json.dumps(doctrine.related_nodes),
            json.dumps(doctrine.tags),
            doctrine.created_at.isoformat(),
            doctrine.updated_at.isoformat()
        ))

        conn.commit()
        conn.close()

    def _serialize_version_metadata(
        self,
        meta: Optional[VersionMetadata]
    ) -> Optional[Dict]:
        """Serialize version metadata for storage."""
        if not meta:
            return None
        return {
            "version_introduced": meta.version_introduced,
            "version_deprecated": meta.version_deprecated,
            "version_removed": meta.version_removed,
            "replacement_path": meta.replacement_path,
            "breaking_changes": meta.breaking_changes,
            "compatibility_notes": meta.compatibility_notes,
            "status": meta.status.value,
            "last_verified": meta.last_verified.isoformat() if meta.last_verified else None
        }

    def _serialize_source(self, source: SourceReference) -> Dict:
        """Serialize source reference for storage."""
        return {
            "source_id": source.source_id,
            "source_type": source.source_type,
            "authority_tier": source.authority_tier.value,
            "trust_level": source.trust_level.value,
            "url": source.url,
            "file_path": str(source.file_path) if source.file_path else None,
            "content_hash": source.content_hash,
            "vendor": source.vendor
        }

    def query(self, query: DoctrineQuery) -> QueryResult:
        """
        Query the doctrine engine.

        DETERMINISM GUARANTEE:
        Identical query → identical result.
        """
        # Compute query hash for caching
        query_hash = self._compute_query_hash(query)

        # Check cache first (determinism requirement)
        if query.require_deterministic and query_hash in self.query_cache:
            cached = self.query_cache[query_hash]
            logger.debug(f"Returning cached result for query: {query_hash[:16]}")
            return cached

        # Find matching doctrines
        candidates = self._find_matching_doctrines(query)

        # Filter by authority if required
        if query.authority_minimum:
            candidates = [
                d for d in candidates
                if d.authority_weight >= query.authority_minimum
            ]

        # Check version compatibility
        version_warnings = []
        if query.target_version:
            filtered = []
            for doctrine in candidates:
                check = self.versions.check_version_compatibility(
                    doctrine, query.target_version
                )
                if check.is_compatible or query.include_deprecated:
                    filtered.append(doctrine)
                    if check.warnings:
                        version_warnings.extend(check.warnings)
            candidates = filtered

        # Resolve conflicts using authority hierarchy
        conflicts_resolved = []
        if len(candidates) > 1:
            # Group by topic/category
            by_category = {}
            for d in candidates:
                cat = d.category or "general"
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(d)

            # Resolve conflicts within each category
            final_candidates = []
            for category, group in by_category.items():
                if len(group) > 1:
                    winner, report = self.authority.resolve_conflict(group)
                    final_candidates.append(winner)
                    conflicts_resolved.append(report)
                else:
                    final_candidates.append(group[0])
            candidates = final_candidates

        # Build reasoning chain
        reasoning_chain = self._build_reasoning_chain(query, candidates)

        # Generate final recommendation
        recommendation = self._generate_recommendation(candidates, version_warnings)

        # Determine confidence
        confidence = self._determine_confidence(candidates, version_warnings)

        # Build authority report
        authority_report = self._build_authority_report(candidates)

        # Create result
        result = QueryResult(
            query_id=query.query_id,
            query_text=query.query_text,
            doctrines=candidates,
            reasoning_chain=reasoning_chain,
            final_recommendation=recommendation,
            confidence=confidence,
            authority_report=authority_report,
            version_warnings=version_warnings,
            conflicts_resolved=conflicts_resolved,
            determinism_hash=""
        )

        # Compute result hash for determinism verification
        result.compute_result_hash()

        # Cache for determinism
        self.query_cache[query_hash] = result

        # Log for audit
        self._log_query(query, result)

        # Create determinism proof
        proof = DeterminismProof(
            query_hash=query_hash,
            result_hash=result.determinism_hash,
            reasoning_hash=hashlib.sha256(
                json.dumps(reasoning_chain, sort_keys=True).encode()
            ).hexdigest(),
            timestamp=datetime.now(),
            inputs_frozen={
                "doctrine_count": str(len(candidates)),
                "target_version": query.target_version or "any"
            }
        )
        self.determinism_log.append(proof)

        logger.info(
            f"Query processed: {query.query_id} | "
            f"Doctrines: {len(candidates)} | "
            f"Confidence: {confidence.value}"
        )

        return result

    def _compute_query_hash(self, query: DoctrineQuery) -> str:
        """Compute deterministic hash for a query."""
        hash_input = json.dumps({
            "query_text": query.query_text,
            "target_version": query.target_version,
            "category_filter": query.category_filter,
            "authority_minimum": query.authority_minimum,
            "include_deprecated": query.include_deprecated
        }, sort_keys=True)
        return hashlib.sha256(hash_input.encode()).hexdigest()

    def _find_matching_doctrines(
        self,
        query: DoctrineQuery
    ) -> List[EngineeringDoctrine]:
        """Find doctrines matching the query."""
        candidates = []
        query_lower = query.query_text.lower()
        query_words = set(query_lower.split())

        for doctrine in self.doctrines.values():
            score = 0

            # Category filter
            if query.category_filter and doctrine.category != query.category_filter:
                continue

            # Title match
            if any(word in doctrine.title.lower() for word in query_words):
                score += 10

            # Content match
            content_lower = doctrine.content.lower()
            for word in query_words:
                if word in content_lower:
                    score += 2

            # Tag match
            for tag in doctrine.tags:
                if tag.lower() in query_words:
                    score += 5

            # Include if score > 0
            if score > 0:
                candidates.append((score, doctrine))

        # Sort by score descending
        candidates.sort(key=lambda x: x[0], reverse=True)
        return [d for _, d in candidates[:20]]  # Top 20

    def _build_reasoning_chain(
        self,
        query: DoctrineQuery,
        doctrines: List[EngineeringDoctrine]
    ) -> List[str]:
        """Build a step-by-step reasoning chain."""
        chain = []

        chain.append(f"Query received: '{query.query_text}'")

        if query.target_version:
            chain.append(f"Target version specified: {query.target_version}")

        chain.append(f"Found {len(doctrines)} relevant doctrines")

        for doctrine in doctrines[:5]:  # Top 5
            source = doctrine.get_controlling_source()
            chain.append(
                f"Doctrine '{doctrine.title}' | "
                f"Authority: {doctrine.authority_weight} | "
                f"Source: {source.vendor if source else 'Unknown'}"
            )

            if doctrine.version_metadata:
                meta = doctrine.version_metadata
                if meta.status != VersionStatus.ACTIVE:
                    chain.append(
                        f"  ⚠ Status: {meta.status.value} | "
                        f"Replacement: {meta.replacement_path or 'N/A'}"
                    )

        # Graph reasoning if nodes connected
        if doctrines:
            primary = doctrines[0]
            if primary.related_nodes:
                graph_result = self.graph.reason_about(
                    query.query_text,
                    primary.related_nodes[:5]
                )
                if graph_result.get("insights"):
                    chain.append("Graph insights:")
                    for insight in graph_result["insights"][:3]:
                        chain.append(f"  - {insight}")

        return chain

    def _generate_recommendation(
        self,
        doctrines: List[EngineeringDoctrine],
        warnings: List[str]
    ) -> str:
        """Generate a final recommendation."""
        if not doctrines:
            return "No relevant doctrines found. Manual research required."

        primary = doctrines[0]

        # Check for deprecation
        if primary.version_metadata:
            meta = primary.version_metadata
            if meta.status == VersionStatus.REMOVED:
                return (
                    f"BLOCKED: '{primary.title}' has been removed. "
                    f"Use: {meta.replacement_path or 'See migration guide'}"
                )
            if meta.status == VersionStatus.DEPRECATED:
                return (
                    f"CAUTION: '{primary.title}' is deprecated. "
                    f"Valid but migration recommended to: {meta.replacement_path or 'newer version'}"
                )

        # Standard recommendation
        source = primary.get_controlling_source()
        authority_desc = (
            "HIGH" if primary.authority_weight >= 80 else
            "MODERATE" if primary.authority_weight >= 60 else
            "REVIEW_RECOMMENDED"
        )

        rec = (
            f"Recommended: '{primary.title}' | "
            f"Authority: {authority_desc} ({primary.authority_weight}) | "
            f"Source: {source.vendor if source else 'Unverified'}"
        )

        if warnings:
            rec += f" | {len(warnings)} warning(s)"

        return rec

    def _determine_confidence(
        self,
        doctrines: List[EngineeringDoctrine],
        warnings: List[str]
    ) -> ConfidenceTier:
        """Determine confidence tier for the result."""
        if not doctrines:
            return ConfidenceTier.REQUIRES_REVIEW

        primary = doctrines[0]

        # Start with doctrine's own confidence
        base_confidence = primary.confidence_tier

        # Adjust based on authority
        if primary.authority_weight >= 80:
            if base_confidence == ConfidenceTier.MODERATE:
                return ConfidenceTier.HIGH_CONFIDENCE
            return ConfidenceTier.DETERMINISTIC

        if primary.authority_weight >= 60:
            return ConfidenceTier.HIGH_CONFIDENCE

        if primary.authority_weight >= 40:
            return ConfidenceTier.MODERATE

        # Downgrade if warnings
        if warnings:
            if base_confidence == ConfidenceTier.HIGH_CONFIDENCE:
                return ConfidenceTier.MODERATE
            return ConfidenceTier.LOW_CONFIDENCE

        return ConfidenceTier.REQUIRES_REVIEW

    def _build_authority_report(
        self,
        doctrines: List[EngineeringDoctrine]
    ) -> Dict[str, Any]:
        """Build detailed authority report for audit."""
        return {
            "doctrine_count": len(doctrines),
            "authority_distribution": {
                "tier_100": len([d for d in doctrines if d.authority_weight == 100]),
                "tier_80": len([d for d in doctrines if 80 <= d.authority_weight < 100]),
                "tier_60": len([d for d in doctrines if 60 <= d.authority_weight < 80]),
                "tier_40": len([d for d in doctrines if 40 <= d.authority_weight < 60]),
                "tier_20": len([d for d in doctrines if d.authority_weight < 40])
            },
            "sources": [
                {
                    "doctrine_id": d.doctrine_id,
                    "controlling_source": d.get_controlling_source().source_id
                    if d.get_controlling_source() else None,
                    "authority": d.authority_weight
                }
                for d in doctrines[:10]
            ],
            "defensibility": (
                "HIGH" if all(d.authority_weight >= 60 for d in doctrines) else
                "MODERATE" if any(d.authority_weight >= 60 for d in doctrines) else
                "REQUIRES_REVIEW"
            )
        }

    def _log_query(self, query: DoctrineQuery, result: QueryResult):
        """Log query for audit trail."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO query_log (
                query_id, query_text, result_hash, determinism_hash, processed_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            query.query_id,
            query.query_text,
            result.determinism_hash,
            result.determinism_hash,
            result.processed_at.isoformat()
        ))

        conn.commit()
        conn.close()

    def verify_determinism(
        self,
        query: DoctrineQuery,
        expected_hash: str
    ) -> Tuple[bool, str]:
        """
        Verify that a query produces the expected result.
        Core determinism guarantee.
        """
        result = self.query(query)

        if result.determinism_hash == expected_hash:
            return True, "Determinism verified: identical result"

        return False, (
            f"Determinism violation detected! "
            f"Expected: {expected_hash[:16]}... "
            f"Got: {result.determinism_hash[:16]}..."
        )

    def get_decision_report(
        self,
        doctrine_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a defensible decision report for a doctrine."""
        doctrine = self.doctrines.get(doctrine_id)
        if not doctrine:
            return None

        return doctrine.to_decision_report()

    def export_doctrines(self) -> Dict[str, Any]:
        """Export all doctrines for backup/transfer."""
        return {
            "doctrines": [
                {
                    "doctrine_id": d.doctrine_id,
                    "title": d.title,
                    "content": d.content,
                    "category": d.category,
                    "authority_weight": d.authority_weight,
                    "confidence_tier": d.confidence_tier.value,
                    "determinism_hash": d.determinism_hash,
                    "tags": d.tags
                }
                for d in self.doctrines.values()
            ],
            "metadata": {
                "total_doctrines": len(self.doctrines),
                "categories": list(self.doctrine_index.keys()),
                "exported_at": datetime.now().isoformat()
            }
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "total_doctrines": len(self.doctrines),
            "categories": {
                cat: len(ids) for cat, ids in self.doctrine_index.items()
            },
            "authority_distribution": {
                "tier_100": len([d for d in self.doctrines.values() if d.authority_weight == 100]),
                "tier_80": len([d for d in self.doctrines.values() if 80 <= d.authority_weight < 100]),
                "tier_60": len([d for d in self.doctrines.values() if 60 <= d.authority_weight < 80]),
                "tier_40": len([d for d in self.doctrines.values() if 40 <= d.authority_weight < 60]),
                "tier_20": len([d for d in self.doctrines.values() if d.authority_weight < 40])
            },
            "cached_queries": len(self.query_cache),
            "determinism_proofs": len(self.determinism_log)
        }
