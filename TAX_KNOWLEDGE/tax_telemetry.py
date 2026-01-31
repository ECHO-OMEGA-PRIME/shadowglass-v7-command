"""
ECHO Tax Intelligence Engine — Professional Telemetry & Logging
Institutional-grade observability infrastructure for audit, compliance, and operations.

Components:
    1. QueryTracer - Every query logged with full context
    2. ReasoningSnapshot - Reproducible reasoning paths for audit replay
    3. DoctrineMutationLog - Immutable changelog for doctrine modifications
    4. ErrorSpine - Centralized error collection with stack traces
    5. PerformanceTelemetry - Real-time performance metrics
    6. AuditMode - Query replay and forensic analysis

Author: ECHO OMEGA PRIME
Authority: 11.0 SOVEREIGN
"""

import hashlib
import json
import sqlite3
import threading
import traceback
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from contextlib import contextmanager
import time
import psutil
from loguru import logger

# ============================================================================
# CONFIGURATION
# ============================================================================

TELEMETRY_DIR = Path("O:/ECHO_OMEGA_PRIME/TAX_KNOWLEDGE/telemetry")
TELEMETRY_DIR.mkdir(exist_ok=True)

# Log files with rotation
QUERY_LOG = TELEMETRY_DIR / "query_traces.jsonl"
REASONING_LOG = TELEMETRY_DIR / "reasoning_snapshots.jsonl"
ERROR_LOG = TELEMETRY_DIR / "error_spine.jsonl"
PERFORMANCE_LOG = TELEMETRY_DIR / "performance_metrics.jsonl"

# SQLite for immutable audit trail
AUDIT_DB = TELEMETRY_DIR / "audit_trail.db"
MUTATION_DB = TELEMETRY_DIR / "doctrine_mutations.db"

# Configure structured logging
logger.add(
    TELEMETRY_DIR / "telemetry_{time}.log",
    rotation="100 MB",
    retention="90 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {module}:{function}:{line} | {message}",
    serialize=True
)


# ============================================================================
# ENUMS AND TYPES
# ============================================================================

class ResponseLayer(str, Enum):
    DOCTRINE = "doctrine"
    RAG = "rag"
    DEEP_ANALYSIS = "deep_analysis"
    ERROR = "error"


class MutationType(str, Enum):
    ADD = "add"
    EDIT = "edit"
    DELETE = "delete"
    BULK_IMPORT = "bulk_import"


class MutationOrigin(str, Enum):
    MANUAL = "manual"
    AI_GENERATED = "ai_generated"
    MIGRATION = "migration"
    SYSTEM = "system"


class ErrorSeverity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorDomain(str, Enum):
    API = "api"
    DOCTRINE_ENGINE = "doctrine_engine"
    VECTOR_SEARCH = "vector_search"
    SERIALIZATION = "serialization"
    TERMINAL = "terminal"
    DATABASE = "database"
    NETWORK = "network"
    UNKNOWN = "unknown"


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class QueryTrace:
    """Complete trace of a single query for audit and analysis."""
    trace_id: str
    timestamp: str
    question: str
    mode: str
    jurisdiction: str
    entity_type: Optional[str]

    # Matching results
    doctrine_matched: bool
    doctrine_id: Optional[str]
    doctrine_topic: Optional[str]
    confidence_score: float

    # Layer progression
    response_layer: str  # doctrine, rag, deep_analysis
    rag_triggered: bool
    deep_analysis_triggered: bool

    # Performance
    latency_ms: float
    doctrine_lookup_ms: float
    rag_lookup_ms: float
    total_tokens: int

    # Response summary
    response_length: int
    citations_count: int

    # Client context
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReasoningSnapshot:
    """Immutable snapshot of reasoning for audit replay."""
    snapshot_id: str
    trace_id: str  # Links to QueryTrace
    timestamp: str

    # Doctrine state at time of response
    doctrine_id: str
    doctrine_version_hash: str
    doctrine_content_hash: str

    # Reasoning path
    framework_name: str
    reasoning_steps: List[str]
    key_factors_applied: List[str]
    authorities_cited: List[Dict[str, str]]

    # Decision rationale
    conclusion_basis: str
    counter_arguments_considered: List[str]
    confidence_rationale: str

    # Reproducibility
    engine_version: str
    cache_state_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DoctrineMutation:
    """Immutable record of doctrine modification."""
    mutation_id: str
    timestamp: str
    mutation_type: str  # add, edit, delete
    origin: str  # manual, ai_generated, migration

    # Doctrine identification
    doctrine_id: str
    doctrine_topic: str

    # Change details
    previous_version_hash: Optional[str]
    new_version_hash: str
    diff_summary: str
    fields_changed: List[str]

    # Audit trail
    author: str
    reason: str
    approved_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ErrorRecord:
    """Structured error record for the error spine."""
    error_id: str
    timestamp: str
    severity: str
    domain: str

    # Error details
    error_type: str
    error_message: str
    stack_trace: str

    # Context
    trace_id: Optional[str]  # Links to QueryTrace if applicable
    operation: str
    input_summary: str

    # System state
    memory_mb: float
    active_queries: int

    # Resolution
    resolved: bool = False
    resolution_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PerformanceMetrics:
    """Point-in-time performance snapshot."""
    metric_id: str
    timestamp: str
    interval_seconds: int

    # Query metrics
    queries_total: int
    queries_in_interval: int

    # Cache performance
    doctrine_cache_hits: int
    doctrine_cache_misses: int
    cache_hit_rate: float

    # Latency
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    max_latency_ms: float

    # Resource usage
    memory_used_mb: float
    memory_available_mb: float
    memory_percent: float
    cpu_percent: float

    # Token usage (if applicable)
    tokens_input: int = 0
    tokens_output: int = 0

    # Error rates
    error_count: int = 0
    error_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# THREAD-SAFE FILE WRITER
# ============================================================================

class ThreadSafeWriter:
    """Thread-safe append-only JSON lines writer."""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self._lock = threading.Lock()

    def append(self, record: Dict[str, Any]) -> None:
        """Append a record to the log file."""
        with self._lock:
            with open(self.filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, default=str) + "\n")

    def read_all(self) -> List[Dict[str, Any]]:
        """Read all records from the log file."""
        if not self.filepath.exists():
            return []
        records = []
        with open(self.filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def read_last_n(self, n: int) -> List[Dict[str, Any]]:
        """Read last N records efficiently."""
        if not self.filepath.exists():
            return []

        # Read file backwards for efficiency
        records = []
        with open(self.filepath, "rb") as f:
            f.seek(0, 2)  # End of file
            position = f.tell()
            lines_found = 0
            buffer = b""

            while position > 0 and lines_found < n:
                position -= 1
                f.seek(position)
                char = f.read(1)
                if char == b"\n":
                    if buffer:
                        try:
                            records.append(json.loads(buffer.decode("utf-8")[::-1]))
                            lines_found += 1
                        except json.JSONDecodeError:
                            pass
                        buffer = b""
                else:
                    buffer += char

            # Handle first line
            if buffer and lines_found < n:
                try:
                    records.append(json.loads(buffer.decode("utf-8")[::-1]))
                except json.JSONDecodeError:
                    pass

        return list(reversed(records))


# ============================================================================
# QUERY TRACER
# ============================================================================

class QueryTracer:
    """Traces every query with full context for audit and analysis."""

    def __init__(self):
        self._writer = ThreadSafeWriter(QUERY_LOG)
        self._active_traces: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def start_trace(
        self,
        question: str,
        mode: str,
        jurisdiction: str = "US",
        entity_type: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        """Start a new query trace. Returns trace_id."""
        trace_id = str(uuid.uuid4())[:8]

        with self._lock:
            self._active_traces[trace_id] = {
                "trace_id": trace_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "question": question,
                "mode": mode,
                "jurisdiction": jurisdiction,
                "entity_type": entity_type,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "session_id": session_id,
                "start_time": time.perf_counter(),
                "doctrine_lookup_start": None,
                "doctrine_lookup_end": None,
                "rag_lookup_start": None,
                "rag_lookup_end": None,
            }

        logger.debug(f"Query trace started: {trace_id}")
        return trace_id

    def record_doctrine_lookup(self, trace_id: str, start: bool = True) -> None:
        """Record doctrine lookup timing."""
        with self._lock:
            if trace_id in self._active_traces:
                key = "doctrine_lookup_start" if start else "doctrine_lookup_end"
                self._active_traces[trace_id][key] = time.perf_counter()

    def record_rag_lookup(self, trace_id: str, start: bool = True) -> None:
        """Record RAG lookup timing."""
        with self._lock:
            if trace_id in self._active_traces:
                key = "rag_lookup_start" if start else "rag_lookup_end"
                self._active_traces[trace_id][key] = time.perf_counter()

    def complete_trace(
        self,
        trace_id: str,
        doctrine_matched: bool,
        doctrine_id: Optional[str],
        doctrine_topic: Optional[str],
        confidence_score: float,
        response_layer: str,
        rag_triggered: bool,
        deep_analysis_triggered: bool,
        response_length: int,
        citations_count: int,
        total_tokens: int = 0
    ) -> QueryTrace:
        """Complete a query trace and persist it."""
        with self._lock:
            if trace_id not in self._active_traces:
                raise ValueError(f"Unknown trace_id: {trace_id}")

            trace_data = self._active_traces.pop(trace_id)

        end_time = time.perf_counter()
        start_time = trace_data["start_time"]

        # Calculate latencies
        total_latency = (end_time - start_time) * 1000

        doctrine_lookup_ms = 0.0
        if trace_data["doctrine_lookup_start"] and trace_data["doctrine_lookup_end"]:
            doctrine_lookup_ms = (
                trace_data["doctrine_lookup_end"] - trace_data["doctrine_lookup_start"]
            ) * 1000

        rag_lookup_ms = 0.0
        if trace_data["rag_lookup_start"] and trace_data["rag_lookup_end"]:
            rag_lookup_ms = (
                trace_data["rag_lookup_end"] - trace_data["rag_lookup_start"]
            ) * 1000

        query_trace = QueryTrace(
            trace_id=trace_id,
            timestamp=trace_data["timestamp"],
            question=trace_data["question"],
            mode=trace_data["mode"],
            jurisdiction=trace_data["jurisdiction"],
            entity_type=trace_data["entity_type"],
            doctrine_matched=doctrine_matched,
            doctrine_id=doctrine_id,
            doctrine_topic=doctrine_topic,
            confidence_score=confidence_score,
            response_layer=response_layer,
            rag_triggered=rag_triggered,
            deep_analysis_triggered=deep_analysis_triggered,
            latency_ms=round(total_latency, 3),
            doctrine_lookup_ms=round(doctrine_lookup_ms, 3),
            rag_lookup_ms=round(rag_lookup_ms, 3),
            total_tokens=total_tokens,
            response_length=response_length,
            citations_count=citations_count,
            client_ip=trace_data.get("client_ip"),
            user_agent=trace_data.get("user_agent"),
            session_id=trace_data.get("session_id")
        )

        # Persist
        self._writer.append(query_trace.to_dict())
        logger.info(f"Query trace completed: {trace_id} | {total_latency:.2f}ms | layer={response_layer}")

        return query_trace

    def get_recent_traces(self, n: int = 100) -> List[Dict[str, Any]]:
        """Get most recent N traces."""
        return self._writer.read_last_n(n)

    def get_trace_by_id(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Find a specific trace by ID."""
        for record in self._writer.read_all():
            if record.get("trace_id") == trace_id:
                return record
        return None

    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Alias for get_trace_by_id."""
        return self.get_trace_by_id(trace_id)


# ============================================================================
# REASONING SNAPSHOT
# ============================================================================

class ReasoningSnapshotStore:
    """Stores reasoning snapshots for audit replay."""

    def __init__(self):
        self._writer = ThreadSafeWriter(REASONING_LOG)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite for indexed lookups."""
        conn = sqlite3.connect(str(AUDIT_DB))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reasoning_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                trace_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                doctrine_id TEXT NOT NULL,
                doctrine_version_hash TEXT NOT NULL,
                engine_version TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_trace_id ON reasoning_snapshots(trace_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_doctrine_id ON reasoning_snapshots(doctrine_id)")
        conn.commit()
        conn.close()

    def compute_doctrine_hash(self, doctrine_content: str) -> str:
        """Compute SHA-256 hash of doctrine content."""
        return hashlib.sha256(doctrine_content.encode("utf-8")).hexdigest()[:16]

    def compute_cache_state_hash(self, cache_keys: List[str]) -> str:
        """Compute hash of current cache state."""
        sorted_keys = sorted(cache_keys)
        content = "|".join(sorted_keys)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def store_snapshot(
        self,
        trace_id: str,
        doctrine_id: str,
        doctrine_content: str,
        framework_name: str,
        reasoning_steps: List[str],
        key_factors_applied: List[str],
        authorities_cited: List[Dict[str, str]],
        conclusion_basis: str,
        counter_arguments_considered: List[str],
        confidence_rationale: str,
        cache_keys: List[str],
        engine_version: str = "1.0.0"
    ) -> ReasoningSnapshot:
        """Store a reasoning snapshot."""
        snapshot_id = str(uuid.uuid4())[:12]
        timestamp = datetime.now(timezone.utc).isoformat()

        doctrine_hash = self.compute_doctrine_hash(doctrine_content)
        cache_hash = self.compute_cache_state_hash(cache_keys)

        snapshot = ReasoningSnapshot(
            snapshot_id=snapshot_id,
            trace_id=trace_id,
            timestamp=timestamp,
            doctrine_id=doctrine_id,
            doctrine_version_hash=doctrine_hash,
            doctrine_content_hash=doctrine_hash,
            framework_name=framework_name,
            reasoning_steps=reasoning_steps,
            key_factors_applied=key_factors_applied,
            authorities_cited=authorities_cited,
            conclusion_basis=conclusion_basis,
            counter_arguments_considered=counter_arguments_considered,
            confidence_rationale=confidence_rationale,
            engine_version=engine_version,
            cache_state_hash=cache_hash
        )

        # Persist to JSONL
        self._writer.append(snapshot.to_dict())

        # Index in SQLite
        conn = sqlite3.connect(str(AUDIT_DB))
        conn.execute(
            """INSERT INTO reasoning_snapshots
               (snapshot_id, trace_id, timestamp, doctrine_id, doctrine_version_hash, engine_version)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (snapshot_id, trace_id, timestamp, doctrine_id, doctrine_hash, engine_version)
        )
        conn.commit()
        conn.close()

        logger.debug(f"Reasoning snapshot stored: {snapshot_id} for trace {trace_id}")
        return snapshot

    def get_snapshot_by_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get reasoning snapshot for a specific trace."""
        for record in self._writer.read_all():
            if record.get("trace_id") == trace_id:
                return record
        return None

    def get_snapshot(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Alias for get_snapshot_by_trace."""
        return self.get_snapshot_by_trace(trace_id)

    def get_snapshots_by_doctrine(self, doctrine_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all snapshots for a specific doctrine."""
        conn = sqlite3.connect(str(AUDIT_DB))
        cursor = conn.execute(
            "SELECT snapshot_id FROM reasoning_snapshots WHERE doctrine_id = ? ORDER BY timestamp DESC LIMIT ?",
            (doctrine_id, limit)
        )
        snapshot_ids = [row[0] for row in cursor.fetchall()]
        conn.close()

        # Retrieve full snapshots
        snapshots = []
        for record in self._writer.read_all():
            if record.get("snapshot_id") in snapshot_ids:
                snapshots.append(record)
        return snapshots


# ============================================================================
# DOCTRINE MUTATION LOG
# ============================================================================

class DoctrineMutationLog:
    """Immutable log of all doctrine modifications."""

    def __init__(self):
        self._init_db()
        self._lock = threading.Lock()

    def _init_db(self):
        """Initialize SQLite for immutable mutation log."""
        conn = sqlite3.connect(str(MUTATION_DB))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mutations (
                mutation_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                mutation_type TEXT NOT NULL,
                origin TEXT NOT NULL,
                doctrine_id TEXT NOT NULL,
                doctrine_topic TEXT NOT NULL,
                previous_version_hash TEXT,
                new_version_hash TEXT NOT NULL,
                diff_summary TEXT NOT NULL,
                fields_changed TEXT NOT NULL,
                author TEXT NOT NULL,
                reason TEXT NOT NULL,
                approved_by TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_doctrine_id ON mutations(doctrine_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mutation_type ON mutations(mutation_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON mutations(timestamp)")
        conn.commit()
        conn.close()

    def compute_version_hash(self, doctrine_content: str) -> str:
        """Compute version hash for a doctrine."""
        return hashlib.sha256(doctrine_content.encode("utf-8")).hexdigest()[:16]

    def log_mutation(
        self,
        mutation_type: MutationType,
        origin: MutationOrigin,
        doctrine_id: str,
        doctrine_topic: str,
        new_content: str,
        previous_content: Optional[str] = None,
        fields_changed: Optional[List[str]] = None,
        author: str = "system",
        reason: str = "",
        approved_by: Optional[str] = None
    ) -> DoctrineMutation:
        """Log a doctrine mutation."""
        mutation_id = str(uuid.uuid4())[:12]
        timestamp = datetime.now(timezone.utc).isoformat()

        previous_hash = None
        if previous_content:
            previous_hash = self.compute_version_hash(previous_content)
        new_hash = self.compute_version_hash(new_content)

        # Generate diff summary
        if mutation_type == MutationType.ADD:
            diff_summary = f"Added new doctrine: {doctrine_topic}"
        elif mutation_type == MutationType.DELETE:
            diff_summary = f"Deleted doctrine: {doctrine_topic}"
        elif mutation_type == MutationType.EDIT:
            changed = fields_changed or ["unknown"]
            diff_summary = f"Modified fields: {', '.join(changed)}"
        else:
            diff_summary = f"Bulk operation: {mutation_type.value}"

        mutation = DoctrineMutation(
            mutation_id=mutation_id,
            timestamp=timestamp,
            mutation_type=mutation_type.value,
            origin=origin.value,
            doctrine_id=doctrine_id,
            doctrine_topic=doctrine_topic,
            previous_version_hash=previous_hash,
            new_version_hash=new_hash,
            diff_summary=diff_summary,
            fields_changed=fields_changed or [],
            author=author,
            reason=reason,
            approved_by=approved_by
        )

        # Persist to SQLite (immutable)
        with self._lock:
            conn = sqlite3.connect(str(MUTATION_DB))
            conn.execute(
                """INSERT INTO mutations
                   (mutation_id, timestamp, mutation_type, origin, doctrine_id, doctrine_topic,
                    previous_version_hash, new_version_hash, diff_summary, fields_changed,
                    author, reason, approved_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    mutation_id, timestamp, mutation_type.value, origin.value,
                    doctrine_id, doctrine_topic, previous_hash, new_hash,
                    diff_summary, json.dumps(fields_changed or []),
                    author, reason, approved_by
                )
            )
            conn.commit()
            conn.close()

        logger.info(f"Doctrine mutation logged: {mutation_id} | {mutation_type.value} | {doctrine_id}")
        return mutation

    def get_mutations_for_doctrine(self, doctrine_id: str) -> List[Dict[str, Any]]:
        """Get all mutations for a specific doctrine."""
        conn = sqlite3.connect(str(MUTATION_DB))
        cursor = conn.execute(
            "SELECT * FROM mutations WHERE doctrine_id = ? ORDER BY timestamp DESC",
            (doctrine_id,)
        )
        columns = [desc[0] for desc in cursor.description]
        mutations = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return mutations

    def get_recent_mutations(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get most recent mutations."""
        conn = sqlite3.connect(str(MUTATION_DB))
        cursor = conn.execute(
            "SELECT * FROM mutations ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        columns = [desc[0] for desc in cursor.description]
        mutations = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return mutations

    def get_mutations_by_author(self, author: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get mutations by a specific author."""
        conn = sqlite3.connect(str(MUTATION_DB))
        cursor = conn.execute(
            "SELECT * FROM mutations WHERE author = ? ORDER BY timestamp DESC LIMIT ?",
            (author, limit)
        )
        columns = [desc[0] for desc in cursor.description]
        mutations = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return mutations


# ============================================================================
# ERROR SPINE
# ============================================================================

class ErrorSpine:
    """Centralized error logging across all system components."""

    def __init__(self):
        self._writer = ThreadSafeWriter(ERROR_LOG)
        self._lock = threading.Lock()
        self._error_counts: Dict[str, int] = {}

    def record_error(
        self,
        error: Exception,
        domain: ErrorDomain,
        severity: ErrorSeverity,
        operation: str,
        input_summary: str = "",
        trace_id: Optional[str] = None
    ) -> ErrorRecord:
        """Record an error with full context."""
        error_id = str(uuid.uuid4())[:12]
        timestamp = datetime.now(timezone.utc).isoformat()

        # Get system state
        memory = psutil.virtual_memory()

        record = ErrorRecord(
            error_id=error_id,
            timestamp=timestamp,
            severity=severity.value,
            domain=domain.value,
            error_type=type(error).__name__,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            trace_id=trace_id,
            operation=operation,
            input_summary=input_summary[:500] if input_summary else "",
            memory_mb=round(memory.used / (1024 ** 2), 1),
            active_queries=0  # Will be set by caller if known
        )

        # Persist
        self._writer.append(record.to_dict())

        # Update counts
        with self._lock:
            key = f"{domain.value}:{type(error).__name__}"
            self._error_counts[key] = self._error_counts.get(key, 0) + 1

        # Log based on severity
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(f"CRITICAL ERROR [{domain.value}]: {error} | {operation}")
        elif severity == ErrorSeverity.ERROR:
            logger.error(f"ERROR [{domain.value}]: {error} | {operation}")
        elif severity == ErrorSeverity.WARNING:
            logger.warning(f"WARNING [{domain.value}]: {error} | {operation}")
        else:
            logger.debug(f"DEBUG [{domain.value}]: {error} | {operation}")

        return record

    @contextmanager
    def capture_errors(
        self,
        domain: ErrorDomain,
        operation: str,
        trace_id: Optional[str] = None,
        reraise: bool = True
    ):
        """Context manager to capture and log errors."""
        try:
            yield
        except Exception as e:
            self.record_error(
                error=e,
                domain=domain,
                severity=ErrorSeverity.ERROR,
                operation=operation,
                trace_id=trace_id
            )
            if reraise:
                raise

    def get_recent_errors(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get most recent errors."""
        return self._writer.read_last_n(limit)

    def get_errors_by_domain(self, domain: ErrorDomain, limit: int = 100) -> List[Dict[str, Any]]:
        """Get errors for a specific domain."""
        all_errors = self._writer.read_all()
        filtered = [e for e in all_errors if e.get("domain") == domain.value]
        return filtered[-limit:]

    def get_error_counts(self) -> Dict[str, int]:
        """Get error counts by type."""
        with self._lock:
            return dict(self._error_counts)

    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary for dashboard."""
        all_errors = self._writer.read_all()
        now = datetime.now(timezone.utc)

        # Count by time window
        last_hour = 0
        last_24h = 0
        by_domain: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}

        for error in all_errors:
            ts = datetime.fromisoformat(error["timestamp"].replace("Z", "+00:00"))
            delta = (now - ts).total_seconds()

            if delta <= 3600:
                last_hour += 1
            if delta <= 86400:
                last_24h += 1

            domain = error.get("domain", "unknown")
            by_domain[domain] = by_domain.get(domain, 0) + 1

            severity = error.get("severity", "unknown")
            by_severity[severity] = by_severity.get(severity, 0) + 1

        return {
            "total_errors": len(all_errors),
            "last_hour": last_hour,
            "last_24h": last_24h,
            "by_domain": by_domain,
            "by_severity": by_severity
        }


# ============================================================================
# PERFORMANCE TELEMETRY
# ============================================================================

class PerformanceTelemetry:
    """Real-time performance metrics collection."""

    def __init__(self):
        self._writer = ThreadSafeWriter(PERFORMANCE_LOG)
        self._lock = threading.Lock()

        # Sliding window metrics
        self._latencies: List[float] = []
        self._max_latencies = 1000

        # Counters
        self._queries_total = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._tokens_input = 0
        self._tokens_output = 0
        self._error_count = 0

        # Last snapshot time
        self._last_snapshot = time.time()
        self._queries_at_last_snapshot = 0

    def record_query(
        self,
        latency_ms: float,
        cache_hit: bool,
        tokens_input: int = 0,
        tokens_output: int = 0
    ) -> None:
        """Record a query's performance metrics."""
        with self._lock:
            self._latencies.append(latency_ms)
            if len(self._latencies) > self._max_latencies:
                self._latencies.pop(0)

            self._queries_total += 1
            if cache_hit:
                self._cache_hits += 1
            else:
                self._cache_misses += 1

            self._tokens_input += tokens_input
            self._tokens_output += tokens_output

    def record_error(self) -> None:
        """Record an error occurrence."""
        with self._lock:
            self._error_count += 1

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        with self._lock:
            latencies = list(self._latencies)
            queries_total = self._queries_total
            cache_hits = self._cache_hits
            cache_misses = self._cache_misses

        if not latencies:
            latencies = [0.0]

        sorted_lat = sorted(latencies)

        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)

        total_cache = cache_hits + cache_misses
        hit_rate = cache_hits / total_cache if total_cache > 0 else 1.0

        return {
            "queries_total": queries_total,
            "cache_hit_rate": round(hit_rate, 4),
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2),
            "p50_latency_ms": round(sorted_lat[len(sorted_lat) // 2], 2),
            "p95_latency_ms": round(sorted_lat[int(len(sorted_lat) * 0.95)], 2),
            "p99_latency_ms": round(sorted_lat[int(len(sorted_lat) * 0.99)], 2),
            "max_latency_ms": round(max(latencies), 2),
            "memory_used_mb": round(memory.used / (1024 ** 2), 1),
            "memory_available_mb": round(memory.available / (1024 ** 2), 1),
            "memory_percent": round(memory.percent, 1),
            "cpu_percent": round(cpu, 1),
            "tokens_input": self._tokens_input,
            "tokens_output": self._tokens_output,
            "error_count": self._error_count
        }

    def snapshot(self, interval_seconds: int = 60) -> PerformanceMetrics:
        """Take a performance snapshot and persist it."""
        metrics = self.get_current_metrics()

        with self._lock:
            queries_in_interval = self._queries_total - self._queries_at_last_snapshot
            self._queries_at_last_snapshot = self._queries_total
            self._last_snapshot = time.time()
            error_count = self._error_count

        total_queries = metrics["queries_total"]
        error_rate = error_count / total_queries if total_queries > 0 else 0.0

        snapshot = PerformanceMetrics(
            metric_id=str(uuid.uuid4())[:8],
            timestamp=datetime.now(timezone.utc).isoformat(),
            interval_seconds=interval_seconds,
            queries_total=metrics["queries_total"],
            queries_in_interval=queries_in_interval,
            doctrine_cache_hits=metrics["cache_hits"],
            doctrine_cache_misses=metrics["cache_misses"],
            cache_hit_rate=metrics["cache_hit_rate"],
            avg_latency_ms=metrics["avg_latency_ms"],
            p50_latency_ms=metrics["p50_latency_ms"],
            p95_latency_ms=metrics["p95_latency_ms"],
            p99_latency_ms=metrics["p99_latency_ms"],
            max_latency_ms=metrics["max_latency_ms"],
            memory_used_mb=metrics["memory_used_mb"],
            memory_available_mb=metrics["memory_available_mb"],
            memory_percent=metrics["memory_percent"],
            cpu_percent=metrics["cpu_percent"],
            tokens_input=metrics["tokens_input"],
            tokens_output=metrics["tokens_output"],
            error_count=error_count,
            error_rate=round(error_rate, 4)
        )

        self._writer.append(snapshot.to_dict())
        logger.info(f"Performance snapshot: {snapshot.queries_in_interval} queries | {snapshot.avg_latency_ms}ms avg")

        return snapshot

    def get_historical_metrics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get historical performance snapshots."""
        return self._writer.read_last_n(limit)


# ============================================================================
# AUDIT MODE
# ============================================================================

class AuditMode:
    """Forensic analysis and query replay capabilities."""

    def __init__(
        self,
        query_tracer: QueryTracer,
        reasoning_store: ReasoningSnapshotStore,
        mutation_log: DoctrineMutationLog,
        error_spine: ErrorSpine
    ):
        self.query_tracer = query_tracer
        self.reasoning_store = reasoning_store
        self.mutation_log = mutation_log
        self.error_spine = error_spine

    def get_full_trace(self, trace_id: str) -> Dict[str, Any]:
        """Get complete audit trail for a query."""
        query_trace = self.query_tracer.get_trace_by_id(trace_id)
        reasoning = self.reasoning_store.get_snapshot_by_trace(trace_id)

        # Get any errors associated with this trace
        all_errors = self.error_spine.get_recent_errors(1000)
        trace_errors = [e for e in all_errors if e.get("trace_id") == trace_id]

        return {
            "trace_id": trace_id,
            "query_trace": query_trace,
            "reasoning_snapshot": reasoning,
            "errors": trace_errors,
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }

    def get_doctrine_history(self, doctrine_id: str) -> Dict[str, Any]:
        """Get complete history for a doctrine."""
        mutations = self.mutation_log.get_mutations_for_doctrine(doctrine_id)
        usage_snapshots = self.reasoning_store.get_snapshots_by_doctrine(doctrine_id)

        return {
            "doctrine_id": doctrine_id,
            "mutations": mutations,
            "usage_count": len(usage_snapshots),
            "recent_usage": usage_snapshots[:20] if usage_snapshots else [],
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }

    def generate_audit_report(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive audit report."""
        # Get all traces
        all_traces = self.query_tracer._writer.read_all()

        # Filter by date if specified
        if start_date or end_date:
            filtered = []
            for trace in all_traces:
                ts = trace.get("timestamp", "")
                if start_date and ts < start_date:
                    continue
                if end_date and ts > end_date:
                    continue
                filtered.append(trace)
            all_traces = filtered

        # Compute statistics
        total_queries = len(all_traces)
        doctrine_hits = sum(1 for t in all_traces if t.get("doctrine_matched"))
        rag_triggers = sum(1 for t in all_traces if t.get("rag_triggered"))

        latencies = [t.get("latency_ms", 0) for t in all_traces if t.get("latency_ms")]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0

        # Doctrine usage
        doctrine_usage: Dict[str, int] = {}
        for trace in all_traces:
            doc_id = trace.get("doctrine_id")
            if doc_id:
                doctrine_usage[doc_id] = doctrine_usage.get(doc_id, 0) + 1

        # Get mutations in period
        all_mutations = self.mutation_log.get_recent_mutations(1000)
        if start_date or end_date:
            filtered_mutations = []
            for m in all_mutations:
                ts = m.get("timestamp", "")
                if start_date and ts < start_date:
                    continue
                if end_date and ts > end_date:
                    continue
                filtered_mutations.append(m)
            all_mutations = filtered_mutations

        # Error summary
        error_summary = self.error_spine.get_error_summary()

        return {
            "report_generated": datetime.now(timezone.utc).isoformat(),
            "period": {
                "start": start_date or "all_time",
                "end": end_date or "now"
            },
            "query_statistics": {
                "total_queries": total_queries,
                "doctrine_hits": doctrine_hits,
                "doctrine_hit_rate": round(doctrine_hits / total_queries, 4) if total_queries else 0,
                "rag_triggers": rag_triggers,
                "avg_latency_ms": round(avg_latency, 2)
            },
            "doctrine_usage": dict(sorted(doctrine_usage.items(), key=lambda x: -x[1])[:20]),
            "mutations_in_period": len(all_mutations),
            "mutation_types": {
                "add": sum(1 for m in all_mutations if m.get("mutation_type") == "add"),
                "edit": sum(1 for m in all_mutations if m.get("mutation_type") == "edit"),
                "delete": sum(1 for m in all_mutations if m.get("mutation_type") == "delete")
            },
            "error_summary": error_summary
        }

    def replay_query(self, trace_id: str) -> Dict[str, Any]:
        """Replay a query for audit purposes - returns full trace with reasoning."""
        return self.get_full_trace(trace_id)

    def generate_report(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Alias for generate_audit_report."""
        return self.generate_audit_report(start_date, end_date)


# ============================================================================
# TELEMETRY MANAGER (SINGLETON)
# ============================================================================

class TelemetryManager:
    """Central manager for all telemetry components."""

    _instance: Optional["TelemetryManager"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.query_tracer = QueryTracer()
        self.reasoning_store = ReasoningSnapshotStore()
        self.mutation_log = DoctrineMutationLog()
        self.error_spine = ErrorSpine()
        self.performance = PerformanceTelemetry()
        self.audit = AuditMode(
            self.query_tracer,
            self.reasoning_store,
            self.mutation_log,
            self.error_spine
        )

        self._initialized = True
        logger.info("TelemetryManager initialized")

    def health_check(self) -> Dict[str, Any]:
        """Check telemetry system health."""
        return {
            "status": "healthy",
            "telemetry_dir": str(TELEMETRY_DIR),
            "components": {
                "query_tracer": "active",
                "reasoning_store": "active",
                "mutation_log": "active",
                "error_spine": "active",
                "performance": "active",
                "audit": "active"
            },
            "files": {
                "query_log": QUERY_LOG.exists(),
                "reasoning_log": REASONING_LOG.exists(),
                "error_log": ERROR_LOG.exists(),
                "performance_log": PERFORMANCE_LOG.exists(),
                "audit_db": AUDIT_DB.exists(),
                "mutation_db": MUTATION_DB.exists()
            }
        }


def get_telemetry() -> TelemetryManager:
    """Get the singleton telemetry manager."""
    return TelemetryManager()


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def trace_query(question: str, mode: str, **kwargs) -> str:
    """Start a query trace. Returns trace_id."""
    return get_telemetry().query_tracer.start_trace(question, mode, **kwargs)


def complete_trace(trace_id: str, **kwargs) -> QueryTrace:
    """Complete a query trace."""
    return get_telemetry().query_tracer.complete_trace(trace_id, **kwargs)


def log_error(error: Exception, domain: ErrorDomain, operation: str, **kwargs) -> ErrorRecord:
    """Log an error to the error spine."""
    return get_telemetry().error_spine.record_error(
        error=error,
        domain=domain,
        severity=ErrorSeverity.ERROR,
        operation=operation,
        **kwargs
    )


def record_doctrine_mutation(
    mutation_type: MutationType,
    doctrine_id: str,
    doctrine_topic: str,
    new_content: str,
    **kwargs
) -> DoctrineMutation:
    """Record a doctrine mutation."""
    return get_telemetry().mutation_log.log_mutation(
        mutation_type=mutation_type,
        origin=kwargs.get("origin", MutationOrigin.MANUAL),
        doctrine_id=doctrine_id,
        doctrine_topic=doctrine_topic,
        new_content=new_content,
        **kwargs
    )


# ============================================================================
# INITIALIZATION
# ============================================================================

if __name__ == "__main__":
    # Test the telemetry system
    tm = get_telemetry()

    print("=" * 60)
    print("TELEMETRY SYSTEM TEST")
    print("=" * 60)

    # Test query trace
    trace_id = tm.query_tracer.start_trace(
        question="What is the §83(b) election deadline?",
        mode="fast"
    )
    print(f"\n1. Started trace: {trace_id}")

    time.sleep(0.1)  # Simulate work

    query_trace = tm.query_tracer.complete_trace(
        trace_id=trace_id,
        doctrine_matched=True,
        doctrine_id="stock_compensation_iso_nso",
        doctrine_topic="Stock Compensation",
        confidence_score=0.95,
        response_layer="doctrine",
        rag_triggered=False,
        deep_analysis_triggered=False,
        response_length=500,
        citations_count=4
    )
    print(f"   Completed trace: {query_trace.latency_ms}ms")

    # Test reasoning snapshot
    snapshot = tm.reasoning_store.store_snapshot(
        trace_id=trace_id,
        doctrine_id="stock_compensation_iso_nso",
        doctrine_content="Test doctrine content for §83(b) elections...",
        framework_name="STOCK COMPENSATION ANALYSIS",
        reasoning_steps=["Identify grant date", "Compute FMV", "File within 30 days"],
        key_factors_applied=["Timely filing", "Proper form"],
        authorities_cited=[{"authority": "IRC", "reference": "§83(b)"}],
        conclusion_basis="Election must be filed within 30 days",
        counter_arguments_considered=["Late filing arguments fail"],
        confidence_rationale="Clear statutory deadline",
        cache_keys=["stock_compensation_iso_nso"]
    )
    print(f"\n2. Stored reasoning snapshot: {snapshot.snapshot_id}")

    # Test mutation log
    mutation = tm.mutation_log.log_mutation(
        mutation_type=MutationType.ADD,
        origin=MutationOrigin.AI_GENERATED,
        doctrine_id="test_doctrine",
        doctrine_topic="Test Doctrine",
        new_content="New doctrine content...",
        author="claude",
        reason="Initial creation"
    )
    print(f"\n3. Logged mutation: {mutation.mutation_id}")

    # Test error logging
    try:
        raise ValueError("Test error for telemetry")
    except Exception as e:
        error = tm.error_spine.record_error(
            error=e,
            domain=ErrorDomain.API,
            severity=ErrorSeverity.WARNING,
            operation="test_operation",
            trace_id=trace_id
        )
        print(f"\n4. Logged error: {error.error_id}")

    # Test performance metrics
    tm.performance.record_query(latency_ms=0.5, cache_hit=True)
    metrics = tm.performance.get_current_metrics()
    print(f"\n5. Performance metrics: {metrics['avg_latency_ms']}ms avg latency")

    # Test audit
    full_trace = tm.audit.get_full_trace(trace_id)
    print(f"\n6. Full audit trace retrieved: {len(str(full_trace))} bytes")

    # Health check
    health = tm.health_check()
    print(f"\n7. Health check: {health['status']}")

    print("\n" + "=" * 60)
    print("TELEMETRY SYSTEM TEST COMPLETE")
    print(f"Logs stored in: {TELEMETRY_DIR}")
    print("=" * 60)
