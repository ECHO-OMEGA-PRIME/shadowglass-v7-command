"""
ECHO Tax Expert Search - Unified RAG Search API
Complete tax knowledge across ALL domains

Domains Covered:
- Personal Tax (1040, filing status, standard/itemized)
- Business Tax (all entity types)
- IRC (Internal Revenue Code Title 26)
- IRS Publications
- Deductions (all categories)
- Credits (tax credits)
- State Taxes

Author: ECHO OMEGA PRIME
Authority: 11.0 SOVEREIGN
"""

from pathlib import Path
from typing import List, Dict, Optional
import chromadb
from dataclasses import dataclass
from loguru import logger

CHROMA_PATH = Path("O:/ECHO_OMEGA_PRIME/TAX_KNOWLEDGE/chroma_db")
COLLECTION_NAME = "tax_knowledge_complete"


@dataclass
class TaxResult:
    """Tax search result."""
    text: str
    domain: str
    section: str
    source: str
    distance: float

    def __repr__(self):
        return f"<Tax [{self.domain}] {self.section} | dist={self.distance:.3f}>"


class TaxExpertSearch:
    """Unified tax expert search across all domains."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        self.collection = self.client.get_collection(COLLECTION_NAME)
        self._initialized = True
        logger.info(f"Tax Expert Search initialized. {self.collection.count()} documents.")

    def search(
        self,
        query: str,
        n_results: int = 10,
        domain: Optional[str] = None
    ) -> List[TaxResult]:
        """
        Search all tax knowledge.

        Args:
            query: Natural language tax question
            n_results: Number of results to return
            domain: Optional domain filter (irc, personal, business, etc.)

        Returns:
            List of TaxResult objects
        """
        where_filter = None
        if domain:
            where_filter = {"domain": domain}

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter
        )

        return [
            TaxResult(
                text=doc,
                domain=meta.get("domain", "unknown"),
                section=meta.get("section", ""),
                source=meta.get("source", ""),
                distance=dist
            )
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            )
        ]

    def personal_tax(self, query: str, n_results: int = 10) -> List[TaxResult]:
        """Search personal tax topics (1040, filing, deductions, credits)."""
        enhanced = f"{query} personal individual 1040 filing"
        return self.search(enhanced, n_results=n_results, domain="personal")

    def business_tax(self, query: str, n_results: int = 10) -> List[TaxResult]:
        """Search business tax topics (all entity types)."""
        enhanced = f"{query} business corporation LLC S-Corp partnership"
        return self.search(enhanced, n_results=n_results, domain="business")

    def irc_search(self, query: str, n_results: int = 10) -> List[TaxResult]:
        """Search Internal Revenue Code sections."""
        return self.search(query, n_results=n_results, domain="irc")

    def deductions(self, query: str, n_results: int = 10) -> List[TaxResult]:
        """Search deduction-related content."""
        enhanced = f"{query} deduction deductible expense"
        # Search both deductions domain and across all
        results = self.search(enhanced, n_results=n_results)
        return results

    def credits(self, query: str, n_results: int = 10) -> List[TaxResult]:
        """Search tax credit-related content."""
        enhanced = f"{query} credit refundable nonrefundable tax credit"
        return self.search(enhanced, n_results=n_results)

    def oilfield(self, query: str, n_results: int = 10) -> List[TaxResult]:
        """Search oilfield/energy tax topics."""
        enhanced = f"{query} oil gas depletion intangible drilling IDC working interest"
        return self.search(enhanced, n_results=n_results)

    def get_irc_section(self, section_num: str, n_chunks: int = 10) -> List[TaxResult]:
        """Get specific IRC section content."""
        query = f"IRC Section {section_num}"
        return self.irc_search(query, n_results=n_chunks)

    def multi_domain(self, query: str, n_results: int = 5) -> Dict[str, List[TaxResult]]:
        """
        Search across multiple domains and return organized results.

        Returns results grouped by domain.
        """
        results = self.search(query, n_results=n_results * 3)

        by_domain: Dict[str, List[TaxResult]] = {}
        for r in results:
            if r.domain not in by_domain:
                by_domain[r.domain] = []
            if len(by_domain[r.domain]) < n_results:
                by_domain[r.domain].append(r)

        return by_domain

    def get_stats(self) -> Dict:
        """Get collection statistics with domain breakdown."""
        total = self.collection.count()

        # Get domain distribution (sample)
        results = self.collection.get(limit=min(total, 20000), include=["metadatas"])
        domains: Dict[str, int] = {}
        for m in results["metadatas"]:
            d = m.get("domain", "unknown")
            domains[d] = domains.get(d, 0) + 1

        return {
            "collection": COLLECTION_NAME,
            "total_documents": total,
            "domains": domains,
            "path": str(CHROMA_PATH)
        }


# Convenience functions
_searcher = None


def _get_searcher() -> TaxExpertSearch:
    global _searcher
    if _searcher is None:
        _searcher = TaxExpertSearch()
    return _searcher


def search_tax(query: str, n_results: int = 10, domain: Optional[str] = None) -> List[TaxResult]:
    """Search all tax knowledge."""
    return _get_searcher().search(query, n_results, domain)


def personal_tax(query: str, n_results: int = 10) -> List[TaxResult]:
    """Search personal tax topics."""
    return _get_searcher().personal_tax(query, n_results)


def business_tax(query: str, n_results: int = 10) -> List[TaxResult]:
    """Search business tax topics."""
    return _get_searcher().business_tax(query, n_results)


def irc_search(query: str, n_results: int = 10) -> List[TaxResult]:
    """Search IRC sections."""
    return _get_searcher().irc_search(query, n_results)


def deductions(query: str, n_results: int = 10) -> List[TaxResult]:
    """Search deductions content."""
    return _get_searcher().deductions(query, n_results)


def credits(query: str, n_results: int = 10) -> List[TaxResult]:
    """Search tax credits content."""
    return _get_searcher().credits(query, n_results)


def oilfield(query: str, n_results: int = 10) -> List[TaxResult]:
    """Search oilfield/energy tax topics."""
    return _get_searcher().oilfield(query, n_results)


def get_irc_section(section_num: str) -> List[TaxResult]:
    """Get specific IRC section."""
    return _get_searcher().get_irc_section(section_num)


def get_tax_stats() -> Dict:
    """Get tax knowledge base stats."""
    return _get_searcher().get_stats()


# Domain coverage tracking
DOMAIN_COVERAGE = {
    "irc": {"status": "COMPLETE", "description": "Internal Revenue Code Title 26"},
    "personal": {"status": "COMPLETE", "description": "Personal tax (1040, filing, deductions)"},
    "business": {"status": "PARTIAL", "description": "Business entities (needs more LLC, S-Corp content)"},
    "irs_publications": {"status": "COMPLETE", "description": "IRS Publications"},
    "deductions": {"status": "NEEDS_CONTENT", "description": "Deduction categories"},
    "credits": {"status": "NEEDS_CONTENT", "description": "Tax credits"},
    "state": {"status": "NEEDS_CONTENT", "description": "State tax laws"},
    "forms": {"status": "NEEDS_CONTENT", "description": "IRS Forms"},
}


if __name__ == "__main__":
    print("=" * 60)
    print("ECHO TAX EXPERT SEARCH TEST")
    print("=" * 60)

    stats = get_tax_stats()
    print(f"\nTotal documents: {stats['total_documents']:,}")
    print("\nDomain breakdown:")
    for domain, count in sorted(stats["domains"].items(), key=lambda x: -x[1]):
        status = DOMAIN_COVERAGE.get(domain, {}).get("status", "UNKNOWN")
        print(f"  {domain}: {count:,} chunks [{status}]")

    # Test searches
    print("\n" + "=" * 60)
    print("SEARCH TESTS")
    print("=" * 60)

    tests = [
        ("standard deduction 2024", "personal"),
        ("S-Corp reasonable compensation", "business"),
        ("percentage depletion oil gas", "irc"),
        ("child tax credit income limits", None),
        ("home office deduction requirements", None),
    ]

    for query, domain in tests:
        print(f"\nQuery: {query}" + (f" [domain: {domain}]" if domain else ""))
        if domain:
            results = search_tax(query, n_results=3, domain=domain)
        else:
            results = search_tax(query, n_results=3)
        for r in results:
            print(f"  [{r.domain}] {r.section}: {r.text[:60]}...")

    print("\n" + "=" * 60)
    print("COVERAGE GAPS")
    print("=" * 60)
    for domain, info in DOMAIN_COVERAGE.items():
        if info["status"] == "NEEDS_CONTENT":
            print(f"  {domain}: {info['description']}")
