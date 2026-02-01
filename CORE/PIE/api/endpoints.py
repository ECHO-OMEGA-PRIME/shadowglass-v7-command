"""
PROGRAMMING INTELLIGENCE ENGINE - API Endpoints

Required endpoints:
/engineering/query
/engineering/version-check
/engineering/migration-path
/engineering/conflict-resolution
/engineering/deprecation-alert
/engineering/authority-report

Engineers must be able to interrogate decisions.

System Class: ISOLATED_REASONING_ENGINE
Governance Tier: ZERO
"""

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware

from .dependencies import require_ingest_auth
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import uuid
from loguru import logger

# Create FastAPI app
app = FastAPI(
    title="Programming Intelligence Engine",
    description="Tier ZERO Isolated Reasoning Engine for Engineering Decisions",
    version="1.0.0",
    docs_url="/engineering/docs",
    redoc_url="/engineering/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# --- Request/Response Models ---

class EngineeringQueryRequest(BaseModel):
    """Query request for engineering decisions."""
    query: str = Field(..., description="Engineering question or topic")
    target_version: Optional[str] = Field(None, description="Target version for compatibility check")
    category: Optional[str] = Field(None, description="Filter by category (API, SECURITY, etc.)")
    authority_minimum: Optional[int] = Field(None, ge=0, le=100, description="Minimum authority weight")
    include_deprecated: bool = Field(False, description="Include deprecated doctrines")


class VersionCheckRequest(BaseModel):
    """Request for version compatibility check."""
    doctrine_id: str = Field(..., description="Doctrine to check")
    target_version: str = Field(..., description="Target version")


class MigrationPathRequest(BaseModel):
    """Request for migration path analysis."""
    from_version: str = Field(..., description="Current version")
    to_version: str = Field(..., description="Target version")
    scope: Optional[str] = Field(None, description="Scope filter (e.g., 'python', 'react')")


class ConflictResolutionRequest(BaseModel):
    """Request for conflict resolution."""
    doctrine_ids: List[str] = Field(..., description="Conflicting doctrine IDs")


class IngestionRequest(BaseModel):
    """Request for document ingestion."""
    source_path: str = Field(..., description="Path to ingest")
    vendor: Optional[str] = Field(None, description="Vendor override")
    category: Optional[str] = Field(None, description="Category override")
    tags: List[str] = Field(default_factory=list, description="Additional tags")
    recursive: bool = Field(True, description="Recursive scan")


class DoctrineResponse(BaseModel):
    """Response containing doctrine information."""
    doctrine_id: str
    title: str
    category: Optional[str]
    authority_weight: int
    confidence_tier: str
    determinism_hash: str
    version_status: Optional[str]
    replacement_path: Optional[str]


class QueryResponse(BaseModel):
    """Response for engineering query."""
    query_id: str
    query: str
    doctrines: List[DoctrineResponse]
    reasoning_chain: List[str]
    recommendation: str
    confidence: str
    authority_report: Dict[str, Any]
    version_warnings: List[str]
    determinism_hash: str
    processed_at: str


class VersionCheckResponse(BaseModel):
    """Response for version check."""
    doctrine_id: str
    target_version: str
    compatible: bool
    optimal: bool
    status: str
    message: str
    warnings: List[str]
    migration_path: Optional[str]
    confidence: float


class MigrationPathResponse(BaseModel):
    """Response for migration path."""
    from_version: str
    to_version: str
    total_affected: int
    removals: List[Dict[str, Any]]
    deprecations: List[Dict[str, Any]]
    breaking_changes: List[Dict[str, Any]]
    migrations_required: List[Dict[str, Any]]
    recommendation: str


class AlertResponse(BaseModel):
    """Response for deprecation alerts."""
    alert_id: str
    type: str
    severity: str
    description: str
    affected_doctrines: List[str]
    migration_path: Optional[str]
    detected_at: str
    auto_remediated: bool


class AuthorityReportResponse(BaseModel):
    """Response for authority report."""
    doctrine_id: str
    title: str
    determinism_hash: str
    authority_weight: int
    confidence_tier: str
    controlling_source: Dict[str, Any]
    version_status: str
    defensibility: str


class StatusResponse(BaseModel):
    """System status response."""
    system: str
    status: str
    governance_tier: str
    doctrines_count: int
    graph_nodes: int
    active_alerts: int
    cache_entries: int
    isolation_protocol: str


# --- Global Engine Instance ---
# Will be initialized on startup
engine = None
authority_engine = None
version_engine = None
graph = None
doctrine_engine = None
drift_sentinel = None
ingestion_pipeline = None


def get_engines():
    """Get or initialize engines."""
    global engine, authority_engine, version_engine, graph, doctrine_engine, drift_sentinel, ingestion_pipeline

    if doctrine_engine is None:
        from ..layers.authority_hierarchy import AuthorityHierarchyEngine
        from ..layers.version_awareness import VersionAwarenessEngine
        from ..layers.semantic_graph import SemanticEngineeringGraph
        from ..layers.deterministic_doctrine import DeterministicDoctrineEngine
        from ..sentinel.drift_sentinel import DriftSentinel
        from ..ingestion.pipeline import IngestionPipeline

        authority_engine = AuthorityHierarchyEngine()
        version_engine = VersionAwarenessEngine()
        graph = SemanticEngineeringGraph()
        doctrine_engine = DeterministicDoctrineEngine(
            authority_engine, version_engine, graph
        )
        drift_sentinel = DriftSentinel(version_engine)
        ingestion_pipeline = IngestionPipeline(
            authority_engine, version_engine, graph
        )

        logger.info("PIE engines initialized")

    return doctrine_engine, version_engine, graph, drift_sentinel, ingestion_pipeline


# --- Endpoints ---

@app.get("/", include_in_schema=False)
async def root():
    """Root redirect to docs."""
    return {"message": "Programming Intelligence Engine", "docs": "/engineering/docs"}


@app.get("/engineering/status", response_model=StatusResponse)
async def get_status():
    """Get PIE system status."""
    doctrine_eng, version_eng, graph, sentinel, pipeline = get_engines()

    stats = doctrine_eng.get_statistics()
    graph_stats = graph.get_statistics()
    sentinel_status = sentinel.get_status()

    return StatusResponse(
        system="Programming Intelligence Engine",
        status="OPERATIONAL",
        governance_tier="ZERO",
        doctrines_count=stats["total_doctrines"],
        graph_nodes=graph_stats["total_nodes"],
        active_alerts=sentinel_status["active_alerts"],
        cache_entries=stats["cached_queries"],
        isolation_protocol="ACTIVE - No OMNISCIENT interference during cognition"
    )


@app.post("/engineering/query", response_model=QueryResponse)
async def query_engineering(request: EngineeringQueryRequest):
    """
    Query the engineering doctrine engine.

    DETERMINISM GUARANTEE: Identical query → identical result.
    """
    doctrine_eng, version_eng, graph, sentinel, pipeline = get_engines()

    from ..layers.deterministic_doctrine import DoctrineQuery

    query = DoctrineQuery(
        query_id=str(uuid.uuid4()),
        query_text=request.query,
        target_version=request.target_version,
        category_filter=request.category,
        authority_minimum=request.authority_minimum,
        include_deprecated=request.include_deprecated
    )

    result = doctrine_eng.query(query)

    return QueryResponse(
        query_id=result.query_id,
        query=result.query_text,
        doctrines=[
            DoctrineResponse(
                doctrine_id=d.doctrine_id,
                title=d.title,
                category=d.category,
                authority_weight=d.authority_weight,
                confidence_tier=d.confidence_tier.value,
                determinism_hash=d.determinism_hash or "",
                version_status=d.version_metadata.status.value if d.version_metadata else None,
                replacement_path=d.version_metadata.replacement_path if d.version_metadata else None
            )
            for d in result.doctrines
        ],
        reasoning_chain=result.reasoning_chain,
        recommendation=result.final_recommendation,
        confidence=result.confidence.value,
        authority_report=result.authority_report,
        version_warnings=result.version_warnings,
        determinism_hash=result.determinism_hash,
        processed_at=result.processed_at.isoformat()
    )


@app.post("/engineering/version-check", response_model=VersionCheckResponse)
async def check_version(request: VersionCheckRequest):
    """
    Check version compatibility for a doctrine.

    Never hallucinate compatibility. Flag uncertainty.
    """
    doctrine_eng, version_eng, graph, sentinel, pipeline = get_engines()

    doctrine = doctrine_eng.doctrines.get(request.doctrine_id)
    if not doctrine:
        raise HTTPException(status_code=404, detail=f"Doctrine not found: {request.doctrine_id}")

    result = version_eng.check_version_compatibility(doctrine, request.target_version)

    return VersionCheckResponse(
        doctrine_id=request.doctrine_id,
        target_version=request.target_version,
        compatible=result.is_compatible,
        optimal=result.is_optimal,
        status=result.status.value,
        message=result.message,
        warnings=result.warnings,
        migration_path=result.migration_path,
        confidence=result.confidence
    )


@app.post("/engineering/migration-path", response_model=MigrationPathResponse)
async def get_migration_path(request: MigrationPathRequest):
    """
    Get migration path between versions.

    Lists all breaking changes, deprecations, and required migrations.
    """
    doctrine_eng, version_eng, graph, sentinel, pipeline = get_engines()

    # Get affected doctrines
    affected = list(doctrine_eng.doctrines.values())

    # Filter by scope if provided
    if request.scope:
        affected = [
            d for d in affected
            if request.scope.lower() in d.title.lower() or
               request.scope.lower() in (d.category or "").lower()
        ]

    advisory = version_eng.create_migration_advisory(
        request.from_version,
        request.to_version,
        affected
    )

    migration = advisory.get("migration_advisory", {})

    return MigrationPathResponse(
        from_version=request.from_version,
        to_version=request.to_version,
        total_affected=migration.get("summary", {}).get("total_affected", 0),
        removals=migration.get("removals", []),
        deprecations=migration.get("deprecations", []),
        breaking_changes=migration.get("breaking_changes", []),
        migrations_required=migration.get("migrations_required", []),
        recommendation=migration.get("recommendation", "No analysis available")
    )


@app.post("/engineering/conflict-resolution")
async def resolve_conflict(request: ConflictResolutionRequest):
    """
    Resolve conflict between multiple doctrines.

    RULE: Higher authority ALWAYS wins.
    """
    doctrine_eng, version_eng, graph, sentinel, pipeline = get_engines()

    doctrines = []
    for doc_id in request.doctrine_ids:
        doc = doctrine_eng.doctrines.get(doc_id)
        if doc:
            doctrines.append(doc)

    if len(doctrines) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 valid doctrine IDs required for conflict resolution"
        )

    winner, report = doctrine_eng.authority.resolve_conflict(doctrines)

    return {
        "resolution": "HIGHER_AUTHORITY_WINS",
        "winner": {
            "doctrine_id": winner.doctrine_id,
            "title": winner.title,
            "authority_weight": winner.authority_weight
        },
        "conflict_report": report,
        "reasoning": f"Doctrine '{winner.title}' wins with authority weight {winner.authority_weight}"
    }


@app.get("/engineering/deprecation-alert", response_model=List[AlertResponse])
async def get_deprecation_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(50, ge=1, le=500)
):
    """
    Get active deprecation and drift alerts.
    """
    doctrine_eng, version_eng, graph, sentinel, pipeline = get_engines()

    alerts = sentinel.get_active_alerts()

    if severity:
        alerts = [a for a in alerts if a.severity == severity.upper()]

    return [
        AlertResponse(
            alert_id=a.alert_id,
            type=a.drift_type.value,
            severity=a.severity,
            description=a.description,
            affected_doctrines=a.affected_doctrines,
            migration_path=a.migration_path,
            detected_at=a.detected_at.isoformat(),
            auto_remediated=a.auto_remediated
        )
        for a in alerts[:limit]
    ]


@app.get("/engineering/authority-report/{doctrine_id}", response_model=AuthorityReportResponse)
async def get_authority_report(doctrine_id: str):
    """
    Get detailed authority report for a doctrine.

    Engineers can interrogate decisions with this endpoint.
    """
    doctrine_eng, version_eng, graph, sentinel, pipeline = get_engines()

    report = doctrine_eng.get_decision_report(doctrine_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Doctrine not found: {doctrine_id}")

    return AuthorityReportResponse(
        doctrine_id=report["doctrine_id"],
        title=report["title"],
        determinism_hash=report["determinism_hash"] or "",
        authority_weight=report["authority_weight"],
        confidence_tier=report["confidence_tier"],
        controlling_source=report["controlling_source"],
        version_status=report["version_status"],
        defensibility=report["defensibility"]
    )


@app.get("/engineering/graph/reason")
async def reason_with_graph(
    query: str = Query(..., description="Engineering question"),
    context: Optional[List[str]] = Query(None, description="Context node IDs")
):
    """
    Use the semantic graph for reasoning about engineering relationships.
    """
    doctrine_eng, version_eng, graph, sentinel, pipeline = get_engines()

    result = graph.reason_about(query, context)

    return result


@app.get("/engineering/graph/impact/{node_id}")
async def analyze_impact(
    node_id: str,
    change_type: str = Query("DEPRECATION", description="Type of change")
):
    """
    Analyze impact of a change to a graph node.
    """
    doctrine_eng, version_eng, graph, sentinel, pipeline = get_engines()

    result = graph.analyze_impact(node_id, change_type)
    return result


@app.post("/engineering/ingest")
async def ingest_documents(
    request: IngestionRequest,
    background_tasks: BackgroundTasks,
    auth: dict = Depends(require_ingest_auth)
):
    """
    Ingest documents into the PIE.

    REQUIRES: TIER_80+ authority (authentication enforced before handler)

    Parse → Classify → Authority Score → Version Tag → Graph Link → Doctrine Create
    """
    # Auth dependency already validated - auth contains actor_id and authority_tier
    logger.info(f"INGEST: actor={auth['actor_id']}, tier={auth['authority_tier']}")
    doctrine_eng, version_eng, graph, sentinel, pipeline = get_engines()

    from ..ingestion.pipeline import IngestionConfig

    config = IngestionConfig(
        source_path=Path(request.source_path),
        vendor=request.vendor,
        category=request.category,
        tags=request.tags,
        recursive=request.recursive
    )

    if not config.source_path.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {request.source_path}")

    # Run ingestion
    doctrines = pipeline.ingest(config)

    # Register doctrines
    for doctrine in doctrines:
        doctrine_eng.register_doctrine(doctrine)

    return {
        "status": "INGESTION_COMPLETE",
        "source": request.source_path,
        "doctrines_created": len(doctrines),
        "statistics": pipeline.get_statistics()
    }


@app.get("/engineering/statistics")
async def get_statistics():
    """Get comprehensive PIE statistics."""
    doctrine_eng, version_eng, graph, sentinel, pipeline = get_engines()

    return {
        "doctrine_engine": doctrine_eng.get_statistics(),
        "semantic_graph": graph.get_statistics(),
        "drift_sentinel": sentinel.get_status(),
        "ingestion_pipeline": pipeline.get_statistics()
    }


@app.post("/engineering/verify-determinism")
async def verify_determinism(
    query: str = Query(...),
    expected_hash: str = Query(...)
):
    """
    Verify that a query produces the expected deterministic result.
    """
    doctrine_eng, version_eng, graph, sentinel, pipeline = get_engines()

    from ..layers.deterministic_doctrine import DoctrineQuery

    query_obj = DoctrineQuery(
        query_id=str(uuid.uuid4()),
        query_text=query
    )

    verified, message = doctrine_eng.verify_determinism(query_obj, expected_hash)

    return {
        "verified": verified,
        "message": message,
        "query": query,
        "expected_hash": expected_hash
    }


# --- Startup/Shutdown ---

@app.on_event("startup")
async def startup():
    """Initialize engines on startup."""
    logger.info("Programming Intelligence Engine starting...")
    get_engines()
    logger.info("PIE operational - REASONING_ISOLATION_PROTOCOL: ACTIVE")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    if drift_sentinel:
        drift_sentinel.stop_monitoring()
    logger.info("PIE shutdown complete")
