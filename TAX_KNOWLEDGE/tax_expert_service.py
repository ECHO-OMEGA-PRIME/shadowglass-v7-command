"""
ECHO Tax Expert FastAPI Service
Doctrine-first with RAG fallback - Sub-millisecond responses

Endpoints:
    GET  /health              - Service health check
    GET  /topics              - List all doctrine topics
    POST /quick               - Instant doctrine answer (0ms)
    POST /full                - Full answer with case law
    POST /search              - Force RAG search
    GET  /audit/{topic}       - Get audit playbook for topic
    GET  /stats               - Collection statistics

Author: ECHO OMEGA PRIME
Authority: 11.0 SOVEREIGN
Port: 8390
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
import time
from loguru import logger

# Configure logging
logger.add(
    "O:/ECHO_OMEGA_PRIME/TAX_KNOWLEDGE/logs/tax_service_{time}.log",
    rotation="10 MB",
    retention="7 days",
    level="INFO"
)


# Lazy load to avoid import errors during startup
_api = None
_search = None


def get_api():
    """Lazy load TaxExpertAPI."""
    global _api
    if _api is None:
        from tax_expert_api import TaxExpertAPI
        _api = TaxExpertAPI()
        logger.info("TaxExpertAPI initialized")
    return _api


def get_search():
    """Lazy load TaxExpertSearch for stats."""
    global _search
    if _search is None:
        from tax_expert_search import TaxExpertSearch
        _search = TaxExpertSearch()
        logger.info("TaxExpertSearch initialized")
    return _search


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("ECHO Tax Expert Service starting...")
    # Pre-warm doctrine cache
    api = get_api()
    topics = api.list_doctrine_topics()
    logger.info(f"Doctrine cache loaded: {len(topics)} topics")
    yield
    logger.info("ECHO Tax Expert Service shutting down...")


app = FastAPI(
    title="ECHO Tax Expert API",
    description="Doctrine-first tax expert with RAG fallback. Sub-millisecond responses for common queries.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class TaxQuery(BaseModel):
    """Tax query request."""
    query: str = Field(..., description="Tax question or topic", min_length=3)
    n_results: int = Field(default=5, description="Number of results for RAG search", ge=1, le=50)


class TaxResponse(BaseModel):
    """Unified tax response."""
    query: str
    topic: str
    answer: str
    source: str  # "doctrine" | "rag" | "none"
    response_time_ms: float
    case_law: Optional[List[str]] = None
    irc_refs: Optional[List[str]] = None
    audit_playbook: Optional[str] = None
    rag_results: Optional[List[Dict[str, Any]]] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    doctrine_topics: int
    chroma_documents: int
    version: str


class StatsResponse(BaseModel):
    """Statistics response."""
    total_documents: int
    doctrine_topics: int
    domains: Dict[str, int]


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/", include_in_schema=False)
async def root():
    """Redirect to docs."""
    return {"message": "ECHO Tax Expert API", "docs": "/docs"}


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Service health check.
    Returns doctrine and ChromaDB status.
    """
    try:
        api = get_api()
        topics = api.list_doctrine_topics()

        # Get ChromaDB count
        try:
            search = get_search()
            stats = search.get_stats()
            doc_count = stats.get("total_documents", 0)
        except Exception:
            doc_count = 0

        return HealthResponse(
            status="healthy",
            service="ECHO Tax Expert",
            doctrine_topics=len(topics),
            chroma_documents=doc_count,
            version="1.0.0"
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/topics", response_model=List[str], tags=["Doctrine"])
async def list_topics():
    """
    List all pre-cached doctrine topics.
    These topics have instant (0ms) response times.
    """
    api = get_api()
    return api.list_doctrine_topics()


@app.post("/quick", response_model=TaxResponse, tags=["Query"])
async def quick_answer(request: TaxQuery):
    """
    Get instant doctrine-based answer.

    - **Speed**: ~0ms for doctrine hits, ~200ms for RAG fallback
    - **Use for**: Real-time chat, quick lookups, API responses
    - **Returns**: Quick answer without full citations
    """
    start = time.time()
    api = get_api()

    result = api.quick(request.query)

    # Convert RAG results if present
    rag_results = None
    if result.rag_results:
        rag_results = [
            {"section": r.section, "text": r.text[:300], "source": r.source}
            for r in result.rag_results
        ]

    return TaxResponse(
        query=result.query,
        topic=result.topic,
        answer=result.quick_answer,
        source=result.source,
        response_time_ms=result.response_time_ms,
        rag_results=rag_results
    )


@app.post("/full", response_model=TaxResponse, tags=["Query"])
async def full_answer(request: TaxQuery):
    """
    Get complete doctrine with case law and audit playbook.

    - **Speed**: ~0ms for doctrine hits
    - **Use for**: Detailed analysis, audit prep, client memos
    - **Returns**: Full answer with case citations and IRC references
    """
    api = get_api()

    result = api.full(request.query)

    # Convert RAG results if present
    rag_results = None
    if result.rag_results:
        rag_results = [
            {"section": r.section, "text": r.text[:300], "source": r.source}
            for r in result.rag_results
        ]

    return TaxResponse(
        query=result.query,
        topic=result.topic,
        answer=result.quick_answer,
        source=result.source,
        response_time_ms=result.response_time_ms,
        case_law=result.case_law,
        irc_refs=result.irc_refs,
        audit_playbook=result.audit_playbook,
        rag_results=rag_results
    )


@app.post("/search", response_model=TaxResponse, tags=["Query"])
async def rag_search(request: TaxQuery):
    """
    Force RAG search, bypass doctrine cache.

    - **Speed**: ~200-500ms
    - **Use for**: Specific IRC lookups, obscure topics, raw document retrieval
    - **Returns**: ChromaDB search results
    """
    api = get_api()

    result = api.search(request.query, n_results=request.n_results)

    # Convert RAG results
    rag_results = None
    if result.rag_results:
        rag_results = [
            {"section": r.section, "text": r.text, "source": r.source, "distance": r.distance}
            for r in result.rag_results
        ]

    return TaxResponse(
        query=result.query,
        topic=result.topic,
        answer=result.quick_answer,
        source=result.source,
        response_time_ms=result.response_time_ms,
        irc_refs=result.irc_refs,
        rag_results=rag_results
    )


@app.get("/audit/{topic}", tags=["Doctrine"])
async def get_audit_playbook(topic: str):
    """
    Get audit defense playbook for a specific topic.

    Returns step-by-step defense strategy for IRS examination.
    """
    api = get_api()

    playbook = api.audit_defense(topic)

    if playbook:
        return {
            "topic": topic,
            "audit_playbook": playbook
        }

    # Try to find similar topic
    topics = api.list_doctrine_topics()
    similar = [t for t in topics if topic.lower() in t.lower()]

    if similar:
        raise HTTPException(
            status_code=404,
            detail=f"Topic not found. Did you mean: {similar}"
        )

    raise HTTPException(
        status_code=404,
        detail=f"No audit playbook for '{topic}'. Use /topics to see available topics."
    )


@app.get("/stats", response_model=StatsResponse, tags=["System"])
async def get_stats():
    """
    Get collection statistics.
    Returns document counts by domain.
    """
    try:
        search = get_search()
        stats = search.get_stats()
        api = get_api()
        topics = api.list_doctrine_topics()

        return StatsResponse(
            total_documents=stats.get("total_documents", 0),
            doctrine_topics=len(topics),
            domains=stats.get("domains", {})
        )
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/irc/{section}", tags=["Query"])
async def get_irc_section(
    section: str,
    chunks: int = Query(default=5, ge=1, le=20, description="Number of chunks to return")
):
    """
    Get specific IRC section content.

    Example: /irc/199A returns QBI deduction content
    """
    try:
        search = get_search()
        results = search.get_irc_section(section, n_chunks=chunks)

        if results:
            return {
                "section": f"IRC §{section}",
                "chunks": [
                    {"text": r.text, "source": r.source}
                    for r in results
                ]
            }

        raise HTTPException(
            status_code=404,
            detail=f"IRC section {section} not found in knowledge base"
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise
        logger.error(f"IRC lookup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DOMAIN-SPECIFIC ENDPOINTS
# ============================================================================

@app.post("/personal", tags=["Domains"])
async def personal_tax_query(request: TaxQuery):
    """Search personal tax knowledge (1040, filing status, income)."""
    search = get_search()
    results = search.personal_tax(request.query, n_results=request.n_results)

    return {
        "query": request.query,
        "domain": "personal_tax",
        "results": [
            {"section": r.section, "text": r.text[:500], "source": r.source}
            for r in results
        ]
    }


@app.post("/business", tags=["Domains"])
async def business_tax_query(request: TaxQuery):
    """Search business tax knowledge (S-Corp, C-Corp, LLC, Partnership)."""
    search = get_search()
    results = search.business_tax(request.query, n_results=request.n_results)

    return {
        "query": request.query,
        "domain": "business_tax",
        "results": [
            {"section": r.section, "text": r.text[:500], "source": r.source}
            for r in results
        ]
    }


@app.post("/oilfield", tags=["Domains"])
async def oilfield_query(request: TaxQuery):
    """Search oilfield/energy tax knowledge (IDC, depletion, working interest)."""
    search = get_search()
    results = search.oilfield(request.query, n_results=request.n_results)

    return {
        "query": request.query,
        "domain": "oilfield",
        "results": [
            {"section": r.section, "text": r.text[:500], "source": r.source}
            for r in results
        ]
    }


@app.post("/deductions", tags=["Domains"])
async def deductions_query(request: TaxQuery):
    """Search deductions knowledge (itemized, above-the-line, business)."""
    search = get_search()
    results = search.deductions(request.query, n_results=request.n_results)

    return {
        "query": request.query,
        "domain": "deductions",
        "results": [
            {"section": r.section, "text": r.text[:500], "source": r.source}
            for r in results
        ]
    }


@app.post("/credits", tags=["Domains"])
async def credits_query(request: TaxQuery):
    """Search tax credits knowledge (CTC, EITC, education, energy)."""
    search = get_search()
    results = search.credits(request.query, n_results=request.n_results)

    return {
        "query": request.query,
        "domain": "credits",
        "results": [
            {"section": r.section, "text": r.text[:500], "source": r.source}
            for r in results
        ]
    }


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting ECHO Tax Expert Service on port 8390...")

    uvicorn.run(
        "tax_expert_service:app",
        host="0.0.0.0",
        port=8390,
        reload=False,
        log_level="info"
    )
