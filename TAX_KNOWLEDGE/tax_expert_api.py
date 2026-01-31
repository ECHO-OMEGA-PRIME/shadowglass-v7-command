"""
ECHO Tax Expert API - Unified Fast Response System
Doctrine-first with RAG fallback

Architecture:
- Layer 1: Doctrine cache (0ms) - Pre-compiled expert reasoning
- Layer 2: RAG search (200-500ms) - ChromaDB semantic search
- Layer 3: Full synthesis (on demand) - Deep multi-source analysis

Author: ECHO OMEGA PRIME
Authority: 11.0 SOVEREIGN
"""

from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from tax_doctrine_cache import (
    TaxDoctrineEngine, DoctrineResponse,
    quick_tax_answer, full_tax_doctrine, get_engine
)
from tax_expert_search import TaxExpertSearch, TaxResult, search_tax
import time


@dataclass
class TaxExpertResponse:
    """Unified tax expert response."""
    query: str
    topic: str
    quick_answer: str
    source: str  # "doctrine" or "rag"
    response_time_ms: float
    case_law: List[str] = None
    irc_refs: List[str] = None
    audit_playbook: str = None
    rag_results: List[TaxResult] = None


class TaxExpertAPI:
    """
    Unified tax expert with doctrine-first architecture.

    Usage:
        api = TaxExpertAPI()

        # Fast answer (doctrine only)
        response = api.quick(query)

        # Full answer with citations
        response = api.full(query)

        # Force RAG search
        response = api.search(query)
    """

    def __init__(self):
        self.doctrine = get_engine()
        self._rag = None  # Lazy load

    @property
    def rag(self) -> TaxExpertSearch:
        """Lazy-load RAG to avoid ChromaDB startup on simple queries."""
        if self._rag is None:
            self._rag = TaxExpertSearch()
        return self._rag

    def quick(self, query: str) -> TaxExpertResponse:
        """
        Instant doctrine-based answer. No RAG, no citations.
        Use for: Real-time chat, quick lookups, API responses.
        """
        start = time.time()

        result = self.doctrine.quick_answer(query)

        if result:
            topic, answer = result
            return TaxExpertResponse(
                query=query,
                topic=topic,
                quick_answer=answer,
                source="doctrine",
                response_time_ms=(time.time() - start) * 1000
            )

        # Fallback to single RAG query
        rag_results = self.rag.search(query, n_results=3)
        if rag_results:
            return TaxExpertResponse(
                query=query,
                topic=rag_results[0].section,
                quick_answer=rag_results[0].text[:500],
                source="rag",
                response_time_ms=(time.time() - start) * 1000,
                rag_results=rag_results
            )

        return TaxExpertResponse(
            query=query,
            topic="Unknown",
            quick_answer="No matching tax doctrine found.",
            source="none",
            response_time_ms=(time.time() - start) * 1000
        )

    def full(self, query: str) -> TaxExpertResponse:
        """
        Complete doctrine with case law and audit playbook.
        Use for: Detailed analysis, audit prep, client memos.
        """
        start = time.time()

        doctrine = self.doctrine.full_doctrine(query)

        if doctrine:
            return TaxExpertResponse(
                query=query,
                topic=doctrine.topic,
                quick_answer=doctrine.quick_answer,
                source="doctrine",
                response_time_ms=(time.time() - start) * 1000,
                case_law=doctrine.case_law,
                irc_refs=doctrine.irc_refs,
                audit_playbook=doctrine.audit_playbook
            )

        # Fallback to RAG with more results
        rag_results = self.rag.search(query, n_results=5)
        if rag_results:
            # Synthesize answer from RAG results
            combined = " ".join([r.text[:300] for r in rag_results[:3]])
            irc_refs = list(set([r.section for r in rag_results if r.section.startswith("§")]))

            return TaxExpertResponse(
                query=query,
                topic=rag_results[0].section,
                quick_answer=combined[:800],
                source="rag",
                response_time_ms=(time.time() - start) * 1000,
                irc_refs=irc_refs,
                rag_results=rag_results
            )

        return TaxExpertResponse(
            query=query,
            topic="Unknown",
            quick_answer="No matching tax information found.",
            source="none",
            response_time_ms=(time.time() - start) * 1000
        )

    def search(self, query: str, n_results: int = 10) -> TaxExpertResponse:
        """
        Force RAG search, bypass doctrine cache.
        Use for: Specific IRC lookups, obscure topics, raw document retrieval.
        """
        start = time.time()

        rag_results = self.rag.search(query, n_results=n_results)

        if rag_results:
            return TaxExpertResponse(
                query=query,
                topic=rag_results[0].section,
                quick_answer=rag_results[0].text[:500],
                source="rag",
                response_time_ms=(time.time() - start) * 1000,
                rag_results=rag_results
            )

        return TaxExpertResponse(
            query=query,
            topic="Unknown",
            quick_answer="No matching documents found.",
            source="none",
            response_time_ms=(time.time() - start) * 1000
        )

    def audit_defense(self, topic: str) -> Optional[str]:
        """
        Get audit playbook for specific topic.
        Returns step-by-step defense strategy.
        """
        doctrine = self.doctrine.get_by_topic(topic)
        if doctrine:
            return doctrine.audit_playbook
        return None

    def list_doctrine_topics(self) -> List[str]:
        """List all pre-cached doctrine topics."""
        return self.doctrine.list_topics()


# Singleton
_api = None

def get_api() -> TaxExpertAPI:
    global _api
    if _api is None:
        _api = TaxExpertAPI()
    return _api


# Convenience functions
def quick(query: str) -> TaxExpertResponse:
    """Instant answer from doctrine cache."""
    return get_api().quick(query)

def full(query: str) -> TaxExpertResponse:
    """Full answer with case law and playbook."""
    return get_api().full(query)

def search(query: str, n_results: int = 10) -> TaxExpertResponse:
    """Force RAG search."""
    return get_api().search(query, n_results)


if __name__ == "__main__":
    api = TaxExpertAPI()

    print("=" * 60)
    print("ECHO TAX EXPERT API - PERFORMANCE TEST")
    print("=" * 60)

    queries = [
        ("S-Corp reasonable compensation under audit", "quick"),
        ("IRS rejects my salary data, argues ownership profit", "full"),
        ("IRC section 613A percentage depletion", "search"),
    ]

    for query, mode in queries:
        print(f"\n[{mode.upper()}] {query}")

        if mode == "quick":
            r = api.quick(query)
        elif mode == "full":
            r = api.full(query)
        else:
            r = api.search(query, n_results=3)

        print(f"  Source: {r.source} | Time: {r.response_time_ms:.1f}ms")
        print(f"  Topic: {r.topic}")
        print(f"  Answer: {r.quick_answer[:150]}...")

        if r.case_law:
            print(f"  Case Law: {r.case_law[0]}")
        if r.irc_refs:
            print(f"  IRC: {', '.join(r.irc_refs[:3])}")
