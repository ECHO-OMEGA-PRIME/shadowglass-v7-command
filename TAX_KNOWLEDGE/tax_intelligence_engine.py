"""
ECHO TAX INTELLIGENCE ENGINE — Production Architecture
Professional-grade tax doctrine system for CPAs, attorneys, and audit teams.

Architecture:
    Layer 1: Doctrine Cache (0-200ms) - Pre-compiled expert reasoning
    Layer 2: Semantic Retrieval (200-700ms) - Fast RAG on cache miss
    Layer 3: Deep Analysis (on-demand) - Multi-source synthesis

Response Modes:
    FAST: Doctrine-driven, minimal citations, sub-2 seconds
    DEFENSE: Structured reasoning, audit-ready, burden analysis
    MEMO: Long-form, citation-heavy, firm documentation

Author: ECHO OMEGA PRIME
Authority: 11.0 SOVEREIGN
Port: 8391
"""

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import hashlib
import time
import uuid
from pathlib import Path
from loguru import logger

# Telemetry integration
from tax_telemetry import (
    get_telemetry,
    trace_query,
    complete_trace,
    log_error,
    record_doctrine_mutation,
    ErrorDomain,
    ResponseLayer,
    MutationType,
    MutationOrigin
)

# Configure production logging
LOG_DIR = Path("O:/ECHO_OMEGA_PRIME/TAX_KNOWLEDGE/logs")
LOG_DIR.mkdir(exist_ok=True)

logger.add(
    LOG_DIR / "tax_engine_{time}.log",
    rotation="50 MB",
    retention="30 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}"
)

AUDIT_LOG = LOG_DIR / "audit_trail.jsonl"


# ============================================================================
# METRICS COLLECTOR (Minimal - No Orchestration)
# ============================================================================

class MetricsCollector:
    """
    Lightweight metrics for operational awareness.
    No external dependencies. No complexity.
    """

    def __init__(self):
        self.latencies: List[float] = []  # Last 100 query latencies
        self.errors: List[float] = []  # Timestamps of errors
        self.queries: List[float] = []  # Timestamps of queries
        self.doctrine_hits: int = 0
        self.doctrine_misses: int = 0
        self.last_error: Optional[str] = None
        self.active_queries: int = 0
        self._lock_latencies = 100  # Keep last N

    def record_query(self, latency_ms: float, doctrine_hit: bool):
        """Record a completed query."""
        now = time.time()
        self.latencies.append(latency_ms)
        if len(self.latencies) > self._lock_latencies:
            self.latencies.pop(0)
        self.queries.append(now)
        # Prune old queries (keep last hour)
        cutoff = now - 3600
        self.queries = [t for t in self.queries if t > cutoff]
        if doctrine_hit:
            self.doctrine_hits += 1
        else:
            self.doctrine_misses += 1

    def record_error(self, error_msg: str):
        """Record an error."""
        self.errors.append(time.time())
        self.last_error = f"{datetime.now(timezone.utc).isoformat()}: {error_msg[:100]}"
        # Prune old errors (keep last 24h)
        cutoff = time.time() - 86400
        self.errors = [t for t in self.errors if t > cutoff]

    def query_start(self):
        self.active_queries += 1

    def query_end(self):
        self.active_queries = max(0, self.active_queries - 1)

    def get_latency_stats(self) -> Dict[str, float]:
        if not self.latencies:
            return {"avg_ms": 0.0, "p95_ms": 0.0, "last_ms": 0.0}
        sorted_lat = sorted(self.latencies)
        p95_idx = int(len(sorted_lat) * 0.95)
        return {
            "avg_ms": round(sum(self.latencies) / len(self.latencies), 2),
            "p95_ms": round(sorted_lat[min(p95_idx, len(sorted_lat) - 1)], 2),
            "last_ms": round(self.latencies[-1], 2)
        }

    def get_error_stats(self) -> Dict[str, Any]:
        now = time.time()
        last_hour = sum(1 for t in self.errors if t > now - 3600)
        last_24h = len(self.errors)
        return {
            "last_hour": last_hour,
            "last_24h": last_24h,
            "last_error": self.last_error
        }

    def get_doctrine_hit_rate(self) -> float:
        total = self.doctrine_hits + self.doctrine_misses
        if total == 0:
            return 1.0
        return round(self.doctrine_hits / total, 3)

    def queries_last_hour(self) -> int:
        cutoff = time.time() - 3600
        return sum(1 for t in self.queries if t > cutoff)


# Global metrics instance
_metrics = MetricsCollector()


def get_metrics() -> MetricsCollector:
    return _metrics


# ============================================================================
# ENUMS AND TYPES
# ============================================================================

class ResponseMode(str, Enum):
    FAST = "fast"
    DEFENSE = "defense"
    MEMO = "memo"


class Complexity(str, Enum):
    STANDARD = "standard"
    ADVANCED = "advanced"


class EntityType(str, Enum):
    INDIVIDUAL = "individual"
    SOLE_PROP = "sole_proprietorship"
    PARTNERSHIP = "partnership"
    LLC = "llc"
    S_CORP = "s_corporation"
    C_CORP = "c_corporation"
    TRUST = "trust"
    ESTATE = "estate"


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class TaxQuery(BaseModel):
    """Professional tax query request."""
    question: str = Field(..., min_length=10, description="Tax question requiring analysis")
    mode: ResponseMode = Field(default=ResponseMode.FAST, description="Response depth mode")
    jurisdiction: str = Field(default="US", description="Tax jurisdiction")
    entity_type: Optional[EntityType] = Field(default=None, description="Entity type context")
    complexity: Complexity = Field(default=Complexity.STANDARD, description="Query complexity level")
    tax_year: Optional[int] = Field(default=None, description="Relevant tax year")
    include_trace: bool = Field(default=False, description="Include reasoning trace")


class Citation(BaseModel):
    """Structured citation."""
    authority: str  # IRC, Case, Reg, Rev Rul, etc.
    reference: str  # Specific citation
    relevance: str  # Why cited


class ReasoningStep(BaseModel):
    """Structured reasoning component."""
    step: int
    analysis: str
    authority: Optional[str] = None


class TaxResponse(BaseModel):
    """Professional tax intelligence response."""
    # Core response
    query_id: str
    question: str
    mode: ResponseMode

    # Primary answer
    conclusion: str
    reasoning: str

    # Structured components
    key_factors: List[str]
    citations: List[Citation]

    # Defense elements (populated in DEFENSE/MEMO modes)
    burden_analysis: Optional[str] = None
    irs_position: Optional[str] = None
    counter_arguments: Optional[List[str]] = None
    appeals_posture: Optional[str] = None

    # Metadata
    doctrine_match: bool
    confidence_tier: Literal["high", "moderate", "requires_review"]
    response_layer: Literal["doctrine", "retrieval", "deep_analysis"]
    latency_ms: float

    # AUTHORITY HARDENING - Conflict Resolution
    conflict_detected: bool = False
    conflict_resolution: Optional[Dict[str, Any]] = None  # Serialized ConflictResolution
    authority_weight: Optional[int] = None
    confidence_stratification: Optional[str] = None  # ConfidenceStratification value
    controlling_precedent: Optional[str] = None  # Precedent anchor citation
    determinism_hash: Optional[str] = None  # For verifying identical results

    # Trace (optional)
    reasoning_trace: Optional[List[ReasoningStep]] = None

    # Caveats
    limitations: List[str] = Field(default_factory=list)

    # Audit
    timestamp: str
    version: str = "1.1.0"  # Bumped for authority hardening


class HealthResponse(BaseModel):
    """Comprehensive system health check for operational awareness."""
    # Status
    status: Literal["healthy", "degraded", "unhealthy"]
    engine: str
    version: str
    uptime_seconds: float

    # Latency Metrics
    api_latency: Dict[str, float]  # avg_ms, p95_ms, last_ms

    # Component Status
    doctrine_cache: Dict[str, Any]  # status, topics, hit_rate
    vector_db: Dict[str, Any]  # status, documents, last_query_ms

    # Resources
    memory_mb: Dict[str, float]  # used, available, percent

    # Activity
    active_queries: int
    queries_last_hour: int

    # Reliability
    error_rate: Dict[str, Any]  # last_hour, last_24h, last_error


# ============================================================================
# AUTHORITY HARDENING — ENUMS AND TYPES
# ============================================================================

class AuthorityLevel(str, Enum):
    """Hierarchical authority weighting. IRC > Regs > Cases > Guidance > Pubs."""
    IRC = "irc"                    # Weight: 100
    TREASURY_REG = "treasury_reg"  # Weight: 80
    COURT_CASE = "court_case"      # Weight: 60
    IRS_GUIDANCE = "irs_guidance"  # Weight: 40
    PUBLICATION = "publication"    # Weight: 20

    @property
    def weight(self) -> int:
        weights = {
            "irc": 100,
            "treasury_reg": 80,
            "court_case": 60,
            "irs_guidance": 40,
            "publication": 20
        }
        return weights.get(self.value, 10)


class ConfidenceStratification(str, Enum):
    """Confidence classification for conclusions."""
    DEFENSIBLE = "defensible"                      # Solid authority, low audit risk
    AGGRESSIVE_SUPPORTABLE = "aggressive_supportable"  # Supportable but may draw scrutiny
    DISCLOSURE_RECOMMENDED = "disclosure_recommended"  # Disclosure on return advisable
    HIGH_AUDIT_RISK = "high_audit_risk"            # Position may not survive examination


@dataclass
class ControllingPrecedent:
    """Binding precedent anchor for doctrine."""
    case_name: str
    citation: str
    court: str  # "Supreme Court", "Tax Court", "Circuit Court", "District Court"
    holding: str
    binding_scope: str  # "nationwide", "circuit", "persuasive"

    @property
    def precedential_weight(self) -> int:
        """Supreme Court > Circuit > Tax Court > District."""
        court_weights = {
            "Supreme Court": 100,
            "Circuit Court": 80,
            "Tax Court": 60,
            "District Court": 40
        }
        return court_weights.get(self.court, 30)


@dataclass
class ConflictResolution:
    """Explicit resolution when multiple doctrines apply."""
    competing_doctrines: List[str]  # Topic keys that could apply
    resolution_rationale: str        # Why one was selected
    authority_basis: str             # Primary authority driving resolution
    rejected_alternatives: List[Dict[str, str]]  # What was rejected and why


@dataclass
class MatchResult:
    """Result of doctrine matching with conflict resolution metadata."""
    doctrine: Optional["DoctrineBlock"]  # Forward reference
    topic_key: Optional[str]
    match_score: int
    authority_weight: int
    conflict_detected: bool
    conflict_resolution: Optional[ConflictResolution]
    all_candidates: List[Dict[str, Any]]  # All doctrines that scored, for audit
    determinism_hash: str  # Hash for verifying identical results across runs

    @property
    def is_match(self) -> bool:
        """True if a doctrine was matched."""
        return self.doctrine is not None


# ============================================================================
# DOCTRINE ENGINE (LAYER 1)
# ============================================================================

@dataclass
class DoctrineBlock:
    """Pre-compiled expert reasoning block with authority hardening."""
    topic: str
    keywords: List[str]

    # Core reasoning
    conclusion_template: str
    reasoning_framework: str
    key_factors: List[str]

    # Citations with authority hierarchy
    primary_authority: List[Dict[str, str]]

    # Defense elements
    burden_holder: str  # "taxpayer" or "irs"
    irs_typical_position: str
    counter_arguments: List[str]
    appeals_strategy: str

    # Applicable entities
    entity_scope: List[str] = field(default_factory=lambda: ["all"])

    # HARDENING: Confidence Stratification
    confidence: str = "high"
    confidence_stratification: ConfidenceStratification = ConfidenceStratification.DEFENSIBLE

    # HARDENING: Controlling Precedent
    controlling_precedent: Optional[ControllingPrecedent] = None

    # HARDENING: Related doctrines for conflict detection
    related_doctrines: List[str] = field(default_factory=list)

    def get_authority_weight(self) -> int:
        """Calculate weighted authority score for this doctrine."""
        if not self.primary_authority:
            return 0
        total = 0
        for auth in self.primary_authority:
            auth_type = auth.get("authority", "").lower()
            if "irc" in auth_type or "§" in auth.get("reference", ""):
                total += AuthorityLevel.IRC.weight
            elif "reg" in auth_type or "treas" in auth_type:
                total += AuthorityLevel.TREASURY_REG.weight
            elif any(x in auth_type for x in ["case", "court", "v.", "vs"]):
                total += AuthorityLevel.COURT_CASE.weight
            elif any(x in auth_type for x in ["rev", "rul", "proc", "notice", "ann"]):
                total += AuthorityLevel.IRS_GUIDANCE.weight
            else:
                total += AuthorityLevel.PUBLICATION.weight
        return total

    def get_precedent_anchor(self) -> Optional[str]:
        """Return controlling precedent citation if available."""
        if self.controlling_precedent:
            return f"{self.controlling_precedent.case_name}, {self.controlling_precedent.citation}"
        # Fall back to highest-weight case in primary_authority
        for auth in self.primary_authority:
            if auth.get("authority", "").lower() == "case":
                return auth.get("reference")
        return None


# Pre-compiled doctrine cache
DOCTRINE_CACHE: Dict[str, DoctrineBlock] = {

    "reasonable_compensation": DoctrineBlock(
        topic="S-Corporation Reasonable Compensation",
        keywords=["reasonable compensation", "s-corp salary", "officer compensation",
                  "shareholder employee", "compensation audit", "payroll tax"],
        conclusion_template="""Reasonable compensation for S-corporation shareholder-employees
is determined by the fair market value of services rendered, not by reference to corporate
profits or distributions. The compensation must reflect what would be paid to an unrelated
party for comparable services in comparable circumstances.""",
        reasoning_framework="""
ANALYSIS FRAMEWORK:

1. COMPARABILITY FACTORS (Rev. Rul. 74-44)
   - Training and experience
   - Duties and responsibilities
   - Time devoted to business
   - Dividend history and policy
   - Compensation agreements
   - Timing and manner of payment
   - Comparable industry compensation

2. INDEPENDENT INVESTOR TEST (Exacto Spring)
   - Calculate return on equity (ROE) after officer compensation
   - Compare to market returns for comparable investments
   - If ROE exceeds market expectations, compensation is presumptively reasonable
   - This test is FAVORABLE to taxpayers in high-profit situations

3. BIFURCATION ANALYSIS
   - Separate return to labor (compensable)
   - Separate return to capital (distribution)
   - Identify enterprise premium (may be either)
   - Document basis for allocation""",
        key_factors=[
            "Comparable salary data from independent sources",
            "Return on equity analysis (Exacto Spring test)",
            "Time and responsibility documentation",
            "Industry-specific compensation studies",
            "Historical compensation patterns"
        ],
        primary_authority=[
            {"authority": "Case", "reference": "Exacto Spring Corp. v. Commissioner, 196 F.3d 833 (7th Cir. 1999)", "relevance": "Establishes Independent Investor Test"},
            {"authority": "IRC", "reference": "IRC §1366(e)", "relevance": "Reasonable compensation requirement"},
            {"authority": "IRC", "reference": "IRC §3121(a)", "relevance": "Wage definition for employment tax"},
            {"authority": "Case", "reference": "Menard Inc. v. Commissioner, 560 F.3d 620 (7th Cir. 2009)", "relevance": "ROE analysis application"}
        ],
        burden_holder="irs",
        irs_typical_position="""The IRS typically argues that distributions should be
recharacterized as wages when: (1) compensation appears artificially low relative to
services performed; (2) distributions significantly exceed salary; (3) no formal
compensation analysis was performed; or (4) comparable salary data is absent or flawed.""",
        counter_arguments=[
            "Independent Investor Test demonstrates adequate ROE after compensation",
            "Comparable salary data from multiple independent sources supports amount",
            "Compensation reflects arm's-length negotiation documented in corporate minutes",
            "IRS comparable data fails to account for industry, geography, or entity size",
            "Historical compensation pattern is consistent and defensible"
        ],
        appeals_strategy="""At Appeals, emphasize: (1) the strength of Independent Investor
Test analysis; (2) quality and independence of comparable salary data; (3) weakness or
absence of examiner's alternative analysis; (4) hazards of litigation given 7th Circuit
precedent. Request Appeals consider Exacto Spring standard if in 7th Circuit or persuasive
authority elsewhere.""",
        entity_scope=["s_corporation"],
        confidence="high"
    ),

    "capital_vs_labor": DoctrineBlock(
        topic="Capital vs Labor Profit Attribution",
        keywords=["capital attribution", "labor attribution", "profit source",
                  "ownership profit", "service income", "return on capital"],
        conclusion_template="""Profits in a closely-held business derive from multiple sources:
labor (services of owner), capital (invested assets), and enterprise premium (going concern
value, goodwill, market position). Attribution requires disaggregation based on economic
substance, not merely ownership percentage.""",
        reasoning_framework="""
ATTRIBUTION FRAMEWORK:

1. IDENTIFY PROFIT SOURCES
   - Labor Return: Value of services if performed by unrelated party
   - Capital Return: Market rate return on invested capital
   - Enterprise Premium: Residual value (systems, brand, relationships)

2. QUANTIFY EACH COMPONENT
   - Labor: Comparable salary + benefits for role
   - Capital: Risk-adjusted return (typically 8-15% depending on industry)
   - Enterprise: Remaining profit after labor and capital returns

3. ALLOCATION METHODOLOGY
   - Document methodology contemporaneously
   - Use independent data sources
   - Consider industry-specific factors
   - Apply consistently year-over-year

4. RESPOND TO IRS RECHARACTERIZATION
   - Challenge lack of independent analysis
   - Demand examiner's alternative calculation
   - Assert burden remains with IRS on recharacterization""",
        key_factors=[
            "Independent valuation of services component",
            "Capitalization rate for invested capital",
            "Industry profit margin benchmarks",
            "Enterprise value separate from personal goodwill",
            "Documentation of allocation methodology"
        ],
        primary_authority=[
            {"authority": "Case", "reference": "Exacto Spring Corp. v. Commissioner, 196 F.3d 833 (7th Cir. 1999)", "relevance": "Capital return analysis"},
            {"authority": "IRC", "reference": "IRC §162(a)(1)", "relevance": "Reasonable compensation deduction"},
            {"authority": "Case", "reference": "Elliots, Inc. v. Commissioner, 716 F.2d 1241 (9th Cir. 1983)", "relevance": "Multi-factor compensation analysis"}
        ],
        burden_holder="irs",
        irs_typical_position="""The IRS may argue that profits in excess of labor compensation
are attributable to ownership and thus properly characterized as distributions (S-corp) or
dividends (C-corp). This position often lacks rigorous capital attribution analysis and may
be challenged on methodological grounds.""",
        counter_arguments=[
            "IRS failed to perform independent capital return analysis",
            "Profit attribution must account for all sources, not just labor",
            "Enterprise premium represents return on going concern, not capital or labor alone",
            "Ownership percentage is not determinative of profit source",
            "Market-based capital return calculation demonstrates remaining profit is not purely capital-derived"
        ],
        appeals_strategy="""Present rigorous three-component analysis. Challenge IRS to
produce alternative methodology. Emphasize that attribution by ownership percentage alone
lacks economic substance and ignores Exacto Spring framework.""",
        entity_scope=["s_corporation", "c_corporation", "partnership", "llc"],
        confidence="high"
    ),

    "constructive_receipt": DoctrineBlock(
        topic="Constructive Receipt Doctrine",
        keywords=["constructive receipt", "income timing", "deferred compensation",
                  "when income received", "cash method timing", "available income"],
        conclusion_template="""Income is constructively received when it is credited to the
taxpayer's account, set apart, or otherwise made available so that the taxpayer may draw
upon it at any time. Mere promise to pay, even if unconditional, does not trigger
constructive receipt if substantial limitations exist.""",
        reasoning_framework="""
CONSTRUCTIVE RECEIPT ANALYSIS:

1. AVAILABILITY TEST (Treas. Reg. §1.451-2)
   - Was income credited to taxpayer's account?
   - Was income set apart for the taxpayer?
   - Was income otherwise made available?
   - Could taxpayer draw upon it without restriction?

2. SUBSTANTIAL LIMITATIONS
   - Income NOT constructively received if:
     * Taxpayer's control is subject to substantial limitations
     * Restrictions are not within taxpayer's control to remove
     * Employer/payor retains discretion over payment

3. COMMON SCENARIOS
   - Deferred compensation arrangements
   - Year-end bonus timing
   - Commission payments
   - Retirement plan distributions

4. ECONOMIC BENEFIT DISTINCTION
   - Even without constructive receipt, economic benefit may trigger inclusion
   - Focus: whether current economic value is conferred""",
        key_factors=[
            "Whether income was unconditionally available",
            "Existence of substantial limitations on access",
            "Whether taxpayer voluntarily turned back on available income",
            "Documentation of restrictions before income became available",
            "Economic benefit analysis separate from constructive receipt"
        ],
        primary_authority=[
            {"authority": "Reg", "reference": "Treas. Reg. §1.451-2(a)", "relevance": "Constructive receipt definition"},
            {"authority": "Case", "reference": "Commissioner v. Oates, 207 F.2d 711 (7th Cir. 1953)", "relevance": "Substantial limitations doctrine"},
            {"authority": "IRC", "reference": "IRC §451(a)", "relevance": "General timing rule for income"},
            {"authority": "Rev Rul", "reference": "Rev. Rul. 60-31", "relevance": "Deferred compensation timing"}
        ],
        burden_holder="irs",
        irs_typical_position="""The IRS may assert constructive receipt when: (1) payment was
available but taxpayer chose to defer; (2) restrictions appear to be taxpayer-controlled;
(3) deferral arrangement lacks business purpose; or (4) payment was already earned and
merely held at taxpayer's request.""",
        counter_arguments=[
            "Substantial limitations existed before income was earned",
            "Taxpayer had no ability to remove restrictions unilaterally",
            "Deferral arrangement had legitimate business purpose",
            "Employer retained genuine discretion over payment timing",
            "No mere turning away from available funds occurred"
        ],
        appeals_strategy="""Demonstrate that substantial limitations were in place before the
right to receive income accrued. Distinguish voluntary deferral of available income from
legitimate advance arrangement. Cite Oates line of cases on substantial limitations.""",
        entity_scope=["all"],
        confidence="high"
    ),

    "economic_substance": DoctrineBlock(
        topic="Economic Substance Doctrine",
        keywords=["economic substance", "business purpose", "sham transaction",
                  "codified economic substance", "6662 penalty", "tax shelter"],
        conclusion_template="""Under IRC §7701(o), a transaction has economic substance only if
(1) the transaction changes the taxpayer's economic position in a meaningful way (apart from
tax effects), AND (2) the taxpayer has a substantial non-tax purpose for entering into the
transaction. Both prongs must be satisfied.""",
        reasoning_framework="""
ECONOMIC SUBSTANCE ANALYSIS (IRC §7701(o)):

1. OBJECTIVE PRONG - ECONOMIC CHANGE
   - Does transaction meaningfully change economic position?
   - Measure: apart from Federal income tax effects
   - Requires genuine pre-tax profit potential
   - Nominal or circular cash flows insufficient

2. SUBJECTIVE PRONG - BUSINESS PURPOSE
   - Does taxpayer have substantial non-tax purpose?
   - Purpose must be genuine, not pretextual
   - Tax benefit cannot be sole or primary purpose
   - Reasonable business justification required

3. PENALTY EXPOSURE (IRC §6662(b)(6))
   - 20% penalty on underpayment
   - Increases to 40% if not disclosed
   - Strict liability - no reasonable cause defense
   - Applies to any transaction lacking economic substance

4. RELEVANCE DETERMINATION
   - Doctrine applies only to transactions TO WHICH IT IS RELEVANT
   - Not all tax benefits require economic substance analysis
   - Common law exceptions may still apply""",
        key_factors=[
            "Pre-tax profit potential (objective)",
            "Genuine business purpose beyond tax savings (subjective)",
            "Whether transaction is in category where doctrine is relevant",
            "Disclosure on Form 8886 if potentially reportable",
            "Documentation of business rationale contemporaneous with transaction"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §7701(o)", "relevance": "Codified economic substance doctrine"},
            {"authority": "IRC", "reference": "IRC §6662(b)(6)", "relevance": "20%/40% penalty"},
            {"authority": "Case", "reference": "ACM Partnership v. Commissioner, 157 F.3d 231 (3d Cir. 1998)", "relevance": "Pre-codification application"},
            {"authority": "Notice", "reference": "Notice 2010-62", "relevance": "IRS interim guidance on codification"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges transactions where: (1) tax benefit is
disproportionate to economic risk; (2) business purpose appears pretextual; (3) transaction
resembles known tax shelter patterns; or (4) circular cash flows suggest no meaningful
economic change.""",
        counter_arguments=[
            "Transaction had genuine pre-tax profit potential documented ex ante",
            "Substantial business purpose independent of tax benefits exists",
            "Transaction is of a type where doctrine is not relevant",
            "Economic position meaningfully changed as demonstrated by actual results",
            "Transaction does not match any listed transaction or shelter pattern"
        ],
        appeals_strategy="""Document business purpose thoroughly before transaction. Maintain
contemporaneous records of non-tax rationale. If challenged, argue doctrine is not relevant
to transaction type, or demonstrate both prongs are satisfied with objective evidence.""",
        entity_scope=["all"],
        confidence="high"
    ),

    "hobby_loss": DoctrineBlock(
        topic="Hobby Loss Rules - IRC §183",
        keywords=["hobby loss", "not for profit", "183", "profit motive",
                  "hobby farm", "horse breeding", "side business losses"],
        conclusion_template="""An activity is presumed engaged in for profit if it produces
profit in 3 of 5 consecutive years (2 of 7 for horse activities). If the presumption does
not apply, the IRS examines nine factors under Treas. Reg. §1.183-2(b) to determine whether
the taxpayer had an actual and honest profit objective.""",
        reasoning_framework="""
HOBBY LOSS ANALYSIS:

1. STATUTORY PRESUMPTION (IRC §183(d))
   - Profit in 3 of 5 years: presumed for-profit
   - Horse breeding/racing: 2 of 7 years
   - Presumption is rebuttable by IRS
   - Election to defer determination (Form 5213)

2. NINE-FACTOR TEST (Treas. Reg. §1.183-2(b))
   1. Manner carried on (businesslike)
   2. Expertise of taxpayer/advisors
   3. Time and effort expended
   4. Expectation of asset appreciation
   5. Success in similar activities
   6. History of income/losses
   7. Amount of occasional profits
   8. Financial status of taxpayer
   9. Personal pleasure/recreation elements

3. APPLICATION PRINCIPLES
   - No single factor is determinative
   - All facts and circumstances considered
   - Actual profit not required, honest objective is
   - Losses during startup phase given more tolerance

4. IF HOBBY CLASSIFICATION APPLIES
   - Deductions limited to income from activity
   - No loss allowed against other income
   - Miscellaneous itemized deductions suspended through 2025""",
        key_factors=[
            "Businesslike manner of operation (separate books, business plan)",
            "Expertise development and professional consultation",
            "Time devoted relative to other activities",
            "Changes made to improve profitability",
            "History of profits or progression toward profitability"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §183", "relevance": "Hobby loss limitation"},
            {"authority": "Reg", "reference": "Treas. Reg. §1.183-2(b)", "relevance": "Nine-factor test"},
            {"authority": "Case", "reference": "Dreicer v. Commissioner, 78 T.C. 642 (1982)", "relevance": "Profit motive standard"},
            {"authority": "Case", "reference": "Golanty v. Commissioner, 72 T.C. 411 (1979)", "relevance": "Startup period analysis"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges activities with: (1) continuous losses over
many years; (2) personal pleasure elements; (3) wealthy taxpayer with losses offsetting
other income; (4) lack of businesslike records; or (5) minimal effort to improve
profitability.""",
        counter_arguments=[
            "Businesslike records and operations maintained consistently",
            "Professional advice sought and business plan developed",
            "Specific changes implemented to achieve profitability",
            "Startup losses are normal for this type of business",
            "Asset appreciation is legitimate component of profit motive",
            "Time devoted is substantial and documented"
        ],
        appeals_strategy="""Emphasize businesslike conduct and documented changes to improve
results. If losses continue, show they are explainable by external factors. Argue that
personal enjoyment does not negate profit motive where genuine business effort exists.""",
        entity_scope=["individual", "sole_proprietorship"],
        confidence="high"
    ),

    "home_office": DoctrineBlock(
        topic="Home Office Deduction - IRC §280A",
        keywords=["home office", "280a", "business use of home", "principal place of business",
                  "exclusive use", "regular use", "home office audit"],
        conclusion_template="""A home office deduction requires a portion of the home used
regularly and exclusively for business. The space must be either the principal place of
business, a place where clients are met, or a separate structure used in business.
Employees may not deduct home office expenses under current law (through 2025).""",
        reasoning_framework="""
HOME OFFICE ANALYSIS:

1. THRESHOLD REQUIREMENTS
   - Regular use: consistent, not occasional
   - Exclusive use: dedicated space, not dual-purpose
   - For the convenience of the employer (if employee - suspended through 2025)

2. QUALIFYING USE TESTS (any one satisfies)
   a. Principal place of business
      - Where most important activities occur, OR
      - Where substantial administrative work done if no other fixed location
   b. Place to meet clients/customers in normal course
   c. Separate structure used in connection with business

3. CALCULATION METHODS
   - Regular: Actual expenses × business use percentage
   - Simplified: $5/sq ft, max 300 sq ft ($1,500)
   - Depreciation: Required under regular method

4. DEDUCTION LIMITATIONS
   - Cannot create or increase business loss
   - Carry forward unused amounts
   - Allocate mortgage interest and RE taxes carefully""",
        key_factors=[
            "Exclusive use - no personal activities in space",
            "Regular use - consistent business activity",
            "Principal place of business determination",
            "Square footage calculation and documentation",
            "Photograph of space maintained in records"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §280A(c)", "relevance": "Home office requirements"},
            {"authority": "Case", "reference": "Commissioner v. Soliman, 506 U.S. 168 (1993)", "relevance": "Principal place of business test"},
            {"authority": "IRC", "reference": "IRC §280A(c)(1)(A)", "relevance": "Administrative/management activities test"},
            {"authority": "Rev Proc", "reference": "Rev. Proc. 2013-13", "relevance": "Simplified method"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS commonly challenges: (1) exclusive use where family
areas overlap; (2) regular use where business activity is sporadic; (3) principal place
designation where other locations are used; (4) calculation methodology and documentation.""",
        counter_arguments=[
            "Space is physically separated or otherwise dedicated exclusively",
            "Daily/weekly use pattern establishes regularity",
            "Administrative/management activities principally performed at home",
            "No other fixed location available for administrative work",
            "Square footage calculation supported by floor plan documentation"
        ],
        appeals_strategy="""Provide photographs, floor plans, and calendar/log showing
regular business use. If exclusive use is challenged, demonstrate physical separation or
dedicated furniture arrangement. Emphasize Soliman administrative activities test if
applicable.""",
        entity_scope=["individual", "sole_proprietorship"],
        confidence="high"
    ),

    "passive_activity_loss": DoctrineBlock(
        topic="Passive Activity Loss Rules - IRC §469",
        keywords=["passive activity", "469", "material participation", "rental real estate",
                  "passive loss limitation", "at-risk", "real estate professional"],
        conclusion_template="""Passive activity losses may only offset passive activity income.
An activity is passive unless the taxpayer materially participates. Rental activities are
per se passive unless the taxpayer qualifies as a real estate professional under IRC
§469(c)(7). Limited partners are generally passive regardless of participation.""",
        reasoning_framework="""
PASSIVE ACTIVITY ANALYSIS:

1. PASSIVE ACTIVITY DEFINED
   - Trade or business in which taxpayer does NOT materially participate
   - Rental activity (per se passive, with exceptions)
   - Limited partnership interest (generally passive)

2. MATERIAL PARTICIPATION TESTS (Temp. Reg. §1.469-5T)
   Any ONE of seven tests satisfies:
   1. 500+ hours during year
   2. Substantially all participation by taxpayer
   3. 100+ hours and no one participates more
   4. Significant participation activities totaling 500+ hours
   5. Material participation in 5 of 10 prior years
   6. Personal service activity - 3 prior years
   7. Facts and circumstances (100+ hour minimum)

3. REAL ESTATE PROFESSIONAL EXCEPTION (§469(c)(7))
   Requirements (both must be met):
   - More than 50% of personal services in real property trades/businesses
   - More than 750 hours in real property trades/businesses
   - Must materially participate in EACH rental activity (or elect to aggregate)

4. $25,000 RENTAL LOSS ALLOWANCE (§469(i))
   - Active participation required (lower standard than material)
   - Phase out: $100K-$150K MAGI
   - Not available for REITs or limited partners""",
        key_factors=[
            "Hours of participation documented contemporaneously",
            "Nature of participation (management vs. passive investment)",
            "Whether rental activity or trade/business",
            "Real estate professional qualification if rental",
            "Grouping elections properly made"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §469", "relevance": "Passive activity loss limitation"},
            {"authority": "Reg", "reference": "Temp. Reg. §1.469-5T", "relevance": "Material participation tests"},
            {"authority": "IRC", "reference": "IRC §469(c)(7)", "relevance": "Real estate professional exception"},
            {"authority": "Case", "reference": "Aragona Trust v. Commissioner, 142 T.C. 165 (2014)", "relevance": "Hour substantiation"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS frequently challenges: (1) hour logs created after
audit notice; (2) real estate professional status where W-2 job exists; (3) nature of
activities counted as participation; (4) failure to make grouping election timely.""",
        counter_arguments=[
            "Contemporaneous time logs maintained throughout year",
            "Calendar entries and third-party records corroborate hours",
            "Real estate activities exceed 750 hours with documentation",
            "W-2 employment was less than 50% of total personal services",
            "Grouping election properly made on original timely-filed return"
        ],
        appeals_strategy="""Hour substantiation is critical. Contemporaneous logs are strongly
preferred but courts have accepted reconstructed records with corroboration. For real estate
professional status, ensure 50% test is clearly met before claiming 750-hour test.""",
        entity_scope=["individual", "partnership", "llc", "s_corporation"],
        confidence="high"
    ),

    "section_1031": DoctrineBlock(
        topic="Like-Kind Exchange - IRC §1031",
        keywords=["1031", "like-kind exchange", "qualified intermediary", "boot",
                  "deferred exchange", "reverse exchange", "identification period"],
        conclusion_template="""IRC §1031 permits deferral of gain on exchange of real property
held for productive use or investment. Personal property no longer qualifies (post-TCJA).
Strict timing requirements apply: 45 days to identify, 180 days to close. Qualified
intermediary required for deferred exchanges.""",
        reasoning_framework="""
1031 EXCHANGE ANALYSIS:

1. QUALIFYING PROPERTY (Post-TCJA)
   - Real property held for productive use in trade/business
   - Real property held for investment
   - NOT: inventory, personal property, stocks, bonds, partnership interests

2. LIKE-KIND REQUIREMENT
   - Broad for real estate (improved for unimproved, commercial for residential)
   - Both properties must be US property (domestic-to-domestic only)
   - Must be like-kind as to nature/character, not grade/quality

3. TIMING REQUIREMENTS (Strict)
   - Day 0: Close on relinquished property
   - Day 45: Identification deadline (midnight)
   - Day 180: Exchange completion deadline
   - Both dates are hard deadlines - no extensions

4. IDENTIFICATION RULES
   - 3-Property Rule: Up to 3 properties regardless of value
   - 200% Rule: Any number if FMV ≤ 200% of relinquished
   - 95% Rule: Any number if 95% of identified properties acquired

5. BOOT
   - Cash received = boot, taxable to extent of gain
   - Mortgage relief in excess of debt assumed = boot
   - Unlike property received = boot""",
        key_factors=[
            "Property held for investment or productive use (not personal)",
            "45-day identification in writing to qualified intermediary",
            "180-day completion of exchange",
            "Qualified intermediary controls proceeds (no constructive receipt)",
            "Boot calculation for mortgage differential"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §1031(a)", "relevance": "Nonrecognition of gain/loss"},
            {"authority": "IRC", "reference": "IRC §1031(a)(3)", "relevance": "Identification and exchange periods"},
            {"authority": "Reg", "reference": "Treas. Reg. §1.1031(k)-1", "relevance": "Deferred exchange rules"},
            {"authority": "Rev Proc", "reference": "Rev. Proc. 2000-37", "relevance": "Reverse exchange safe harbor"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges exchanges where: (1) taxpayer had access to
proceeds (no QI or defective QI); (2) identification was late or informal; (3) property was
held for personal use, not investment; (4) pre-arranged sale to related party.""",
        counter_arguments=[
            "Qualified intermediary agreement properly structured before closing",
            "Written identification delivered to QI within 45 days, documented",
            "Property was consistently held for investment, not personal use",
            "No constructive receipt - taxpayer had no access to funds",
            "Related party rules satisfied or not applicable"
        ],
        appeals_strategy="""Documentation is critical. Maintain complete QI agreement,
identification letters, and closing statements. If personal use is alleged, demonstrate
predominant investment intent through holding period, rental activity, or marketing efforts.""",
        entity_scope=["all"],
        confidence="high"
    ),

    "percentage_depletion": DoctrineBlock(
        topic="Percentage Depletion - Oil & Gas (IRC §613A)",
        keywords=["percentage depletion", "oil and gas", "613a", "independent producer",
                  "depletion allowance", "working interest", "royalty owner"],
        conclusion_template="""Independent producers and royalty owners may claim percentage
depletion of 15% of gross income from oil and gas properties, subject to limitations. The
deduction cannot exceed 100% of net income from the property. Integrated oil companies
are limited to cost depletion.""",
        reasoning_framework="""
PERCENTAGE DEPLETION ANALYSIS:

1. ELIGIBILITY (§613A)
   - Independent producers (not integrated companies)
   - Royalty owners
   - Working interest holders
   - NOT available to refiners above de minimis threshold

2. CALCULATION
   - 15% of gross income from property
   - Cannot exceed 100% of taxable income from property (before depletion)
   - Cannot exceed 65% of taxpayer's overall taxable income (before depletion)

3. BARRELS-PER-DAY LIMITATION (§613A(c))
   - 1,000 barrels/day average for oil
   - 6,000 MCF/day for natural gas
   - Allocation rules for related parties

4. ADVANTAGE OVER COST DEPLETION
   - Percentage depletion can exceed cost basis
   - May continue after basis recovered
   - Often more beneficial for producing properties""",
        key_factors=[
            "Independent producer vs. integrated company status",
            "Gross income from property calculation",
            "Net income limitation applied property-by-property",
            "Barrels-per-day limitation compliance",
            "Cost depletion comparison for optimal method"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §613A", "relevance": "Percentage depletion limitations"},
            {"authority": "IRC", "reference": "IRC §613", "relevance": "General depletion rules"},
            {"authority": "Reg", "reference": "Treas. Reg. §1.613A-3", "relevance": "Independent producer definition"},
            {"authority": "IRC", "reference": "IRC §613A(d)(4)", "relevance": "Integrated company definition"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS may challenge: (1) independent producer status where
refining activity exists; (2) gross income calculation including improper deductions;
(3) property-by-property net income limitation; (4) related party allocation.""",
        counter_arguments=[
            "Refining activity below de minimis threshold",
            "Gross income properly determined at wellhead",
            "Net income limitation correctly applied per property",
            "Barrels-per-day limitation properly computed and allocated",
            "Cost depletion alternative was less beneficial (comparison provided)"
        ],
        appeals_strategy="""Maintain detailed records by property. Ensure independent producer
status is clearly documented. If refining is involved, demonstrate de minimis threshold
compliance with specificity.""",
        entity_scope=["individual", "sole_proprietorship", "partnership", "llc", "s_corporation", "c_corporation"],
        confidence="high"
    ),

    "intangible_drilling_costs": DoctrineBlock(
        topic="Intangible Drilling Costs (IDC) - IRC §263(c)",
        keywords=["intangible drilling costs", "idc", "drilling expenses", "oil and gas deduction",
                  "263c", "election to expense", "alternative minimum tax"],
        conclusion_template="""Intangible drilling costs (wages, fuel, supplies, site preparation)
may be elected to expense currently under IRC §263(c) or capitalized and recovered through
depletion or depreciation. Most taxpayers elect immediate deduction. IDCs are a preference
item for AMT purposes.""",
        reasoning_framework="""
IDC ANALYSIS:

1. WHAT QUALIFIES AS IDC
   - Wages, fuel, repairs, supplies for drilling
   - Site preparation and ground clearing
   - Rig transportation and setup costs
   - Costs with no salvage value

   NOT IDC (must capitalize):
   - Casing, tubing, wellhead equipment
   - Tanks, separators, flow lines
   - Anything with salvage value

2. ELECTION OPTIONS
   - Expense: Deduct in year incurred (§263(c))
   - Capitalize: Recover through depletion or 60-month amortization
   - Election made on return for first year with IDC
   - Binding for that property and future similar properties

3. WORKING INTEREST REQUIREMENT
   - Deduction flows to working interest holder
   - Royalty owners do NOT get IDC deduction
   - Must have economic interest in production

4. AMT TREATMENT
   - Excess IDC over 10-year amortization is preference item
   - 65% of net oil/gas income is exempt from preference
   - Exception for independent producers in some cases""",
        key_factors=[
            "Working interest ownership documentation",
            "Proper allocation between IDC and tangible drilling costs",
            "Election made on timely-filed return",
            "AMT preference calculation if applicable",
            "Partnership allocation if flow-through"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §263(c)", "relevance": "IDC election authority"},
            {"authority": "Reg", "reference": "Treas. Reg. §1.612-4", "relevance": "IDC definition and treatment"},
            {"authority": "IRC", "reference": "IRC §57(a)(2)", "relevance": "AMT preference for IDC"},
            {"authority": "IRC", "reference": "IRC §59(e)", "relevance": "Optional 60-month amortization"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS may examine: (1) whether costs are properly
classified as intangible vs. tangible; (2) whether working interest ownership is properly
established; (3) IDC/tangible allocation methodology; (4) AMT preference calculation.""",
        counter_arguments=[
            "AFE (Authorization for Expenditure) breakdown supports classification",
            "Working interest documented through operating agreement",
            "Allocation between IDC and tangible follows industry standards",
            "Election properly made on timely-filed return",
            "AMT preference correctly computed with allowable exceptions"
        ],
        appeals_strategy="""Maintain detailed AFE and well completion records. Ensure
working interest is established before drilling begins. If classification is challenged,
use industry-standard definitions and operator records.""",
        entity_scope=["individual", "sole_proprietorship", "partnership", "llc", "s_corporation", "c_corporation"],
        confidence="high"
    ),

    "qbi_deduction": DoctrineBlock(
        topic="Qualified Business Income Deduction - IRC §199A",
        keywords=["qbi", "199a", "qualified business income", "pass-through deduction",
                  "20 percent deduction", "sstb", "specified service trade"],
        conclusion_template="""IRC §199A allows a deduction of up to 20% of qualified business
income from pass-through entities and sole proprietorships. The deduction is subject to
W-2 wage and capital limitations above income thresholds, and may be disallowed for
specified service trades or businesses (SSTBs) at higher income levels.""",
        reasoning_framework="""
QBI DEDUCTION ANALYSIS:

1. BASIC DEDUCTION (§199A(a))
   - 20% of QBI from qualified trades or businesses
   - Cannot exceed 20% of taxable income (minus capital gains)
   - Computed separately for each qualified business

2. LIMITATIONS (Above Threshold)
   2024 Thresholds: $191,950 (single) / $383,900 (MFJ)

   W-2 Wage/Capital Limit (greater of):
   - 50% of W-2 wages paid by business, OR
   - 25% of W-2 wages + 2.5% of UBIA of qualified property

   Limitation phases in over $50,000/$100,000 above threshold

3. SSTB EXCLUSION
   Specified Service Trades (cannot claim QBI above threshold):
   - Health, law, accounting, consulting, financial services
   - Performing arts, athletics, brokerage
   - Any business where principal asset is reputation/skill

   NOT SSTB: Engineering, architecture (specifically excluded)

4. AGGREGATION RULES
   - May aggregate commonly-controlled businesses
   - Useful to maximize W-2/UBIA limitations
   - Must share items among aggregated group""",
        key_factors=[
            "Taxable income level relative to thresholds",
            "SSTB classification analysis",
            "W-2 wages paid by the business",
            "UBIA of qualified property",
            "Aggregation election if multiple businesses"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §199A", "relevance": "QBI deduction provision"},
            {"authority": "Reg", "reference": "Treas. Reg. §1.199A-1 to -6", "relevance": "Final regulations"},
            {"authority": "IRC", "reference": "IRC §199A(d)(2)", "relevance": "SSTB definition"},
            {"authority": "Notice", "reference": "Notice 2019-07", "relevance": "Safe harbor for rental real estate"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS may challenge: (1) SSTB classification where
services are involved; (2) reasonable compensation reduction where owner works in business;
(3) aggregation elections improperly made; (4) W-2 wage allocations among businesses.""",
        counter_arguments=[
            "Business is not an SSTB under specific regulatory definitions",
            "Engineering/architecture exclusion applies",
            "Reasonable compensation has already been deducted before QBI calculation",
            "Aggregation election properly made on timely return",
            "W-2 wages allocated based on actual payment, not arbitrary allocation"
        ],
        appeals_strategy="""SSTB classification is often contested. Examine whether business
falls clearly within or outside definitions. For borderline cases, document substantial
non-service activities. Ensure reasonable compensation is properly determined before
computing QBI.""",
        entity_scope=["sole_proprietorship", "partnership", "llc", "s_corporation"],
        confidence="high"
    ),

    "statute_of_limitations": DoctrineBlock(
        topic="Statute of Limitations - Assessment & Collection",
        keywords=["statute of limitations", "assessment period", "collection period",
                  "6 year rule", "tolling", "refund claim", "audit timeline"],
        conclusion_template="""The IRS generally has 3 years from filing to assess additional
tax (IRC §6501). This extends to 6 years if gross income is understated by more than 25%.
No limitation applies for fraud or failure to file. Collection statute is 10 years from
assessment (IRC §6502).""",
        reasoning_framework="""
STATUTE OF LIMITATIONS FRAMEWORK:

1. ASSESSMENT PERIOD (§6501)
   - General: 3 years from later of due date or filing date
   - 25% omission: 6 years (substantial omission)
   - Fraud/False return: No limitation
   - Failure to file: No limitation
   - FBAR: 6 years from due date

2. EXTENSIONS AND TOLLING
   - Form 872: Consent to extend (voluntary)
   - Form 872-A: Indefinite extension
   - Bankruptcy: Tolled during proceedings
   - Collection Due Process: Tolled during CDP
   - Pending Tax Court case: Assessment suspended

3. COLLECTION PERIOD (§6502)
   - 10 years from date of assessment
   - Tolled during: installment agreement, OIC, bankruptcy, CDP
   - Fresh 10 years on each new assessment

4. REFUND CLAIMS (§6511)
   - 3 years from filing, OR 2 years from payment
   - Claim limited to amounts paid within applicable period
   - "Lookback" period for payments""",
        key_factors=[
            "Filing date of return (actual, not due date)",
            "Whether 25% substantial omission applies",
            "Any extensions executed (Form 872/872-A)",
            "Tolling events (bankruptcy, CDP, Tax Court)",
            "Assessment date for collection statute"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §6501", "relevance": "Assessment limitations"},
            {"authority": "IRC", "reference": "IRC §6502", "relevance": "Collection limitations"},
            {"authority": "IRC", "reference": "IRC §6511", "relevance": "Refund claim limitations"},
            {"authority": "Case", "reference": "United States v. Home Concrete, 566 U.S. 478 (2012)", "relevance": "25% omission definition"}
        ],
        burden_holder="irs",
        irs_typical_position="""The IRS may argue extended limitations where: (1) substantial
omission of income exists; (2) consent to extend was executed; (3) fraud indicators are
present; (4) return was not properly filed.""",
        counter_arguments=[
            "Assessment is barred by expired 3-year period",
            "No substantial omission - overstatement of basis is not omission (Home Concrete)",
            "Extension consent was limited in scope or has expired",
            "Return was properly filed, starting limitation period",
            "No fraud badges present - burden on IRS to prove fraud"
        ],
        appeals_strategy="""Statute of limitations is a complete defense if applicable.
Carefully document filing date and any extension agreements. Challenge 6-year assertion
by distinguishing basis overstatements from income omissions. IRS bears burden on fraud.""",
        entity_scope=["all"],
        confidence="high"
    ),

    "offer_in_compromise": DoctrineBlock(
        topic="Offer in Compromise (OIC) - IRC §7122",
        keywords=["offer in compromise", "oic", "settle tax debt", "doubt as to collectibility",
                  "irs settlement", "reasonable collection potential", "rcp"],
        conclusion_template="""An Offer in Compromise allows taxpayers to settle tax liabilities
for less than the full amount owed. IRS will accept an OIC when the offered amount equals or
exceeds the reasonable collection potential (RCP). Doubt as to collectibility is the most
common basis; doubt as to liability and effective tax administration are also available.""",
        reasoning_framework="""
OFFER IN COMPROMISE ANALYSIS:

1. GROUNDS FOR OIC (§7122)
   a. Doubt as to Collectibility (DATC)
      - IRS unlikely to collect full amount before CSED
      - Based on assets and income analysis
      - Most common OIC basis

   b. Doubt as to Liability (DATL)
      - Genuine dispute about correct tax
      - Not merely disagreement with prior assessment

   c. Effective Tax Administration (ETA)
      - Full collection would cause hardship
      - OR would be unfair/inequitable
      - Requires exceptional circumstances

2. REASONABLE COLLECTION POTENTIAL (RCP)
   RCP = Equity in Assets + Future Income

   Assets: FMV minus encumbrances, using IRS quick sale values
   Future Income: 12 or 24 months of disposable income
   - Lump sum (5+ months): 12 months of future income
   - Periodic payment (6-24 months): 24 months

3. PROCESS
   - Form 656 with $205 application fee
   - Form 433-A(OIC) or 433-B(OIC) for financials
   - 20% initial payment required for lump sum offers
   - IRS has 24 months to decide (deemed accepted if no decision)

4. COMPLIANCE REQUIREMENTS
   - Must be current on all filing requirements
   - Must remain compliant for 5 years post-acceptance
   - Default provisions apply if terms violated""",
        key_factors=[
            "Reasonable collection potential calculation",
            "Asset equity using quick sale values",
            "Monthly disposable income analysis",
            "Compliance with filing requirements",
            "Collection Statute Expiration Date proximity"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §7122", "relevance": "OIC authority"},
            {"authority": "Reg", "reference": "Treas. Reg. §301.7122-1", "relevance": "OIC procedures"},
            {"authority": "IRM", "reference": "IRM 5.8", "relevance": "Offer in Compromise guidelines"},
            {"authority": "Form", "reference": "Form 656 Booklet", "relevance": "Current OIC requirements"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS may reject OIC where: (1) RCP calculation shows ability
to pay more; (2) asset values understated; (3) income capacity underreported; (4) CSED is
near expiration (prefer waiting); (5) dissipated assets indicate collection potential.""",
        counter_arguments=[
            "RCP correctly calculated using IRS allowable expenses",
            "Asset values reflect actual quick sale values with documentation",
            "Income capacity accounts for necessary living expenses",
            "Economic hardship or health circumstances justify ETA basis",
            "CSED timing does not affect statutory right to submit OIC"
        ],
        appeals_strategy="""If rejected, request Appeals conference. Present corrected RCP
analysis addressing examiner's specific concerns. Consider ETA argument if DATC alone
insufficient. Document any changed circumstances since rejection.""",
        entity_scope=["all"],
        confidence="high"
    ),

    # ========================================================================
    # HIGH-RISK AUDIT-SENSITIVE DOMAINS
    # ========================================================================

    "employee_retention_credit": DoctrineBlock(
        topic="Employee Retention Credit (ERC) - COVID Relief",
        keywords=["employee retention credit", "erc", "ertc", "covid credit",
                  "refundable payroll credit", "erc audit", "erc disallowance",
                  "voluntary disclosure", "erc withdrawal"],
        conclusion_template="""The Employee Retention Credit was a refundable payroll tax credit
for eligible employers affected by COVID-19. Eligibility requires either: (1) full or partial
suspension of operations due to government orders, OR (2) significant decline in gross receipts.
The IRS has identified widespread fraudulent and erroneous claims and is actively auditing.""",
        reasoning_framework="""
ERC ELIGIBILITY ANALYSIS:

1. ELIGIBILITY PATHS (CARES Act, as amended)
   Path A: Government Order Suspension
   - Operations fully or partially suspended
   - Due to orders from appropriate governmental authority
   - Orders must limit commerce, travel, or group meetings
   - Partial suspension requires more than nominal impact

   Path B: Gross Receipts Decline
   - 2020: >50% decline vs same quarter 2019
   - 2021: >20% decline vs same quarter 2019
   - Alternative: prior quarter comparison

2. QUALIFIED WAGES
   - Wages paid during eligible period
   - Large employer (>100/500): only non-working time wages
   - Small employer: all wages during eligible quarter
   - Health plan expenses includable
   - Cannot double-dip with PPP wages

3. IRS ENFORCEMENT PRIORITIES
   - Claims filed by promoters without documentation
   - Essential businesses claiming suspension
   - Vague or non-specific government order citations
   - Gross receipts miscalculations
   - Aggregation rule violations (controlled groups)

4. REMEDIATION OPTIONS
   - Withdrawal program (before processing)
   - Amended return correction
   - Voluntary Disclosure Program (reduced penalties)""",
        key_factors=[
            "Specific government order documentation",
            "Quantified impact of suspension on operations",
            "Gross receipts calculation with supporting records",
            "Aggregation analysis for related entities",
            "No overlap with PPP forgiveness wages"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §3134 (2021), §2301 CARES Act (2020)", "relevance": "ERC statutory authority"},
            {"authority": "Notice", "reference": "Notice 2021-20", "relevance": "IRS ERC guidance"},
            {"authority": "Notice", "reference": "Notice 2021-49", "relevance": "Additional ERC guidance"},
            {"authority": "IR", "reference": "IR-2024-169", "relevance": "Voluntary Disclosure Program"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS is aggressively examining ERC claims, particularly those
filed through third-party promoters. Common disallowance grounds include: (1) no qualifying
government order or order did not suspend operations; (2) business was essential and continued
operating; (3) gross receipts decline not substantiated; (4) aggregation rules ignored.""",
        counter_arguments=[
            "Specific government order identified with operational impact documented",
            "Partial suspension demonstrated through reduced capacity or services",
            "Gross receipts decline calculated correctly with contemporaneous records",
            "Aggregation analysis performed and documented",
            "Claim prepared with professional analysis, not promoter-driven"
        ],
        appeals_strategy="""ERC cases are high-priority. If disallowed, immediately request
Appeals conference. Document specific government orders and their operational impact.
Prepare gross receipts analysis with source documents. If claim was promoter-driven and
clearly erroneous, consider Voluntary Disclosure Program for penalty mitigation.""",
        entity_scope=["all"],
        confidence="high"
    ),

    "worker_classification": DoctrineBlock(
        topic="Worker Classification - Employee vs Independent Contractor",
        keywords=["worker classification", "independent contractor", "1099 vs w2",
                  "employee vs contractor", "misclassification", "ss-8",
                  "gig worker", "common law employee"],
        conclusion_template="""Worker classification is determined by the common law test examining
the degree of control exercised over how work is performed. The key inquiry is whether the
business has the right to control not just what work is done, but how it is done. Factors are
weighed holistically; no single factor is determinative.""",
        reasoning_framework="""
WORKER CLASSIFICATION ANALYSIS:

1. COMMON LAW TEST - THREE CATEGORIES

   BEHAVIORAL CONTROL
   - Instructions: when, where, how to work
   - Training provided by company
   - Required methods or procedures
   - Evaluation systems beyond results

   FINANCIAL CONTROL
   - Significant investment by worker
   - Unreimbursed expenses
   - Opportunity for profit/loss
   - Services available to market
   - Method of payment (hourly vs project)

   RELATIONSHIP TYPE
   - Written contracts and intent
   - Employee benefits provided
   - Permanency of relationship
   - Services integral to business

2. IRS ENFORCEMENT TRIGGERS
   - Large number of 1099 workers in traditional roles
   - Industry-wide reclassification initiatives
   - Worker complaints (Form SS-8)
   - State agency referrals
   - Prior audit history

3. SECTION 530 RELIEF (Safe Harbor)
   Requirements:
   - Reasonable basis for treatment (prior audit, industry practice, etc.)
   - Substantive consistency in treatment
   - Reporting consistency (1099s filed)
   If met: protection from federal employment tax liability

4. CONSEQUENCES OF MISCLASSIFICATION
   - Back employment taxes (FICA, FUTA)
   - Penalties under §6651, §6656, §6721
   - Interest from original due dates
   - Potential §3509 reduced rates if 1099s filed""",
        key_factors=[
            "Degree of behavioral control over work methods",
            "Financial investment and profit/loss opportunity",
            "Permanency and exclusivity of relationship",
            "Whether Section 530 safe harbor applies",
            "Consistency of treatment across similar workers"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §3121(d), §3306(i)", "relevance": "Employee definition"},
            {"authority": "IRC", "reference": "IRC §530 (Revenue Act 1978)", "relevance": "Safe harbor relief"},
            {"authority": "Rev Rul", "reference": "Rev. Rul. 87-41", "relevance": "20-factor test (superseded but instructive)"},
            {"authority": "Pub", "reference": "IRS Pub 15-A", "relevance": "Employer's Supplemental Tax Guide"}
        ],
        burden_holder="irs",
        irs_typical_position="""The IRS typically argues worker is employee when: (1) company
controls manner of work performance; (2) worker has no significant investment; (3) worker
performs services integral to business; (4) relationship is ongoing/exclusive; (5) company
provides tools, training, or benefits.""",
        counter_arguments=[
            "Worker controls how work is performed without company direction",
            "Significant investment in tools, equipment, or facilities",
            "Genuine opportunity for profit or loss based on management skill",
            "Services available to general market, not exclusive",
            "Section 530 safe harbor requirements satisfied",
            "Industry practice supports contractor treatment"
        ],
        appeals_strategy="""Worker classification cases are fact-intensive. Document actual
working relationship with specific examples of worker autonomy. If Section 530 applies,
assert it early. Consider requesting Technical Advice if novel industry issues exist.
At Appeals, emphasize control factors favoring contractor status.""",
        entity_scope=["all"],
        confidence="high"
    ),

    "conservation_easement": DoctrineBlock(
        topic="Conservation Easements - Syndicated Transactions",
        keywords=["conservation easement", "syndicated easement", "charitable deduction",
                  "land preservation", "facade easement", "listed transaction",
                  "easement audit", "qualified appraisal"],
        conclusion_template="""Conservation easement deductions require a qualified real property
interest donated to a qualified organization exclusively for conservation purposes. Syndicated
conservation easements—where deductions exceed 2.5x investment—are IRS-designated listed
transactions requiring disclosure. The IRS is actively litigating and disallowing these claims.""",
        reasoning_framework="""
CONSERVATION EASEMENT ANALYSIS:

1. STATUTORY REQUIREMENTS (§170(h))
   - Qualified real property interest (perpetual restriction)
   - Donation to qualified organization (§170(h)(3))
   - Exclusively for conservation purposes:
     * Outdoor recreation or education
     * Natural habitat protection
     * Open space preservation
     * Historic preservation
   - Perpetuity requirement

2. VALUATION REQUIREMENTS
   - Qualified appraisal by qualified appraiser
   - Before-and-after methodology
   - Highest and best use analysis
   - Appraisal must be contemporaneous
   - Form 8283 properly completed

3. SYNDICATED EASEMENT INDICATORS (Listed Transaction)
   Notice 2017-10 identifies:
   - Promotional materials promising tax benefits
   - Deduction-to-investment ratio exceeds 2.5x
   - Pass-through entity formed shortly before donation
   - Investors lack pre-existing relationship to property
   - Appraised value substantially exceeds purchase price

4. IRS ENFORCEMENT POSTURE
   - Listed transaction (mandatory Form 8886 disclosure)
   - Promoter penalties under §6700
   - Gross valuation misstatement penalties (40%)
   - Accuracy-related penalties (20%)
   - Substantial understatement penalties

5. CURRENT LITIGATION LANDSCAPE
   - IRS prevailing in most Tax Court cases
   - Penalties consistently upheld
   - Some circuit court challenges pending""",
        key_factors=[
            "Whether transaction meets syndicated easement definition",
            "Qualified appraisal with supportable methodology",
            "Conservation purpose clearly established",
            "Perpetuity and subordination requirements met",
            "Form 8886 filed if listed transaction"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §170(h)", "relevance": "Conservation contribution requirements"},
            {"authority": "Notice", "reference": "Notice 2017-10", "relevance": "Syndicated easements as listed transaction"},
            {"authority": "Reg", "reference": "Treas. Reg. §1.170A-14", "relevance": "Conservation contribution regulations"},
            {"authority": "Case", "reference": "Hewitt v. Commissioner, 21 F.4th 1336 (11th Cir. 2021)", "relevance": "Perpetuity requirement"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges syndicated easements on multiple grounds:
(1) valuation grossly inflated above economic reality; (2) appraisal methodology flawed;
(3) no genuine conservation purpose; (4) perpetuity requirements not satisfied; (5) listed
transaction not disclosed. Penalties are routinely asserted.""",
        counter_arguments=[
            "Transaction does not meet syndicated easement definition (ratio < 2.5x)",
            "Qualified appraisal follows recognized methodology",
            "Genuine conservation purpose documented with land trust",
            "Investor had pre-existing relationship to property",
            "Form 8886 properly filed if applicable"
        ],
        appeals_strategy="""Syndicated easement cases face significant headwinds. If claim was
made through syndicate, evaluate settlement posture early. If legitimate non-syndicated
easement, distinguish from listed transaction characteristics. Appraisal quality is critical—
prepare to defend methodology. Penalty abatement requires reasonable cause showing.""",
        entity_scope=["individual", "partnership", "llc", "s_corporation"],
        confidence="high"
    ),

    "micro_captive_insurance": DoctrineBlock(
        topic="Micro-Captive Insurance - §831(b) Elections",
        keywords=["micro captive", "captive insurance", "831b", "small insurance company",
                  "listed transaction", "captive audit", "risk distribution",
                  "risk shifting"],
        conclusion_template="""Micro-captive insurance arrangements under §831(b) allow small
insurance companies to elect to be taxed only on investment income. Abusive arrangements—
lacking genuine risk shifting and distribution—are IRS-designated listed transactions.
Legitimate captives require arm's-length premiums, adequate capitalization, and true insurance
characteristics.""",
        reasoning_framework="""
MICRO-CAPTIVE INSURANCE ANALYSIS:

1. LEGITIMATE CAPTIVE REQUIREMENTS
   - Genuine risk shifting (insured transfers risk)
   - Genuine risk distribution (captive pools risk)
   - Arm's-length premium determination
   - Adequate capitalization
   - Insurance company operations
   - Claims administration infrastructure

2. §831(b) ELECTION REQUIREMENTS
   - Net written premiums ≤ $2.65M (2024, indexed)
   - Valid insurance company
   - Must make annual election
   - Taxed only on investment income

3. LISTED TRANSACTION INDICATORS (Notice 2016-66)
   - Captive owned by insured or related parties
   - Coverage for implausible risks
   - Premiums lack actuarial support
   - Low or no claims history
   - Captive lacks genuine operations
   - Coverage duplicates commercial insurance
   - Policy terms inconsistent with commercial practice

4. IRS ENFORCEMENT FOCUS
   - Premium deductibility denied
   - Economic substance challenges
   - Accuracy-related penalties
   - Promoter investigations
   - Listed transaction penalties if not disclosed

5. REQUIRED INSURANCE CHARACTERISTICS
   (1) Risk shifting must occur
   (2) Risk distribution required
   (3) Insurance risk (not investment/business risk)
   (4) Premiums actuarially determined
   (5) Common notions of insurance satisfied""",
        key_factors=[
            "Actuarial support for premium amounts",
            "Genuine risk shifting and distribution",
            "Arms-length transaction characteristics",
            "Captive operational infrastructure",
            "Claims history and administration"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §831(b)", "relevance": "Small insurance company election"},
            {"authority": "Notice", "reference": "Notice 2016-66", "relevance": "Micro-captive listed transaction"},
            {"authority": "Case", "reference": "Avrahami v. Commissioner, 149 T.C. 144 (2017)", "relevance": "Captive insurance requirements"},
            {"authority": "Case", "reference": "Reserve Mechanical Corp. v. Commissioner, 34 F.4th 881 (10th Cir. 2022)", "relevance": "Risk distribution"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges micro-captives where: (1) premiums are not
actuarially supportable; (2) risk is circular (captive owned by insured); (3) no genuine risk
distribution exists; (4) claims history is absent or minimal; (5) coverage is for implausible
risks at inflated premiums. Economic substance doctrine frequently invoked.""",
        counter_arguments=[
            "Premiums determined by independent actuary using recognized methods",
            "Risk distribution achieved through unrelated party pooling",
            "Captive operates as genuine insurance company",
            "Claims paid consistent with policy terms",
            "Commercial insurance not available for covered risks"
        ],
        appeals_strategy="""Micro-captive cases are heavily litigated with IRS prevailing
frequently. Focus on actuarial support and risk distribution. If arrangement is abusive,
early settlement may be advisable. Document legitimate business purpose for captive
formation. Penalty abatement requires substantial authority or reasonable cause.""",
        entity_scope=["c_corporation", "s_corporation", "partnership", "llc"],
        confidence="high"
    ),

    "related_party_transactions": DoctrineBlock(
        topic="Related Party Transactions - §267 and §707(b)",
        keywords=["related party", "267", "707b", "controlled group",
                  "constructive ownership", "matching rule", "loss disallowance",
                  "below market", "family attribution"],
        conclusion_template="""Related party transactions are subject to special rules that may
defer or disallow losses, recharacterize gain, or adjust timing. Section 267 disallows losses
and defers deductions between related parties. Section 707(b) applies to partnerships and
partners. Constructive ownership rules expand the definition of related parties.""",
        reasoning_framework="""
RELATED PARTY ANALYSIS:

1. §267 LOSS DISALLOWANCE
   Related parties include:
   - Family members (siblings, spouse, ancestors, descendants)
   - Individual and >50% owned corporation
   - Corporations in same controlled group (>50%)
   - Grantor and fiduciary of trust
   - Various trust, estate, and beneficiary relationships

   Consequences:
   - Loss on sale disallowed (transferee gets basis adjustment)
   - Accrued expense/interest deduction deferred until paid
   - Ordinary income on certain depreciable property sales

2. §707(b) PARTNERSHIP RULES
   Applies to:
   - Partner owning >50% (capital or profits)
   - Two partnerships with >50% common ownership

   Consequences:
   - Loss disallowed on sales
   - Gain ordinary if property not capital in buyer's hands

3. CONSTRUCTIVE OWNERSHIP (§267(c))
   - Stock owned by family attributed to individual
   - Stock owned by entity attributed to owners
   - Option to acquire treated as ownership
   - Circular attribution rules apply

4. §482 AUTHORITY
   - IRS may reallocate income/deductions
   - Arm's-length standard applies
   - Requires commonly controlled entities
   - Penalties for transfer pricing adjustments""",
        key_factors=[
            "Identification of all related parties",
            "Constructive ownership analysis",
            "Arm's-length pricing documentation",
            "Timing of accrued expenses vs payment",
            "Character of gain on depreciable property"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §267", "relevance": "Related party loss and expense rules"},
            {"authority": "IRC", "reference": "IRC §707(b)", "relevance": "Partnership related party rules"},
            {"authority": "IRC", "reference": "IRC §482", "relevance": "Allocation of income/deductions"},
            {"authority": "IRC", "reference": "IRC §267(c)", "relevance": "Constructive ownership rules"}
        ],
        burden_holder="irs",
        irs_typical_position="""The IRS examines related party transactions for: (1) disallowed
losses on sales between related parties; (2) deferred deductions for accrued but unpaid
expenses; (3) ordinary income treatment on depreciable property; (4) §482 reallocation
authority for non-arm's-length pricing; (5) constructive ownership expanding related party
definitions.""",
        counter_arguments=[
            "Parties are not related under statutory definitions",
            "Constructive ownership rules do not apply to transaction",
            "Transaction was at arm's length with contemporaneous documentation",
            "Accrued expenses paid within required time period",
            "Loss disallowance rule inapplicable to transaction type"
        ],
        appeals_strategy="""Related party issues often turn on factual ownership analysis.
Document constructive ownership conclusions contemporaneously. For pricing disputes, arm's-
length comparables are essential. If loss disallowed, preserve transferee's basis step-up
position for future recognition.""",
        entity_scope=["all"],
        confidence="high"
    ),

    "partnership_allocations": DoctrineBlock(
        topic="Partnership Special Allocations - §704(b)",
        keywords=["special allocation", "704b", "substantial economic effect",
                  "partnership allocation", "capital account", "deficit restoration",
                  "qio", "targeted allocation"],
        conclusion_template="""Partnership allocations must have substantial economic effect under
§704(b) or be reallocated according to partners' interests in the partnership. Substantial
economic effect requires proper capital account maintenance, liquidation according to capital
accounts, and either deficit restoration obligations or qualified income offsets.""",
        reasoning_framework="""
PARTNERSHIP ALLOCATION ANALYSIS:

1. SUBSTANTIAL ECONOMIC EFFECT TEST

   ECONOMIC EFFECT (all three required):
   (1) Capital accounts maintained per §704(b) regulations
   (2) Liquidating distributions per positive capital accounts
   (3) Deficit restoration obligation OR qualified income offset

   SUBSTANTIALITY:
   - Reasonable possibility allocation affects dollar amounts
   - Not tax avoidance with offsetting allocations
   - Shifting and transitory allocation tests

2. CAPITAL ACCOUNT MAINTENANCE
   - Increase: contributions, allocated income
   - Decrease: distributions, allocated losses
   - Revaluation events properly reflected
   - Must follow regulatory book/tax differences

3. SAFE HARBORS AND ALTERNATIVES
   - Primary test: deficit restoration
   - Alternative: qualified income offset (QIO)
   - Allocations of nonrecourse deductions: special rules
   - Partner's interest in partnership: fallback

4. COMMON AUDIT ISSUES
   - Capital accounts not properly maintained
   - Liquidation not following capital accounts
   - No deficit restoration or QIO
   - Shifting allocations lacking substantiality
   - Nonrecourse deduction allocations invalid

5. CONSEQUENCES OF FAILED ALLOCATIONS
   - Reallocation per partners' interests
   - Often results in greater taxable income to limited partners
   - May affect outside basis calculations
   - Can cascade through multiple years""",
        key_factors=[
            "Capital accounts maintained under §704(b) regulations",
            "Liquidation provision follows capital accounts",
            "Deficit restoration obligation or QIO exists",
            "Substantiality requirement satisfied",
            "Nonrecourse deduction allocations properly made"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §704(b)", "relevance": "Allocation rules"},
            {"authority": "Reg", "reference": "Treas. Reg. §1.704-1(b)(2)", "relevance": "Economic effect regulations"},
            {"authority": "Reg", "reference": "Treas. Reg. §1.704-2", "relevance": "Nonrecourse deduction rules"},
            {"authority": "Case", "reference": "Orrisch v. Commissioner, 55 T.C. 395 (1970)", "relevance": "Partner's interest standard"}
        ],
        burden_holder="irs",
        irs_typical_position="""The IRS challenges allocations where: (1) capital accounts are
not properly maintained; (2) liquidating distributions do not follow capital accounts;
(3) no deficit restoration or qualified income offset exists; (4) allocations are
transitory or shifting without economic substance; (5) partnership agreement does not
reflect actual economic arrangement.""",
        counter_arguments=[
            "Capital accounts maintained in accordance with §704(b) regulations",
            "Partnership agreement requires liquidation per capital accounts",
            "Deficit restoration obligations are legally enforceable",
            "Qualified income offset provision meets regulatory requirements",
            "Allocations have genuine economic substance beyond tax effects"
        ],
        appeals_strategy="""Partnership allocation cases are technical. Document capital
account maintenance with annual calculations. If agreement is ambiguous, partnership
practices may establish economic effect. For failed allocations, prepare partners' interest
analysis as fallback position.""",
        entity_scope=["partnership", "llc"],
        confidence="high"
    ),

    "wash_sale": DoctrineBlock(
        topic="Wash Sale Rules - §1091",
        keywords=["wash sale", "1091", "substantially identical", "loss disallowance",
                  "30 day rule", "replacement shares", "basis adjustment"],
        conclusion_template="""The wash sale rule disallows loss deductions when substantially
identical securities are acquired within 30 days before or after the sale. The disallowed loss
is added to the basis of the replacement securities. The rule applies to stocks, securities,
and options, but not to commodities or forex.""",
        reasoning_framework="""
WASH SALE ANALYSIS:

1. WASH SALE RULE (§1091)
   Loss disallowed if:
   - Substantially identical stock/securities acquired
   - Within 30 days BEFORE or AFTER the sale at a loss
   - Applies to purchases, contracts, or options

2. SUBSTANTIALLY IDENTICAL
   - Same corporation stock: identical
   - Preferred vs common: generally not identical
   - Bonds with same terms: may be identical
   - Mutual funds tracking same index: may be identical
   - Options on same stock: substantially identical

   NOT substantially identical:
   - Stock of different corporations (even same industry)
   - Bonds with materially different terms
   - Funds with different objectives/compositions

3. 61-DAY WINDOW
   - 30 days before sale
   - Day of sale
   - 30 days after sale
   - Acquisition anywhere in window triggers rule

4. CONSEQUENCES
   - Loss disallowed (deferred, not permanent)
   - Disallowed loss added to replacement basis
   - Holding period of old shares tacks
   - Applies across accounts (IRA, taxable, spouse)

5. SPECIAL SITUATIONS
   - Sales and purchases in IRA: may permanently disallow
   - Short sales: acquisition starts holding period
   - Options exercise: may trigger wash sale
   - Dividend reinvestment: can trigger rule""",
        key_factors=[
            "Whether replacement securities are substantially identical",
            "Timing of acquisition relative to loss sale",
            "Basis adjustment to replacement securities",
            "Holding period tacking",
            "Cross-account applications (IRA, spouse)"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §1091", "relevance": "Wash sale rule"},
            {"authority": "Reg", "reference": "Treas. Reg. §1.1091-1", "relevance": "Wash sale regulations"},
            {"authority": "Rev Rul", "reference": "Rev. Rul. 2008-5", "relevance": "IRA wash sale treatment"},
            {"authority": "Pub", "reference": "IRS Pub 550", "relevance": "Investment income guidance"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS applies wash sale rules to: (1) obvious repurchases of
same security; (2) purchases in related accounts (spouse, IRA); (3) options on same
underlying securities; (4) substantially identical funds or ETFs; (5) automatic dividend
reinvestment within the 61-day window.""",
        counter_arguments=[
            "Replacement securities are not substantially identical",
            "Acquisition occurred outside 61-day window",
            "Disallowed loss properly added to replacement basis",
            "Different fund with materially different portfolio",
            "Stock of different corporation despite same industry"
        ],
        appeals_strategy="""Wash sale issues often arise from broker reporting discrepancies.
Verify 1099-B wash sale adjustments against actual trading records. Document why securities
are not substantially identical. Ensure basis adjustments are properly tracked across tax
years.""",
        entity_scope=["individual", "trust", "estate"],
        confidence="high"
    ),

    "net_operating_loss": DoctrineBlock(
        topic="Net Operating Losses - §172",
        keywords=["net operating loss", "nol", "loss carryforward", "loss carryback",
                  "172", "80 percent limitation", "cares act nol", "excess business loss"],
        conclusion_template="""Net operating losses (NOLs) generally may only be carried forward
indefinitely and are limited to 80% of taxable income (post-2017 NOLs). Pre-2018 NOLs may be
carried back 2 years and forward 20 years without the 80% limitation. Special rules applied
for 2018-2020 under the CARES Act.""",
        reasoning_framework="""
NET OPERATING LOSS ANALYSIS:

1. NOL CALCULATION (§172(d))
   Start with negative taxable income, then:
   - Add back: NOL deduction from other years
   - Add back: Capital loss in excess of capital gains
   - Add back: §199A deduction
   - Add back: Non-business deductions exceeding non-business income

   Result: Net Operating Loss

2. CARRYOVER RULES BY PERIOD

   Pre-2018 NOLs:
   - 2-year carryback (waiver available)
   - 20-year carryforward
   - No taxable income limitation

   Post-2017 NOLs (general rule):
   - No carryback (exceptions exist)
   - Indefinite carryforward
   - Limited to 80% of taxable income

   CARES Act (2018-2020 NOLs):
   - 5-year carryback allowed
   - 80% limit suspended for these years
   - Could generate AMT credit carryforwards

3. ORDERING RULES
   - Pre-2018 NOLs used first
   - Then post-2017 NOLs chronologically
   - 80% limit applies after pre-2018 NOLs exhausted

4. EXCESS BUSINESS LOSS LIMITATION (§461(l))
   - Limits business losses for non-corporate taxpayers
   - Excess becomes NOL carryforward
   - $289,000 single / $578,000 MFJ (2024)
   - Applies before NOL calculation""",
        key_factors=[
            "Year in which NOL arose (pre-2018, 2018-2020, post-2020)",
            "Whether 80% limitation applies",
            "Carryback election or waiver",
            "Ordering of multiple-year NOLs",
            "Excess business loss limitation impact"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §172", "relevance": "NOL deduction rules"},
            {"authority": "IRC", "reference": "IRC §461(l)", "relevance": "Excess business loss limitation"},
            {"authority": "CARES Act", "reference": "CARES Act §2303", "relevance": "NOL modifications 2018-2020"},
            {"authority": "Rev Proc", "reference": "Rev. Proc. 2020-24", "relevance": "CARES Act NOL procedures"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS examines NOL claims for: (1) proper calculation under
§172(d) modification rules; (2) correct application of 80% limitation; (3) proper ordering
of multi-year NOLs; (4) excess business loss limitation compliance; (5) carryback claims
to closed years reopening assessments.""",
        counter_arguments=[
            "NOL calculation follows §172(d) modification requirements",
            "80% limitation correctly applied or inapplicable to NOL year",
            "Carryback election or waiver properly made",
            "Excess business loss limitation properly computed",
            "Ordering of NOLs follows statutory requirements"
        ],
        appeals_strategy="""NOL issues often involve computational disputes. Prepare year-by-
year NOL schedule showing origin, carryover, and utilization. For CARES Act carrybacks,
document proper election procedures. If AMT implications exist, prepare integrated regular
tax and AMT analysis.""",
        entity_scope=["all"],
        confidence="high"
    ),

    "shareholder_basis": DoctrineBlock(
        topic="S-Corporation Shareholder Basis - Loss Limitations",
        keywords=["shareholder basis", "s corp basis", "stock basis", "debt basis",
                  "loss limitation", "aaa", "distribution ordering", "basis schedule"],
        conclusion_template="""S-corporation shareholders may only deduct losses to the extent of
their basis in stock and debt. Basis increases for income and contributions, decreases for
distributions and losses. Loans from the shareholder (not third parties) create debt basis.
Losses exceeding basis are suspended and carried forward indefinitely.""",
        reasoning_framework="""
S-CORP SHAREHOLDER BASIS ANALYSIS:

1. STOCK BASIS CALCULATION
   Increases:
   + Capital contributions
   + Share of income items (including tax-exempt)
   + Share of excess depletion

   Decreases (in order):
   - Non-dividend distributions
   - Non-deductible expenses
   - Depletion deduction
   - Share of loss/deduction items

   Stock basis cannot go below zero

2. DEBT BASIS REQUIREMENTS
   - Direct loan FROM shareholder TO corporation
   - Shareholder must have genuine economic outlay
   - Guarantees alone do NOT create basis
   - Back-to-back loans: substance over form
   - Related party loans: heightened scrutiny

3. LOSS DEDUCTION ORDERING (§1366(d))
   (1) Losses first reduce stock basis to zero
   (2) Then reduce debt basis to zero
   (3) Excess losses suspended and carried forward

4. BASIS RESTORATION
   - Income items first restore debt basis
   - Then restore stock basis
   - Suspended losses deducted when basis created

5. DISTRIBUTION ORDERING (§1368)
   From AAA (accumulated adjustments account):
   - Tax-free to extent of stock basis
   - Then from E&P (if any) as dividend
   - Then return of capital reducing basis
   - Then capital gain when basis exhausted""",
        key_factors=[
            "Annual stock basis calculation maintained",
            "Debt basis supported by actual shareholder loans",
            "Loss limitation computed before deduction",
            "Distribution ordering rules applied",
            "Suspended loss carryforward tracked"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §1366(d)", "relevance": "Shareholder loss limitation"},
            {"authority": "IRC", "reference": "IRC §1367", "relevance": "Basis adjustments"},
            {"authority": "IRC", "reference": "IRC §1368", "relevance": "Distribution rules"},
            {"authority": "Reg", "reference": "Treas. Reg. §1.1366-2", "relevance": "Loss limitation regulations"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges S-corp losses where: (1) shareholder cannot
substantiate sufficient stock basis; (2) debt basis claimed from guarantees rather than
actual loans; (3) third-party loans lack back-to-back substance; (4) distributions exceed
basis creating unreported gain; (5) basis schedules not maintained annually.""",
        counter_arguments=[
            "Stock basis schedule maintained and substantiated annually",
            "Debt basis from actual economic outlay, not mere guarantee",
            "Loan documentation evidences genuine shareholder obligation",
            "Losses properly suspended when basis exceeded",
            "Distributions correctly ordered under §1368"
        ],
        appeals_strategy="""Shareholder basis is frequently disputed. Maintain contemporaneous
basis schedules updated annually. For debt basis claims, document actual funds flow from
shareholder. Guarantees alone are insufficient per Maloof line of cases. Reconstruct basis
from formation if records incomplete.""",
        entity_scope=["s_corporation"],
        confidence="high"
    ),

    "self_employment_tax": DoctrineBlock(
        topic="Self-Employment Tax - §1401",
        keywords=["self employment tax", "se tax", "schedule se", "1401",
                  "seca", "limited partner exception", "llc member",
                  "guaranteed payment"],
        conclusion_template="""Self-employment tax applies to net earnings from self-employment,
including sole proprietorship income, general partnership income, and LLC member distributive
shares (unless limited partner exception applies). The tax is 15.3% (12.4% Social Security
up to wage base, 2.9% Medicare with no cap). A deduction for 50% of SE tax is allowed.""",
        reasoning_framework="""
SELF-EMPLOYMENT TAX ANALYSIS:

1. SUBJECT TO SE TAX
   - Sole proprietorship net income
   - General partner distributive share
   - LLC member distributive share (generally)
   - Guaranteed payments for services
   - Director fees and other self-employment income

2. NOT SUBJECT TO SE TAX
   - Limited partner distributive share (exception)
   - Rental income (unless real estate dealer)
   - S-corporation distributive share
   - Dividends, interest, capital gains
   - Wages (subject to FICA instead)

3. LIMITED PARTNER EXCEPTION (§1402(a)(13))
   Exception applies if:
   - Individual is limited partner
   - Income is distributive share (not guaranteed payment)
   - Genuine limited partner status (no management)

   Note: LLC members generally NOT limited partners
   Proposed regulations (1997): service partners subject to SE tax

4. CALCULATION
   Net SE income × 92.35% = SE tax base
   SE tax = 15.3% up to wage base + 2.9% on excess
   Additional 0.9% Medicare on income over $200K/$250K
   Deduction: 50% of SE tax (above-the-line)

5. COMMON ISSUES
   - LLC members claiming limited partner exception
   - Mischaracterizing income as rental
   - S-corp reasonable compensation circumvention
   - Failure to include guaranteed payments""",
        key_factors=[
            "Whether income is from trade or business",
            "Limited partner exception applicability",
            "Guaranteed payments separately identified",
            "SE tax base correctly calculated",
            "Additional Medicare tax on high earners"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §1401", "relevance": "Self-employment tax rates"},
            {"authority": "IRC", "reference": "IRC §1402", "relevance": "Net earnings from self-employment"},
            {"authority": "IRC", "reference": "IRC §1402(a)(13)", "relevance": "Limited partner exception"},
            {"authority": "Prop Reg", "reference": "Prop. Reg. §1.1402(a)-2", "relevance": "LLC member treatment"}
        ],
        burden_holder="irs",
        irs_typical_position="""The IRS challenges SE tax positions where: (1) LLC members
claim limited partner exception inappropriately; (2) active partners mischaracterize income
as rental; (3) guaranteed payments not separately reported; (4) S-corp distributions used
to avoid reasonable compensation/SE tax; (5) SE income understated or omitted.""",
        counter_arguments=[
            "Limited partner exception applies - no participation in management",
            "Income is genuine rental, not disguised self-employment",
            "Guaranteed payments properly identified and taxed",
            "LLC operating agreement limits member's role to capital contribution",
            "S-corp reasonable compensation analysis supports salary level"
        ],
        appeals_strategy="""LLC member SE tax treatment remains unsettled in absence of final
regulations. Assert limited partner exception if member genuinely does not participate in
management. Document capital vs. service nature of interest. S-corp reasonable compensation
arguments may apply by analogy.""",
        entity_scope=["sole_proprietorship", "partnership", "llc"],
        confidence="high"
    ),

    # =========================================================================
    # HIGH-STAKES PROFESSIONAL DOCTRINE - SENIOR PARTNER JUDGMENT
    # =========================================================================

    "hobby_loss": DoctrineBlock(
        topic="Hobby Loss - §183 Activity Not Engaged for Profit",
        keywords=["hobby loss", "183", "not for profit", "hobby farm", "horse breeding",
                  "art collecting", "side business losses", "profit motive",
                  "nine factor test", "presumption of profit"],
        conclusion_template="""An activity is presumed for profit if it generates profit in 3 of
5 consecutive years (2 of 7 for horse breeding/racing). If the presumption does not apply,
§183 limits deductions to gross income from the activity. The burden of proving profit motive
shifts to the taxpayer when the presumption is not met. Deductions disallowed under §183
cannot create or increase a loss.""",
        reasoning_framework="""
PROFIT MOTIVE ANALYSIS — DECISION FRAMEWORK FOR RETURN SIGNING:

1. PRESUMPTION STATUS (Critical First Step)
   □ 3 of 5 years profitable? → Presumption applies, burden on IRS
   □ 2 of 7 years for horses? → Same analysis
   □ Neither met? → Burden on taxpayer, heightened documentation required

2. NINE-FACTOR TEST (Treas. Reg. §1.183-2(b))
   FACTOR                           WEIGHT     DOCUMENTATION REQUIRED
   ───────────────────────────────────────────────────────────────────
   (1) Businesslike manner           HIGH      Business plan, books, changes based on P&L
   (2) Taxpayer expertise            MEDIUM    Training, advisors, study of methods
   (3) Time/effort expended          MEDIUM    Time logs, substantial personal effort
   (4) Asset appreciation expected   LOW       Appraisals, market analysis
   (5) Success in similar activities HIGH      Prior profitable ventures in field
   (6) History of income/losses      HIGH      Startup phase explanation, trend to profit
   (7) Occasional profits amount     MEDIUM    Ratio of profits to losses, investment size
   (8) Taxpayer financial status     NEGATIVE  Wealth enables loss absorption = against
   (9) Personal pleasure/recreation  NEGATIVE  Enjoyment element = factor against

3. POSITION DEFENSIBILITY MATRIX
   SCENARIO                          ACTION
   ───────────────────────────────────────────────────────────────────
   Presumption met                   Sign return, standard documentation
   4-5 factors favorable             Sign with disclosure statement
   3 factors favorable               Sign only with written profit plan, expert opinion
   <3 factors favorable              DO NOT sign unless losses minimal
   High personal pleasure element    Requires extraordinary profit documentation

4. EXAMINER FOCUS AREAS
   - Years of consistent losses without adjustment
   - Lifestyle activities (horses, boats, art, travel)
   - High-income taxpayer with loss-generating hobby
   - Minimal time devoted, professional managers
   - No business plan or changes in operations""",
        key_factors=[
            "Presumption status: 3 of 5 or 2 of 7 years profitable",
            "Written business plan with profit projections",
            "Evidence of businesslike conduct (books, advisors, adjustments)",
            "Time and effort documentation",
            "Explanation for losses (startup phase, market conditions)"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §183", "relevance": "Activity not engaged for profit"},
            {"authority": "Reg", "reference": "Treas. Reg. §1.183-2(b)", "relevance": "Nine-factor test"},
            {"authority": "IRC", "reference": "IRC §183(d)", "relevance": "Presumption of profit"},
            {"authority": "Case", "reference": "Dreicer v. Commissioner, 78 T.C. 642 (1982)", "relevance": "Hobby loss analysis"}
        ],
        burden_holder="depends",
        irs_typical_position="""The IRS challenges activities with: (1) history of consistent
losses; (2) high recreation/pleasure element; (3) wealthy taxpayer absorbing losses;
(4) minimal operational changes despite losses; (5) no written business plan. Examiner
will focus on lifestyle assets and personal use indicators.""",
        counter_arguments=[
            "Presumption applies: profit in 3 of 5 years, burden on IRS",
            "Business plan documents specific path to profitability",
            "Operational changes made in response to losses",
            "Time logs demonstrate substantial personal effort",
            "Expert advisors engaged to improve operations",
            "Startup phase losses expected in this industry"
        ],
        appeals_strategy="""If presumption met, assert burden on IRS and demand specific
factor-by-factor rebuttal. If presumption not met, present comprehensive nine-factor
analysis with emphasis on businesslike conduct. Request Appeals conference before
agreeing to any adjustment. Consider protective disclosure on original return.""",
        entity_scope=["sole_proprietorship", "s_corporation", "partnership", "llc"],
        confidence="high"
    ),

    "passive_activity_loss": DoctrineBlock(
        topic="Passive Activity Loss Limitations - §469",
        keywords=["passive activity", "469", "material participation", "rental activity",
                  "passive loss", "at risk", "grouping", "real estate professional",
                  "seven tests", "500 hours"],
        conclusion_template="""Passive activity losses can only offset passive activity income.
A taxpayer materially participates in an activity if they meet one of seven tests, most
commonly: 500+ hours participation, substantially all participation, or 100+ hours when no
one else participates more. Real estate professionals may treat rental activities as
non-passive if they meet the 750-hour and more-than-half tests.""",
        reasoning_framework="""
MATERIAL PARTICIPATION — DECISION FRAMEWORK:

1. THE SEVEN TESTS (Temp. Reg. §1.469-5T)
   TEST   DESCRIPTION                                    DOCUMENTATION
   ─────────────────────────────────────────────────────────────────────────
   (1)    500+ hours participation                       Time logs, calendars
   (2)    Substantially all participation                Activity records
   (3)    100+ hours & not less than any other person    Comparative analysis
   (4)    Significant participation activities >500 hrs  Aggregation of SPAs
   (5)    Material participation in 5 of 10 prior years  Historical records
   (6)    Personal service activity, 3 prior years       Historical records
   (7)    Facts and circumstances (100+ hours required)  Detailed narrative

2. REAL ESTATE PROFESSIONAL EXCEPTION (§469(c)(7))
   BOTH requirements must be met:
   □ >750 hours in real property trades/businesses
   □ More than 50% of personal services in real property trades

   THEN: Each rental separately tested for material participation
   OR: Make grouping election to combine rentals

3. GROUPING STRATEGIES (Reg. §1.469-4)
   □ Similar activities may be grouped as single activity
   □ Election is binding, disclosed on return
   □ Grouping can be critical to meet 500-hour test
   □ Rental and non-rental CANNOT generally be grouped
   □ Consider grouping before year-end, document basis

4. POSITION DEFENSIBILITY
   DOCUMENTATION STANDARD          SIGNING COMFORT
   ─────────────────────────────────────────────────────────────────────────
   Contemporaneous time logs       HIGH - sign with confidence
   Reconstructed logs with support MEDIUM - sign with backup documentation
   Estimates without support       LOW - require engagement letter disclaimer
   No documentation                DO NOT SIGN claiming non-passive treatment

5. EXAMINER FOCUS AREAS
   - Time log authenticity and specificity
   - Multiple activities with 500+ hours each (implausible)
   - Real estate professional status for W-2 employees
   - Grouping elections not properly disclosed""",
        key_factors=[
            "Contemporaneous time logs with specific activities",
            "Which of the seven tests is met and documentation for it",
            "Real estate professional 750-hour and 50% tests",
            "Grouping election disclosure on timely filed return",
            "Comparative hours analysis if using test (3)"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §469", "relevance": "Passive activity loss limitations"},
            {"authority": "Temp Reg", "reference": "Temp. Reg. §1.469-5T", "relevance": "Material participation tests"},
            {"authority": "IRC", "reference": "IRC §469(c)(7)", "relevance": "Real estate professional exception"},
            {"authority": "Reg", "reference": "Reg. §1.469-4", "relevance": "Grouping of activities"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges material participation when: (1) time logs
appear reconstructed or lack specificity; (2) claimed hours are implausible given other
employment; (3) real estate professional claimed by W-2 employee spouse; (4) grouping
election not properly disclosed; (5) no contemporaneous documentation exists.""",
        counter_arguments=[
            "Contemporaneous time logs document all participation",
            "500-hour test clearly met with margin",
            "Real estate professional status documented with time records",
            "Grouping election properly disclosed on timely filed return",
            "Facts and circumstances support material participation even if hours borderline"
        ],
        appeals_strategy="""Burden is on taxpayer. If time logs are weak, consider conceding
or proposing partial adjustment. If documentation is strong, request Appeals sustain
position fully. Real estate professional cases often turn on credibility of time records.
Offer to provide additional contemporaneous evidence (calendars, emails, travel records).""",
        entity_scope=["individual", "partnership", "s_corporation", "llc"],
        confidence="high"
    ),

    "at_risk_limitations": DoctrineBlock(
        topic="At-Risk Limitations - §465",
        keywords=["at risk", "465", "nonrecourse debt", "basis limitation",
                  "at risk basis", "loss limitation", "qualified nonrecourse financing",
                  "recourse debt", "personal liability"],
        conclusion_template="""A taxpayer may only deduct losses from an activity to the extent
they are "at risk" in the activity. At-risk amount includes: (1) cash contributed, (2) adjusted
basis of property contributed, (3) amounts borrowed for which taxpayer is personally liable,
and (4) amounts borrowed secured by property not used in the activity. Nonrecourse debt is
generally NOT included unless it qualifies under the real estate exception.""",
        reasoning_framework="""
AT-RISK ANALYSIS — LOSS DEDUCTIBILITY FRAMEWORK:

1. AT-RISK AMOUNT CALCULATION
   Component                          Treatment
   ─────────────────────────────────────────────────────────────────────────
   Cash contributed                   Included
   Basis of property contributed      Included (FMV if FMV < basis)
   Recourse debt (personal liability) Included
   Nonrecourse debt (general)         EXCLUDED
   Qualified nonrecourse financing    Included (real estate only)

2. QUALIFIED NONRECOURSE FINANCING (§465(b)(6))
   ALL of the following required:
   □ Borrowed from qualified lender (not seller or related party)
   □ Secured by real property used in activity
   □ No personal liability to taxpayer
   □ No convertible debt or equity kickers

   IF all met: Treat as amount at risk for real estate activities

3. LOSS ORDERING AND SUSPENDED LOSSES
   Step 1: Determine current year loss
   Step 2: Apply at-risk limitation (this step)
   Step 3: Apply passive activity loss rules (§469)
   Step 4: Apply excess business loss rules (§461(l))

   Suspended losses: Carry forward indefinitely

4. BASIS VS AT-RISK — CRITICAL DISTINCTION
   - Basis ≠ At-Risk Amount
   - Basis allows loss allocation; at-risk allows deduction
   - Partner may have basis (including share of partnership debt)
     but NOT be at risk if debt is nonrecourse

5. DOCUMENTATION REQUIREMENTS
   □ Annual at-risk calculation maintained
   □ Loan documents reviewed for recourse status
   □ Lender qualification confirmed
   □ Security interest documented
   □ No side agreements eliminating risk""",
        key_factors=[
            "Personal liability for debts (recourse vs nonrecourse)",
            "Qualified lender status for nonrecourse real estate debt",
            "Security interest limited to activity property",
            "No related party lending arrangements",
            "Annual at-risk basis tracking schedule"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §465", "relevance": "At-risk limitations"},
            {"authority": "IRC", "reference": "IRC §465(b)(6)", "relevance": "Qualified nonrecourse financing"},
            {"authority": "Reg", "reference": "Temp. Reg. §1.465-1T through 1.465-27", "relevance": "At-risk regulations"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges at-risk positions when: (1) nonrecourse debt
included without qualified financing analysis; (2) related party debt treated as at-risk;
(3) circular arrangements eliminate actual risk; (4) guarantee arrangements are illusory;
(5) no annual at-risk tracking maintained.""",
        counter_arguments=[
            "Debt is recourse with documented personal liability",
            "Qualified nonrecourse financing requirements fully met",
            "Lender is unrelated qualified lender",
            "At-risk calculation maintained annually",
            "No side agreements reduce actual economic risk"
        ],
        appeals_strategy="""At-risk challenges often involve loan document interpretation.
Request Appeals review actual loan documents, not just characterizations. If debt is
borderline, consider whether partial adjustment is defensible. Document economic substance
of risk assumption.""",
        entity_scope=["individual", "partnership", "s_corporation", "llc"],
        confidence="high"
    ),

    "section_1031_exchange": DoctrineBlock(
        topic="Like-Kind Exchange - §1031",
        keywords=["1031", "like kind exchange", "qualified intermediary", "boot",
                  "replacement property", "identification", "180 days",
                  "45 day rule", "reverse exchange", "deferred exchange"],
        conclusion_template="""No gain or loss is recognized on the exchange of property held for
productive use in trade or business or for investment if exchanged solely for property of
like kind also held for productive use or investment. Strict timing requirements apply:
identification within 45 days, completion within 180 days. Boot received triggers gain
recognition to the extent of boot or realized gain, whichever is less.""",
        reasoning_framework="""
1031 EXCHANGE — STRICT COMPLIANCE FRAMEWORK:

1. LIKE-KIND REQUIREMENT
   □ Real property for real property (post-TCJA: real estate only)
   □ Both properties held for business/investment use
   □ EXCLUDE: inventory, stock, partnership interests, personal use property

2. TIMING REQUIREMENTS — NO EXTENSIONS
   Day 0:   Relinquished property closes
   Day 45:  Identification deadline (midnight, no extensions)
   Day 180: Exchange completion deadline (or tax return due date if earlier)

   WARNING: These are absolute deadlines. Missing by one day = fully taxable.

3. IDENTIFICATION RULES (One must be satisfied)
   □ 3-Property Rule: Identify up to 3 properties regardless of value
   □ 200% Rule: Identify any number if aggregate FMV ≤ 200% of relinquished
   □ 95% Rule: Acquire 95% of identified value

   IDENTIFICATION MUST BE:
   - Written and signed
   - Delivered to QI or other party (not taxpayer's agent)
   - Unambiguous property description

4. BOOT RECOGNITION
   Boot includes:
   - Cash received (including debt relief in excess of debt assumed)
   - Non-like-kind property received

   Gain recognized = Lesser of:
   - Boot received, OR
   - Realized gain

   Strategy: Acquire equal or greater debt to avoid relief boot

5. QUALIFIED INTERMEDIARY REQUIREMENTS
   □ QI cannot be related party
   □ Written exchange agreement before closing
   □ QI holds funds (taxpayer cannot have actual/constructive receipt)
   □ Direct deeding permitted but funds through QI

6. POSITION DEFENSIBILITY
   ISSUE                             RISK LEVEL
   ─────────────────────────────────────────────────────────────────────────
   Missed 45-day identification      FATAL - fully taxable exchange
   Verbal identification only        HIGH - likely fatal
   QI is related party               HIGH - exchange fails
   Replacement held for resale       HIGH - not investment purpose
   Personal use of replacement       MEDIUM - partial disqualification""",
        key_factors=[
            "Written identification delivered within 45 days",
            "Exchange completed within 180 days",
            "Independent qualified intermediary used",
            "Boot calculation including debt relief",
            "Business/investment use documented for both properties"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §1031", "relevance": "Like-kind exchange nonrecognition"},
            {"authority": "Reg", "reference": "Treas. Reg. §1.1031(k)-1", "relevance": "Deferred exchange rules"},
            {"authority": "Reg", "reference": "Treas. Reg. §1.1031(a)-1", "relevance": "Like-kind property definition"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges 1031 exchanges when: (1) identification
requirements not strictly met; (2) QI is disqualified person; (3) taxpayer had actual or
constructive receipt of funds; (4) property held for resale not investment; (5) personal
use of replacement property; (6) documentation incomplete.""",
        counter_arguments=[
            "Written identification delivered within 45 days with proof of delivery",
            "Independent QI with no disqualifying relationship",
            "No actual or constructive receipt - funds controlled by QI only",
            "Both properties held for investment with documentation",
            "Boot properly calculated and gain recognized to extent required"
        ],
        appeals_strategy="""1031 challenges are often binary - either requirements met or not.
If timing requirements met, defend vigorously. If not met, little room for appeal.
Use purpose may be disputed - provide evidence of investment intent (rental history,
business use). QI independence can be documented with organizational charts.""",
        entity_scope=["individual", "sole_proprietorship", "partnership", "s_corporation", "c_corporation", "llc"],
        confidence="high"
    ),

    "cancellation_of_debt": DoctrineBlock(
        topic="Cancellation of Debt Income - §61/§108",
        keywords=["cancellation of debt", "cod income", "108", "insolvency",
                  "bankruptcy", "debt forgiveness", "1099-c", "qualified principal residence",
                  "qualified real property business", "form 982"],
        conclusion_template="""Cancellation of debt (COD) is generally includible in gross income
under §61(a)(11). However, §108 provides exclusions for: (1) bankruptcy, (2) insolvency up to
the amount of insolvency, (3) qualified farm indebtedness, (4) qualified real property business
debt, and (5) qualified principal residence debt (expired/limited). Excluded COD income
generally requires reduction of tax attributes under §108(b).""",
        reasoning_framework="""
CANCELLATION OF DEBT — ANALYSIS FRAMEWORK:

1. DETERMINE COD AMOUNT
   COD = Debt canceled - Amount paid (if any)

   Special rules:
   - Purchase price reduction: NO COD (purchase price adjustment)
   - Contested liability: NO COD until contest resolved
   - Related party acquisition: special rules apply

2. EXCLUSIONS — APPLY IN ORDER (§108)
   EXCLUSION                     ATTRIBUTE REDUCTION REQUIRED
   ─────────────────────────────────────────────────────────────────────────
   (1) Bankruptcy (Title 11)     Yes - in order specified
   (2) Insolvency                Yes - to extent of insolvency
   (3) Qualified farm debt       Yes - special rules
   (4) QRPBI (real property)     Reduce basis of depreciable RE only
   (5) QPRI (principal res)      No - but expired/limited

3. INSOLVENCY CALCULATION — CRITICAL
   Insolvency = Liabilities exceed FMV of assets

   INCLUDE in assets:
   - All assets, including exempt assets (IRA, pension)
   - Interest in partnerships/S-corps at FMV
   - Contingent rights if ascertainable value

   INCLUDE in liabilities:
   - All liabilities, including contingent if probable
   - Nonrecourse debt to extent of securing asset value

   Exclusion limited to amount of insolvency IMMEDIATELY BEFORE discharge

4. ATTRIBUTE REDUCTION ORDER (§108(b)(2))
   Reduce in order:
   (1) NOLs and NOL carryovers
   (2) General business credit carryovers
   (3) Minimum tax credit
   (4) Capital losses and carryovers
   (5) Basis of property
   (6) Passive activity losses
   (7) Foreign tax credits

   OR: Elect to reduce basis of depreciable property first (§108(b)(5))

5. FORM 982 REQUIREMENTS
   □ File Form 982 with return claiming exclusion
   □ Attach insolvency worksheet if applicable
   □ Track attribute reductions in subsequent years
   □ Document FMV of assets at discharge date""",
        key_factors=[
            "Amount of debt canceled and timing",
            "Insolvency calculation immediately before discharge",
            "FMV of all assets including exempt assets",
            "Order of attribute reduction applied",
            "Form 982 filed with exclusion election"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §61(a)(11)", "relevance": "COD income inclusion"},
            {"authority": "IRC", "reference": "IRC §108", "relevance": "COD exclusions"},
            {"authority": "IRC", "reference": "IRC §108(b)", "relevance": "Attribute reduction"},
            {"authority": "Reg", "reference": "Treas. Reg. §1.108-1 through 1.108-9", "relevance": "COD regulations"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges COD exclusions when: (1) insolvency
calculation overstates liabilities or understates assets; (2) exempt assets not included
in insolvency analysis; (3) Form 982 not filed; (4) attribute reduction not properly
tracked; (5) FMV of assets at discharge not documented.""",
        counter_arguments=[
            "Insolvency calculation includes all assets at FMV",
            "Documentation supports liability amounts",
            "Form 982 timely filed with return",
            "Attribute reduction properly tracked and applied",
            "Appraisal or other FMV evidence supports asset values"
        ],
        appeals_strategy="""Insolvency cases often turn on asset valuation. Obtain appraisals
or market comparables for major assets. Document all liabilities including contingent
claims. If IRS disputes insolvency, request Appeals consider whether difference is material.
Partial insolvency exclusion may be defensible even if fully insolvent status not proven.""",
        entity_scope=["individual", "partnership", "s_corporation", "c_corporation", "llc"],
        confidence="high"
    ),

    "substantial_understatement_penalty": DoctrineBlock(
        topic="Substantial Understatement Penalty - §6662",
        keywords=["substantial understatement", "6662", "accuracy penalty", "disclosure",
                  "reasonable basis", "substantial authority", "form 8275",
                  "penalty protection", "reasonable cause"],
        conclusion_template="""The §6662 accuracy-related penalty is 20% of the underpayment
attributable to substantial understatement (greater of 10% of tax required or $5,000).
Understatement is reduced by positions with substantial authority OR positions with
reasonable basis if adequately disclosed on Form 8275. The penalty is waived for
reasonable cause and good faith.""",
        reasoning_framework="""
PENALTY PROTECTION — DECISION FRAMEWORK:

1. PENALTY THRESHOLDS
   Substantial understatement = Greater of:
   - 10% of tax required to be shown, OR
   - $5,000 ($10,000 for corporations)

   Tax shelter items: Lower thresholds, disclosure protection limited

2. AUTHORITY HIERARCHY (From strongest to weakest)
   LEVEL              PROTECTION                   DISCLOSURE REQUIRED?
   ─────────────────────────────────────────────────────────────────────────
   More-likely-than-not (>50%)  Full protection          No
   Substantial authority        Full protection          No
   Reasonable basis             Protection if disclosed  Yes (Form 8275)
   Below reasonable basis       NO protection            Disclosure insufficient

3. SUBSTANTIAL AUTHORITY ANALYSIS
   Weight of authorities:
   - IRC, regulations, revenue rulings, court cases = Direct authority
   - Legislative history, IRS notices, PLRs = Secondary authority
   - Treatises, articles = Little weight

   Analysis: Do favorable authorities outweigh unfavorable considering:
   - Relevance of authorities
   - Persuasiveness of reasoning
   - Strength of adverse authorities

4. DISCLOSURE STRATEGY
   WHEN TO DISCLOSE (Form 8275/8275-R):
   □ Position has reasonable basis but not substantial authority
   □ Position contrary to regulation (use 8275-R)
   □ Aggressive position where examination likely
   □ Material item with litigation potential

   DISCLOSURE MUST:
   - Identify specific provision and position
   - Describe relevant facts
   - Explain taxpayer's legal basis
   - Be on timely filed return (including extensions)

5. REASONABLE CAUSE DEFENSE (§6664(c))
   Requirements:
   - Taxpayer acted in good faith
   - Reasonable cause for position
   - Reliance on professional advice (Reg. §1.6664-4)

   Reliance on professional requires:
   - All pertinent facts disclosed to advisor
   - Advisor is competent professional
   - Reliance is reasonable under circumstances

6. POSITION DEFENSIBILITY FOR RETURN SIGNING
   SCENARIO                          ACTION
   ─────────────────────────────────────────────────────────────────────────
   Substantial authority             Sign - no disclosure needed
   Reasonable basis, no disclosure   Advise client of penalty exposure
   Reasonable basis + disclosure     Sign with 8275 attached
   Below reasonable basis            DO NOT SIGN""",
        key_factors=[
            "Level of authority for position taken",
            "Whether disclosure made if position is below substantial authority",
            "Reasonable cause documentation if penalty asserted",
            "Competent professional advice relied upon",
            "All relevant facts disclosed to advisor"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §6662", "relevance": "Accuracy-related penalties"},
            {"authority": "IRC", "reference": "IRC §6662(d)(2)(B)", "relevance": "Substantial authority and disclosure"},
            {"authority": "IRC", "reference": "IRC §6664(c)", "relevance": "Reasonable cause defense"},
            {"authority": "Reg", "reference": "Treas. Reg. §1.6662-4", "relevance": "Substantial understatement"}
        ],
        burden_holder="depends",
        irs_typical_position="""The IRS asserts penalties when: (1) no substantial authority
for position and no disclosure; (2) disclosure inadequate or on wrong form; (3) return
preparer did not have all relevant facts; (4) position is frivolous; (5) reasonable
cause defense lacks documentation.""",
        counter_arguments=[
            "Substantial authority exists based on [specific authorities]",
            "Adequate disclosure made on Form 8275 attached to return",
            "Reasonable cause: relied on competent professional with full facts",
            "Position has reasonable basis at minimum",
            "Good faith demonstrated through consultation and documentation"
        ],
        appeals_strategy="""Penalty cases often resolved at Appeals. Present substantial
authority memorandum analyzing favorable and unfavorable authorities. If disclosure made,
argue it was adequate. Reasonable cause defense requires contemporaneous documentation of
professional advice. Request waiver for first-time penalty or voluntary disclosure.""",
        entity_scope=["all"],
        confidence="high"
    ),

    "home_office_deduction": DoctrineBlock(
        topic="Home Office Deduction - §280A",
        keywords=["home office", "280a", "exclusive use", "regular use",
                  "principal place of business", "simplified method",
                  "administrative convenience", "business use percentage"],
        conclusion_template="""A home office deduction is allowed under §280A(c) if the space is
used exclusively and regularly as: (1) the principal place of business, (2) a place to meet
clients/customers in the normal course of business, or (3) a separate structure used for
business. The deduction cannot exceed gross income from the business. Simplified method
allows $5/sq ft up to 300 sq ft ($1,500 max).""",
        reasoning_framework="""
HOME OFFICE — STRICT COMPLIANCE FRAMEWORK:

1. EXCLUSIVE USE TEST — ABSOLUTE REQUIREMENT
   □ Space used ONLY for business (no exceptions for occasional personal use)
   □ Identifiable area - need not be separate room but must be regular and exclusive
   □ EXCEPTION: Daycare facility or inventory storage may have non-exclusive use

   FAILURE OF EXCLUSIVE USE = NO DEDUCTION (cannot prorate for business portion)

2. REGULAR USE TEST
   □ Consistent and ongoing use, not occasional or incidental
   □ No specific hour requirement but must be habitual
   □ Seasonal businesses: regular during active season sufficient

3. PRINCIPAL PLACE OF BUSINESS (§280A(c)(1)(A))
   Analysis (Commissioner v. Soliman, modified by 1999 amendment):

   □ Administrative/management activities performed at home
   □ No other fixed location for substantial admin/mgmt activities
   □ OR: Most important activities performed at home relative to all work locations

   Note: 1999 amendment allows home office if admin activities there even if
   income-generating activities occur elsewhere (e.g., contractor, consultant)

4. DEDUCTION CALCULATION

   Direct expenses (100% to office):
   - Painting/repairs to office only
   - Dedicated phone line

   Indirect expenses (prorate by area):
   - Rent/mortgage interest, RE taxes
   - Insurance, utilities, depreciation

   Percentage calculation:
   - Office sq ft ÷ Total home sq ft, OR
   - Number of rooms method if rooms similar size

   Deduction limitation:
   - Cannot exceed gross income from business
   - Carryforward for excess amounts

5. SIMPLIFIED METHOD (Rev. Proc. 2013-13)
   □ $5 per square foot
   □ Maximum 300 sq ft = $1,500 maximum
   □ No depreciation recapture on sale
   □ Full mortgage interest/RE taxes still deductible on Schedule A
   □ Election made annually

6. AUDIT TRIGGERS
   - Large deduction relative to income
   - Claimed 100% of home as office
   - W-2 employee claiming home office
   - No corroborating business activity""",
        key_factors=[
            "Exclusive use documented (photos, floor plan)",
            "Regular use pattern established",
            "Principal place of business or client meeting test",
            "Business use percentage calculation supported",
            "Deduction limited to gross income from activity"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §280A(c)", "relevance": "Home office deduction"},
            {"authority": "Case", "reference": "Commissioner v. Soliman, 506 U.S. 168 (1993)", "relevance": "Principal place of business"},
            {"authority": "IRC", "reference": "IRC §280A(c)(1) as amended 1999", "relevance": "Admin/mgmt activities test"},
            {"authority": "Rev Proc", "reference": "Rev. Proc. 2013-13", "relevance": "Simplified method"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges home office deductions when: (1) exclusive
use cannot be demonstrated; (2) another location serves as principal place of business;
(3) business use percentage appears inflated; (4) W-2 employee claims without employer
certification; (5) no substantiation of business activity from home.""",
        counter_arguments=[
            "Photos and floor plan document exclusive business use",
            "No other fixed location available for administrative activities",
            "Regular use demonstrated by business records created at home",
            "Business use percentage calculated conservatively",
            "Gross income limitation properly applied"
        ],
        appeals_strategy="""Home office cases turn on facts. Provide photos, floor plans,
and third-party evidence of business use. If W-2 employee, show employer convenience
requirement. If exclusive use questionable, may concede but argue partial deduction.
Simplified method avoids many disputes if deduction amount is modest.""",
        entity_scope=["individual", "sole_proprietorship"],
        confidence="high"
    ),

    "research_credit": DoctrineBlock(
        topic="Research and Development Tax Credit - §41",
        keywords=["research credit", "41", "r&d credit", "qualified research expenses",
                  "four part test", "substantially all", "technological uncertainty",
                  "business component", "qre"],
        conclusion_template="""The §41 research credit equals 20% of qualified research expenses
(QRE) over a base amount (regular credit) or 14% of QRE over 50% of average QRE for prior
3 years (alternative simplified credit). QRE includes in-house wages and supplies for
qualified research, plus 65% of contract research. Qualified research must meet the
four-part test: §174 eligibility, technological uncertainty, process of experimentation,
and technological in nature.""",
        reasoning_framework="""
RESEARCH CREDIT — DOCUMENTATION FRAMEWORK FOR DEFENSIBILITY:

1. THE FOUR-PART TEST (All must be met)

   (1) §174 TEST
       - Expenditure treated as R&D expense under §174
       - Research in laboratory sense or for new/improved function
       - NOT: Quality control, style changes, market research

   (2) TECHNOLOGICAL UNCERTAINTY
       - Uncertainty regarding capability, method, or design
       - Must exist at OUTSET of research
       - Eliminated through process of experimentation
       - Uncertainty can be in-house even if solution exists externally

   (3) PROCESS OF EXPERIMENTATION
       - Systematic process to evaluate alternatives
       - Testing hypotheses, modeling, prototyping
       - Trial and error IS experimentation if systematic
       - Mere production troubleshooting is NOT experimentation

   (4) TECHNOLOGICAL IN NATURE
       - Relies on hard sciences: engineering, physics, chemistry, biology, CS
       - Social sciences, economics, arts do NOT qualify
       - Software development can qualify if technical uncertainty exists

2. QUALIFIED RESEARCH EXPENSES (QRE)

   Component          Rate     Requirements
   ─────────────────────────────────────────────────────────────────────────
   Wages (in-house)   100%     Employee engaged in qualified research
   Supplies           100%     Used in qualified research
   Contract research   65%     Expenses for third-party research
   Basic research      75%     Payments to qualified organizations

   SUBSTANTIALLY ALL TEST:
   - 80% of employee's time must be qualified research to include all wages
   - Otherwise, prorate to actual qualified activities

3. DOCUMENTATION REQUIREMENTS — CRITICAL

   CONTEMPORANEOUS (Required for defensibility):
   □ Project lists with research objectives
   □ Technical uncertainty identified at project start
   □ Experimentation process documented (testing, iterations)
   □ Time tracking by project and activity
   □ Payroll records tied to projects

   MINIMUM STANDARD:
   □ Employee interviews (contemporaneous notes)
   □ Technical memos or engineering documents
   □ Project records, test results, prototypes

4. AUDIT DEFENSE
   IRS Focus Areas:
   - Funded research exclusion (customer pays for development)
   - Substantially all test for employee wages
   - Process of experimentation vs. production troubleshooting
   - Documentation insufficient to allocate by project
   - Third-party study lacks taxpayer-specific analysis

5. CALCULATION METHODS
   Regular Credit:     20% × (QRE - Base Amount)
   Alternative (ASC):  14% × (QRE - 50% of 3-year average QRE)
   Startup:            6% of QRE if no QRE in any of 3 prior years""",
        key_factors=[
            "Four-part test documented for each project",
            "Technological uncertainty identified at project inception",
            "Process of experimentation contemporaneously documented",
            "Time tracking supporting wage allocation to qualified activities",
            "Substantially all test met (80% for full wage inclusion)"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §41", "relevance": "Research credit"},
            {"authority": "Reg", "reference": "Treas. Reg. §1.41-4", "relevance": "Qualified research definition"},
            {"authority": "IRC", "reference": "IRC §174", "relevance": "R&D expense deduction"},
            {"authority": "Case", "reference": "Union Carbide Corp. v. Commissioner, 97 T.C. 653 (1991)", "relevance": "Process of experimentation"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges R&D credits when: (1) documentation lacks
project-level detail; (2) studies based solely on estimates without contemporaneous records;
(3) activities are production troubleshooting, not experimentation; (4) funded research
exclusion applies; (5) substantially all test not met for included wages.""",
        counter_arguments=[
            "Four-part test met with contemporaneous project documentation",
            "Technological uncertainty existed at project inception (documented)",
            "Process of experimentation evidenced by test records and iterations",
            "Time tracking supports wage allocation to qualified activities",
            "Not funded research - customer did not pay for development"
        ],
        appeals_strategy="""R&D credit appeals are documentation-intensive. Provide project
narratives, technical memos, and time records. If documentation is thin, consider
conceding weaker projects. Expert technical testimony may support uncertainty existed.
Request technical conference with Appeals engineer if available.""",
        entity_scope=["c_corporation", "s_corporation", "partnership", "llc", "sole_proprietorship"],
        confidence="high"
    ),

    "listed_transaction_disclosure": DoctrineBlock(
        topic="Listed/Reportable Transaction Penalties - §6707A/§6662A",
        keywords=["listed transaction", "reportable transaction", "6707a", "6662a",
                  "form 8886", "material advisor", "tax shelter", "transaction of interest",
                  "disclosure penalty"],
        conclusion_template="""Failure to disclose a reportable transaction on Form 8886 triggers
a penalty under §6707A: $10,000 for individuals and $50,000 for other taxpayers for listed
transactions; $10,000 for other reportable transactions (lower for individuals). §6662A
imposes a 20% accuracy penalty (30% if not disclosed) on understatements from reportable
transactions, with no reasonable cause defense for listed transactions.""",
        reasoning_framework="""
REPORTABLE TRANSACTION COMPLIANCE — PENALTY AVOIDANCE:

1. TRANSACTION CATEGORIES (Treas. Reg. §1.6011-4)

   Category             Description                     Form 8886?
   ─────────────────────────────────────────────────────────────────────────
   Listed               Identified by IRS as abusive    YES - mandatory
   Confidential         Confidentiality imposed         YES - mandatory
   Contractual protection  Tax benefit protected        YES - mandatory
   Loss                 $10M+ loss (corp) / $2M+ (ind)  YES - mandatory
   Transaction of interest  Potential for abuse         YES - if designated

   CRITICAL: Listed transactions carry highest penalties and no reasonable cause

2. LISTED TRANSACTION IDENTIFICATION
   □ Check Notice 2009-59 and updates for current list
   □ Examples: Conservation easements (syndicated), Micro-captive insurance,
     Syndicated losses, Certain captive arrangements
   □ Substantially similar transactions also listed

   IF LISTED: Immediate disclosure required; consider withdrawal if possible

3. PENALTY STRUCTURE

   Failure to Disclose (§6707A):
   - Listed transaction: $10K (individual), $50K (other)
   - Rescission available: IRS may rescind if taxpayer cooperates

   Accuracy-Related (§6662A):
   - 20% of understatement (disclosed)
   - 30% of understatement (not disclosed)
   - NO reasonable cause defense for listed transactions
   - Strengthened reasonable cause standard for others

4. DISCLOSURE TIMING
   □ File with return for year of participation
   □ Also file with OTSA within 60 days of earliest of:
     - Due date of return (with extensions), or
     - Date return is filed
   □ Amended returns: file 8886 with amendment

5. MATERIAL ADVISOR OBLIGATIONS (§6111/§6112)
   Threshold: $50K fee (individual), $250K (corporate)
   Obligations:
   - Disclose to IRS (Form 8918)
   - Maintain participant list
   - Penalty: Greater of $50K or 75% of fee

6. PROTECTIVE DISCLOSURE
   IF uncertain whether transaction is reportable:
   □ Consider protective Form 8886 disclosure
   □ Attach statement explaining disclosure made under protest
   □ Avoids non-disclosure penalty if later determined reportable""",
        key_factors=[
            "Whether transaction is listed, reportable, or transaction of interest",
            "Timely Form 8886 filed with return and OTSA",
            "Material advisor disclosure obligations met",
            "Participant lists maintained if applicable",
            "Withdrawal or rescission options evaluated"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §6707A", "relevance": "Disclosure penalty"},
            {"authority": "IRC", "reference": "IRC §6662A", "relevance": "Accuracy penalty for reportable transactions"},
            {"authority": "Reg", "reference": "Treas. Reg. §1.6011-4", "relevance": "Reportable transaction definition"},
            {"authority": "Notice", "reference": "Notice 2009-59", "relevance": "Listed transaction identification"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS asserts penalties when: (1) Form 8886 not filed;
(2) disclosure incomplete or filed late; (3) substantially similar to listed transaction;
(4) material advisor failed to disclose; (5) participant lists not maintained. For
listed transactions, no reasonable cause defense available.""",
        counter_arguments=[
            "Form 8886 timely filed with return and OTSA",
            "Transaction is not substantially similar to listed transaction",
            "Protective disclosure made out of abundance of caution",
            "Material advisor threshold not met",
            "Rescission request submitted for inadvertent failure"
        ],
        appeals_strategy="""Listed transaction cases have limited appeal options due to
strict liability. If disclosure was made but deficient, request rescission. If transaction
arguably not substantially similar, present technical analysis. Non-listed reportable
transactions: assert reasonable cause with detailed professional advice documentation.""",
        entity_scope=["all"],
        confidence="high"
    ),

    "family_employment": DoctrineBlock(
        topic="Family Employment - Reasonable Compensation",
        keywords=["family employment", "children employees", "kiddie tax",
                  "reasonable compensation family", "spouse employee",
                  "family limited partnership", "family llc", "income shifting"],
        conclusion_template="""Compensation paid to family members is deductible only if: (1) bona
fide employment relationship exists, (2) services are actually performed, and (3) compensation
is reasonable for services rendered. Special rules apply: children under 18 employed by parent's
sole proprietorship are exempt from FICA; family attribution rules apply to controlled entities;
kiddie tax applies to unearned income of children under 19 (24 if student).""",
        reasoning_framework="""
FAMILY EMPLOYMENT — DOCUMENTATION FRAMEWORK:

1. BONA FIDE EMPLOYMENT REQUIREMENTS
   □ Written job description with defined duties
   □ Actual services performed (contemporaneous records)
   □ Reasonable hours for age and role
   □ Compensation paid regularly (not year-end lump sum)
   □ Time records maintained

   IF NOT GENUINE EMPLOYMENT: Recharacterization as gift or distribution

2. REASONABLE COMPENSATION ANALYSIS
   □ Compare to unrelated party for same services
   □ Consider: age, experience, skills, local rates
   □ Child employees: minimum wage is floor, not ceiling
   □ Spouse employees: market rate for actual role

   DOCUMENTATION NEEDED:
   - Job description matching actual duties
   - Comparable wage data (DOL, salary surveys)
   - Time records showing hours worked

3. FICA EXEMPTION FOR CHILDREN (§3121(b)(3))
   Requirements:
   □ Child under 18 (no FICA exemption) -OR-
   □ Child under 21 (no FUTA)
   □ Employed by parent's sole proprietorship OR
   □ Partnership of only parents (each spouse is parent)

   NOT EXEMPT:
   - Employment by corporation (even family-owned)
   - Employment by partnership with non-parent partners
   - Child employed by parent's LLC (taxed as corp)

4. KIDDIE TAX CONSIDERATIONS (§1(g))
   Applies if:
   - Child under 19, OR
   - Child under 24 if full-time student
   - Unearned income exceeds threshold ($2,500 for 2024)

   EARNED INCOME (wages) not subject to kiddie tax
   PLANNING: Shift income to wages, avoid kiddie tax

5. FAMILY ATTRIBUTION TRAPS
   §267: Loss on sale to family member disallowed
   §318: Stock ownership attribution in family
   §704(e): Family partnership rules
   §1563: Family controlled group rules

6. IRS FOCUS AREAS
   - Compensation exceeds reasonable for child's role
   - No contemporaneous time records
   - Payment timing suspicious (year-end bonus)
   - Child's duties vague or unsupervised
   - Multiple family members with inflated pay""",
        key_factors=[
            "Written job description documenting actual duties",
            "Time records showing hours worked",
            "Comparable wage data supporting reasonableness",
            "Regular payment of compensation (not year-end)",
            "FICA exemption requirements met if claimed"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §162(a)(1)", "relevance": "Reasonable compensation deduction"},
            {"authority": "IRC", "reference": "IRC §3121(b)(3)", "relevance": "FICA exemption for children"},
            {"authority": "IRC", "reference": "IRC §1(g)", "relevance": "Kiddie tax"},
            {"authority": "Case", "reference": "Eller v. Commissioner, T.C. Memo 1993-647", "relevance": "Family compensation reasonableness"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges family compensation when: (1) no documentation
of services performed; (2) compensation unreasonable for child's age/role; (3) time records
absent or appear fabricated; (4) payment made in lump sum at year-end; (5) FICA exemption
claimed when not available (e.g., corporate employer).""",
        counter_arguments=[
            "Written job description matches actual duties performed",
            "Time records contemporaneously maintained",
            "Comparable wage data supports compensation amount",
            "Regular payroll with appropriate withholding",
            "FICA exemption requirements documented (sole prop, child under 18)"
        ],
        appeals_strategy="""Family compensation cases are fact-intensive. Provide time records,
job descriptions, and comparable wage data. If child is minor, emphasize actual services
appropriate for age. If compensation appears high, compare to third-party market rates.
Consider partial concession if documentation weak for some periods.""",
        entity_scope=["sole_proprietorship", "partnership", "s_corporation", "c_corporation", "llc"],
        confidence="high"
    ),

    # =========================================================================
    # PARTNER-LEVEL JUDGMENT DOCTRINE — COMPLEX TRANSACTIONS
    # =========================================================================

    "installment_sale_related_party": DoctrineBlock(
        topic="Installment Sale - Related Party Rules (§453)",
        keywords=["installment sale", "related party", "453", "second disposition",
                  "two year rule", "deferred gain", "installment note",
                  "related party disposition", "marketable securities"],
        conclusion_template="""Installment sale treatment is available under §453 for sales where
at least one payment is received after the year of sale. However, related party sales trigger
special rules under §453(e): if the related buyer disposes of the property within 2 years,
the original seller must recognize gain as if payment was received. Installment treatment
is NOT available for dealer dispositions, sales of publicly traded stock, or depreciation
recapture amounts.""",
        reasoning_framework="""
INSTALLMENT SALE — RELATED PARTY ANALYSIS:

1. RELATED PARTY DEFINITION (§453(f)(1))
   Related parties include:
   □ Family: spouse, children, grandchildren, parents (§267(b))
   □ Controlled entities: >50% ownership (§267(b), §707(b))
   □ Trusts/beneficiaries, estates/beneficiaries
   □ Attribution rules apply (§318)

   NOTE: Siblings are NOT related parties for §453(e)

2. TWO-YEAR DISPOSITION RULE (§453(e))
   IF related buyer disposes within 2 years:
   → Original seller recognizes gain immediately
   → Amount = lesser of: (a) amount realized by related buyer, OR
                         (b) remaining deferred gain

   EXCEPTIONS to acceleration:
   □ Disposition after death of seller or buyer
   □ Involuntary conversion (if proceeds reinvested)
   □ Disposition establishing non-tax-avoidance purpose
   □ Sale of marketable securities (no installment allowed anyway)

3. TAX AVOIDANCE PURPOSE TEST
   Acceleration AVOIDED if taxpayer establishes:
   □ Neither sale nor disposition had tax avoidance as principal purpose
   □ Legitimate business reason for both transactions
   □ Not structured to accelerate basis to related party

   IRS PRESUMPTION: Related party sales are presumed tax-motivated
   BURDEN: Taxpayer must prove otherwise

4. PLANNING CONSIDERATIONS
   □ Waiting period: Ensure 2-year hold before resale
   □ Document business purpose contemporaneously
   □ Consider non-related party sale if resale anticipated
   □ Depreciation recapture cannot be deferred regardless

5. AUDIT TRIGGERS
   - Large installment gain followed by related buyer resale
   - Short hold period before disposition
   - Related buyer financed by third party (cash-out structure)
   - No business purpose documentation
   - Pattern of related party installment transactions""",
        key_factors=[
            "Related party status confirmed under §267/§318 attribution",
            "Two-year holding period tracked from original sale",
            "Business purpose documented at time of sale",
            "Second disposition terms and timing analyzed",
            "Depreciation recapture recognized in year of sale"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §453", "relevance": "Installment method"},
            {"authority": "IRC", "reference": "IRC §453(e)", "relevance": "Related party rules"},
            {"authority": "IRC", "reference": "IRC §453(f)(1)", "relevance": "Related party definition"},
            {"authority": "IRC", "reference": "IRC §267(b)", "relevance": "Related party relationships"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges related party installment sales when:
(1) related buyer disposes within 2 years; (2) transaction structured to monetize
low-basis property through related party; (3) no independent business purpose exists;
(4) attribution rules create undisclosed related party relationship.""",
        counter_arguments=[
            "Two-year holding period satisfied before any disposition",
            "Business purpose documented contemporaneously",
            "Related buyer disposition was involuntary",
            "Disposition occurred after death of original seller",
            "Non-tax-avoidance purpose established with evidence"
        ],
        appeals_strategy="""If second disposition occurred within 2 years, focus on
establishing non-tax-avoidance purpose. Present business rationale for both transactions
with contemporaneous documentation. If purpose defense weak, calculate gain acceleration
and negotiate timing of payment. Death exception requires proof of date.""",
        entity_scope=["individual", "partnership", "s_corporation", "c_corporation", "llc", "trust"],
        confidence="high"
    ),

    "section_351_formation": DoctrineBlock(
        topic="Section 351 Tax-Free Corporate Formation",
        keywords=["351", "corporate formation", "control", "80 percent",
                  "property for stock", "boot", "services", "tax free incorporation",
                  "contribution to capital", "assumption of liabilities"],
        conclusion_template="""No gain or loss is recognized when property is transferred to a
corporation solely in exchange for stock, if immediately after the exchange the transferor(s)
control the corporation (80% of voting power AND 80% of each class of nonvoting stock).
Boot received triggers gain recognition. Services do not qualify as 'property.' Liabilities
assumed may trigger gain under §357(c) if liabilities exceed basis.""",
        reasoning_framework="""
SECTION 351 — CONTROL AND QUALIFICATION ANALYSIS:

1. CONTROL REQUIREMENT (§368(c))
   BOTH must be met:
   □ 80% of total combined voting power, AND
   □ 80% of each class of nonvoting stock

   "Immediately after" = part of integrated plan
   Multiple transferors can aggregate to meet 80%

   WARNING: Transferor receiving only services = NOT counted toward control

2. PROPERTY vs. SERVICES DISTINCTION
   PROPERTY (Qualifies):
   - Cash, tangible assets, real estate
   - Intangibles (patents, copyrights, know-how)
   - Accounts receivable (cash basis: zero basis)
   - Installment notes

   NOT PROPERTY (Gain recognized):
   - Services rendered to corporation
   - Services rendered to other transferors
   - Debt of transferor canceled

   HYBRID: Stock for property AND services → Bifurcate

3. BOOT RECOGNITION (§351(b))
   Boot includes:
   - Cash received
   - Property other than stock
   - Stock rights, warrants
   - Securities (debt with >5 year term: complicated)

   Gain recognized = Lesser of:
   - Boot received, OR
   - Realized gain

   Character: Same as if property sold (capital/ordinary)

4. LIABILITY ASSUMPTION (§357)
   General rule: Assumption of liabilities NOT boot

   EXCEPTIONS triggering gain:
   □ §357(b): Tax avoidance purpose → All liabilities = boot
   □ §357(c): Liabilities > aggregate basis → Gain = excess

   §357(c) calculation:
   - Aggregate all properties transferred
   - Aggregate all liabilities assumed
   - If liabilities > basis = gain (ordinary to extent of recapture)

5. BASIS RULES
   Transferor's stock basis = Property basis - boot + gain recognized
   Corporation's property basis = Transferor's basis + gain recognized

6. AUDIT TRIGGERS
   - Contribution of high-liability, low-basis property
   - Services characterized as property
   - Control requirement questionable (exactly 80%)
   - Step transaction risk (prearranged resale of stock)
   - Assignment of income issues (cash basis receivables)""",
        key_factors=[
            "Control requirement met (80% voting AND 80% each nonvoting class)",
            "Property vs. services properly distinguished",
            "Boot recognized and character determined",
            "Liability assumption analyzed under §357(b) and (c)",
            "Basis calculations documented for stock and property"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §351", "relevance": "Tax-free exchange"},
            {"authority": "IRC", "reference": "IRC §368(c)", "relevance": "Control definition"},
            {"authority": "IRC", "reference": "IRC §357", "relevance": "Liability assumption"},
            {"authority": "IRC", "reference": "IRC §358", "relevance": "Transferor basis"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges §351 treatment when: (1) control not
maintained immediately after exchange; (2) services disguised as property; (3) liabilities
assumed exceed basis; (4) tax avoidance purpose for liability assumption; (5) step
transaction doctrine applies to integrated plan.""",
        counter_arguments=[
            "Control requirement satisfied with documentation of stock ownership",
            "All transfers were property, not services, with FMV established",
            "Liability assumption had business purpose, not tax avoidance",
            "Aggregate basis exceeds aggregate liabilities assumed",
            "No prearranged disposition of stock received"
        ],
        appeals_strategy="""Control requirement is strict - either met or not. If marginally
missed, little room for appeal. If services vs. property disputed, present evidence of
property nature. §357(c) gain is mechanical - verify calculations. Tax avoidance under
§357(b) requires proving business purpose for liability transfer.""",
        entity_scope=["c_corporation", "s_corporation"],
        confidence="high"
    ),

    "section_754_election": DoctrineBlock(
        topic="Section 754 Partnership Basis Adjustment Election",
        keywords=["754", "basis adjustment", "743b", "734b", "inside basis",
                  "outside basis", "step up", "step down", "partnership election",
                  "mandatory adjustment", "substantial built-in loss"],
        conclusion_template="""A §754 election allows a partnership to adjust the basis of
partnership property following a transfer of partnership interest (§743(b)) or distribution
of property (§734(b)). Once made, the election is irrevocable and applies to all future
transfers and distributions unless IRS consents to revocation. Adjustments under §743(b)
are mandatory for transfers with substantial built-in loss (>$250,000).""",
        reasoning_framework="""
SECTION 754 — ELECTION AND ADJUSTMENT ANALYSIS:

1. WHEN 754 APPLIES
   §743(b) - Transfer of partnership interest:
   → Adjusts inside basis to reflect purchase price
   → Benefits buyer if FMV > inside basis (step-up)
   → Applies ONLY to transferee partner

   §734(b) - Distribution of partnership property:
   → Adjusts remaining property basis after distribution
   → Applies when distributed property basis ≠ distributee's basis reduction
   → Benefits/burdens ALL partners

2. MAKING THE ELECTION
   □ Statement attached to partnership return
   □ Filed by due date (with extensions) for year of transfer/distribution
   □ Once made: BINDING on all future transactions
   □ Revocation requires IRS consent (rarely granted)

   STRATEGIC CONSIDERATION: Evaluate ALL partners before electing

3. §743(b) ADJUSTMENT CALCULATION
   Transferee's adjustment = Purchase price - Proportionate share of inside basis

   Example:
   - Partner buys 25% interest for $300,000
   - Partnership inside basis = $800,000
   - Proportionate share = $200,000
   - §743(b) adjustment = +$100,000 step-up

   Allocation: Follows §755 rules (ordinary vs. capital property)

4. MANDATORY ADJUSTMENT (§743(d))
   Election NOT required if partnership has:
   □ Substantial built-in loss: Inside basis > FMV by >$250,000
   □ Transferee would have loss >$250,000 without adjustment

   MANDATORY step-DOWN in these cases

5. §734(b) ADJUSTMENT SCENARIOS
   Adjustment required when distribution causes:
   □ Gain recognition to distributee (distributed cash > outside basis)
   □ Basis increase in distributed property (§732 limitations)

   Adjustment = Amount of gain recognized OR basis increase

6. AUDIT ISSUES
   - Election not properly filed
   - §743(b) adjustment not allocated per §755
   - Mandatory adjustment ignored
   - Substantial built-in loss not identified
   - Technical termination reset election (pre-2018)

7. DECISION FRAMEWORK: SHOULD PARTNERSHIP ELECT?
   FAVOR ELECTION if:
   □ Partnership anticipates sales of appreciated interests
   □ New partners acquiring at premium to inside basis
   □ Partnership holds appreciating assets

   AGAINST ELECTION if:
   □ Assets likely to decline in value (step-down risk)
   □ Complex multi-tier structure (administrative burden)
   □ Frequent partner turnover with minimal basis disparity""",
        key_factors=[
            "Election properly filed with timely return",
            "§743(b) adjustments allocated under §755",
            "Mandatory adjustment evaluated for substantial built-in loss",
            "Inside/outside basis tracking maintained",
            "Impact on ALL partners considered before election"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §754", "relevance": "Election to adjust basis"},
            {"authority": "IRC", "reference": "IRC §743(b)", "relevance": "Transfer adjustment"},
            {"authority": "IRC", "reference": "IRC §734(b)", "relevance": "Distribution adjustment"},
            {"authority": "IRC", "reference": "IRC §755", "relevance": "Allocation rules"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges §754 positions when: (1) election not
properly filed or untimely; (2) adjustments not allocated per §755; (3) substantial
built-in loss triggers mandatory adjustment that was ignored; (4) basis tracking
inadequate to support claimed adjustments.""",
        counter_arguments=[
            "Election timely filed with partnership return",
            "§743(b) adjustment properly calculated and allocated",
            "No substantial built-in loss existed at transfer date",
            "Inside/outside basis schedule supports adjustment",
            "§755 allocation methodology documented"
        ],
        appeals_strategy="""§754 issues often involve procedural failures. If election
filing disputed, present evidence of attachment to return. If allocation disputed,
demonstrate §755 compliance with asset classifications. Late election relief may
be available under Rev. Proc. 2015-13 for inadvertent failures.""",
        entity_scope=["partnership", "llc"],
        confidence="high"
    ),

    "accumulated_earnings_tax": DoctrineBlock(
        topic="Accumulated Earnings Tax - §531",
        keywords=["accumulated earnings", "531", "reasonable needs", "bardahl formula",
                  "unreasonable accumulation", "dividend equivalent", "aet",
                  "operating cycle", "business needs"],
        conclusion_template="""The accumulated earnings tax under §531 imposes a 20% penalty tax
on C corporations that accumulate earnings beyond the reasonable needs of the business to
avoid shareholder-level tax on dividends. A minimum credit of $250,000 ($150,000 for personal
service corporations) is allowed. The tax applies to 'accumulated taxable income' which is
taxable income with certain adjustments, less dividends paid and the accumulated earnings
credit.""",
        reasoning_framework="""
ACCUMULATED EARNINGS TAX — REASONABLE NEEDS ANALYSIS:

1. ELEMENTS FOR AET IMPOSITION
   IRS must show:
   □ Earnings accumulated beyond reasonable business needs
   □ Tax avoidance purpose (proscribed purpose)

   Tax avoidance purpose PRESUMED if accumulation unreasonable
   Taxpayer may rebut with evidence of business purpose

2. REASONABLE BUSINESS NEEDS (Treas. Reg. §1.537-2)
   VALID needs include:
   □ Business expansion (plant, equipment, facilities)
   □ Working capital for operations (Bardahl formula)
   □ Debt retirement
   □ Acquisition of business
   □ Product liability reserves
   □ Self-insurance reserves (if reasonable)
   □ §303 stock redemption reserves

   INVALID needs:
   □ Loans to shareholders (strong evidence of avoidance)
   □ Investment in unrelated business
   □ Personal investments for shareholders
   □ Unreasonable compensation reserves

3. BARDAHL FORMULA — WORKING CAPITAL
   Operating cycle method:
   Step 1: Calculate inventory cycle (Inventory ÷ COGS × 365)
   Step 2: Calculate receivables cycle (A/R ÷ Sales × 365)
   Step 3: Subtract payables cycle (A/P ÷ Operating expenses × 365)
   Step 4: Net operating cycle × (Operating expenses ÷ 365)
   = Working capital needs

   Compare to: Actual accumulated E&P
   Excess = Potential unreasonable accumulation

4. ACCUMULATED TAXABLE INCOME CALCULATION
   Taxable income
   + Dividends received deduction add-back
   - Federal income taxes
   - Charitable contributions (up to 10% limit)
   - Net capital loss adjustment
   - Dividends paid deduction
   - Accumulated earnings credit
   = Accumulated taxable income × 20% = AET

5. AUDIT TRIGGERS
   - Large E&P accumulation relative to operations
   - Loans to shareholders
   - Investment portfolio unrelated to business
   - No dividend history despite profits
   - Personal holding company characteristics
   - Declining business with growing accumulation

6. DEFENSE DOCUMENTATION
   □ Board resolutions documenting business needs
   □ Capital expenditure plans with timelines
   □ Debt agreements requiring reserves
   □ Bardahl or similar working capital analysis
   □ Acquisition targets under negotiation""",
        key_factors=[
            "Reasonable business needs documented with specificity",
            "Bardahl formula working capital calculation",
            "Board resolutions contemporaneous with accumulation",
            "No loans to shareholders or personal investments",
            "Dividend policy consistent with business needs"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §531", "relevance": "Accumulated earnings tax"},
            {"authority": "IRC", "reference": "IRC §533", "relevance": "Presumption of tax avoidance"},
            {"authority": "IRC", "reference": "IRC §535", "relevance": "Accumulated taxable income"},
            {"authority": "Case", "reference": "Bardahl Mfg. Corp., 24 T.C.M. 1030 (1965)", "relevance": "Working capital formula"}
        ],
        burden_holder="depends",
        irs_typical_position="""The IRS challenges accumulations when: (1) earnings far exceed
Bardahl working capital needs; (2) shareholder loans evidence no business need; (3) investment
portfolio unrelated to operations; (4) no contemporaneous documentation of expansion plans;
(5) similar companies pay dividends from comparable earnings.""",
        counter_arguments=[
            "Bardahl formula demonstrates working capital needs justify accumulation",
            "Board resolutions document specific expansion plans",
            "Debt covenants require maintenance of reserves",
            "Industry conditions require contingency reserves",
            "Planned acquisition evidenced by negotiations"
        ],
        appeals_strategy="""AET cases turn on documentation of business needs. Present
Bardahl analysis and board resolutions. If expansion plans documented but not executed,
explain business reasons for delay. Shareholder loans are damaging - address directly
or consider concession. Working capital defense strongest for operating companies.""",
        entity_scope=["c_corporation"],
        confidence="high"
    ),

    "disguised_sale_partnership": DoctrineBlock(
        topic="Disguised Sale Rules - §707(a)(2)(B)",
        keywords=["disguised sale", "707", "contribution distribution", "partnership",
                  "two year presumption", "debt allocation", "sale vs contribution",
                  "related transfers", "qualified liability"],
        conclusion_template="""A transfer of property to a partnership followed by a transfer
of money or property from the partnership to the contributing partner may be treated as a
disguised sale under §707(a)(2)(B). If transfers occur within 2 years, a rebuttable presumption
of sale applies. Transfers more than 2 years apart are presumed NOT to be a sale. Qualified
liabilities assumed by the partnership are not treated as sale proceeds.""",
        reasoning_framework="""
DISGUISED SALE — ANALYSIS FRAMEWORK:

1. DISGUISED SALE TEST (Treas. Reg. §1.707-3)
   Sale treatment if facts indicate:
   □ Transfer of property to partnership, AND
   □ Related direct or indirect transfer TO the partner, AND
   □ Transfers are properly characterized as a sale

   Factors indicating sale:
   - Timing of transfers (closer = more like sale)
   - Certainty of distribution (guaranteed vs. contingent)
   - Partner's entitlement secured by contributed property
   - Distribution exceeds partner's share of profits

2. TIMING PRESUMPTIONS
   Within 2 years: PRESUMED to be disguised sale
   → Taxpayer must rebut with facts and circumstances

   More than 2 years: PRESUMED NOT to be sale
   → IRS must prove sale characterization

3. QUALIFIED LIABILITIES — NOT SALE PROCEEDS
   Liability is "qualified" if:
   □ Incurred >2 years before transfer, OR
   □ Incurred within 2 years but in ordinary course of business, OR
   □ Liability allocable to capital expenditures on property, OR
   □ Liability for which partner was personally liable before transfer

   CAUTION: Debt incurred in anticipation of transfer = NOT qualified

4. DEBT-FINANCED DISTRIBUTION ANALYSIS
   Partnership borrows → Distributes to partner
   May be disguised sale if:
   □ Contributed property secures loan
   □ Distribution funded by borrowing
   □ Partner's economic risk shifted to partnership

   SAFE HARBOR: Allocable share of recourse liability shift is NOT sale
   (Partner's share based on loss allocation ratio)

5. CALCULATION IF SALE FOUND
   Sale proceeds = Money received + FMV of property + Debt relief
   Less: Qualified liabilities assumed
   = Net sale proceeds

   Gain = Sale proceeds - Adjusted basis of contributed property

6. AUDIT TRIGGERS
   - Large distribution shortly after contribution
   - Contribution of encumbered appreciated property
   - Guarantee arrangements benefiting contributor
   - Distribution from partnership borrowing
   - Precontribution debt incurred in anticipation

7. PLANNING CONSIDERATIONS
   □ Wait >2 years between contribution and distribution
   □ Ensure distribution tied to partnership profits, not contribution
   □ Document business purpose for timing
   □ Qualify liabilities before transfer window""",
        key_factors=[
            "Timing between contribution and distribution (2-year line)",
            "Whether liabilities qualify under regulations",
            "Entrepreneurial risk retained by partner",
            "Distribution tied to contributed property vs. operations",
            "Documentation of facts and circumstances"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §707(a)(2)(B)", "relevance": "Disguised sale rule"},
            {"authority": "Reg", "reference": "Treas. Reg. §1.707-3", "relevance": "Disguised sale standards"},
            {"authority": "Reg", "reference": "Treas. Reg. §1.707-5", "relevance": "Qualified liabilities"},
            {"authority": "Reg", "reference": "Treas. Reg. §1.707-6", "relevance": "Disclosure requirements"}
        ],
        burden_holder="depends",
        irs_typical_position="""The IRS recharacterizes as sale when: (1) distribution occurs
within 2 years of contribution; (2) liability assumed was incurred in anticipation of
transfer; (3) distribution funded by borrowing secured by contributed property;
(4) partner bore no genuine risk of loss on contributed property after transfer.""",
        counter_arguments=[
            "Distribution occurred >2 years after contribution (presumption applies)",
            "Distribution represents allocable share of partnership profits",
            "All liabilities meet qualified liability definition",
            "Partner retained genuine entrepreneurial risk",
            "Timing explained by business purpose, not tax avoidance"
        ],
        appeals_strategy="""Timing is critical. If within 2 years, burden is on taxpayer to
show facts and circumstances negate sale treatment. Focus on entrepreneurial risk retained.
If liability-related, establish qualification with evidence of incurrence date. Business
purpose documentation essential for overcoming presumption.""",
        entity_scope=["partnership", "llc"],
        confidence="high"
    ),

    "built_in_gains_tax": DoctrineBlock(
        topic="Built-In Gains Tax - §1374 (S Corporation)",
        keywords=["built in gains", "1374", "big tax", "s corp conversion",
                  "c corp to s corp", "recognition period", "net unrealized built in gain",
                  "nubig", "nubil", "rbig"],
        conclusion_template="""When a C corporation converts to S corporation status, the §1374
built-in gains tax imposes corporate-level tax on net recognized built-in gains (RBIG)
during the 5-year recognition period. The tax rate is 21% (highest corporate rate). RBIG
cannot exceed net unrealized built-in gain (NUBIG) at conversion. Net unrealized built-in
loss (NUBIL) provides offset. The recognition period was permanently set at 5 years in 2015.""",
        reasoning_framework="""
BUILT-IN GAINS TAX — S CONVERSION ANALYSIS:

1. WHEN BIG TAX APPLIES
   Corporation has BIG exposure if:
   □ C corporation converts to S corporation
   □ S corporation acquires C corp assets in tax-free transaction
   □ Assets held at conversion had FMV > basis (appreciation)

   RECOGNITION PERIOD: 5 years from conversion date

2. NET UNREALIZED BUILT-IN GAIN (NUBIG)
   Calculated at conversion date:
   FMV of all assets
   Less: Adjusted basis of all assets
   Less: §1374(d)(2) adjustments (income items)
   = Net Unrealized Built-In Gain

   NUBIG CEILING: Total BIG tax over 5 years cannot exceed NUBIG
   If NUBIG is negative (NUBIL): No BIG tax exposure

3. RECOGNIZED BUILT-IN GAIN (RBIG)
   Each year during recognition period:
   □ Gain from sale of asset held at conversion
   □ If FMV at conversion < sale price: Portion is NOT BIG
   □ Income from accounts receivable (cash basis C corp)
   □ Completed contract income from contracts at conversion

   BIG CHARACTER: Preserves character from C corp period

4. OFFSETS AND LIMITATIONS
   RBIG is reduced by:
   □ Net operating loss carryforwards from C years
   □ Business credit carryforwards (limited)
   □ Built-in losses recognized during period
   □ NUBIG ceiling

   ANNUAL LIMITATION: Taxable income limitation (similar to §1375)

5. PLANNING STRATEGIES
   □ Defer asset sales until after 5-year period
   □ Document FMV at conversion with appraisals
   □ Identify built-in loss assets to offset gains
   □ Time conversion when asset values are low
   □ Consider installment sale reporting for large gains

6. APPRAISAL REQUIREMENT
   CRITICAL: Document FMV of ALL assets at conversion
   - Real estate appraisals
   - Equipment valuations
   - Intangible asset valuations (goodwill, customer lists)
   - Inventory at FMV

   Without appraisal: IRS may argue FMV = later sale price

7. AUDIT TRIGGERS
   - Large asset sale shortly after conversion
   - No FMV appraisal at conversion date
   - NUBIG calculation undocumented
   - C corp NOLs not properly applied
   - Appreciation ignored in RBIG calculation""",
        key_factors=[
            "Conversion date documented",
            "NUBIG calculated with supporting appraisals",
            "Recognition period tracking (5 years)",
            "RBIG properly limited to appreciation at conversion",
            "C corp NOL carryforwards applied"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §1374", "relevance": "Built-in gains tax"},
            {"authority": "IRC", "reference": "IRC §1374(d)(1)", "relevance": "Recognition period"},
            {"authority": "IRC", "reference": "IRC §1374(d)(3)", "relevance": "RBIG definition"},
            {"authority": "Notice", "reference": "Notice 2003-65", "relevance": "NUBIG calculation methods"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges BIG positions when: (1) no appraisal at
conversion to establish FMV; (2) NUBIG understated by ignoring appreciated assets;
(3) post-conversion appreciation included in BIG calculation offset; (4) recognition
period miscalculated; (5) C corp NOLs improperly applied.""",
        counter_arguments=[
            "Appraisal at conversion establishes FMV for all assets",
            "NUBIG properly calculated using IRS-approved method",
            "Post-conversion appreciation excluded from RBIG",
            "Recognition period correctly tracked from election date",
            "C corp NOL carryforwards properly documented and applied"
        ],
        appeals_strategy="""BIG cases often turn on valuation at conversion. Present
appraisals obtained at or near conversion date. If no appraisal exists, use
contemporaneous evidence (industry multiples, comparable sales). NOL carryforward
application is mechanical - verify calculations. Request Appeals consider
reasonable estimation methods if perfect data unavailable.""",
        entity_scope=["s_corporation"],
        confidence="high"
    ),

    "excess_business_loss": DoctrineBlock(
        topic="Excess Business Loss Limitation - §461(l)",
        keywords=["excess business loss", "461l", "business loss limitation",
                  "threshold amount", "nol conversion", "aggregate loss",
                  "tcja", "pass through loss", "qualified business income"],
        conclusion_template="""Section 461(l) limits the deductibility of aggregate business losses
for non-corporate taxpayers to $289,000 (single) or $578,000 (MFJ) for 2024, indexed for
inflation. Excess business losses above this threshold are converted to net operating loss
(NOL) carryforwards, subject to the 80% taxable income limitation. The limitation applies
AFTER the at-risk and passive activity loss rules.""",
        reasoning_framework="""
EXCESS BUSINESS LOSS — LIMITATION ANALYSIS:

1. SCOPE AND CALCULATION
   Applies to: Individuals, trusts, estates (NOT C corps)
   Calculation:
   Aggregate business deductions
   Less: Aggregate business gross income
   Less: Threshold amount ($289K/$578K for 2024)
   = Excess Business Loss (if negative)

   Excess converts to NOL carryforward

2. ORDERING RULES — CRITICAL
   Apply limitations in this order:
   Step 1: Basis limitation (§704(d) for partnerships)
   Step 2: At-risk limitation (§465)
   Step 3: Passive activity loss limitation (§469)
   Step 4: Excess business loss limitation (§461(l))

   §461(l) applies LAST to remaining business losses

3. BUSINESS vs. NONBUSINESS
   BUSINESS income/loss:
   - Schedule C, E (pass-through), F
   - §1231 gains/losses
   - Interest/dividends if from trade or business

   NOT BUSINESS:
   - Wages and salaries (W-2 income)
   - Investment income (unless dealer)
   - Capital gains from investments
   - Hobby losses (already limited by §183)

4. THRESHOLD AMOUNTS (Indexed annually)
   2024: $289,000 (single/HoH), $578,000 (MFJ)
   Married filing separately: 50% of MFJ amount

   Threshold REDUCES allowable loss (creates ceiling)

5. NOL CARRYFORWARD TREATMENT
   Disallowed loss becomes NOL
   NOL limitations apply:
   □ 80% of taxable income limitation
   □ Indefinite carryforward (no carryback post-TCJA)
   □ Separate tracking required

6. INTERACTION WITH QBI (§199A)
   §461(l) applied BEFORE QBI calculation
   Reduces business income available for 20% deduction
   May create QBI carryforward for future years

7. PLANNING CONSIDERATIONS
   □ Aggregate all business activities for single limit
   □ Time income/deductions to manage threshold
   □ Business losses from sale of business included
   □ Carryforward utilization planning critical
   □ Consider entity conversion for large loss years""",
        key_factors=[
            "All business activities aggregated for single threshold",
            "Ordering rules applied correctly (§465, §469, then §461(l))",
            "Threshold amount indexed for current year",
            "Excess converted to NOL with 80% limitation",
            "Business vs. non-business classification documented"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §461(l)", "relevance": "Excess business loss limitation"},
            {"authority": "IRC", "reference": "IRC §461(l)(3)", "relevance": "Threshold amounts"},
            {"authority": "Notice", "reference": "Notice 2019-66", "relevance": "Ordering rules"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges EBL positions when: (1) non-business losses
included in business aggregate; (2) threshold not applied to aggregated losses; (3) ordering
rules not followed (§461(l) applied before §469); (4) wages treated as business income;
(5) NOL carryforward not properly tracked.""",
        counter_arguments=[
            "Only bona fide business losses included in aggregate",
            "Ordering rules properly applied - §461(l) applied last",
            "Threshold correctly indexed for tax year",
            "Business vs. non-business classification supportable",
            "NOL carryforward schedule maintained"
        ],
        appeals_strategy="""EBL is mechanical calculation - verify ordering and threshold.
If business classification disputed, present evidence of business nature. NOL carryforward
tracking is critical for future years. Consider whether entity restructuring would
avoid limitation for large recurring losses.""",
        entity_scope=["individual", "partnership", "s_corporation", "llc", "trust"],
        confidence="high"
    ),

    "charitable_contribution_substantiation": DoctrineBlock(
        topic="Charitable Contribution Substantiation - §170",
        keywords=["charitable contribution", "170", "substantiation", "contemporaneous",
                  "quid pro quo", "appraisal", "form 8283", "donee acknowledgment",
                  "cash contribution", "noncash contribution"],
        conclusion_template="""Charitable contributions are deductible under §170 only if properly
substantiated. Cash contributions require bank record or written receipt from charity.
Contributions over $250 require contemporaneous written acknowledgment from donee stating
amount and whether goods/services were provided in exchange. Noncash contributions over
$5,000 require qualified appraisal and Form 8283. Failure to comply = complete disallowance.""",
        reasoning_framework="""
SUBSTANTIATION — STRICT COMPLIANCE REQUIREMENTS:

1. CASH CONTRIBUTIONS
   Under $250:
   □ Bank record (canceled check, bank statement), OR
   □ Receipt from donee organization

   $250 or more:
   □ Contemporaneous written acknowledgment from donee
   □ Must state: Amount, whether goods/services provided in exchange
   □ If goods/services provided: Good faith FMV estimate
   □ NO DEDUCTION without acknowledgment (strict rule)

   "Contemporaneous" = Obtained by earlier of:
   - Return filing date (with extensions)
   - Return due date

2. NONCASH CONTRIBUTIONS
   Under $250:
   □ Receipt from donee (if practicable)
   □ Maintain records: Property description, FMV, basis, acquisition

   $250 - $500:
   □ Same as $250+ cash (written acknowledgment)

   $501 - $5,000:
   □ Written acknowledgment PLUS
   □ Form 8283, Section A

   Over $5,000 (not publicly traded securities):
   □ Qualified appraisal (obtained within 60 days before or after donation)
   □ Form 8283, Section B (signed by appraiser and donee)
   □ Attach appraisal summary to return

   Over $500,000:
   □ Attach COMPLETE qualified appraisal to return

3. QUALIFIED APPRAISAL REQUIREMENTS
   Appraiser must:
   □ Hold professional designation or meet education/experience test
   □ Regularly perform appraisals for compensation
   □ Not be excluded by §170(f)(11)(E) (party to transaction, related)

   Appraisal must include:
   □ Description of property
   □ Physical condition (if relevant)
   □ FMV and valuation method
   □ Appraiser qualifications
   □ Date of contribution

4. COMMON FATAL DEFECTS
   - No acknowledgment obtained before filing return
   - Acknowledgment lacks quid pro quo statement
   - Appraisal not "qualified" (appraiser ineligible)
   - Form 8283 not attached to return
   - Appraisal obtained too late (>60 days after donation)

5. QUID PRO PRO CONTRIBUTIONS
   If donor receives goods/services:
   □ Donee must state value of benefit
   □ Deduction = Contribution - FMV of benefit
   □ De minimis benefits ignored (token items)
   □ Intangible religious benefits excluded from reduction

6. AUDIT TRIGGERS
   - Large noncash deductions without appraisal
   - Conservation easement contributions
   - Vehicle donations claimed at high values
   - Art, collectibles, closely-held stock
   - Related party appraisers""",
        key_factors=[
            "Contemporaneous written acknowledgment obtained before filing",
            "Acknowledgment contains required quid pro quo statement",
            "Qualified appraisal for contributions over $5,000",
            "Form 8283 attached with required signatures",
            "Appraisal obtained within 60-day window"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §170", "relevance": "Charitable contribution deduction"},
            {"authority": "IRC", "reference": "IRC §170(f)(8)", "relevance": "Substantiation requirements"},
            {"authority": "IRC", "reference": "IRC §170(f)(11)", "relevance": "Appraisal requirements"},
            {"authority": "Reg", "reference": "Treas. Reg. §1.170A-13", "relevance": "Recordkeeping"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS disallows deductions when: (1) contemporaneous
acknowledgment not obtained; (2) appraisal does not meet qualified appraisal requirements;
(3) Form 8283 not properly completed or attached; (4) appraiser is disqualified;
(5) FMV overstated on noncash contributions.""",
        counter_arguments=[
            "Contemporaneous written acknowledgment obtained and maintained",
            "Qualified appraisal meets all regulatory requirements",
            "Form 8283 properly completed with required signatures",
            "Appraiser meets qualification standards",
            "FMV supported by reasonable valuation methodology"
        ],
        appeals_strategy="""Substantiation failures are often fatal - courts strictly enforce.
If acknowledgment obtained late, argue substantial compliance (rarely successful). If
appraisal deficient, determine if cure is possible. Valuation disputes more negotiable
than procedural failures. Request Appeals consider proportional adjustment if only
FMV contested, not substantiation.""",
        entity_scope=["individual", "c_corporation", "s_corporation", "partnership", "llc", "trust"],
        confidence="high"
    ),

    "qualified_opportunity_zone": DoctrineBlock(
        topic="Qualified Opportunity Zone Investment - §1400Z",
        keywords=["opportunity zone", "1400z", "qof", "qualified opportunity fund",
                  "180 day", "capital gain deferral", "10 year hold",
                  "basis step up", "qozp", "qozb"],
        conclusion_template="""A taxpayer may defer capital gains by investing in a Qualified
Opportunity Fund (QOF) within 180 days of the gain recognition. Benefits include: deferral
until 2026 (or earlier disposition), 10% basis increase if held 5 years (no longer available
for new investments), and permanent exclusion of post-investment gain if held 10 years.
The QOF must hold at least 90% of assets in Qualified Opportunity Zone Property (QOZP).""",
        reasoning_framework="""
QUALIFIED OPPORTUNITY ZONE — COMPLIANCE FRAMEWORK:

1. ELIGIBLE GAIN
   Capital gains eligible for deferral:
   □ Short-term or long-term capital gains
   □ §1231 gains (treated as capital)
   □ Gains from sale to unrelated party
   □ Gains from stocks, real estate, business assets

   NOT ELIGIBLE:
   - Ordinary income
   - Gain from related party sale (generally)
   - Previously deferred gain from another QOF

2. 180-DAY INVESTMENT REQUIREMENT
   Investment must occur within 180 days of gain recognition

   START DATE varies by gain type:
   □ Sale/exchange: Date of sale
   □ Partnership gain: Last day of partnership tax year, OR
     Elect to use date gain would be recognized (K-1 date)
   □ Installment sale: Date of each payment

   STRICT DEADLINE: No extensions, no relief for late investment

3. QUALIFIED OPPORTUNITY FUND (QOF) REQUIREMENTS
   QOF must be:
   □ Corporation or partnership (including LLC)
   □ Organized for investing in QOZP
   □ Self-certified on Form 8996

   90% TEST: At least 90% of assets must be QOZP
   Tested semiannually (6-month intervals)
   Penalty for failure: Monthly penalty on shortfall

4. QUALIFIED OPPORTUNITY ZONE PROPERTY (QOZP)
   Three types:
   (A) QOZ stock - stock in QOZ business (QOZB)
   (B) QOZ partnership interest - interest in QOZB
   (C) QOZ business property - Tangible property in QOZ

   Direct property must meet "original use" or "substantial improvement" test

5. SUBSTANTIAL IMPROVEMENT TEST
   For acquired property (not original use):
   □ Additions to basis must exceed original basis
   □ Within 30-month period
   □ Land not required to be substantially improved

6. GAIN DEFERRAL AND EXCLUSION
   DEFERRAL: Original gain deferred until earlier of:
   - Sale of QOF investment
   - December 31, 2026

   BASIS STEP-UP (No longer available for new investments):
   - 5-year hold: 10% basis increase (investment by 12/31/2019)
   - 7-year hold: Additional 5% (15% total) (investment by 12/31/2019)

   10-YEAR EXCLUSION:
   If held 10 years: Basis in QOF = FMV at sale
   Result: ALL post-investment appreciation tax-free

7. AUDIT TRIGGERS
   - 180-day deadline missed
   - QOF fails 90% test
   - Substantial improvement not completed in 30 months
   - Working capital safe harbor violated
   - Non-qualifying property in QOZ business""",
        key_factors=[
            "180-day investment deadline strictly met",
            "QOF self-certification on Form 8996",
            "90% asset test satisfied at each testing date",
            "Substantial improvement test met within 30 months",
            "10-year holding period tracked for exclusion eligibility"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §1400Z-2", "relevance": "QOZ gain deferral"},
            {"authority": "Reg", "reference": "Treas. Reg. §1.1400Z2(a)-1", "relevance": "Deferral election"},
            {"authority": "Reg", "reference": "Treas. Reg. §1.1400Z2(d)-1", "relevance": "QOF requirements"},
            {"authority": "Reg", "reference": "Treas. Reg. §1.1400Z2(d)-2", "relevance": "QOZB requirements"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS denies QOZ benefits when: (1) 180-day investment window
missed; (2) QOF fails 90% asset test; (3) substantial improvement test not met;
(4) working capital held too long; (5) business not located in QOZ;
(6) self-certification not timely filed.""",
        counter_arguments=[
            "180-day deadline met with documentation of gain date and investment",
            "Form 8996 timely filed with qualifying asset schedule",
            "90% test satisfied at each semiannual testing date",
            "Substantial improvement documented within 30-month window",
            "Working capital safe harbor requirements met"
        ],
        appeals_strategy="""QOZ issues often involve timing (180-day) or testing (90%).
Present documentation of gain recognition date and investment date. If 90% test failed,
determine if penalty regime applies vs. complete disqualification. Substantial improvement
requires contemporaneous records of capital expenditures.""",
        entity_scope=["individual", "c_corporation", "s_corporation", "partnership", "llc", "trust"],
        confidence="high"
    ),

    "form_3520_foreign_trust": DoctrineBlock(
        topic="Foreign Trust Reporting - Form 3520/3520-A Penalties",
        keywords=["foreign trust", "3520", "3520-A", "foreign gift",
                  "foreign inheritance", "responsible party", "beneficiary statement",
                  "35 percent penalty", "grantor trust"],
        conclusion_template="""U.S. persons with foreign trust transactions must file Form 3520
(Annual Return to Report Transactions with Foreign Trusts) and/or Form 3520-A (Annual
Information Return of Foreign Trust with U.S. Owner). Penalties are severe: 35% of gross
value for failure to report transfers, 5% of trust value for failure to report ownership,
and 35% of distributions for failure to report receipts. Reasonable cause may abate penalties.""",
        reasoning_framework="""
FOREIGN TRUST REPORTING — PENALTY AVOIDANCE:

1. FORM 3520 FILING REQUIREMENTS
   U.S. person must file if:
   □ Treated as owner of foreign trust (grantor trust rules)
   □ Transferred property to foreign trust
   □ Received distribution from foreign trust
   □ Received large gift/bequest from foreign person (>$100K)

   Due date: With income tax return (with extensions)

2. FORM 3520-A REQUIREMENTS
   Foreign trust with U.S. owner must file Form 3520-A
   Provides: Foreign Grantor Trust Beneficiary Statement
             Foreign Grantor Trust Owner Statement

   Due date: March 15 (calendar year trust) with extensions

   IF TRUST FAILS TO FILE: U.S. owner must complete substitute 3520-A

3. PENALTY STRUCTURE
   Form 3520 penalties:
   □ Failure to report transfer: 35% of gross value transferred
   □ Failure to report ownership: 5% of trust assets (per year)
   □ Failure to report distribution: 35% of gross distribution

   Form 3520-A penalties:
   □ Failure to file: 5% of trust assets
   □ Failure to provide beneficiary/owner statements: $10,000

   Penalties are PER OCCURRENCE, can stack

4. REASONABLE CAUSE DEFENSE
   Penalties may be abated if:
   □ Failure due to reasonable cause, AND
   □ Not due to willful neglect

   Factors considered:
   - Complexity of reporting
   - Reliance on professional advice
   - First-time penalty
   - Prompt correction when discovered

   IRS Streamlined Procedures available for non-willful failures

5. FOREIGN GIFT REPORTING (Form 3520, Part IV)
   Report gifts/bequests from:
   □ Foreign person >$100,000 (aggregate per year)
   □ Foreign corporation/partnership >$18,567 (2024)

   Penalty: 5% per month of unreported amount (up to 25%)

6. COMMON COMPLIANCE FAILURES
   - Unaware of foreign trust existence (inherited interest)
   - Trust restructuring not reported
   - Gifts from foreign family not reported
   - Failure to obtain 3520-A from foreign trustee
   - Late filing without extension

7. AUDIT TRIGGERS
   - FBAR showing foreign accounts related to trust
   - Form 8938 disclosures referencing foreign trust
   - Large wire transfers from foreign sources
   - Estate with foreign assets
   - Expatriation of settlor or beneficiary""",
        key_factors=[
            "All foreign trust transactions identified and reported",
            "Form 3520 filed timely with return (or extension)",
            "Form 3520-A obtained from foreign trustee or substitute filed",
            "Foreign gifts over threshold reported",
            "Reasonable cause documentation maintained"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §6048", "relevance": "Foreign trust reporting"},
            {"authority": "IRC", "reference": "IRC §6039F", "relevance": "Foreign gift reporting"},
            {"authority": "IRC", "reference": "IRC §6677", "relevance": "Penalties"},
            {"authority": "Proc", "reference": "Rev. Proc. 2020-17", "relevance": "Late filing relief"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS asserts penalties when: (1) Form 3520 not filed or
filed late; (2) 3520-A not obtained from foreign trustee; (3) foreign gifts not reported;
(4) reasonable cause claim lacks documentation; (5) pattern of non-compliance across
multiple years.""",
        counter_arguments=[
            "Reasonable cause: Relied on professional advice",
            "First-time penalty with prompt correction",
            "Streamlined procedures used for non-willful failures",
            "Complexity of foreign trust rules supports reasonable cause",
            "No tax due on transaction reduces penalty appropriateness"
        ],
        appeals_strategy="""Foreign trust penalties are severe but reasonable cause defense
available. Document reliance on professional advice. If penalty stacks across years,
request consolidation. Consider Streamlined Filing Compliance Procedures for non-willful
failures. First-time abatement may apply to some penalties.""",
        entity_scope=["individual", "trust"],
        confidence="high"
    ),

    # =========================================================================
    # PARTNER-LEVEL JUDGMENT DOCTRINE — ADVANCED CORPORATE/PARTNERSHIP
    # =========================================================================

    "personal_holding_company": DoctrineBlock(
        topic="Personal Holding Company Tax - §542",
        keywords=["personal holding company", "phc", "542", "undistributed income",
                  "phc tax", "60 percent test", "50 percent test",
                  "passive income", "trapped earnings", "dividend requirement"],
        conclusion_template="""A corporation is a personal holding company (PHC) if it meets
both: (1) the 50% stock ownership test (5 or fewer individuals own >50% of stock value),
and (2) the 60% income test (≥60% of adjusted ordinary gross income is PHC income).
PHC status triggers a 20% penalty tax on undistributed PHC income. Dividends paid
(including consent dividends and deficiency dividends) reduce PHC income.""",
        reasoning_framework="""
PERSONAL HOLDING COMPANY — §542 ANALYSIS:

1. STOCK OWNERSHIP TEST (§542(a)(2))
   □ 5 or fewer individuals must own >50% of stock value
   □ Measured at ANY point during last half of tax year
   □ Attribution rules apply (§544)
   □ Options treated as stock (§544(a)(3))

   ATTRIBUTION (§544):
   - Family: Spouse, siblings, ancestors, descendants
   - Entity to owner (proportionate)
   - Trusts to beneficiaries
   - Partnerships to partners

2. 60% INCOME TEST (§542(a)(1))
   PHC income includes:
   □ Dividends, interest, royalties, annuities
   □ Rents (unless >50% of AOGI and certain conditions met)
   □ Personal service contracts (named/designated individual)
   □ Compensation for use of corporate property by 25%+ shareholder
   □ Copyright royalties (unless active business)

   RENT EXCLUSION from PHC income if:
   - Rents ≥50% of adjusted ordinary gross income
   - Dividends paid = non-rent PHC income less 10% of OGI

3. PHC TAX CALCULATION (§541)
   Undistributed PHC Income (UPHCI):
   = Taxable income
   - Federal income taxes
   - Charitable contributions (up to 10% limit)
   - Net capital gains (less attributable taxes)
   - Dividends paid deduction

   PHC TAX = 20% × UPHCI

4. AVOIDING PHC TAX
   □ Distribute dividends before year-end
   □ Consent dividends (§565) — shareholders include in income without cash
   □ Deficiency dividends (§547) — post-determination correction
   □ Restructure income to fail 60% test
   □ Manage ownership to fail 50% test

5. AUDIT ISSUES
   - Unreported PHC status
   - Dividend deduction timing (must be within 2½ months)
   - Incorrect PHC income calculation
   - Attribution rules misapplied
   - Consent dividend elections defective""",
        key_factors=[
            "Stock ownership traced through attribution rules",
            "PHC income properly classified",
            "Rent income analyzed for exclusion eligibility",
            "Dividend paid deduction properly calculated",
            "Consent dividend elections properly executed"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §541", "relevance": "PHC tax imposed"},
            {"authority": "IRC", "reference": "IRC §542", "relevance": "PHC definition"},
            {"authority": "IRC", "reference": "IRC §543", "relevance": "PHC income"},
            {"authority": "IRC", "reference": "IRC §544", "relevance": "Attribution rules"},
            {"authority": "IRC", "reference": "IRC §562", "relevance": "Dividends paid deduction"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges PHC positions when: (1) taxpayer fails
to recognize PHC status; (2) dividends paid after 2½ month window; (3) consent dividends
not properly elected; (4) rental income improperly excluded from PHC income;
(5) attribution rules not applied to stock ownership.""",
        counter_arguments=[
            "Stock ownership fails 50% test under §544 attribution",
            "PHC income below 60% of AOGI",
            "Rent exclusion requirements satisfied",
            "Timely dividends paid within 2½ months of year-end",
            "Consent dividend elections properly executed"
        ],
        appeals_strategy="""PHC status is binary — focus on one failing test. If ownership
disputed, trace through attribution carefully. If income test disputed, reclassify rent/royalty
income. Deficiency dividend procedure available post-determination to eliminate tax.""",
        entity_scope=["c_corporation"],
        confidence="high"
    ),

    "partnership_hot_assets": DoctrineBlock(
        topic="Partnership Hot Assets - §751 Ordinary Income",
        keywords=["hot assets", "751", "unrealized receivables", "inventory items",
                  "partnership sale", "ordinary income", "substantially appreciated",
                  "look-through", "partnership interest sale"],
        conclusion_template="""When a partner sells a partnership interest, §751 requires the
seller to recognize ordinary income (not capital gain) to the extent the sale price is
attributable to 'hot assets' — unrealized receivables and inventory items. This prevents
conversion of ordinary income into capital gain through sale of a partnership interest.
The partnership must provide the selling partner with a statement of hot asset values.""",
        reasoning_framework="""
PARTNERSHIP HOT ASSETS — §751 ANALYSIS:

1. HOT ASSET CATEGORIES (§751(c), (d))

   UNREALIZED RECEIVABLES (§751(c)):
   □ Rights to payment for services rendered (not yet received)
   □ Rights to payment for goods delivered (accrual method)
   □ §1245 depreciation recapture potential
   □ §1250 depreciation recapture potential
   □ Other ordinary income recapture (§1252, §1254, etc.)
   □ Market discount bonds

   INVENTORY ITEMS (§751(d)):
   □ Items held for sale to customers
   □ Items that would be inventory if held by selling partner
   □ Items producing ordinary income if sold by partnership
   □ "Substantially appreciated" NOT required after 2017

2. SALE OF PARTNERSHIP INTEREST
   Step 1: Determine total gain/loss on sale
   Step 2: Allocate purchase price to hot assets (FMV)
   Step 3: Calculate ordinary income = Hot asset FMV - Partner's share of inside basis
   Step 4: Remaining gain/loss = Capital gain/loss

   EXAMPLE:
   - Partner sells 25% interest for $300,000
   - Share of hot assets: FMV $60,000, basis $20,000
   - Ordinary income = $40,000
   - Capital gain = $300,000 - (outside basis + $40,000)

3. DISTRIBUTION OF HOT ASSETS (§751(b))
   When partner receives disproportionate distribution:
   □ Treated as taxable exchange
   □ Partner receiving less than share → deemed sale
   □ Partner receiving more than share → deemed purchase
   □ Extremely complex calculations

4. INFORMATION REQUIREMENTS
   Partnership MUST provide selling partner:
   □ Schedule of §751 property
   □ Partnership's basis in §751 property
   □ Fair market value of §751 property
   □ Selling partner's share of each

5. AUDIT ISSUES
   - Failure to report ordinary income portion
   - Incorrect valuation of receivables/inventory
   - Recapture potential not included
   - Distribution transactions mischaracterized
   - Information statement not provided

6. PLANNING CONSIDERATIONS
   □ Time sale to minimize unrealized receivables
   □ Consider installment sale (§453 limits apply)
   □ Evaluate redemption vs. sale structure
   □ Contribution of hot assets before sale""",
        key_factors=[
            "Hot assets identified and valued at FMV",
            "Unrealized receivables include recapture potential",
            "Inventory items valued (appreciation not required)",
            "Partner's share of inside basis determined",
            "Ordinary income properly reported"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §751(a)", "relevance": "Sale rules"},
            {"authority": "IRC", "reference": "IRC §751(b)", "relevance": "Distribution rules"},
            {"authority": "IRC", "reference": "IRC §751(c)", "relevance": "Unrealized receivables"},
            {"authority": "IRC", "reference": "IRC §751(d)", "relevance": "Inventory items"},
            {"authority": "Reg", "reference": "Reg. §1.751-1", "relevance": "Hot asset rules"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges §751 positions when: (1) seller fails to
report ordinary income portion; (2) hot assets undervalued; (3) recapture potential
not included in unrealized receivables; (4) disproportionate distribution not reported;
(5) §751(b) exchange treatment not applied.""",
        counter_arguments=[
            "Hot asset schedule obtained from partnership",
            "FMV supported by appraisal or market data",
            "Recapture potential calculated correctly",
            "Partner's share of inside basis documented",
            "Capital gain/ordinary income bifurcation accurate"
        ],
        appeals_strategy="""§751 issues are mathematical. Focus on valuation disputes and
whether assets qualify as hot. Recapture potential is often missed — ensure
§1245/§1250 recapture included. If distribution involved, §751(b) calculations are
extremely complex — request specialist consideration.""",
        entity_scope=["partnership", "llc"],
        confidence="high"
    ),

    "qsbs_exclusion": DoctrineBlock(
        topic="Qualified Small Business Stock Exclusion - §1202",
        keywords=["qsbs", "1202", "qualified small business stock", "100 percent exclusion",
                  "$10 million", "small business stock", "c corp stock gain",
                  "startup stock", "founder stock exclusion"],
        conclusion_template="""Section 1202 provides up to 100% exclusion of gain on sale of
qualified small business stock (QSBS) held more than 5 years. The exclusion is capped
at the greater of $10 million or 10× the adjusted basis of stock sold. Stock must be
acquired at original issuance from a C corporation with gross assets ≤$50 million.
The corporation must be an active business (not services, finance, hospitality, etc.).""",
        reasoning_framework="""
SECTION 1202 — QSBS EXCLUSION ANALYSIS:

1. EXCLUSION PERCENTAGE (by acquisition date)
   □ Pre-February 18, 2009: 50% exclusion
   □ February 18, 2009 - September 27, 2010: 75% exclusion
   □ After September 27, 2010: 100% exclusion

   Non-excluded portion: 28% rate (§1(h)(4)) — 7% AMT preference (pre-100%)

2. QUALIFICATION REQUIREMENTS
   A. At Acquisition:
      □ C corporation at issuance
      □ Gross assets ≤$50 million before AND immediately after issuance
      □ Stock acquired at original issuance (cash, property, services)
      □ Active business requirement met (80% of assets)

   B. At Sale:
      □ Held for more than 5 years
      □ C corporation status maintained
      □ Active business requirement met substantially all of holding period

3. ACTIVE BUSINESS REQUIREMENT (§1202(e))
   EXCLUDED BUSINESSES (no QSBS treatment):
   □ Professional services (health, law, engineering, accounting, etc.)
   □ Banking, insurance, financing, leasing
   □ Farming
   □ Hotels, motels, restaurants
   □ Mining, oil & gas extraction

   QUALIFIED: Technology, manufacturing, retail, software, biotech

4. $50 MILLION GROSS ASSET TEST
   □ Cash plus aggregate adjusted bases of other assets
   □ Tested immediately before AND after issuance
   □ Includes assets of subsidiaries
   □ Contributions to capital count
   □ FMV of contributed property (not basis)

5. GAIN EXCLUSION LIMITS
   Per-issuer, per-taxpayer limit:
   = Greater of: $10 million OR 10 × adjusted basis

   EXAMPLE:
   - Invested $500,000 for founder stock
   - Limit = Greater of $10M or $5M = $10 million exclusion available
   - Sold for $25 million → $10M excluded, $15M taxable (at 28% rate? Or 20%?)

6. AUDIT TRIGGERS
   - Large gain exclusions ($10M+)
   - Gross asset test documentation absent
   - Active business qualification marginal
   - Stock acquired in secondary transaction
   - S corp history during holding period
   - Services business claiming exclusion

7. DOCUMENTATION REQUIREMENTS
   □ Certification from corporation re: qualification
   □ Gross asset test compliance at issuance
   □ Active business test compliance
   □ Original issuance documentation
   □ Holding period records""",
        key_factors=[
            "Stock acquired at original issuance from C corporation",
            "Gross assets ≤$50 million at issuance",
            "Active business requirement satisfied",
            "More than 5-year holding period",
            "Gain within $10M/10× basis limits"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §1202", "relevance": "QSBS exclusion"},
            {"authority": "IRC", "reference": "IRC §1202(c)", "relevance": "QSBS definition"},
            {"authority": "IRC", "reference": "IRC §1202(d)", "relevance": "Qualified corporation"},
            {"authority": "IRC", "reference": "IRC §1202(e)", "relevance": "Active business"},
            {"authority": "IRS", "reference": "Notice 2010-65", "relevance": "100% exclusion guidance"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges QSBS exclusion when: (1) gross asset test
not documented at issuance; (2) active business requirement failed (services company);
(3) stock not acquired at original issuance; (4) S corporation election during holding
period; (5) exclusion limit exceeded; (6) holding period not met.""",
        counter_arguments=[
            "Corporation certified §1202 compliance at issuance",
            "Gross asset test documented with balance sheet",
            "Active business test met (not excluded category)",
            "Original issuance evidenced by stock ledger",
            "5+ year holding period documented"
        ],
        appeals_strategy="""QSBS issues are factual. Obtain contemporaneous documentation
of gross asset test. Active business test is often disputed — prepare detailed analysis
of business activities and asset deployment. If stock received for services, ensure
no §83 issues that would reset holding period.""",
        entity_scope=["individual", "trust", "estate"],
        confidence="high"
    ),

    "section_1245_recapture": DoctrineBlock(
        topic="Depreciation Recapture - §1245/§1250 Ordinary Income",
        keywords=["1245", "1250", "depreciation recapture", "ordinary income",
                  "section 1245 property", "section 1250 property",
                  "recapture", "tangible property", "real property"],
        conclusion_template="""Section 1245 requires recapture as ordinary income of gain
attributable to depreciation deductions taken on tangible personal property and certain
other property. Section 1250 applies to real property and recaptures only the excess
of accelerated depreciation over straight-line. For real property placed in service
after 1986, straight-line is required, so §1250 recapture is minimal — but 25% unrecaptured
§1250 gain rate applies to remaining depreciation.""",
        reasoning_framework="""
DEPRECIATION RECAPTURE — §1245/§1250 ANALYSIS:

1. SECTION 1245 PROPERTY (Full Recapture)
   □ Tangible personal property (machinery, equipment, vehicles)
   □ Amortizable §197 intangibles
   □ Single-purpose agricultural structures
   □ Storage facilities for petroleum/fungible commodities
   □ Railroad grading and tunnel bores

   RECAPTURE = Lesser of:
   - Recognized gain, OR
   - Total depreciation/amortization taken

   ALL recaptured as ORDINARY INCOME (up to 37%)

2. SECTION 1250 PROPERTY (Partial Recapture)
   □ Real property that is not §1245 property
   □ Buildings, land improvements
   □ Residential rental property
   □ Commercial real estate

   RECAPTURE = "Additional depreciation"
   = Accelerated depreciation minus straight-line equivalent

   For property placed in service AFTER 1986:
   → Straight-line required → No §1250 recapture
   → BUT: "Unrecaptured §1250 gain" taxed at 25% (§1(h)(6))

3. UNRECAPTURED §1250 GAIN (§1(h)(6))
   = Gain attributable to prior straight-line depreciation
   = Taxed at 25% rate (not 20% LTCG)

   EXAMPLE:
   - Building sold for $800,000
   - Original cost: $600,000
   - Accumulated depreciation: $100,000
   - Adjusted basis: $500,000
   - Total gain: $300,000
   - Unrecaptured §1250 gain: $100,000 (taxed at 25%)
   - Remaining gain: $200,000 (taxed at 20% LTCG)

4. SECTION 1231 INTEGRATION
   Order of character determination:
   1. §1245 recapture → Ordinary income
   2. §1250 recapture → Ordinary income
   3. Unrecaptured §1250 → 25% rate
   4. Remaining §1231 gain → Long-term capital gain
   5. §1231 lookback (5-year netting)

5. INSTALLMENT SALES
   §1245/§1250 recapture CANNOT be deferred
   → Ordinary income recognized in year of sale
   → Remaining gain eligible for installment treatment

6. LIKE-KIND EXCHANGES
   Recapture is "tacked" to replacement property
   → Deferred, not eliminated
   → Triggers on ultimate taxable disposition

7. AUDIT ISSUES
   - Incorrect property classification
   - Depreciation history not reconstructed
   - §1245 recapture not reported separately
   - Installment treatment claimed on recapture
   - Unrecaptured §1250 gain undertaxed""",
        key_factors=[
            "Property correctly classified as §1245 or §1250",
            "Depreciation history accurately reconstructed",
            "§1245 recapture limited to gain",
            "Unrecaptured §1250 gain identified",
            "Proper tax rate applied (ordinary/25%/20%)"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §1245", "relevance": "Personal property recapture"},
            {"authority": "IRC", "reference": "IRC §1250", "relevance": "Real property recapture"},
            {"authority": "IRC", "reference": "IRC §1(h)(6)", "relevance": "Unrecaptured §1250 gain"},
            {"authority": "IRC", "reference": "IRC §1231", "relevance": "Section 1231 property"},
            {"authority": "Reg", "reference": "Reg. §1.1245-1", "relevance": "Recapture rules"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges recapture positions when: (1) §1245 property
misclassified as §1250; (2) depreciation history incomplete; (3) recapture ordinary
income not reported; (4) installment treatment claimed on recapture portion;
(5) unrecaptured §1250 gain taxed at 20% instead of 25%.""",
        counter_arguments=[
            "Property classification supported by asset records",
            "Complete depreciation schedule maintained",
            "§1245 recapture properly calculated and reported",
            "Unrecaptured §1250 gain correctly taxed at 25%",
            "Form 4797 properly completed"
        ],
        appeals_strategy="""Recapture issues are computational. Provide complete depreciation
history for each asset. If classification disputed, analyze asset function and use.
Cost segregation studies may support favorable classification but require engineering
documentation.""",
        entity_scope=["individual", "c_corporation", "s_corporation", "partnership", "trust"],
        confidence="high"
    ),

    "pfic_taxation": DoctrineBlock(
        topic="Passive Foreign Investment Company - §1291 (PFIC)",
        keywords=["pfic", "passive foreign investment company", "1291", "foreign fund",
                  "qef", "mark to market", "excess distribution",
                  "foreign mutual fund", "pfic tax"],
        conclusion_template="""A PFIC is a foreign corporation where either: (1) 75%+ of gross
income is passive income, OR (2) 50%+ of assets produce passive income. U.S. shareholders
of PFICs face punitive taxation under the default §1291 regime: deferred tax plus
interest on 'excess distributions' and gain on sale. QEF and mark-to-market elections
provide alternative (often preferable) treatment.""",
        reasoning_framework="""
PFIC — PASSIVE FOREIGN INVESTMENT COMPANY ANALYSIS:

1. PFIC DEFINITION (§1297)
   A foreign corporation is a PFIC if:

   INCOME TEST (§1297(a)(1)):
   □ 75%+ of gross income is passive income

   OR ASSET TEST (§1297(a)(2)):
   □ 50%+ of assets (avg FMV) produce passive income

   PASSIVE INCOME includes:
   - Dividends, interest, royalties, rents, annuities
   - Net gain from commodity transactions
   - Net foreign currency gain
   - Income equivalent to interest
   - Gain from passive assets

   EXCEPTIONS:
   - Active banking/insurance income
   - Look-through rules for 25%+ subsidiaries
   - Start-up exception (first year only)

2. DEFAULT TAXATION — §1291 "EXCESS DISTRIBUTION" REGIME
   Applies if NO election made:

   EXCESS DISTRIBUTION:
   = Current distribution − (125% × avg of prior 3 years)
   Allocated ratably over holding period
   Each prior year portion: Tax at highest rate + interest

   GAIN ON SALE:
   Treated as excess distribution — same punitive treatment

   EXAMPLE:
   - $100,000 gain on PFIC sale after 5-year hold
   - $20,000 allocated to each year
   - Each year: Taxed at 37% + interest from that year
   - Effective rate often 50%+

3. QEF ELECTION — QUALIFIED ELECTING FUND (§1293)
   Shareholder elects to:
   □ Include pro rata share of earnings annually
   □ Ordinary income for passive earnings
   □ LTCG for net capital gains
   □ Increases basis → No double tax on sale

   ADVANTAGES:
   - Avoids interest charge
   - Current inclusion at regular rates
   - Basis step-up

   REQUIREMENTS:
   - PFIC must provide annual information statement
   - Elect on Form 8621

4. MARK-TO-MARKET ELECTION (§1296)
   □ Recognize gain/loss annually based on FMV change
   □ Gain = ordinary income
   □ Loss = ordinary deduction (limited to prior MTM gains)
   □ Must be "marketable stock"

5. ANNUAL REPORTING — FORM 8621
   Required for ANY U.S. shareholder who:
   □ Owns PFIC stock directly or indirectly
   □ Receives distribution from PFIC
   □ Recognizes gain on PFIC disposition
   □ Makes/has QEF or MTM election

   PENALTY: Failure to file extends statute of limitations

6. AUDIT ISSUES
   - Failure to identify PFIC status
   - Form 8621 not filed
   - §1291 tax calculated incorrectly
   - No election made (default regime applies)
   - Foreign mutual funds overlooked as PFICs""",
        key_factors=[
            "PFIC status determined under income/asset tests",
            "Form 8621 filed annually",
            "Appropriate election made (QEF or MTM)",
            "Excess distribution regime properly applied if no election",
            "Basis adjusted for QEF inclusions"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §1291", "relevance": "Default taxation"},
            {"authority": "IRC", "reference": "IRC §1293", "relevance": "QEF election"},
            {"authority": "IRC", "reference": "IRC §1296", "relevance": "Mark-to-market"},
            {"authority": "IRC", "reference": "IRC §1297", "relevance": "PFIC definition"},
            {"authority": "IRS", "reference": "Form 8621", "relevance": "PFIC reporting"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges PFIC positions when: (1) taxpayer failed to
identify PFIC; (2) Form 8621 not filed; (3) no election made but favorable treatment
claimed; (4) interest charge not computed on excess distributions; (5) foreign mutual
fund held without PFIC analysis.""",
        counter_arguments=[
            "PFIC status analyzed and documented",
            "Form 8621 filed for all PFIC holdings",
            "Timely QEF or MTM election made",
            "§1291 tax properly calculated if no election",
            "Information statements obtained from fund"
        ],
        appeals_strategy="""PFIC issues often involve taxpayer unawareness. Consider late
QEF election under §1295(b) protective election rules. If §1291 regime applies,
verify interest calculations. Purging elections may reset basis. Reasonable cause
defense for Form 8621 penalty.""",
        entity_scope=["individual", "trust", "estate"],
        confidence="high"
    ),

    "step_transaction_doctrine": DoctrineBlock(
        topic="Step Transaction Doctrine - Substance Over Form",
        keywords=["step transaction", "substance over form", "economic substance",
                  "integrated transaction", "binding commitment", "end result",
                  "interdependence test", "prearranged plan"],
        conclusion_template="""The step transaction doctrine collapses a series of formally
separate transactions into a single transaction for tax purposes when they are, in
substance, part of a prearranged plan to achieve an end result. Courts apply three tests:
(1) binding commitment test, (2) end result test, or (3) interdependence test. If applied,
intermediate steps are disregarded and the tax consequences follow the ultimate result.""",
        reasoning_framework="""
STEP TRANSACTION DOCTRINE — ANALYSIS FRAMEWORK:

1. DOCTRINE PURPOSE
   Prevents taxpayers from achieving through multiple steps
   what could not be achieved in a single transaction.

   Core principle: SUBSTANCE over FORM
   Tax consequences follow economic reality, not labels

2. THREE TESTS (Courts apply most appropriate)

   A. BINDING COMMITMENT TEST (narrowest)
      Steps collapsed IF:
      □ At time of first step, binding commitment existed
      □ Commitment to complete subsequent steps
      □ Legal obligation to proceed

      Example: Sale with binding agreement to repurchase

   B. END RESULT TEST (broadest)
      Steps collapsed IF:
      □ Series of closely related steps
      □ Undertaken to reach a particular result
      □ Would not be taken but for achieving end result

      Example: Transfer to sub, then liquidation of sub

   C. INTERDEPENDENCE TEST (moderate)
      Steps collapsed IF:
      □ Each step is so interdependent that
      □ Legal relations created by one step
      □ Would be fruitless without completing others

      Example: Reorganization with prearranged spin-off

3. COMMON APPLICATIONS
   □ Reorganizations with prearranged sale
   □ §351 transfers followed by redemption
   □ Sale-leaseback transactions
   □ Entity formations followed by distributions
   □ Basis-shifting schemes
   □ Circular cash flows

4. TAXPAYER-FAVORABLE APPLICATION
   Doctrine can HELP taxpayers:
   □ Combine steps to achieve tax-free treatment
   □ Example: Failed §351 + subsequent contribution = §351
   □ Require proper substance for protection

5. DEFENSE AGAINST DOCTRINE
   □ Genuine business purpose for each step
   □ Economic substance independent of tax benefits
   □ Time between steps (longer = better)
   □ No binding commitment
   □ Uncertainty in subsequent steps
   □ Independent decision points

6. PLANNING CONSIDERATIONS
   □ Document business purpose for each step
   □ Allow meaningful time between steps
   □ Genuine uncertainty about subsequent transactions
   □ Independent advisors for different steps
   □ Consider substance vs. form from IRS perspective

7. AUDIT TRIGGERS
   - Multi-step transaction with integrated planning memo
   - Short time between related steps
   - Same advisors throughout
   - Circular cash flows
   - End result inconsistent with intermediate forms""",
        key_factors=[
            "Each step has independent business purpose",
            "No binding commitment to complete all steps",
            "Meaningful time elapsed between steps",
            "Genuine uncertainty at each decision point",
            "Economic substance independent of tax benefits"
        ],
        primary_authority=[
            {"authority": "Case", "reference": "Commissioner v. Court Holding Co., 324 U.S. 331", "relevance": "Substance doctrine"},
            {"authority": "Case", "reference": "Gregory v. Helvering, 293 U.S. 465", "relevance": "Economic substance"},
            {"authority": "Case", "reference": "McDonald's Restaurants of Illinois v. Commissioner", "relevance": "Interdependence test"},
            {"authority": "IRC", "reference": "IRC §7701(o)", "relevance": "Codified economic substance"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS invokes step transaction doctrine when: (1) multiple
steps achieve result not available directly; (2) planning documents show prearranged
plan; (3) short time between steps; (4) circular cash flows; (5) no business purpose
other than tax avoidance for intermediate steps.""",
        counter_arguments=[
            "Each step had independent business purpose",
            "No binding commitment existed at first step",
            "Substantial time elapsed between steps",
            "Genuine business uncertainty at each stage",
            "Economic substance exists apart from tax benefits"
        ],
        appeals_strategy="""Step transaction is highly fact-dependent. Document contemporaneous
business purpose for each step. Time gaps between steps are persuasive. If doctrine
applies, argue which test should apply (narrower is better for taxpayer). Consider
whether doctrine could actually help achieve desired treatment.""",
        entity_scope=["individual", "c_corporation", "s_corporation", "partnership", "trust"],
        confidence="high"
    ),

    "estate_freeze_2701": DoctrineBlock(
        topic="Estate Freeze Transactions - §2701 Valuation Rules",
        keywords=["estate freeze", "2701", "preferred stock", "family limited partnership",
                  "valuation discount", "gift tax", "freeze transaction",
                  "retained interest", "applicable retained interest"],
        conclusion_template="""Section 2701 provides special valuation rules for transfers of
interests in corporations or partnerships to family members when the transferor retains
certain 'applicable retained interests.' Under §2701, retained distribution rights may
be valued at zero (the 'zero-value rule'), which can dramatically increase the value
of the gift. Exceptions apply for qualified payments and proportionate interests.""",
        reasoning_framework="""
SECTION 2701 — ESTATE FREEZE VALUATION ANALYSIS:

1. WHAT IS AN ESTATE FREEZE?
   Transfer of growth/common interests to next generation
   While retaining income/preferred interests
   Goal: Lock in current value, shift future appreciation

   EXAMPLE:
   Parent creates LLC, retains 8% preferred return
   Gifts common interests to children
   Future growth passes outside estate

2. WHEN §2701 APPLIES
   A. Transfer to family member of:
      □ Equity interest in corporation, OR
      □ Equity interest in partnership

   B. Transferor (or applicable family member) retains:
      □ "Applicable retained interest" — distribution rights
      □ That is NOT a qualified payment

   "APPLICABLE FAMILY MEMBER" (§2701(e)(2)):
   - Transferor's spouse
   - Ancestor of transferor/spouse
   - Spouse of such ancestor

3. THE ZERO-VALUE RULE (§2701(a)(3))
   Applicable retained interests are valued at ZERO unless:
   □ Same class as transferred interest, OR
   □ "Qualified payments" (defined below)

   EFFECT: Gift value = FMV of entity minus $0 retained interest
   = Much larger gift than intended

   EXAMPLE:
   Parent transfers common stock worth $2M (FMV)
   Retains preferred stock with $8M liquidation preference
   If §2701 applies: Gift = $10M (not $2M)

4. QUALIFIED PAYMENTS (§2701(c)(3))
   ESCAPE the zero-value rule:
   □ Cumulative dividends at fixed rate
   □ Payable at least annually
   □ Determined at time of transfer

   CAUTION: Must ACTUALLY pay qualified payments
   §2701(d) — If qualified payments not made, gift tax due

5. EXCEPTIONS — §2701 DOES NOT APPLY
   □ Marketable securities (active market)
   □ Same proportionate interests retained and transferred
   □ No retained "applicable retained interest"
   □ Interest held by non-family member (25%+ test)

6. MINIMUM VALUE RULE (§2701(a)(4))
   Even with zero-value rule, gift cannot exceed:
   □ 10% of entity value for junior equity
   □ Protects against extreme results

7. FAMILY LIMITED PARTNERSHIP PLANNING
   Common §2701 triggers:
   □ GP retains priority distributions
   □ LP interests transferred to children
   □ Carried interest arrangements

   PLANNING: Use qualified payments or proportionate interests

8. AUDIT ISSUES
   - §2701 not considered in gift tax reporting
   - Qualified payment structure defective
   - Qualified payments not actually made
   - Valuation ignores zero-value rule
   - Minimum value rule not applied""",
        key_factors=[
            "Transfer to family member identified",
            "Applicable retained interest analyzed",
            "Zero-value rule application evaluated",
            "Qualified payment structure properly designed",
            "§2701(d) compliance for payment timing"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §2701", "relevance": "Special valuation rules"},
            {"authority": "IRC", "reference": "IRC §2701(c)(3)", "relevance": "Qualified payments"},
            {"authority": "IRC", "reference": "IRC §2701(d)", "relevance": "Unpaid qualified payments"},
            {"authority": "Reg", "reference": "Reg. §25.2701-1", "relevance": "Valuation rules"},
            {"authority": "Reg", "reference": "Reg. §25.2701-4", "relevance": "Qualified payment election"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS applies §2701 zero-value rule when: (1) family transfer
with retained preferred interest; (2) distribution rights not qualified payments;
(3) gift value understated on Form 709; (4) qualified payments not actually made;
(5) minimum value rule not respected.""",
        counter_arguments=[
            "Transaction uses qualified payment structure",
            "Proportionate interests retained and transferred",
            "Qualified payments made on schedule",
            "Minimum value rule properly applied",
            "§2701 exception applies (same class/marketable)"
        ],
        appeals_strategy="""§2701 issues are technical. If zero-value rule applies, consider
whether qualified payment election was properly made. If qualified payments missed,
calculate gift tax due under §2701(d). Verify proportionate interest exception not
available. Consider minimum value rule protection.""",
        entity_scope=["individual", "trust", "estate"],
        confidence="high"
    ),

    "tax_shelter_penalties_6707a": DoctrineBlock(
        topic="Tax Shelter Disclosure and Penalties - §6707A/§6662A",
        keywords=["tax shelter", "6707a", "6662a", "reportable transaction",
                  "material advisor", "listed transaction", "disclosure penalty",
                  "schedule m-1", "confidential transaction"],
        conclusion_template="""Participants in 'reportable transactions' must disclose them on
Form 8886. Material advisors must report on Form 8918. Failure triggers severe penalties:
§6707A imposes $10,000-$200,000 penalties for non-disclosure by participants; §6707
imposes similar penalties on advisors. §6662A imposes 20-30% accuracy penalties on
understatements from reportable transactions with extended statute of limitations.""",
        reasoning_framework="""
TAX SHELTER DISCLOSURE — §6707A/§6662A ANALYSIS:

1. REPORTABLE TRANSACTION CATEGORIES (Reg. §1.6011-4)

   A. LISTED TRANSACTIONS
      □ Identified by IRS as abusive (Notices)
      □ Examples: Son-of-BOSS, CARDS, SILO
      □ Highest penalties — presumed abusive

   B. CONFIDENTIAL TRANSACTIONS
      □ Advisor imposes confidentiality condition
      □ Advisor receives fee ≥$250,000 (individuals)
      □ Or ≥$50,000 minimum fee regardless of outcome

   C. TRANSACTIONS WITH CONTRACTUAL PROTECTION
      □ Refund/contingent fee if tax benefits disallowed
      □ Insurance protection against disallowance

   D. LOSS TRANSACTIONS
      □ Losses exceeding thresholds:
        - Individuals: ≥$2M in single year or ≥$4M over combination
        - Corporations: ≥$10M single year or ≥$20M combination
        - Partnerships (individual): ≥$2M/$4M
        - S Corps: ≥$2M/$4M or ≥$200,000 if ≥20% §1202 stock

   E. TRANSACTIONS OF INTEREST
      □ Designated by IRS as potentially abusive
      □ IRS gathering information

2. DISCLOSURE REQUIREMENTS
   PARTICIPANTS (§6011):
   □ Form 8886 with return for each reportable transaction
   □ Copy to Office of Tax Shelter Analysis (OTSA)
   □ Due: With return (or by return due date)

   MATERIAL ADVISORS (§6111):
   □ Form 8918 within defined time periods
   □ Maintain investor list for 7 years (§6112)

3. PENALTY STRUCTURE (§6707A)
   PARTICIPANTS:
   □ Listed transactions: $200,000 (corporations) / $100,000 (others)
   □ Other reportable: $10,000
   □ Can be waived for reasonable cause

   MATERIAL ADVISORS (§6707):
   □ Listed: Greater of $200,000 or 50% of fees
   □ Other: $50,000

4. ACCURACY PENALTIES (§6662A)
   Understatements from reportable transactions:
   □ 20% penalty (30% if not disclosed)
   □ No reasonable cause exception for listed transactions
   □ Enhanced reasonable cause for others

5. STATUTE OF LIMITATIONS
   Normal 3-year extended to:
   □ 6 years if >25% gross income omitted
   □ Unlimited if fraud
   □ Special rules for reportable transactions

6. AUDIT ISSUES
   - Form 8886 not filed
   - Transaction meets definition but not disclosed
   - Listed transaction participation denied
   - Material advisor failed to file Form 8918
   - Investor lists not maintained""",
        key_factors=[
            "Transaction analyzed against all reportable categories",
            "Form 8886 filed with return and copy to OTSA",
            "Material advisor obligations evaluated",
            "Listed transaction status confirmed with IRS notices",
            "Accuracy-related penalty exposure assessed"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §6707A", "relevance": "Participant penalties"},
            {"authority": "IRC", "reference": "IRC §6707", "relevance": "Advisor penalties"},
            {"authority": "IRC", "reference": "IRC §6662A", "relevance": "Accuracy penalties"},
            {"authority": "IRC", "reference": "IRC §6111", "relevance": "Advisor disclosure"},
            {"authority": "Reg", "reference": "Reg. §1.6011-4", "relevance": "Reportable definitions"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS asserts penalties when: (1) Form 8886 not filed for
reportable transaction; (2) transaction meets listed transaction characteristics;
(3) large loss not disclosed; (4) advisor fees structured as contingent/refundable;
(5) confidentiality imposed on transaction.""",
        counter_arguments=[
            "Transaction does not meet any reportable category",
            "Form 8886 timely filed and copy sent to OTSA",
            "Loss below disclosure thresholds",
            "No confidentiality or fee protection arrangements",
            "Reasonable cause for any disclosure failure"
        ],
        appeals_strategy="""Tax shelter penalties are severe. First, argue transaction is not
reportable. If disclosure was required, establish reasonable cause (reliance on counsel).
For listed transactions, reasonable cause is limited. Consider §6707A penalty waiver
request procedures. Statute of limitations arguments may apply.""",
        entity_scope=["individual", "c_corporation", "s_corporation", "partnership", "trust"],
        confidence="high"
    ),

    "partnership_anti_abuse": DoctrineBlock(
        topic="Partnership Anti-Abuse Rules - Reg. §1.701-2",
        keywords=["partnership anti-abuse", "anti-abuse", "1.701-2", "abuse of entity",
                  "subchapter k", "partnership formation", "partnership abuse",
                  "aggregate theory", "disguised transaction"],
        conclusion_template="""The partnership anti-abuse rule (Reg. §1.701-2) authorizes the IRS
to recast partnership transactions that use Subchapter K to achieve tax results
inconsistent with the intent of the partnership provisions. The rule applies when:
(1) a partnership is formed or used with a principal purpose of tax reduction, AND
(2) the tax reduction is inconsistent with the intent of Subchapter K. The rule can
recharacterize transactions, disregard the partnership, or treat partners as non-partners.""",
        reasoning_framework="""
PARTNERSHIP ANTI-ABUSE RULE — REG. §1.701-2 ANALYSIS:

1. GENERAL ANTI-ABUSE RULE (§1.701-2(b))
   Partnership transactions recast IF:

   A. PRINCIPAL PURPOSE TEST:
      □ Partnership formed/used principally to reduce taxes
      □ Reduction in substantially consistent manner
      □ Applies to aggregate tax liability of all partners

   B. INTENT INCONSISTENCY TEST:
      □ Tax reduction inconsistent with intent of Subchapter K
      □ Intent = underlying policy of partnership provisions
      □ Not just technical compliance with rules

2. ABUSE OF ENTITY RULE (§1.701-2(c))
   Applies when parties use partnership to achieve results that:
   □ Could not be achieved directly
   □ Are inconsistent with arm's-length dealing
   □ Depend on form over substance

3. IRS REMEDIES
   Commissioner may:
   □ Recast transaction for tax purposes
   □ Disregard partnership in whole or part
   □ Treat one or more partners as not partners
   □ Reallocate items among partners
   □ Adjust partner outside basis

4. EXAMPLES OF ABUSE (Reg. §1.701-2(d))
   □ Basis shifting transactions
   □ Artificial loss generation
   □ Character conversion (ordinary ↔ capital)
   □ Circumventing at-risk/passive rules
   □ Leveraged partnership formations
   □ Partnership mergers to shift attributes

5. SAFE HARBOR / LEGITIMATE USES
   Subchapter K specifically PERMITS:
   □ Flexibility in allocating economic items
   □ Pass-through taxation to partners
   □ Non-recognition on formation (§721)
   □ Special allocations with substantial economic effect

   These are NOT abusive merely because they reduce taxes

6. SUBSTANTIAL ECONOMIC EFFECT RELATIONSHIP
   If allocation has substantial economic effect:
   □ Generally not subject to anti-abuse recast
   □ But economic substance still required
   □ Allocation must affect dollar-for-dollar economics

7. PLANNING CONSIDERATIONS
   □ Document business purpose for formation
   □ Ensure economic substance beyond tax
   □ Comply with §704(b) allocation rules
   □ Avoid circular/offset transactions
   □ Consider IRS challenge likelihood

8. AUDIT TRIGGERS
   - Partnerships formed shortly before tax event
   - Special allocations with no business purpose
   - Basis shifting among related parties
   - Large losses without economic exposure
   - Partnership with no business activities""",
        key_factors=[
            "Business purpose for partnership formation documented",
            "Economic substance exists beyond tax reduction",
            "Allocations have substantial economic effect",
            "Transaction could be achieved between unrelated parties",
            "No circular cash flows or offsetting arrangements"
        ],
        primary_authority=[
            {"authority": "Reg", "reference": "Reg. §1.701-2(b)", "relevance": "General anti-abuse rule"},
            {"authority": "Reg", "reference": "Reg. §1.701-2(c)", "relevance": "Abuse of entity rule"},
            {"authority": "Reg", "reference": "Reg. §1.701-2(d)", "relevance": "Examples"},
            {"authority": "IRC", "reference": "IRC §704(b)", "relevance": "Allocation rules"},
            {"authority": "Case", "reference": "TIFD III-E, Inc. v. United States (Castle Harbour)", "relevance": "Partnership abuse"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS invokes anti-abuse when: (1) partnership used primarily
for tax reduction; (2) economic substance is lacking; (3) transaction could not occur
between unrelated parties; (4) allocations inconsistent with economics; (5) basis
shifting among related parties.""",
        counter_arguments=[
            "Partnership formed for legitimate business purpose",
            "Economic substance exists independent of tax benefits",
            "Allocations reflect economic agreement and have substantial economic effect",
            "Arm's-length terms between partners",
            "No circular cash flows or basis manipulation"
        ],
        appeals_strategy="""Anti-abuse arguments are subjective. Focus on documenting business
purpose contemporaneously. Demonstrate economic substance beyond taxes. If allocations
challenged, establish substantial economic effect. Compare to transactions between
unrelated parties. Argue rule should not apply to specifically permitted Subchapter K
flexibility.""",
        entity_scope=["partnership", "llc"],
        confidence="high"
    ),

    "reasonable_cause_penalty_defense": DoctrineBlock(
        topic="Reasonable Cause Penalty Defense - §6664",
        keywords=["reasonable cause", "penalty defense", "6664", "good faith",
                  "penalty abatement", "reliance on professional",
                  "first time abatement", "penalty relief", "willful neglect"],
        conclusion_template="""Most tax penalties can be abated upon showing 'reasonable cause
and good faith' under §6664. The taxpayer must demonstrate: (1) exercise of ordinary
business care and prudence, (2) inability to file correctly despite such care, and
(3) good faith reliance on professional advice where applicable. First-time abatement
is administratively available for certain penalties. Willful neglect defeats penalty
relief.""",
        reasoning_framework="""
REASONABLE CAUSE — PENALTY DEFENSE ANALYSIS:

1. REASONABLE CAUSE STANDARD (§6664(c))
   Penalty waived if taxpayer shows:
   □ Reasonable cause for underpayment, AND
   □ Good faith in attempting compliance

   DEFINITION (Reg. §1.6664-4(b)):
   "Ordinary business care and prudence" considering:
   - Taxpayer's sophistication and experience
   - Complexity of the issue
   - History of compliance
   - Actions taken to determine correct tax

2. RELIANCE ON PROFESSIONAL ADVICE
   Strong defense if taxpayer can show:
   □ Competent professional engaged
   □ All relevant facts provided to advisor
   □ Advisor gave specific advice on issue
   □ Taxpayer relied on that advice in good faith

   REQUIREMENTS (Reg. §1.6664-4(c)):
   - Advisor had expertise in the matter
   - Taxpayer disclosed all relevant facts
   - Advice was specific (not general/boilerplate)
   - Taxpayer actually relied on advice

   DOCUMENTATION:
   - Engagement letters
   - Written advice (memo/email)
   - Evidence of facts provided

3. FACTORS CONSIDERED
   FAVORABLE:
   □ First offense (clean compliance history)
   □ Attempted to comply correctly
   □ Complex issue
   □ Relied on professional advice
   □ Made good faith effort
   □ Timely filed (though incorrect)

   UNFAVORABLE:
   □ Pattern of noncompliance
   □ Ignored obvious requirements
   □ Failed to maintain records
   □ Disregarded clear guidance
   □ Large understatement relative to income
   □ Tax shelter involvement

4. FIRST-TIME ABATEMENT (FTA)
   Administrative relief for certain penalties:
   □ Failure to file (§6651(a)(1))
   □ Failure to pay (§6651(a)(2))
   □ Failure to deposit (§6656)

   REQUIREMENTS:
   - No penalties in prior 3 years
   - All returns filed (or extensions)
   - All taxes paid (or payment agreement)

   Request: Call IRS or write letter citing clean history

5. SPECIFIC PENALTY CATEGORIES
   ACCURACY-RELATED (§6662):
   - Reasonable cause generally available
   - No reasonable cause for listed transactions
   - Enhanced standard for reportable transactions

   FAILURE TO FILE/PAY (§6651):
   - Reasonable cause available
   - First-time abatement available

   FRAUD (§6663):
   - NO reasonable cause defense
   - Civil fraud has clear and convincing standard

6. DOCUMENTATION FOR DEFENSE
   □ Written advice from professionals
   □ Research materials consulted
   □ Records of compliance efforts
   □ Evidence of complexity
   □ Corrective actions taken""",
        key_factors=[
            "Taxpayer exercised ordinary business care",
            "Good faith attempt to comply with tax law",
            "Professional advice obtained and relied upon",
            "All relevant facts disclosed to advisor",
            "Clean compliance history supports relief"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §6664(c)", "relevance": "Reasonable cause waiver"},
            {"authority": "Reg", "reference": "Reg. §1.6664-4", "relevance": "Reasonable cause factors"},
            {"authority": "IRC", "reference": "IRC §6651(a)", "relevance": "Failure to file/pay"},
            {"authority": "IRM", "reference": "IRM 20.1.1.3.6.1", "relevance": "First-time abatement"},
            {"authority": "Case", "reference": "United States v. Boyle, 469 U.S. 241", "relevance": "Reliance on agent"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS denies reasonable cause when: (1) taxpayer sophisticated
enough to know better; (2) issue was straightforward; (3) no documented advice obtained;
(4) pattern of similar failures; (5) noncompliance is substantial; (6) listed/reportable
transaction involved.""",
        counter_arguments=[
            "Taxpayer exercised ordinary business care given circumstances",
            "Relied in good faith on competent professional advice",
            "All relevant facts were disclosed to advisor",
            "First offense with clean compliance history",
            "Complexity of issue supports reasonable cause"
        ],
        appeals_strategy="""Reasonable cause is fact-intensive. Document every effort to comply.
If professional advice involved, get written confirmation of facts provided and advice
received. For first-time abatement, verify 3-year clean history. Consider partial
penalty reduction if full abatement denied. Appeals officers have discretion.""",
        entity_scope=["individual", "c_corporation", "s_corporation", "partnership", "trust"],
        confidence="high"
    ),

    # =========================================================================
    # PARTNER-LEVEL JUDGMENT DOCTRINE — SPECIALIZED AREAS
    # =========================================================================

    "section_280e_cannabis": DoctrineBlock(
        topic="Section 280E - Cannabis Business Deduction Denial",
        keywords=["280e", "cannabis", "marijuana", "controlled substance",
                  "trafficking", "no deductions", "cogs only",
                  "dispensary", "cultivation", "cannabis business"],
        conclusion_template="""Section 280E denies all deductions and credits to any trade or
business that consists of trafficking in controlled substances. Cannabis businesses,
including state-legal dispensaries and cultivators, are subject to 280E because marijuana
remains a Schedule I controlled substance under federal law. The ONLY reduction allowed
is cost of goods sold (COGS), which is not a 'deduction' but rather an adjustment to
gross income.""",
        reasoning_framework="""
SECTION 280E — CANNABIS BUSINESS ANALYSIS:

1. THE STATUTORY PROHIBITION
   §280E: "No deduction or credit shall be allowed for any amount
   paid or incurred during the taxable year in carrying on any
   trade or business if such trade or business consists of trafficking
   in controlled substances..."

   SCOPE:
   □ ALL deductions denied (rent, wages, utilities, insurance)
   □ ALL credits denied (WOTC, R&D, etc.)
   □ Applies regardless of state legality
   □ No reasonable cause exception

2. COST OF GOODS SOLD — THE ONLY RELIEF
   COGS is NOT a "deduction" — it's a component of gross income
   Therefore, COGS reduces gross receipts before 280E applies

   COGS INCLUDES (per §263A):
   □ Direct materials (cannabis, packaging)
   □ Direct labor (cultivation, processing)
   □ Indirect costs allocable to production:
     - Production facility rent
     - Production utilities
     - Production equipment depreciation
     - Quality control
     - Production management

   COGS EXCLUDES:
   □ Selling expenses
   □ General & administrative
   □ Distribution costs
   □ Marketing and advertising
   □ Executive compensation (non-production)

3. TWO-BUSINESS STRATEGY (CHAMP v. Commissioner)
   If taxpayer operates TWO distinct businesses:
   □ One: Cannabis trafficking (subject to 280E)
   □ Two: Non-trafficking (NOT subject to 280E)

   Requirements for separate business:
   - Separate books and records
   - Separate income/expense allocation
   - Genuine independent business purpose
   - Not mere recharacterization

   EXAMPLES:
   - Dispensary + separate wellness consulting
   - Cultivation + separate equipment rental
   - Retail + separate security services

4. AUDIT ISSUES — IRS FOCUS AREAS
   □ COGS inflated with non-production costs
   □ Two-business structure lacks substance
   □ Wages misclassified as production
   □ Facility costs not properly allocated
   □ §263A not properly applied

5. DOCUMENTATION REQUIREMENTS
   □ Detailed cost accounting records
   □ Time tracking for production vs. non-production
   □ Facility space allocation
   □ §263A computations
   □ Separate business substantiation

6. PLANNING CONSIDERATIONS
   □ Maximize allocable costs to COGS
   □ Proper §263A uniform capitalization
   □ Consider vertical integration (more production activity)
   □ Evaluate two-business structures carefully
   □ Monitor federal rescheduling efforts""",
        key_factors=[
            "Cannabis business subject to 280E (federal Schedule I)",
            "Only COGS reduces gross income",
            "§263A uniform capitalization rules apply",
            "Two-business strategy requires genuine substance",
            "Detailed cost allocation records essential"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §280E", "relevance": "Deduction denial"},
            {"authority": "IRC", "reference": "IRC §263A", "relevance": "COGS calculation"},
            {"authority": "Case", "reference": "CHAMP v. Commissioner, T.C. Memo 2007-323", "relevance": "Two business doctrine"},
            {"authority": "Case", "reference": "Californians Helping to Alleviate Med. Problems v. Comm'r", "relevance": "280E scope"},
            {"authority": "Case", "reference": "Alterman v. Commissioner, T.C. Memo 2018-83", "relevance": "COGS limits"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS aggressively applies 280E, denying: (1) expenses claimed
as COGS that are not production costs; (2) two-business deductions where separation lacks
substance; (3) any deduction related to cannabis operations; (4) wage deductions not
clearly production-related.""",
        counter_arguments=[
            "COGS properly computed under §263A",
            "Production vs. non-production costs documented",
            "Two businesses have genuine independent purpose",
            "Facility allocation based on actual use",
            "Time records support labor classification"
        ],
        appeals_strategy="""§280E cases are factual. Focus on proper COGS computation per §263A.
If two-business structure, demonstrate genuine separation. Allocations must be supportable.
Consider timing — federal rescheduling could moot §280E prospectively. Appeals
officers have seen many cannabis cases; documentation is critical.""",
        entity_scope=["individual", "c_corporation", "s_corporation", "partnership", "llc"],
        confidence="high"
    ),

    "material_participation_tests": DoctrineBlock(
        topic="Material Participation Tests - Reg. §1.469-5T",
        keywords=["material participation", "469", "passive activity", "7 tests",
                  "500 hours", "substantially all", "participation test",
                  "rental activity", "passive loss", "participation hours"],
        conclusion_template="""Material participation determines whether an activity is passive
under §469. A taxpayer materially participates if they meet ANY of seven tests under
Reg. §1.469-5T, including: (1) 500+ hours, (2) substantially all participation,
(3) 100+ hours and not less than anyone else, (4) significant participation aggregating
500+ hours, (5) prior 5 of 10 years participation, (6) personal service activity with
3 prior years, or (7) facts and circumstances showing regular, continuous, and substantial
involvement.""",
        reasoning_framework="""
MATERIAL PARTICIPATION — THE SEVEN TESTS:

1. TEST 1: 500 HOURS (Reg. §1.469-5T(a)(1))
   □ Participate >500 hours during year
   □ Most straightforward test
   □ Time log essential for audit

2. TEST 2: SUBSTANTIALLY ALL (Reg. §1.469-5T(a)(2))
   □ Taxpayer's participation constitutes substantially all participation
   □ No specific hour threshold
   □ Useful when sole participant

3. TEST 3: 100 HOURS + NOT LESS THAN ANYONE (Reg. §1.469-5T(a)(3))
   □ Participate >100 hours during year
   □ AND no one else participates more
   □ Includes employees, partners, etc.

4. TEST 4: SIGNIFICANT PARTICIPATION ACTIVITIES (Reg. §1.469-5T(a)(4))
   □ Significant participation activity (SPA): 100+ hours but not material
   □ Aggregate ALL SPAs
   □ If aggregate >500 hours, each SPA becomes material

5. TEST 5: 5 OF 10 PRIOR YEARS (Reg. §1.469-5T(a)(5))
   □ Materially participated in any 5 of prior 10 years
   □ Need not be consecutive
   □ Activity must be same activity

6. TEST 6: PERSONAL SERVICE ACTIVITY (Reg. §1.469-5T(a)(6))
   □ Personal service activity (health, law, engineering, etc.)
   □ Materially participated in any 3 prior years
   □ Years need not be consecutive

7. TEST 7: FACTS AND CIRCUMSTANCES (Reg. §1.469-5T(a)(7))
   □ Regular, continuous, and substantial involvement
   □ MUST participate >100 hours
   □ Spouse's management services don't count
   □ Hardest test — IRS skeptical

WHAT COUNTS AS PARTICIPATION:
□ Work ordinarily done by owner
□ Not investor-type activities (studying financials, monitoring)
□ Travel time to activity generally included
□ Spouse's participation aggregated (§469(h)(5))

WHAT DOESN'T COUNT:
□ Investor activities (reviewing financials)
□ Work not customarily done by owner
□ Work primarily to avoid passive rules

RENTAL ACTIVITIES — SPECIAL RULES:
□ Rental activities are AUTOMATICALLY passive
□ Exception: Real estate professional (§469(c)(7))
□ Requires: 750+ hours AND majority of personal services
□ Must materially participate in each rental (or group election)

DOCUMENTATION REQUIREMENTS:
□ Contemporaneous time logs preferred
□ Calendars, emails, travel records
□ Appointment books
□ Third-party testimony""",
        key_factors=[
            "One of seven tests must be satisfied",
            "Hours documented contemporaneously",
            "Spouse's hours can be aggregated",
            "Investor-type activities excluded",
            "Real estate professional exception requires 750+ hours"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §469(h)", "relevance": "Material participation defined"},
            {"authority": "Reg", "reference": "Reg. §1.469-5T", "relevance": "Seven tests"},
            {"authority": "IRC", "reference": "IRC §469(c)(7)", "relevance": "Real estate professional"},
            {"authority": "Case", "reference": "Assaf v. Commissioner, T.C. Memo 2005-14", "relevance": "Contemporaneous records"},
            {"authority": "Case", "reference": "Goshorn v. Commissioner, T.C. Memo 1993-578", "relevance": "Work nature analysis"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges material participation when: (1) no
contemporaneous time records; (2) claimed hours include investor activities;
(3) work not customarily done by owners; (4) hours reconstructed after audit begins;
(5) real estate professional status claimed without 750+ hours documentation.""",
        counter_arguments=[
            "Contemporaneous time log maintained",
            "Activities constitute work normally done by owners",
            "Hours exclude investor-type monitoring",
            "Test 1 (500+ hours) clearly satisfied",
            "Third-party witnesses confirm participation"
        ],
        appeals_strategy="""Material participation is highly factual. Contemporaneous records
are persuasive; reconstructions are suspect. If records weak, consider Test 2 (substantially
all) or Test 3 (100+ hours, not less than anyone). Spouse aggregation under §469(h)(5)
may help. Real estate professional cases require meticulous hour tracking.""",
        entity_scope=["individual", "trust"],
        confidence="high"
    ),

    "trader_vs_investor": DoctrineBlock(
        topic="Trader vs Investor Status - §475(f) Mark-to-Market Election",
        keywords=["trader", "investor", "475", "mark to market", "securities trader",
                  "trading business", "day trader", "capital loss",
                  "ordinary loss", "trader election"],
        conclusion_template="""A securities trader (not mere investor) can elect §475(f) mark-to-market
accounting, converting capital gains/losses to ordinary income/loss. Trader status requires:
(1) seeking profit from daily market movements, not dividends or appreciation,
(2) substantial and frequent trading activity, and (3) continuous activity throughout
the year. The election eliminates wash sale rules and $3,000 capital loss limitation,
but gains become ordinary income and self-employment tax may apply.""",
        reasoning_framework="""
TRADER VS. INVESTOR — STATUS DETERMINATION:

1. THE CRITICAL DISTINCTION
   INVESTOR:
   □ Holds securities for appreciation/dividends
   □ Capital gain/loss treatment
   □ $3,000 capital loss limitation
   □ Wash sale rules apply
   □ Investment expenses: Misc itemized (suspended 2018-2025)

   TRADER:
   □ Treats trading as business
   □ Without §475 election: Same as investor
   □ With §475 election: Ordinary income/loss
   □ No capital loss limitation
   □ No wash sale rules
   □ Business expenses deductible

2. TRADER STATUS — REQUIRED FACTORS
   A. PROFIT FROM DAILY MOVEMENTS
      □ Seeking to profit from short-term swings
      □ NOT from dividends or long-term appreciation
      □ Holding period typically days/weeks, not months

   B. SUBSTANTIAL ACTIVITY
      □ No bright-line rule
      □ Cases suggest 1,000+ trades/year common
      □ Trading most days market is open
      □ Significant time devoted to trading

   C. CONTINUITY AND REGULARITY
      □ Activity throughout tax year
      □ Not sporadic or seasonal
      □ Treat like full-time job

3. THE §475(f) ELECTION
   REQUIREMENTS:
   □ Must be made by due date (without extension) of prior year return
   □ File statement with return
   □ Identify securities held for trading vs. investment

   EFFECT:
   □ Securities marked to market at year-end
   □ Gains/losses are ORDINARY
   □ No wash sale rules (§1091 doesn't apply)
   □ No $3,000 capital loss limitation
   □ BUT: Gains taxed as ordinary income (up to 37%)

4. FACTORS COURTS CONSIDER (Endicott v. Commissioner)
   □ Trading frequency and volume
   □ Dollar amounts involved
   □ Time devoted to activity
   □ Holding periods of securities
   □ Source of profit (speculation vs. dividends)
   □ Trading vs. long-term positions

5. ELECTION MECHANICS
   New taxpayer: Election due by date return due (without extensions)
   Existing taxpayer: Same deadline, but for PRIOR year's return

   STATEMENT must include:
   □ Taxpayer's name and identification
   □ Statement electing §475(f)
   □ First year election is effective
   □ Trade or business involved

   ONCE MADE: Irrevocable without IRS consent

6. AUDIT ISSUES
   - Trader status claimed without sufficient activity
   - Election not timely filed
   - Mixed investment/trading positions not segregated
   - Self-employment tax not paid on trading income
   - Holding periods inconsistent with trader status""",
        key_factors=[
            "Trading activity substantial and frequent",
            "Profit sought from daily price movements",
            "Activity continuous throughout year",
            "§475(f) election timely filed",
            "Investment positions properly segregated"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §475(f)", "relevance": "Mark-to-market election"},
            {"authority": "IRC", "reference": "IRC §475(c)", "relevance": "Securities defined"},
            {"authority": "Case", "reference": "Endicott v. Commissioner, T.C. Memo 2013-199", "relevance": "Trader factors"},
            {"authority": "Case", "reference": "Chen v. Commissioner, T.C. Memo 2004-132", "relevance": "Frequency requirement"},
            {"authority": "Rev Proc", "reference": "Rev. Proc. 99-17", "relevance": "Election procedures"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS denies trader status when: (1) trading activity insufficient
(too few trades, too sporadic); (2) holding periods suggest investment, not trading;
(3) activity not continuous throughout year; (4) §475(f) election not timely or properly
filed; (5) taxpayer works full-time elsewhere.""",
        counter_arguments=[
            "Trading activity substantial (document trade count/frequency)",
            "Holding periods reflect trading, not investing",
            "Activity continuous throughout tax year",
            "§475(f) election timely and properly filed",
            "Significant time devoted to market analysis"
        ],
        appeals_strategy="""Trader status is highly factual. Document trade frequency, volumes,
and holding periods. Compare to successful cases (Endicott). If election timing challenged,
verify filing date carefully. Consider whether mark-to-market is beneficial given
ordinary income treatment. Self-employment tax must be considered.""",
        entity_scope=["individual", "c_corporation", "s_corporation", "partnership", "llc"],
        confidence="high"
    ),

    "innocent_spouse_relief": DoctrineBlock(
        topic="Innocent Spouse Relief - §6015",
        keywords=["innocent spouse", "6015", "injured spouse", "joint return",
                  "equitable relief", "separation of liability", "spouse liability",
                  "marital settlement", "innocent spouse relief"],
        conclusion_template="""Section 6015 provides three forms of relief from joint and several
liability on joint returns: (1) Traditional innocent spouse relief (§6015(b)) requiring
no knowledge of understatement, (2) Separation of liability (§6015(c)) for divorced or
separated spouses, and (3) Equitable relief (§6015(f)) as a catch-all. Relief must be
requested within 2 years (§6015(b)/(c)) or within the collection statute (§6015(f)).
Equitable factors include abuse, financial hardship, and lack of benefit.""",
        reasoning_framework="""
INNOCENT SPOUSE RELIEF — §6015 ANALYSIS:

1. THREE TYPES OF RELIEF

   A. TRADITIONAL INNOCENT SPOUSE (§6015(b))
      Requirements (ALL must be met):
      □ Joint return filed
      □ Understatement of tax on return
      □ Understatement due to erroneous items of other spouse
      □ Requesting spouse didn't know/have reason to know of understatement
      □ Inequitable to hold requesting spouse liable
      □ Requested within 2 years of IRS collection action

   B. SEPARATION OF LIABILITY (§6015(c))
      Requirements:
      □ Joint return filed
      □ No longer married OR legally separated OR lived apart 12 months
      □ Elect allocation of deficiency
      □ Request within 2 years of collection action
      □ DISQUALIFIED if: Actual knowledge of erroneous items

   C. EQUITABLE RELIEF (§6015(f))
      Requirements:
      □ Joint return filed
      □ Ineligible for (b) or (c) relief
      □ Considering all facts, inequitable to hold liable
      □ For understatements OR underpayments
      □ Must request within collection statute period

2. EQUITABLE FACTORS (Rev. Proc. 2013-34)
   FACTORS WEIGHING FOR RELIEF:
   □ Abuse by other spouse
   □ Other spouse controlled finances
   □ Requesting spouse received no significant benefit
   □ Requesting spouse in financial hardship
   □ Other spouse had legal obligation to pay
   □ Other spouse solely responsible for erroneous item

   FACTORS WEIGHING AGAINST RELIEF:
   □ Requesting spouse knew/should have known
   □ Received significant benefit from understatement
   □ Failed to comply with tax laws in subsequent years
   □ No financial hardship

3. KNOWLEDGE STANDARD
   "Knew OR had reason to know"

   KNOWLEDGE: Actual awareness of erroneous item
   REASON TO KNOW: Would have known if exercised reasonable inquiry

   Factors:
   - Financial sophistication
   - Control over finances
   - Lifestyle inconsistent with reported income
   - Suspicious behavior of other spouse

4. ABUSE CONSIDERATIONS
   Abuse (physical/emotional/financial) is:
   □ Significant favorable factor for relief
   □ May excuse failure to question spouse
   □ Documented through:
     - Police reports
     - Medical records
     - Counseling records
     - Court orders

5. PROCEDURAL REQUIREMENTS
   □ File Form 8857 (Request for Innocent Spouse Relief)
   □ Attach documentation
   □ IRS notifies other spouse (opportunity to participate)
   □ Right to Tax Court petition if denied

6. TIMING
   §6015(b)/(c): Within 2 years of first collection action
   §6015(f): Before expiration of collection statute

7. AUDIT/APPEALS CONSIDERATIONS
   - Documentation of lack of knowledge
   - Evidence of other spouse's control
   - Abuse documentation
   - Financial benefit analysis
   - Current financial hardship""",
        key_factors=[
            "Joint return filed for year in question",
            "Requesting spouse lacked knowledge of item",
            "Inequitable to hold requesting spouse liable",
            "Timely request filed (2 years for b/c)",
            "Abuse or financial control documented if applicable"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §6015(b)", "relevance": "Traditional relief"},
            {"authority": "IRC", "reference": "IRC §6015(c)", "relevance": "Separation of liability"},
            {"authority": "IRC", "reference": "IRC §6015(f)", "relevance": "Equitable relief"},
            {"authority": "Rev Proc", "reference": "Rev. Proc. 2013-34", "relevance": "Equitable factors"},
            {"authority": "IRS", "reference": "Form 8857", "relevance": "Relief request"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS denies innocent spouse relief when: (1) requesting spouse
had knowledge or reason to know; (2) requesting spouse benefited significantly from
understatement; (3) request untimely; (4) requesting spouse participated in return
preparation; (5) lifestyle inconsistent with reported income.""",
        counter_arguments=[
            "No actual knowledge of erroneous items",
            "Other spouse controlled financial matters",
            "No significant benefit received from understatement",
            "Abuse prevented questioning of spouse",
            "Request timely filed within statutory period"
        ],
        appeals_strategy="""Innocent spouse cases are highly factual. Document lack of knowledge
thoroughly. If abuse involved, gather all supporting records. Financial sophistication
and access to information are key factors. Consider Tax Court petition if IRS denies
— burden shifts in certain circumstances. Equitable relief under (f) is discretionary;
present all favorable factors.""",
        entity_scope=["individual"],
        confidence="high"
    ),

    "grantor_trust_rules": DoctrineBlock(
        topic="Grantor Trust Rules - §§671-679",
        keywords=["grantor trust", "671", "679", "defective grantor trust",
                  "idgt", "intentionally defective", "reversionary interest",
                  "power to revoke", "grantor trust income"],
        conclusion_template="""A grantor trust is disregarded for income tax purposes under §§671-679,
with all income/deductions/credits taxable to the grantor. Trust becomes a grantor trust
if grantor retains certain powers: reversionary interest >5% (§673), power to control
beneficial enjoyment (§674), administrative powers (§675), power to revoke (§676),
or income for benefit of grantor (§677). Intentionally defective grantor trusts (IDGTs)
combine income tax disregard with completed gift for transfer tax — a powerful planning tool.""",
        reasoning_framework="""
GRANTOR TRUST — §§671-679 ANALYSIS:

1. CORE CONCEPT
   If trust is "grantor trust":
   □ Trust income taxed to GRANTOR (not trust or beneficiaries)
   □ Grantor claims deductions and credits
   □ Trust files Form 1041 as information return
   □ Trust uses grantor's SSN (in some cases)

   KEY: Grantor trust for INCOME tax may still be completed gift for TRANSFER tax

2. TRIGGERING PROVISIONS

   A. §673 — REVERSIONARY INTEREST
      Grantor trust if:
      □ Grantor's reversionary interest >5% of trust corpus
      □ Measured at inception of trust
      □ Actuarial tables apply (§7520 rate)

   B. §674 — POWER TO CONTROL BENEFICIAL ENJOYMENT
      Grantor trust if:
      □ Grantor/non-adverse party can control beneficial enjoyment
      □ Examples: Sprinkle power, accumulation power
      □ EXCEPTIONS: Independent trustee, reasonably definite standard

   C. §675 — ADMINISTRATIVE POWERS
      Grantor trust if grantor retains:
      □ Power to deal with trust for less than adequate consideration
      □ Power to borrow without adequate security
      □ Power to vote stock closely held corp (grantor actual/constructive owner)
      □ Power to reacquire corpus by substituting property of equal value

   D. §676 — POWER TO REVOKE
      Grantor trust if:
      □ Grantor (or spouse) can revest title in grantor
      □ Revocable trust is classic example
      □ Power need not be exercised

   E. §677 — INCOME FOR BENEFIT OF GRANTOR
      Grantor trust if income:
      □ Is or may be distributed to grantor/spouse
      □ Is accumulated for future distribution to grantor/spouse
      □ May be used to pay life insurance premiums on grantor/spouse

   F. §678 — PERSON OTHER THAN GRANTOR
      Beneficiary treated as owner if:
      □ Has power to vest corpus in themselves
      □ Previously released such power but retained §671-677 triggers

   G. §679 — FOREIGN TRUSTS
      US grantor treated as owner of foreign trust with US beneficiary

3. INTENTIONALLY DEFECTIVE GRANTOR TRUST (IDGT)
   STRUCTURE:
   □ Create irrevocable trust (completed gift for transfer tax)
   □ Retain §675 power (swap power) → grantor trust for income tax

   BENEFITS:
   - Grantor pays income tax (gift-tax-free wealth transfer)
   - Trust grows income-tax-free from beneficiary perspective
   - Sale to IDGT: No gain recognition (grantor selling to self)
   - Step-up in basis at grantor's death? (Unsettled)

   COMMON SWAP POWER:
   "Grantor may substitute property of equivalent value"

4. PLANNING APPLICATIONS
   □ IDGT for estate freeze transactions
   □ Sale to IDGT (grantor note) — freeze value + income shift
   □ Life insurance trusts (ILIT) with grantor trust status
   □ Spousal lifetime access trusts (SLAT)

5. GRANTOR TRUST vs. NON-GRANTOR TRUST
   Grantor Trust:
   - Grantor pays tax on all income
   - No separate trust return (or information return)
   - Sales to trust are non-events

   Non-Grantor Trust:
   - Trust or beneficiaries pay tax
   - Form 1041 required
   - Sales to trust are taxable transactions""",
        key_factors=[
            "Specific power retained that triggers §§671-679",
            "Grantor trust status properly reflected on return",
            "IDGT structure: completed gift + retained power",
            "Foreign trust rules under §679 analyzed if applicable",
            "Sale to grantor trust is disregarded transaction"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §§671-679", "relevance": "Grantor trust rules"},
            {"authority": "IRC", "reference": "IRC §675(4)(C)", "relevance": "Swap power"},
            {"authority": "IRC", "reference": "IRC §679", "relevance": "Foreign trust rules"},
            {"authority": "Reg", "reference": "Reg. §1.671-4", "relevance": "Reporting requirements"},
            {"authority": "Rev Rul", "reference": "Rev. Rul. 85-13", "relevance": "Sale to grantor trust"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges grantor trust positions when: (1) power retained
does not actually trigger grantor trust status; (2) IDGT sale lacks economic substance;
(3) grantor trust income not properly reported by grantor; (4) foreign trust reporting
failed; (5) step-transaction collapses IDGT planning.""",
        counter_arguments=[
            "Specific triggering power identified in trust document",
            "Grantor reported all trust income on individual return",
            "IDGT sale properly structured with arm's-length terms",
            "Swap power exercisable without trustee consent",
            "No step-transaction concern (genuine sale terms)"
        ],
        appeals_strategy="""Grantor trust status is determined by trust terms. Point to specific
power retained and applicable code section. For IDGT sales, document fair value
exchange and economic substance. If §679 foreign trust issues, consider Streamlined
procedures. Basis questions at death remain unsettled — document position taken.""",
        entity_scope=["individual", "trust"],
        confidence="high"
    ),

    "section_338h10_election": DoctrineBlock(
        topic="Section 338(h)(10) Election - Deemed Asset Sale",
        keywords=["338h10", "338 h 10", "deemed asset sale", "stock acquisition",
                  "asset acquisition", "section 338", "step-up basis",
                  "corporate acquisition", "purchase price allocation"],
        conclusion_template="""A §338(h)(10) election treats a qualified stock purchase of a target
corporation as a deemed asset sale for tax purposes. The target recognizes gain/loss
as if it sold all assets at FMV, then liquidated. The purchaser receives a stepped-up
basis in target's assets. The election requires a qualified stock purchase (80%+ within
12 months) and joint election by purchaser and target. It's commonly used in S corporation
and consolidated group acquisitions where asset sale treatment is desired without actual
asset transfer.""",
        reasoning_framework="""
SECTION 338(h)(10) — DEEMED ASSET SALE ANALYSIS:

1. BASIC CONCEPT
   Without election: Stock purchase → Buyer takes target stock
                     Target retains historic asset basis

   With §338(h)(10): Stock purchase TREATED AS asset purchase
                     Target deemed to sell all assets at FMV
                     Buyer gets stepped-up basis in assets

2. WHEN TO USE §338(h)(10)
   FAVORABLE WHEN:
   □ Target has significant built-in losses (recognizable on deemed sale)
   □ Buyer wants asset basis step-up for depreciation/amortization
   □ Target has NOLs to absorb deemed sale gain
   □ S corporation target (single level of tax on deemed sale)
   □ Consolidated group target (intercompany gains eliminated)

   UNFAVORABLE WHEN:
   □ Target has large built-in gains with no offsetting attributes
   □ C corporation target with shareholder-level tax on liquidation
   □ Administrative complexity outweighs benefits

3. REQUIREMENTS FOR ELECTION
   A. QUALIFIED STOCK PURCHASE (QSP)
      □ Purchase of 80%+ (vote AND value) of target stock
      □ Within 12-month acquisition period
      □ "Purchase" excludes certain related party transactions

   B. JOINT ELECTION
      □ Both purchaser AND target must join in election
      □ Filed with purchaser's return for year including acquisition date
      □ Irrevocable once made

   C. ELIGIBLE TARGETS
      □ S corporations
      □ Members of consolidated groups (selling parent consents)
      □ NOT available for standalone C corps (use regular §338 instead)

4. TAX CONSEQUENCES

   TO TARGET (Old T):
   □ Deemed sale of all assets at ADSP (aggregate deemed sale price)
   □ Recognize gain/loss
   □ Allocate ADSP among assets per §338(b)(5) (residual method)
   □ Deemed liquidation follows

   TO SELLING SHAREHOLDERS:
   □ S Corp: Deemed sale gain passes through (K-1)
      Then deemed liquidation → no additional gain if basis adjusted
   □ Consolidated: Intercompany gain often deferred/eliminated

   TO PURCHASER (New T):
   □ Treat as new corporation
   □ Acquire assets with stepped-up basis (AGUB)
   □ Allocate AGUB per §338(b)(5) residual method

5. PRICE ALLOCATION — RESIDUAL METHOD (§338(b)(5))
   Priority:
   1. Cash and cash equivalents
   2. CDs, government securities
   3. Accounts receivable, mortgages
   4. Inventory
   5. All other assets (except intangibles)
   6. §197 intangibles (except goodwill)
   7. Goodwill and going concern value

6. S CORPORATION CONSIDERATIONS
   □ Single level of tax (deemed sale taxed to shareholders)
   □ Deemed liquidation under §331
   □ Often tax-efficient structure
   □ Buyer can amortize goodwill (§197)

7. FORM 8023
   □ Election statement filed by purchaser
   □ Due: By 15th day of 9th month after acquisition date
   □ Attach statement describing transaction""",
        key_factors=[
            "Qualified stock purchase (80%+) within 12 months",
            "Joint election by purchaser and target",
            "Eligible target (S corp or consolidated member)",
            "Form 8023 timely filed",
            "Purchase price allocation per residual method"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §338(h)(10)", "relevance": "Election provision"},
            {"authority": "IRC", "reference": "IRC §338(b)(5)", "relevance": "Allocation rules"},
            {"authority": "IRC", "reference": "IRC §197", "relevance": "Goodwill amortization"},
            {"authority": "Reg", "reference": "Reg. §1.338(h)(10)-1", "relevance": "Election mechanics"},
            {"authority": "IRS", "reference": "Form 8023", "relevance": "Election form"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges §338(h)(10) elections when: (1) qualified stock
purchase not achieved (related party issues); (2) election not timely or properly filed;
(3) purchase price allocation inflates depreciable assets; (4) S corporation tax
attributes not properly calculated on deemed sale; (5) consolidated return regulations
not followed.""",
        counter_arguments=[
            "Qualified stock purchase documented (80%+ in 12 months)",
            "Form 8023 timely filed with required attachments",
            "Purchase price allocation follows residual method",
            "S corporation shareholders reported deemed sale income",
            "Arm's-length purchase price supported by valuation"
        ],
        appeals_strategy="""§338(h)(10) issues often involve allocation disputes. Obtain
contemporaneous valuation. Residual method requires proper asset classification.
If election validity challenged, document timeline carefully. S corporation issues
require reviewing shareholder-level reporting.""",
        entity_scope=["c_corporation", "s_corporation"],
        confidence="high"
    ),

    # =========================================================================
    # PARTNER-LEVEL JUDGMENT DOCTRINE — AUDIT-SENSITIVE AREAS
    # =========================================================================

    "constructive_dividend": DoctrineBlock(
        topic="Constructive Dividends - §301 Disguised Distributions",
        keywords=["constructive dividend", "301", "disguised distribution",
                  "shareholder benefit", "corporate distribution", "deemed dividend",
                  "below market", "personal expense", "unreasonable compensation"],
        conclusion_template="""A constructive dividend occurs when a corporation confers an economic
benefit on a shareholder that is not formally declared as a dividend. Common examples
include below-market loans, personal expenses paid by the corporation, bargain purchases,
and excessive compensation to shareholder-employees. The IRS recharacterizes these
transactions as §301 distributions: ordinary income to the shareholder (to extent of E&P),
and no corporate deduction. The shareholder's intent is irrelevant — only the economic
substance matters.""",
        reasoning_framework="""
CONSTRUCTIVE DIVIDEND — §301 ANALYSIS:

1. CORE DOCTRINE
   Constructive dividend found when:
   □ Corporation transfers value to shareholder
   □ Transfer NOT in exchange for property/services
   □ Distribution not formally declared
   □ Shareholder receives economic benefit

   TAX CONSEQUENCE:
   - Shareholder: Dividend income (§301(c))
   - Corporation: No deduction; may affect E&P

2. COMMON CONSTRUCTIVE DIVIDEND SCENARIOS

   A. PERSONAL EXPENSES PAID BY CORPORATION
      □ Personal travel, entertainment, club dues
      □ Home improvements, personal auto
      □ Children's expenses, family vacations
      □ Life insurance benefiting shareholder personally

   B. BELOW-MARKET TRANSACTIONS
      □ Below-market loans to shareholders (§7872)
      □ Bargain sales of property to shareholders
      □ Rent-free use of corporate property
      □ Forgiveness of shareholder debt

   C. COMPENSATION-RELATED
      □ Excessive compensation (recharacterized as dividend)
      □ Payments to family members for no services
      □ Payments disguised as consulting fees
      □ Bonuses without business justification

   D. RELATED PARTY DEALINGS
      □ Above-market purchases from shareholders
      □ Loans to shareholder-controlled entities
      □ Guarantees of shareholder obligations
      □ Payment of shareholder's personal liabilities

3. MEASURING THE DIVIDEND AMOUNT
   Amount = Fair market value of benefit received
            MINUS consideration paid by shareholder

   For below-market loans (§7872):
   - Imputed interest = AFR - Actual rate charged
   - Deemed dividend to shareholder
   - Deemed interest payment back to corporation

4. E&P ANALYSIS
   Distribution treated as:
   □ Dividend to extent of current + accumulated E&P
   □ Return of capital (reduces stock basis) to extent of basis
   □ Capital gain if exceeds basis

5. INTENT IS IRRELEVANT
   Courts apply OBJECTIVE test:
   □ Did corporation confer economic benefit?
   □ Was benefit proportionate to shareholding?
   □ No legitimate business purpose for payment?

   Shareholder's subjective intent doesn't matter

6. DOCUMENTATION DEFENSE
   □ Clear business purpose for each transaction
   □ Arm's-length pricing documentation
   □ Board resolutions for compensation
   □ Expense reports with business nexus
   □ Loan agreements at market rates

7. AUDIT RED FLAGS
   - Large shareholder loans with no repayment
   - Lavish travel/entertainment
   - Corporate property used personally
   - No formal documentation of transactions
   - Pattern of year-end shareholder payments""",
        key_factors=[
            "Economic benefit conferred on shareholder",
            "No legitimate business purpose documented",
            "Transaction not at arm's length",
            "E&P sufficient to characterize as dividend",
            "Benefit proportionate to stock ownership"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §301", "relevance": "Distribution rules"},
            {"authority": "IRC", "reference": "IRC §316", "relevance": "Dividend defined"},
            {"authority": "IRC", "reference": "IRC §7872", "relevance": "Below-market loans"},
            {"authority": "Case", "reference": "Truesdell v. Commissioner, 89 T.C. 1280", "relevance": "Constructive dividend standard"},
            {"authority": "Case", "reference": "Magnon v. Commissioner, T.C. Memo 1973-170", "relevance": "Personal expense doctrine"}
        ],
        burden_holder="IRS initially; shifts to taxpayer if prima facie case",
        irs_typical_position="""The IRS asserts constructive dividends when: (1) corporation
pays shareholder's personal expenses; (2) below-market loans to shareholders;
(3) shareholder uses corporate assets personally; (4) excessive compensation paid;
(5) no contemporaneous documentation of business purpose.""",
        counter_arguments=[
            "Transaction had legitimate business purpose",
            "Arm's-length terms documented",
            "Expense properly allocable to business",
            "Loan repaid on commercial terms",
            "Board resolution supports compensation level"
        ],
        appeals_strategy="""Constructive dividend cases are fact-intensive. Document business
purpose contemporaneously. For loans, ensure written agreement and regular payments.
For compensation, obtain comparability studies. Personal use of property should be
reimbursed at FMV. Pattern of informal dealings is problematic — formalize going forward.""",
        entity_scope=["c_corporation", "s_corporation"],
        confidence="high"
    ),

    "section_83_stock_compensation": DoctrineBlock(
        topic="Section 83 Stock Compensation - Timing and Valuation",
        keywords=["section 83", "83b election", "restricted stock", "vesting",
                  "stock compensation", "substantial risk of forfeiture",
                  "83b", "stock grant", "service provider stock"],
        conclusion_template="""Section 83 governs taxation of property (typically stock) transferred
in connection with services. Income is recognized when property is either: (1) transferable,
OR (2) no longer subject to substantial risk of forfeiture — whichever occurs first.
The §83(b) election allows recognition at grant (before vesting), locking in lower value
and converting future appreciation to capital gain. The election must be filed within
30 days of transfer — this deadline is absolute and cannot be extended.""",
        reasoning_framework="""
SECTION 83 — STOCK COMPENSATION ANALYSIS:

1. BASIC RULE — §83(a)
   When property transferred for services:
   □ Income = FMV of property MINUS amount paid
   □ Recognized when: Transferable OR not subject to SRF
   □ Character: Ordinary income (compensation)

   EMPLOYER:
   □ Deduction equal to employee's income
   □ Deduction timing matches employee inclusion
   □ Subject to reasonable compensation limits

2. SUBSTANTIAL RISK OF FORFEITURE (SRF)
   Property subject to SRF if:
   □ Rights conditioned on future services
   □ Condition is substantial (not mere formality)
   □ Enforcement is likely

   EXAMPLES of SRF:
   - 4-year vesting schedule (forfeiture if leave)
   - Performance conditions (revenue targets)
   - Noncompete tied to forfeiture

   NOT SRF:
   - Covenant not to compete alone (must be enforceable)
   - Condition issuer unlikely to enforce
   - Risk of decline in property value

3. THE §83(b) ELECTION
   ALLOWS: Include FMV in income at GRANT (not vesting)

   BENEFITS:
   □ Lock in low value (startup stock worth little)
   □ Future appreciation = capital gain
   □ Start long-term holding period at grant

   RISKS:
   □ Pay tax now on property that may be forfeited
   □ NO refund if forfeiture occurs
   □ If value declines, still paid tax on higher amount

   REQUIREMENTS:
   □ Written election within 30 DAYS of transfer
   □ Filed with IRS (service center for return)
   □ Copy to employer
   □ Attach copy to tax return for year

   DEADLINE IS ABSOLUTE — No extensions, no relief

4. ELECTION MECHANICS
   Election statement must include:
   □ Taxpayer name, address, SSN
   □ Description of property
   □ Date of transfer
   □ Taxable year of transfer
   □ Nature of restrictions
   □ FMV at transfer
   □ Amount paid for property
   □ Statement that copies furnished

5. VALUATION AT GRANT
   FMV determined without regard to:
   □ Lapse restrictions (vesting)
   □ BUT with regard to non-lapse restrictions

   For private company stock:
   - 409A valuation often used
   - Arm's-length transaction evidence
   - Comparable company analysis

6. PLANNING CONSIDERATIONS
   §83(b) FAVORED WHEN:
   □ Property value is low (early stage)
   □ High appreciation expected
   □ Low risk of forfeiture
   □ Cash available to pay tax

   §83(b) NOT FAVORED WHEN:
   □ Significant forfeiture risk
   □ Value already substantial
   □ Appreciation uncertain
   □ Cash-flow constraints

7. AUDIT ISSUES
   - Election not timely filed (30-day deadline)
   - Valuation at grant unsupportable
   - SRF not properly analyzed
   - Employer deduction timing mismatch
   - Forfeiture after §83(b) — no refund""",
        key_factors=[
            "Property subject to substantial risk of forfeiture",
            "§83(b) election filed within 30 days if made",
            "FMV determined under applicable standards",
            "Employer deduction matches employee inclusion",
            "Forfeiture provisions properly analyzed"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §83(a)", "relevance": "General rule"},
            {"authority": "IRC", "reference": "IRC §83(b)", "relevance": "Election"},
            {"authority": "IRC", "reference": "IRC §83(c)", "relevance": "SRF defined"},
            {"authority": "Reg", "reference": "Reg. §1.83-2", "relevance": "Election procedures"},
            {"authority": "Reg", "reference": "Reg. §1.83-3", "relevance": "Definitions"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges §83 positions when: (1) §83(b) election not
timely or properly filed; (2) valuation at grant inflated or unsupported; (3) SRF not
substantial (foregone conclusion of vesting); (4) employer deduction claimed before
employee inclusion; (5) non-lapse restrictions improperly valued.""",
        counter_arguments=[
            "§83(b) election timely filed (receipt/tracking evidence)",
            "Valuation supported by 409A or contemporaneous appraisal",
            "SRF substantial — meaningful forfeiture risk",
            "Employer deduction properly timed",
            "Copy of election retained by employer"
        ],
        appeals_strategy="""§83 issues often involve election timing or valuation. For timing,
provide mailing evidence (certified mail receipt). Valuation requires contemporaneous
support — 409A valuations are persuasive. If election missed, no relief available;
focus on current compliance. Forfeiture after §83(b) creates no tax benefit — advise
clients of this risk upfront.""",
        entity_scope=["individual", "c_corporation", "s_corporation", "partnership", "llc"],
        confidence="high"
    ),

    "debt_discharge_income_108": DoctrineBlock(
        topic="Cancellation of Debt Income - §108 Exclusions",
        keywords=["cancellation of debt", "cod income", "108", "debt discharge",
                  "insolvency", "bankruptcy", "forgiveness of debt",
                  "qualified principal residence", "attribute reduction"],
        conclusion_template="""Cancellation of debt (COD) is generally gross income under §61(a)(11).
However, §108 provides exclusions for discharge in: (1) bankruptcy (Title 11), (2) insolvency
(to extent insolvent), (3) qualified farm indebtedness, (4) qualified real property
business indebtedness, and (5) qualified principal residence indebtedness (through 2025).
Excluded COD income requires reduction of tax attributes under §108(b) — NOLs first,
then credits, then basis, in prescribed order. The excluded amount is NOT permanently
tax-free; it reduces future tax benefits.""",
        reasoning_framework="""
CANCELLATION OF DEBT — §108 ANALYSIS:

1. GENERAL RULE — COD IS INCOME (§61(a)(11))
   When debt discharged for less than adjusted issue price:
   □ Difference = COD income
   □ Ordinary income character
   □ Report on Form 1099-C (issued by lender)

   EXCEPTIONS (not COD income):
   - Disputed debt (liability contested)
   - Gift (donative intent by creditor)
   - Purchase price reduction (§108(e)(5))
   - Deductible payment if paid

2. SECTION 108 EXCLUSIONS (Priority Order)

   A. TITLE 11 BANKRUPTCY (§108(a)(1)(A))
      □ Complete exclusion
      □ Discharge must be IN bankruptcy case
      □ Granted by court or pursuant to plan
      □ Attribute reduction required

   B. INSOLVENCY (§108(a)(1)(B))
      □ Exclusion LIMITED to extent of insolvency
      □ Insolvency = Liabilities > FMV of assets
      □ Measure IMMEDIATELY BEFORE discharge
      □ Partial exclusion if partially insolvent

      EXAMPLE:
      - Assets FMV: $100,000
      - Liabilities: $150,000
      - Insolvency: $50,000
      - COD: $80,000
      - Excluded: $50,000 (extent insolvent)
      - Taxable: $30,000

   C. QUALIFIED FARM INDEBTEDNESS (§108(a)(1)(C))
      □ Debt incurred in farming business
      □ Owed to qualified lender
      □ At least 50% gross receipts from farming

   D. QUALIFIED REAL PROPERTY BUSINESS DEBT (§108(a)(1)(D))
      □ Incurred in real property trade or business
      □ Secured by real property
      □ Taxpayer election required
      □ Exclusion limited to excess of debt over FMV

   E. QUALIFIED PRINCIPAL RESIDENCE (§108(a)(1)(E))
      □ Acquisition indebtedness
      □ Principal residence
      □ Up to $2 million ($1M if MFS)
      □ Extended through 2025
      □ Reduces basis (not other attributes)

3. ATTRIBUTE REDUCTION — §108(b)
   Excluded COD REDUCES tax attributes in order:
   1. NOLs (dollar-for-dollar)
   2. General business credits (33⅓¢ per $1)
   3. Minimum tax credits (33⅓¢ per $1)
   4. Capital losses (dollar-for-dollar)
   5. Basis of property (dollar-for-dollar)
   6. Passive activity losses (dollar-for-dollar)
   7. Foreign tax credits (33⅓¢ per $1)

   ELECTION: May elect to reduce basis FIRST (§108(b)(5))

4. INSOLVENCY CALCULATION
   ASSETS (at FMV):
   □ All assets, including exempt assets (IRA, pension)
   □ Contingent assets if reasonably certain
   □ Measure FMV, not basis

   LIABILITIES:
   □ All liabilities, including contingent
   □ Recourse and nonrecourse
   □ Include debt being discharged

5. SPECIAL RULES
   PARTNERSHIP DEBT (§108(d)(6)):
   - Exclusion determined at partner level
   - Partner's share of partnership liabilities matters

   PURCHASE PRICE REDUCTION (§108(e)(5)):
   - Seller reduces debt for property sold
   - Reduces basis instead of income
   - Must be solvent buyer

6. AUDIT ISSUES
   - Insolvency calculation errors
   - Assets undervalued / liabilities overstated
   - Attribute reduction not properly made
   - Form 982 not filed
   - QPRI exclusion on non-acquisition debt""",
        key_factors=[
            "Type of exclusion properly identified",
            "Insolvency calculated immediately before discharge",
            "Attribute reduction applied in correct order",
            "Form 982 filed with return",
            "Assets valued at FMV (not basis)"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §108(a)", "relevance": "Exclusions"},
            {"authority": "IRC", "reference": "IRC §108(b)", "relevance": "Attribute reduction"},
            {"authority": "IRC", "reference": "IRC §108(d)", "relevance": "Definitions"},
            {"authority": "IRC", "reference": "IRC §1017", "relevance": "Basis reduction"},
            {"authority": "IRS", "reference": "Form 982", "relevance": "Exclusion reporting"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges §108 exclusions when: (1) insolvency
overstated (assets undervalued); (2) attribute reduction not properly computed;
(3) Form 982 not filed; (4) QPRI exclusion claimed on non-acquisition debt;
(5) exempt assets excluded from insolvency calculation.""",
        counter_arguments=[
            "Insolvency documented with asset valuations",
            "Form 982 timely filed with return",
            "Attribute reduction follows §108(b) order",
            "All assets included (including exempt)",
            "COD properly sourced to excluded category"
        ],
        appeals_strategy="""§108 issues often involve insolvency calculations. Document all
assets at FMV (appraisals, account statements). Include exempt assets (IRAs) in
calculation. Attribute reduction is mechanical — follow the order. If Form 982 missing,
file amended return. QPRI requires acquisition indebtedness — trace original debt.""",
        entity_scope=["individual", "c_corporation", "s_corporation", "partnership"],
        confidence="high"
    ),

    "assignment_of_income": DoctrineBlock(
        topic="Assignment of Income Doctrine - Lucas v. Earl",
        keywords=["assignment of income", "lucas v earl", "fruit tree",
                  "income shifting", "anticipatory assignment", "who is taxed",
                  "earned income", "income attribution"],
        conclusion_template="""The assignment of income doctrine (Lucas v. Earl) provides that
income is taxed to the person who earns it or owns the income-producing property.
A taxpayer cannot avoid tax by assigning income to another party after the right to
receive it has ripened. The 'fruit and tree' metaphor holds: one who owns the tree
(property or services) is taxed on the fruit (income), regardless of who actually
receives it. The doctrine applies to both earned income and property income, but
with different tests for each.""",
        reasoning_framework="""
ASSIGNMENT OF INCOME — DOCTRINE ANALYSIS:

1. CORE PRINCIPLE (Lucas v. Earl, 1930)
   "The tax could not be escaped by anticipatory arrangements
   and contracts however skillfully devised to prevent the
   salary when paid from vesting even for a second in the
   person who earned it."

   RULE: Income taxed to EARNER, not recipient

2. TWO BRANCHES OF DOCTRINE

   A. EARNED INCOME (Services)
      Taxed to person who PERFORMS services
      □ Cannot assign salary/wages to family member
      □ Cannot gift right to future bonus
      □ Cannot redirect fees to charity before earned

      EXCEPTION: If family member actually performs services
      (reasonable compensation for actual work)

   B. PROPERTY INCOME (Investment)
      Taxed to person who OWNS income-producing property
      □ Must transfer the "tree" not just the "fruit"
      □ Transfer must be complete (no retained control)
      □ Gift of income alone ineffective

      EXAMPLE:
      - Gift of stock → donee taxed on dividends
      - Gift of right to next dividend → donor taxed
      - Gift of rental property → donee taxed on rent
      - Gift of rent already earned → donor taxed

3. THE FRUIT/TREE METAPHOR (Horst)
   "The fruit is not to be attributed to a different tree
   from that on which it grew."

   PROPERTY: Transfer the TREE to shift FRUIT
   SERVICES: Cannot transfer — you ARE the tree

4. COMMON APPLICATIONS

   A. FAMILY INCOME SPLITTING
      □ Cannot assign wages to spouse/children
      □ Can employ family members (if actually work)
      □ Can gift property (shifts future income)
      □ Cannot gift right to income from property retained

   B. CONTROLLED ENTITY ARRANGEMENTS
      □ Cannot assign personal service income to corporation
        without actually being employee of corporation
      □ Substance over form — who did the work?
      □ PSC rules (§269A) reinforce

   C. DEFERRED COMPENSATION
      □ §409A governs timing of inclusion
      □ Constructive receipt doctrine related
      □ Cannot just "defer" already-earned income

5. EXCEPTIONS AND PLANNING

   ALLOWED INCOME SHIFTING:
   □ Bona fide gift of property (donee taxed on future income)
   □ Employment of family members (reasonable compensation)
   □ Partnership/S-Corp (pass-through allocations)
   □ Family LLC with genuine economic arrangements

   NOT ALLOWED:
   □ Assignment of already-earned income
   □ Backdating property transfers
   □ Sham family employment
   □ "Loans" that are really compensation

6. AUDIT TRIGGERS
   - Income diverted to family members
   - Controlled entity receiving personal fees
   - Below-market family transactions
   - Last-minute property transfers before income event
   - Pattern of income-splitting arrangements""",
        key_factors=[
            "Income earned by taxpayer vs. another party",
            "Property transferred before income earned",
            "Transfer complete (no retained control)",
            "Substance of arrangement analyzed",
            "Family employment is bona fide"
        ],
        primary_authority=[
            {"authority": "Case", "reference": "Lucas v. Earl, 281 U.S. 111 (1930)", "relevance": "Earned income doctrine"},
            {"authority": "Case", "reference": "Helvering v. Horst, 311 U.S. 112 (1940)", "relevance": "Fruit/tree metaphor"},
            {"authority": "Case", "reference": "Commissioner v. Culbertson, 337 U.S. 733", "relevance": "Family partnerships"},
            {"authority": "IRC", "reference": "IRC §73", "relevance": "Child's income from services"},
            {"authority": "IRC", "reference": "IRC §1(g)", "relevance": "Kiddie tax"}
        ],
        burden_holder="IRS to prove assignment; taxpayer to prove genuine transfer",
        irs_typical_position="""The IRS invokes assignment of income when: (1) services income
paid to related party; (2) property income shifted without genuine property transfer;
(3) deferred compensation without §409A compliance; (4) sham family employment;
(5) controlled entity receives fees for shareholder's services.""",
        counter_arguments=[
            "Property genuinely transferred before income event",
            "Family member actually performed services",
            "Compensation reasonable for work performed",
            "No retained control over transferred property",
            "Economic substance supports arrangement"
        ],
        appeals_strategy="""Assignment of income requires careful timing analysis. Document
when income was earned vs. when property transferred. For family employment, maintain
job descriptions, time records, and comparability data. Gift transfers should be
complete — no retained powers. Entity arrangements require genuine employment
relationships.""",
        entity_scope=["individual", "c_corporation", "s_corporation", "partnership", "trust"],
        confidence="high"
    ),

    "statute_of_limitations_6501": DoctrineBlock(
        topic="Statute of Limitations - §6501 Assessment Periods",
        keywords=["statute of limitations", "6501", "assessment period",
                  "3 year rule", "6 year rule", "unlimited statute",
                  "substantial omission", "fraud", "tolling"],
        conclusion_template="""The general statute of limitations for tax assessment is 3 years
from the later of return filing or due date (§6501(a)). Extended periods apply for:
(1) 25% gross income omission — 6 years (§6501(e)), (2) no return filed — unlimited,
(3) false/fraudulent return — unlimited (§6501(c)), and (4) failure to report certain
foreign items — 6 years. The statute can be extended by agreement (Form 872) and
is suspended during certain proceedings. Understanding limitations periods is critical
for audit defense and refund claims.""",
        reasoning_framework="""
STATUTE OF LIMITATIONS — §6501 ANALYSIS:

1. GENERAL 3-YEAR RULE (§6501(a))
   Assessment must be made within 3 years of:
   □ Date return FILED, or
   □ Return DUE DATE (without extensions)
   □ Whichever is LATER

   EXAMPLE:
   - 2024 return due April 15, 2025
   - Filed March 1, 2025
   - Statute expires April 15, 2028 (3 years from due date)

   EXAMPLE:
   - 2024 return due April 15, 2025
   - Filed October 15, 2025 (on extension)
   - Statute expires October 15, 2028 (3 years from filing)

2. 6-YEAR RULE — SUBSTANTIAL OMISSION (§6501(e))
   Applies if taxpayer omits:
   □ >25% of GROSS INCOME stated on return
   □ Gross income = total receipts without reduction for COGS

   For trade/business income:
   - "Gross income" = gross receipts (not net)
   - COGS not subtracted before calculation

   WHAT COUNTS AS OMISSION:
   - Completely unreported income
   - Basis overstatement? (Colony v. Commissioner says NO)
   - But §6501(e)(1)(B) now includes certain basis overstatements

3. UNLIMITED STATUTE — FRAUD/NO RETURN (§6501(c))
   NO time limit if:
   □ Fraudulent return with intent to evade (§6501(c)(1))
   □ Willful attempt to evade (§6501(c)(2))
   □ NO return filed (§6501(c)(3))

   FRAUD requires:
   - Intentional wrongdoing
   - Specific purpose to evade tax
   - IRS must prove by clear and convincing evidence

4. SPECIAL 6-YEAR RULES

   A. FOREIGN INCOME/ASSETS (§6501(e)(1)(A)(ii))
      6-year statute if >$5,000 omission from:
      □ Foreign financial assets (§6038D)
      □ Certain foreign gifts (§6039F)
      □ FBAR-reportable accounts

   B. LISTED TRANSACTIONS
      If Form 8886 not filed → Statute remains open

   C. PASS-THROUGH ENTITIES
      Partnership/S-Corp items — special rules under TEFRA/BBA

5. EXTENSION BY AGREEMENT (§6501(c)(4))
   Form 872 extends assessment period:
   □ Must be signed before original statute expires
   □ Taxpayer is NOT required to sign
   □ Tactical considerations: May enable resolution

   Form 872-A: Extends indefinitely until terminated

6. SUSPENSION OF STATUTE
   Statute SUSPENDED during:
   □ Tax Court petition period (§6503(a))
   □ Bankruptcy stay (§6503(h))
   □ Taxpayer outside US for 6+ months (§6503(c))
   □ John Doe summons litigation
   □ Certain CDP proceedings

7. REFUND CLAIMS — §6511
   Refund claim must be filed within LATER of:
   □ 3 years from return filing, OR
   □ 2 years from tax payment

   Refund AMOUNT limited:
   - If filed within 3 years: Tax paid within 3 years + extensions
   - If filed within 2 years: Tax paid within 2 years

8. AUDIT STRATEGY
   □ Verify exact statute expiration date
   □ Check for tolling events
   □ Evaluate whether extension agreement tactical
   □ Consider quick resolution if statute short""",
        key_factors=[
            "Return filing date vs. due date — later controls",
            "Gross income omission calculated correctly",
            "Foreign asset reporting requirements met",
            "No fraud or fraudulent intent",
            "Extension agreements tracked"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §6501(a)", "relevance": "3-year general rule"},
            {"authority": "IRC", "reference": "IRC §6501(c)", "relevance": "Unlimited periods"},
            {"authority": "IRC", "reference": "IRC §6501(e)", "relevance": "6-year substantial omission"},
            {"authority": "IRC", "reference": "IRC §6511", "relevance": "Refund claims"},
            {"authority": "Case", "reference": "Colony v. Commissioner, 357 U.S. 28", "relevance": "Omission scope"}
        ],
        burden_holder="IRS to prove extended/unlimited statute applies",
        irs_typical_position="""The IRS asserts extended statute when: (1) gross income omission
exceeds 25%; (2) foreign asset reporting failed; (3) fraud indicators present;
(4) listed transaction not disclosed; (5) return not filed for year.""",
        counter_arguments=[
            "All income reported on return",
            "No substantial omission (proper gross income calculation)",
            "Foreign reporting requirements satisfied",
            "No fraud — errors were negligent, not intentional",
            "3-year statute has expired"
        ],
        appeals_strategy="""Statute issues are often outcome-determinative. Calculate exact
expiration date carefully. For 6-year statute, dispute gross income calculation
methodology. Fraud requires clear and convincing evidence — assert negligence instead.
If statute short, delay tactics may achieve dismissal. Document all extension
agreements.""",
        entity_scope=["individual", "c_corporation", "s_corporation", "partnership", "trust"],
        confidence="high"
    ),

    "199a_sstb": DoctrineBlock(
        topic="Section 199A SSTB - Specified Service Trade or Business",
        keywords=["199a", "sstb", "specified service", "qbi deduction",
                  "professional services", "reputation", "skill",
                  "qualified business income", "service business limitation"],
        conclusion_template="""A Specified Service Trade or Business (SSTB) under §199A is limited
or excluded from the 20% QBI deduction for taxpayers above income thresholds
($191,950 single / $383,900 MFJ for 2024). SSTBs include professional services (health,
law, accounting, actuarial, performing arts, consulting, athletics, financial services,
brokerage) and any business where the principal asset is the reputation or skill
of employees. The SSTB classification is determined at the trade or business level,
not the entity level, and de minimis exceptions apply for mixed businesses.""",
        reasoning_framework="""
SECTION 199A — SSTB ANALYSIS:

1. WHY SSTB MATTERS
   For taxpayers ABOVE threshold income:
   □ SSTB income → NO QBI deduction (phased out)
   □ Non-SSTB income → 20% deduction available

   Threshold income (2024):
   - Single: $191,950 (phase-out begins)
   - MFJ: $383,900 (phase-out begins)
   - Complete phase-out $50K/$100K above

   BELOW threshold: SSTB classification irrelevant

2. SSTB CATEGORIES (§199A(d)(2))

   A. HEALTH (Reg. §1.199A-5(b)(2)(ii))
      □ Medical services (physicians, dentists, nurses)
      □ Pharmacies (if providing medical services)
      □ NOT: Gyms, health clubs, research (no patient care)

   B. LAW (Reg. §1.199A-5(b)(2)(iii))
      □ Legal services of any kind
      □ Paralegals (if billable to clients)
      □ NOT: Court reporting, legal software

   C. ACCOUNTING (Reg. §1.199A-5(b)(2)(iv))
      □ Tax preparation and advice
      □ Audit, attestation, assurance
      □ Bookkeeping (generally)
      □ NOT: Payment processing, payroll services

   D. ACTUARIAL SCIENCE (Reg. §1.199A-5(b)(2)(v))
      □ Actuarial analysis and certification

   E. PERFORMING ARTS (Reg. §1.199A-5(b)(2)(vi))
      □ Performers (actors, musicians, entertainers)
      □ NOT: Crew, stagehands, directors (behind scenes)

   F. CONSULTING (Reg. §1.199A-5(b)(2)(vii))
      □ Advice and counsel
      □ NOT: Training, embedded staff, implementation
      □ Architecture and engineering NOT consulting

   G. ATHLETICS (Reg. §1.199A-5(b)(2)(viii))
      □ Athletes, coaches, team managers
      □ NOT: Stadium operators, equipment sellers

   H. FINANCIAL SERVICES (Reg. §1.199A-5(b)(2)(ix))
      □ Wealth management, financial planning
      □ Investment banking, securities dealing
      □ NOT: Banks (lending), insurance

   I. BROKERAGE (Reg. §1.199A-5(b)(2)(x))
      □ Securities brokers
      □ Real estate brokers/agents

   J. REPUTATION/SKILL (Reg. §1.199A-5(b)(2)(xiv))
      □ Principal asset is reputation or skill
      □ Endorsement income
      □ Licensing of name/likeness
      □ Appearance fees
      □ NOT: Normal trade or business operations

3. DE MINIMIS RULES (Reg. §1.199A-5(c)(1))
   Mixed business (SSTB + non-SSTB):
   □ If gross receipts ≤$25M: SSTB < 10% → all non-SSTB
   □ If gross receipts >$25M: SSTB < 5% → all non-SSTB
   □ Otherwise: Bifurcate or treat all as SSTB

4. ANTI-ABUSE RULES
   CANNOT separate SSTB by:
   □ Creating separate entity for non-SSTB functions
   □ Leasing property from SSTB owner
   □ Common control → treated as one business

5. PLANNING CONSIDERATIONS
   □ Evaluate if truly SSTB or misclassified
   □ Below-threshold taxpayers — no issue
   □ Consider income management near thresholds
   □ Document non-SSTB activities separately

6. AUDIT ISSUES
   - Consulting vs. non-consulting activities
   - Reputation/skill category overbroad claims
   - Improper separation of SSTB components
   - De minimis calculation errors""",
        key_factors=[
            "Trade or business correctly classified as SSTB or not",
            "Taxable income above/below threshold determined",
            "De minimis rule properly applied for mixed business",
            "Reputation/skill category narrowly construed",
            "Anti-abuse rules not triggered"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §199A(d)(2)", "relevance": "SSTB definition"},
            {"authority": "Reg", "reference": "Reg. §1.199A-5", "relevance": "SSTB guidance"},
            {"authority": "IRC", "reference": "IRC §199A(e)(2)", "relevance": "Threshold amounts"},
            {"authority": "Reg", "reference": "Reg. §1.199A-5(c)(1)", "relevance": "De minimis rules"},
            {"authority": "Reg", "reference": "Reg. §1.199A-5(c)(2)", "relevance": "Anti-abuse rules"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges SSTB classification when: (1) consulting
activities misclassified; (2) reputation/skill category applies but not reported;
(3) separate entities lack substance (anti-abuse); (4) de minimis calculation inflated
non-SSTB portion; (5) mixed business not properly bifurcated.""",
        counter_arguments=[
            "Business does not fit SSTB categories",
            "Consulting is incidental to non-SSTB services",
            "Reputation/skill not principal asset — operations are",
            "De minimis rule satisfied (SSTB < 10%/5%)",
            "Separate entities have genuine business purpose"
        ],
        appeals_strategy="""SSTB classification is fact-intensive. Regulations provide helpful
examples — match to closest. Consulting is narrowly defined; distinguish training,
implementation. Reputation/skill category is limited to endorsements/appearances.
If near threshold, consider timing strategies. Document non-SSTB revenue streams
separately.""",
        entity_scope=["individual", "s_corporation", "partnership", "llc", "trust"],
        confidence="high"
    ),

    "check_the_box_7701": DoctrineBlock(
        topic="Entity Classification - Check-the-Box Rules §7701",
        keywords=["check the box", "7701", "entity classification", "disregarded entity",
                  "partnership election", "association", "per se corporation",
                  "form 8832", "default classification"],
        conclusion_template="""The check-the-box regulations (Reg. §301.7701-1 through -3) allow
eligible entities to elect their federal tax classification. Eligible entities include
LLCs, partnerships, and certain foreign entities — but NOT per se corporations (state-law
corporations, publicly traded partnerships, certain foreign entities). Default classification
depends on liability protection and number of members. Elections are made on Form 8832
and are generally effective when filed (or up to 75 days retroactively). Entity classification
is fundamental to all tax planning involving business structures.""",
        reasoning_framework="""
CHECK-THE-BOX — ENTITY CLASSIFICATION ANALYSIS:

1. WHAT ENTITIES ARE ELIGIBLE? (Reg. §301.7701-2)
   ELIGIBLE (can elect):
   □ LLCs
   □ Limited partnerships
   □ General partnerships
   □ Certain foreign entities (not per se corporations)

   NOT ELIGIBLE (per se corporations):
   □ State-law corporations (Inc., Corp.)
   □ Publicly traded partnerships (§7704)
   □ Certain foreign entities (listed)
   □ Banks, insurance companies
   □ REITs, RICs

2. DEFAULT CLASSIFICATION (Reg. §301.7701-3(b))

   DOMESTIC ENTITIES:
   □ Single member + limited liability → Disregarded entity
   □ Two+ members + limited liability → Partnership
   □ No limited liability → Partnership

   FOREIGN ENTITIES:
   □ All members limited liability → Association (corporation)
   □ Any member unlimited liability → Partnership
   □ Single member, limited liability → Disregarded
   □ Single member, no limited liability → Disregarded

3. ELECTIVE CLASSIFICATION (Form 8832)

   DOMESTIC ELIGIBLE ENTITY can elect:
   □ Disregarded entity (single member)
   □ Partnership (2+ members)
   □ Association taxed as corporation

   FOREIGN ELIGIBLE ENTITY can elect:
   □ Same options
   □ But default differs (per above)

4. TIMING OF ELECTION
   □ Effective date can be specified
   □ No more than 75 days BEFORE filing
   □ No more than 12 months AFTER filing
   □ If no date specified: Filing date

5. LIMITATIONS ON ELECTION CHANGES
   Once classification elected:
   □ Cannot change for 60 months
   □ Exception: >50% ownership change
   □ Exception: Deemed elections (conversion to corporation)

6. DEEMED ELECTIONS AND CONVERSIONS

   CONVERSION TO CORPORATION (checking to "association"):
   - Treated as: Contribution of all assets to new corp under §351
   - Then: Corp assumes all liabilities
   - Basis: Generally carry-over

   CONVERSION FROM CORPORATION (unchecking):
   - Treated as: Complete liquidation under §331/§336
   - Taxable event (gain recognition)
   - New entity takes FMV basis

   CONVERSION TO/FROM PARTNERSHIP:
   - Contribution/distribution mechanics apply

7. DISREGARDED ENTITIES
   Single-member LLC taxed as disregarded:
   □ No separate federal return (generally)
   □ Owner reports all items
   □ Still separate for employment tax (Reg. changes)
   □ Still separate for state law purposes

8. PLANNING APPLICATIONS
   □ Single-member LLC for liability protection + pass-through
   □ Partnership election for flexibility
   □ S corporation via 8832 + 2553
   □ Foreign entity check-the-box for tax efficiency

9. AUDIT ISSUES
   - Classification inconsistent with state law entity
   - Form 8832 not timely filed
   - 60-month limitation violated
   - Conversion consequences not reported
   - Per se corporation treated as eligible""",
        key_factors=[
            "Entity eligible (not per se corporation)",
            "Default classification correctly determined",
            "Form 8832 timely filed if election made",
            "60-month limitation respected",
            "Conversion consequences properly reported"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §7701(a)(2), (3)", "relevance": "Entity definitions"},
            {"authority": "Reg", "reference": "Reg. §301.7701-1", "relevance": "Classification overview"},
            {"authority": "Reg", "reference": "Reg. §301.7701-2", "relevance": "Business entities"},
            {"authority": "Reg", "reference": "Reg. §301.7701-3", "relevance": "Elections"},
            {"authority": "IRS", "reference": "Form 8832", "relevance": "Election form"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges classification when: (1) entity is per se
corporation but treated as eligible; (2) Form 8832 not filed or untimely; (3) conversion
to/from corporation not properly reported; (4) 60-month limitation violated;
(5) disregarded entity employment taxes mishandled.""",
        counter_arguments=[
            "Entity is eligible (not per se corporation)",
            "Form 8832 timely filed and effective date correct",
            "Default classification properly applied if no election",
            "Conversion consequences reported on applicable forms",
            "60-month limitation satisfied (or exception applies)"
        ],
        appeals_strategy="""Classification issues are usually mechanical. Verify entity formed
under proper state law. If Form 8832 late, consider late election relief (Rev. Proc. 2009-41).
Conversion consequences are often significant — ensure gain/loss properly computed.
Disregarded entity rules continue to evolve for employment purposes.""",
        entity_scope=["c_corporation", "s_corporation", "partnership", "llc"],
        confidence="high"
    ),

    "partnership_basis_704d": DoctrineBlock(
        topic="Partnership Basis Limitations - §704(d) Loss Deduction",
        keywords=["partnership basis", "704d", "basis limitation", "loss limitation",
                  "partner basis", "outside basis", "suspended losses",
                  "basis computation", "partner loss deduction"],
        conclusion_template="""A partner may only deduct partnership losses to the extent of the
partner's adjusted basis in the partnership interest at year-end (§704(d)). Losses
in excess of basis are suspended and carried forward indefinitely until basis is
restored. Basis is computed under §705: increased by contributions and share of income,
decreased by distributions and share of losses. Loss limitation ordering is critical:
§704(d) basis limit applies first, then at-risk (§465), then passive activity (§469).""",
        reasoning_framework="""
PARTNERSHIP BASIS — §704(d) LOSS LIMITATION:

1. THE BASIC RULE (§704(d))
   Partner's deductible share of partnership losses
   LIMITED TO: Partner's adjusted basis at END of partnership year

   Losses exceeding basis:
   □ Suspended (not lost)
   □ Carried forward indefinitely
   □ Deductible when basis restored

2. COMPUTING PARTNER'S OUTSIDE BASIS (§705)

   INITIAL BASIS:
   □ Cash contributed
   □ FMV of property contributed (with adjustments)
   □ Basis in partnership interest acquired

   INCREASES TO BASIS:
   □ Additional contributions
   □ Share of partnership income (including tax-exempt)
   □ Share of partnership liabilities (§752)

   DECREASES TO BASIS:
   □ Distributions of money
   □ Share of partnership losses
   □ Share of partnership nondeductible expenses
   □ Reduction in share of liabilities

   BASIS CANNOT GO BELOW ZERO

3. LIABILITY SHARE (§752)
   Critical for basis calculation:

   RECOURSE LIABILITIES:
   □ Allocated to partner bearing economic risk of loss
   □ Generally: General partners, guarantors
   □ Analyzed under complex EROL rules

   NONRECOURSE LIABILITIES:
   □ First: To partners with §704(c) minimum gain
   □ Second: Per significant built-in loss
   □ Third: Per profit-sharing ratio

4. TIMING CONSIDERATIONS
   Basis computed at END of taxable year:
   □ Contributions increase basis immediately
   □ Distributions decrease basis immediately
   □ Income/loss computed, then basis adjusted

   ORDER OF ADJUSTMENTS:
   1. Add income items
   2. Add contributions
   3. Subtract distributions
   4. Subtract loss items (limited to remaining basis)

5. LOSS LIMITATION ORDERING
   Multiple limitations apply IN ORDER:
   1. §704(d) — Partnership basis limit
   2. §465 — At-risk limit
   3. §469 — Passive activity limit

   Each limit REDUCES the amount available for next test

6. SUSPENDED LOSSES — CARRYFORWARD
   Losses exceeding basis:
   □ Character preserved (ordinary, capital, §1231)
   □ Carry forward indefinitely
   □ Deductible when basis increases
   □ NOT transferred on sale of interest

7. DISPOSITION OF INTEREST
   If losses suspended and interest sold:
   □ Suspended losses LOST
   □ Add suspended amount to basis for gain/loss computation
   □ Effectively reduces gain or increases loss on sale

8. AUDIT ISSUES
   - Basis overstated (liability allocation errors)
   - Loss claimed exceeds year-end basis
   - Liability share not recalculated annually
   - Suspended losses not properly tracked
   - Ordering rules not followed""",
        key_factors=[
            "Year-end basis correctly computed",
            "Liability share properly allocated (§752)",
            "Ordering rules followed (§704(d) → §465 → §469)",
            "Suspended losses tracked and preserved",
            "Basis adjustments made in correct order"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §704(d)", "relevance": "Loss limitation"},
            {"authority": "IRC", "reference": "IRC §705", "relevance": "Basis computation"},
            {"authority": "IRC", "reference": "IRC §752", "relevance": "Liability allocation"},
            {"authority": "Reg", "reference": "Reg. §1.704-1(d)", "relevance": "Loss limitation rules"},
            {"authority": "Reg", "reference": "Reg. §1.752-1", "relevance": "Liability rules"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges basis positions when: (1) partner claims losses
exceeding year-end basis; (2) liability share overstated (EROL analysis incorrect);
(3) suspended losses not carried forward properly; (4) nonrecourse liability allocation
inflated; (5) basis not reduced for distributions.""",
        counter_arguments=[
            "Year-end basis computation documented",
            "Liability allocation follows §752 regulations",
            "Losses limited to basis, excess suspended",
            "Carryforward schedule maintained",
            "All contributions and distributions tracked"
        ],
        appeals_strategy="""§704(d) issues require detailed basis schedules. Liability allocation
under §752 is complex — work through EROL analysis for recourse debt. Ordering rules
are mechanical but often missed. Suspended loss tracking is essential. If partnership
interest disposed, ensure suspended losses added to basis for sale computation.""",
        entity_scope=["individual", "partnership", "llc", "trust"],
        confidence="high"
    ),

    "passive_activity_469": DoctrineBlock(
        topic="Passive Activity Loss Limitations - §469 Material Participation",
        keywords=["passive activity", "469", "material participation", "passive loss",
                  "rental activity", "passive income generator", "PIG", "PAL",
                  "7 tests", "real estate professional", "grouping"],
        conclusion_template="""Passive activity losses may only offset passive income (§469).
Passive activities are trades/businesses in which the taxpayer does not materially
participate. Material participation requires meeting one of seven regulatory tests.
Rental activities are per se passive unless real estate professional exception
applies. Grouping elections and proper documentation are critical for audit defense.""",
        reasoning_framework="""
PASSIVE ACTIVITY LOSS LIMITATIONS — §469 ANALYSIS:

1. FUNDAMENTAL RULE (§469(a))
   Passive activity losses ONLY deductible against passive income

   Disallowed losses:
   □ Suspended and carried forward
   □ Released on complete disposition
   □ Character preserved (ordinary, capital)

2. WHAT IS PASSIVE ACTIVITY?
   A trade or business in which taxpayer does NOT materially participate

   TWO CATEGORIES:
   a) Trade/business — No material participation
   b) Rental activities — Per se passive (with exceptions)

3. SEVEN MATERIAL PARTICIPATION TESTS (Reg. §1.469-5T)
   Meet ANY ONE to avoid passive classification:

   □ TEST 1: 500+ hours participation during year
   □ TEST 2: Taxpayer's participation is substantially all
   □ TEST 3: 100+ hours AND not less than any other individual
   □ TEST 4: Significant participation activity (100+ hrs) and
             aggregate of all such activities exceeds 500 hours
   □ TEST 5: Material participation in any 5 of prior 10 years
   □ TEST 6: Personal service activity + material in any 3 prior years
   □ TEST 7: Regular, continuous, substantial participation (facts/circumstances)

   NOTE: Test 7 rarely succeeds — IRS scrutinizes heavily

4. RENTAL ACTIVITY RULES
   Generally per se passive UNLESS:

   EXCEPTION 1 — Real Estate Professional (§469(c)(7)):
   □ More than 50% of personal services in real estate trades/businesses
   □ More than 750 hours in real estate trades/businesses
   □ Material participation in EACH rental activity (or election to group)

   EXCEPTION 2 — Short-Term Rentals (Avg. 7 days or less)
   EXCEPTION 3 — Significant Services Rentals

5. GROUPING ELECTIONS (Reg. §1.469-4)
   Taxpayers may group activities IF:
   □ Activities form "appropriate economic unit"
   □ Grouping is consistent year-to-year
   □ Election disclosed in year of grouping change

   ANTI-ABUSE: IRS can regroup if principal purpose is tax avoidance

6. COMPLETE DISPOSITION (§469(g))
   On fully taxable disposition to unrelated party:
   □ All suspended losses deductible in year of disposition
   □ Includes gains/losses from disposition
   □ Must be COMPLETE disposition (entire interest)

7. $25,000 RENTAL ALLOWANCE (§469(i))
   For individuals actively participating in rental:
   □ Up to $25,000 losses allowed against nonpassive
   □ Phases out $1 for $2 of AGI over $100,000
   □ Gone entirely at $150,000 AGI
   □ Does NOT apply to limited partners

8. AUDIT ISSUES
   - Material participation not documented (hours)
   - Grouping election never made or improperly changed
   - Real estate professional tests not met
   - Rental losses claimed against active income
   - Suspended loss carryforwards not tracked""",
        key_factors=[
            "Material participation documented with contemporaneous logs",
            "Grouping election properly made and consistent",
            "Real estate professional hours substantiated",
            "Suspended losses tracked annually",
            "Disposition rules properly applied"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §469", "relevance": "Passive activity limitations"},
            {"authority": "Reg", "reference": "Reg. §1.469-5T", "relevance": "Material participation tests"},
            {"authority": "Reg", "reference": "Reg. §1.469-4", "relevance": "Grouping rules"},
            {"authority": "IRC", "reference": "IRC §469(c)(7)", "relevance": "Real estate professional"},
            {"authority": "Case", "reference": "Tolin v. Commissioner, 154 T.C. No. 4 (2020)", "relevance": "Grouping"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges passive losses when: (1) no contemporaneous
time logs for material participation; (2) grouping elections never formally made; (3) real
estate professional hours not documented or under 750; (4) rental losses offset W-2 income
without active participation or RE professional status; (5) suspended losses claimed
without proper carryforward tracking.""",
        counter_arguments=[
            "Contemporaneous activity logs establish material participation",
            "Grouping election documented on return or statement",
            "Real estate professional calendar and hours log maintained",
            "Business records support participation claims",
            "Third-party evidence corroborates involvement"
        ],
        appeals_strategy="""§469 cases turn on documentation. Contemporaneous logs are gold
standard; reconstruct from calendars, emails, texts if needed. For real estate professional,
spouse's hours do NOT count for 750-hour test. Grouping elections are powerful but must
be properly made. At disposition, ensure all suspended losses properly computed and released.
Consider technical termination rules for partnerships.""",
        entity_scope=["individual", "trust", "estate", "partnership", "s_corporation"],
        confidence="high"
    ),

    "at_risk_rules_465": DoctrineBlock(
        topic="At-Risk Limitations - §465 Loss Limitation Rules",
        keywords=["at risk", "465", "at-risk rules", "nonrecourse debt",
                  "qualified nonrecourse financing", "amount at risk",
                  "recourse liability", "real estate financing"],
        conclusion_template="""Under §465, losses from activities are limited to the taxpayer's
amount at-risk. At-risk amount includes cash invested, adjusted basis of property contributed,
and amounts borrowed for which the taxpayer is personally liable or has pledged property.
Qualified nonrecourse financing is at-risk for real estate activities only. At-risk rules
apply AFTER §704(d) but BEFORE §469 passive activity limitations.""",
        reasoning_framework="""
AT-RISK LIMITATIONS — §465 ANALYSIS:

1. FUNDAMENTAL RULE (§465(a))
   Losses ONLY deductible to extent taxpayer is "at risk"

   Losses exceeding at-risk amount:
   □ Suspended (not lost)
   □ Carried forward indefinitely
   □ Deductible when at-risk amount increases

2. ACTIVITIES COVERED (§465(c))
   At-risk rules apply to:
   □ Holding, producing, distributing motion pictures/tapes
   □ Farming
   □ Leasing §1245 property
   □ Exploring/exploiting oil/gas/geothermal
   □ ALL OTHER ACTIVITIES (post-1978)

   NOTE: Virtually all business activities subject to §465

3. COMPUTING AMOUNT AT-RISK (§465(b))

   AMOUNTS INCLUDED — AT-RISK:
   □ Cash contributed to activity
   □ Adjusted basis of property contributed
   □ Amounts borrowed for which taxpayer is personally liable
   □ Amounts borrowed secured by property used in activity
     (but not property used in activity itself)
   □ Qualified nonrecourse financing (real estate only)

   AMOUNTS EXCLUDED — NOT AT-RISK:
   □ Nonrecourse debt (generally)
   □ Amounts protected against loss
   □ Amounts borrowed from related parties (if nonrecourse)
   □ Stop-loss agreements, guarantees

4. QUALIFIED NONRECOURSE FINANCING (§465(b)(6))
   ONLY for real estate — nonrecourse debt is at-risk IF:
   □ Borrowed from qualified lender (bank, govt, unrelated third party)
   □ NOT borrowed from related party
   □ NOT borrowed from seller or person receiving fee for loan
   □ NOT convertible debt

   Qualified Person: Federal/state government, bank, insurance company,
   pension plan, or person actively engaged in lending (but not seller)

5. RELATED PARTY FINANCING (§465(b)(3))
   Amounts borrowed from related parties NOT at-risk if:
   □ Nonrecourse nature
   □ OR protection against loss exists

   Related = §267(b) relationships

6. RECAPTURE RULES (§465(e))
   If at-risk amount DECREASES below zero:
   □ Previously deducted losses recaptured as income
   □ Common when debt refinanced to nonrecourse
   □ Recapture is ordinary income

7. ORDERING RULES
   Multiple loss limitations apply IN ORDER:
   1. §704(d) — Partnership basis limit
   2. §465 — At-risk limit (THIS ONE)
   3. §469 — Passive activity limit
   4. §461(l) — Excess business loss (post-TCJA)

8. AUDIT ISSUES
   - Nonrecourse debt treated as at-risk
   - Related party loans classified as at-risk
   - QNRF requirements not met
   - At-risk amount not recomputed annually
   - Recapture not recognized on refinancing""",
        key_factors=[
            "At-risk amount computed annually",
            "Recourse vs. nonrecourse debt properly classified",
            "Qualified nonrecourse financing requirements documented",
            "Related party debt identified and excluded",
            "Recapture triggered on decrease in at-risk amount"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §465", "relevance": "At-risk limitations"},
            {"authority": "IRC", "reference": "IRC §465(b)(6)", "relevance": "Qualified nonrecourse financing"},
            {"authority": "Reg", "reference": "Temp. Reg. §1.465-22", "relevance": "Real estate QNRF"},
            {"authority": "IRC", "reference": "IRC §465(e)", "relevance": "Recapture rules"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges at-risk amounts when: (1) nonrecourse debt
improperly included; (2) QNRF requirements not met (lender not qualified, related party);
(3) stop-loss agreements or guarantees exist; (4) recapture not recognized on refinancing;
(5) at-risk amount not properly reduced by distributions or losses.""",
        counter_arguments=[
            "Loan documents establish personal liability",
            "Lender qualifies under §465(b)(6)",
            "No related party involvement in financing",
            "Annual at-risk computation maintained",
            "No undisclosed guarantees or protection"
        ],
        appeals_strategy="""At-risk cases often turn on loan documentation and lender
qualification. Obtain loan agreements showing recourse nature. For QNRF, verify lender
is qualified person — actively and regularly engaged in lending business. Related party
analysis follows §267(b) rules. Watch for constructive ownership. Recapture applies
mechanically on refinancing — no intent element required.""",
        entity_scope=["individual", "trust", "estate", "partnership", "s_corporation", "c_corporation"],
        confidence="high"
    ),

    "hobby_loss_183": DoctrineBlock(
        topic="Hobby Loss Limitations - §183 Profit Motive Analysis",
        keywords=["hobby loss", "183", "profit motive", "not for profit",
                  "horse breeding", "farming hobby", "hobby deductions",
                  "9 factors", "section 183", "presumption"],
        conclusion_template="""Under §183, if an activity is not engaged in for profit, deductions
are limited to gross income from the activity. The determination is based on nine regulatory
factors, with no single factor controlling. A presumption of profit motive applies if the
activity is profitable in 3 of 5 consecutive years (2 of 7 for horse activities). The
taxpayer bears the burden of proving profit objective.""",
        reasoning_framework="""
HOBBY LOSS — §183 ANALYSIS:

1. FUNDAMENTAL RULE (§183(a)-(b))
   If activity NOT engaged in for profit:
   □ Deductions allowed ONLY to extent of gross income
   □ No net loss deduction
   □ Deductions allowed in priority order:
     1. Deductions allowed regardless (taxes, interest)
     2. Operating expenses (not affecting basis)
     3. Basis adjustments (depreciation)

2. KEY QUESTION: PROFIT MOTIVE
   Is activity engaged in with genuine objective of making profit?

   PROFIT = Any economic profit, not just tax benefit
   Need not be reasonable expectation of profit
   Need not expect profit every year
   Small profit can satisfy requirement

3. NINE REGULATORY FACTORS (Reg. §1.183-2(b))
   Courts weigh all factors — no single factor controls:

   □ FACTOR 1: Businesslike manner
     Records, separate accounts, business plan, changes when unprofitable

   □ FACTOR 2: Expertise of taxpayer/advisors
     Studied the activity, consulted experts, followed advice

   □ FACTOR 3: Time and effort expended
     Personal involvement, not delegated entirely

   □ FACTOR 4: Expectation of asset appreciation
     Land or other assets may appreciate despite operating losses

   □ FACTOR 5: Prior success in similar activities
     Track record in same or similar businesses

   □ FACTOR 6: History of income or losses
     Pattern of profits, losses only in startup, loss trend improving

   □ FACTOR 7: Amount of occasional profits
     Profits relative to losses, investment, asset appreciation

   □ FACTOR 8: Financial status of taxpayer
     Do losses offset other substantial income? (disfavors if yes)

   □ FACTOR 9: Elements of personal pleasure
     Activity enjoyable, recreational aspects (disfavors if strong)

4. PRESUMPTION OF PROFIT MOTIVE (§183(d))
   Activity PRESUMED for-profit IF:
   □ Gross income exceeds deductions in 3 of 5 consecutive years
   □ For horse breeding/racing: 2 of 7 consecutive years

   Presumption is REBUTTABLE by IRS
   Election to postpone determination available

5. ELECTION TO POSTPONE (§183(e))
   Taxpayer may elect to defer hobby determination
   until end of 5-year (or 7-year) period
   □ Extends statute of limitations for those years
   □ Interest accrues if activity later deemed hobby

6. TCJA IMPACT (2018-2025)
   §67 2% miscellaneous itemized deductions SUSPENDED
   □ Hobby expenses get NO deduction (itemizers)
   □ But hobby income still taxable
   □ Creates phantom income situations

7. SPECIFIC ACTIVITIES — HIGH SCRUTINY
   - Horse breeding/racing
   - Farming with other substantial income
   - Art collecting
   - Yacht chartering
   - Auto racing
   - Writing (unpublished)

8. AUDIT ISSUES
   - Recurring losses with no business plan adjustments
   - High personal enjoyment elements
   - Other substantial income offset by activity losses
   - Lack of business records
   - No expertise or expert consultation""",
        key_factors=[
            "Businesslike records and operations demonstrated",
            "Changes made in response to losses",
            "Expertise obtained through study or advisors",
            "Time and effort personally expended",
            "History shows improving trend toward profitability"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §183", "relevance": "Not-for-profit activity rules"},
            {"authority": "Reg", "reference": "Reg. §1.183-2", "relevance": "Nine factors"},
            {"authority": "Case", "reference": "Dreicer v. Commissioner, 78 T.C. 642 (1982)", "relevance": "Substantial/bona fide profit objective"},
            {"authority": "Case", "reference": "Golanty v. Commissioner, 72 T.C. 411 (1979)", "relevance": "Overall profit motive standard"},
            {"authority": "IRC", "reference": "IRC §183(d)", "relevance": "Presumption rules"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS asserts hobby classification when: (1) activity shows
consistent losses year after year; (2) taxpayer has substantial other income being offset;
(3) activity has significant personal enjoyment elements; (4) no meaningful business plan
or changes when unprofitable; (5) taxpayer lacks expertise and doesn't seek it.""",
        counter_arguments=[
            "Business plan exists and is followed",
            "Records kept in businesslike manner",
            "Expert advice sought and implemented",
            "Significant time devoted to activity",
            "Losses explainable by startup phase or market conditions",
            "Asset appreciation expected (land, breeding stock)"
        ],
        appeals_strategy="""§183 cases are highly factual. Document every business-improving
action taken. Obtain expert opinions on profitability prospects. Show adjustments made
in response to losses. De-emphasize personal enjoyment through separate personal use
tracking. If possible, achieve 3/5 profitability presumption. Consider §183(e) election
to delay determination if early years profitable.""",
        entity_scope=["individual", "sole_proprietorship", "partnership", "s_corporation"],
        confidence="high"
    ),

    "related_party_267": DoctrineBlock(
        topic="Related Party Transactions - §267 Loss Disallowance and Matching",
        keywords=["related party", "267", "loss disallowance", "related party loss",
                  "controlled group", "family attribution", "matching rules",
                  "constructive ownership", "267 deferred payment"],
        conclusion_template="""§267 disallows losses on sales between related parties. Related
parties include family members, controlled entities (>50% ownership), and fiduciaries.
The disallowed loss is preserved: the related buyer receives a reduced gain (or increased
loss) on later sale to an unrelated party. §267 also defers deduction timing on payments
between related accrual and cash-method parties. Attribution rules apply for ownership.""",
        reasoning_framework="""
RELATED PARTY TRANSACTIONS — §267 ANALYSIS:

1. LOSS DISALLOWANCE RULE (§267(a)(1))
   NO DEDUCTION for losses on sale/exchange of property between
   related persons (directly or indirectly)

   Effect:
   □ Seller's loss disallowed entirely
   □ Buyer takes cost basis (FMV paid)
   □ Loss "preserved" for buyer on subsequent sale

2. DEFERRED BUYER'S GAIN (§267(d))
   When buyer later sells to unrelated party:
   □ Gain recognized ONLY to extent it exceeds disallowed loss
   □ If buyer sells at loss, cannot use seller's disallowed loss
   □ Disallowed loss reduces buyer's gain, does not create loss

   Example:
   - Father sells stock to son: Basis $100, price $60, loss $40 (disallowed)
   - Son later sells to third party for $90
   - Son's gain: $30 ($90-$60), but reduced by $30 (portion of $40 disallowed loss)
   - Net taxable gain: $0

3. WHO IS RELATED? (§267(b))
   Comprehensive list of related parties:

   FAMILY (§267(c)(4)):
   □ Brothers, sisters (whole or half)
   □ Spouse
   □ Ancestors (parents, grandparents)
   □ Lineal descendants (children, grandchildren)
   NOTE: Aunts, uncles, cousins NOT included

   ENTITIES:
   □ Individual and >50% owned corporation
   □ Two corporations in same controlled group
   □ Grantor and fiduciary of trust
   □ Fiduciaries of two trusts with same grantor
   □ Trust and its beneficiary
   □ S corp and >50% shareholder
   □ C corp and partnership if same persons own >50%
   □ Two partnerships with same partners >50%
   □ Executor and beneficiary of estate

4. CONSTRUCTIVE OWNERSHIP (§267(c))
   Stock/interests owned by related party attributed:

   □ Family attribution: Stock owned by family member
   □ Entity-to-owner: From corp/partnership to >50% owner
   □ Owner-to-entity: From owner to >50% owned entity
   □ Option attribution: Right to acquire = ownership

   NO "family-to-entity" attribution
   NO reattribution from family to family

5. ACCRUAL-CASH MATCHING (§267(a)(2))
   Different rule for expense deductions:

   If related accrual-method payor owes cash-method payee:
   □ Payor's deduction DEFERRED until payee includes in income
   □ Prevents timing mismatch abuse
   □ Applies to interest, rent, compensation, etc.

6. 50% OWNERSHIP THRESHOLD
   Most §267 relationships require >50% ownership
   □ Measured by vote AND value for corporations
   □ Capital and profits for partnerships
   □ Attribution rules apply to determine %

7. COMMON SCENARIOS
   - Parent sells depreciated stock to child
   - Shareholder sells property to >50% owned corp
   - One related corp sells to another
   - Partnership sells to >50% partner

8. AUDIT ISSUES
   - Loss claimed on related party sale
   - Constructive ownership not considered
   - Buyer's basis not properly tracked
   - Matching rule ignored for accrual/cash
   - Family relationship not disclosed""",
        key_factors=[
            "Related party status properly determined",
            "Constructive ownership rules applied",
            "Disallowed loss documented for buyer",
            "Matching rules followed for accrual/cash",
            ">50% ownership threshold correctly computed"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §267(a)(1)", "relevance": "Loss disallowance"},
            {"authority": "IRC", "reference": "IRC §267(b)", "relevance": "Related party definitions"},
            {"authority": "IRC", "reference": "IRC §267(c)", "relevance": "Constructive ownership"},
            {"authority": "IRC", "reference": "IRC §267(d)", "relevance": "Buyer's gain limitation"},
            {"authority": "Case", "reference": "McWilliams v. Commissioner, 331 U.S. 694 (1947)", "relevance": "Indirect sales"}
        ],
        burden_holder="IRS initially; taxpayer if related status unclear",
        irs_typical_position="""The IRS disallows losses when: (1) sale is between listed
related parties under §267(b); (2) constructive ownership creates related status;
(3) indirect sales through intermediaries are identified; (4) step transactions
collapse multiple sales into single related party transaction.""",
        counter_arguments=[
            "Parties not within §267(b) listed relationships",
            "Constructive ownership does not apply (different family)",
            "Ownership below 50% threshold",
            "Transaction has independent business purpose",
            "Timing matches (accrual/cash rule satisfied)"
        ],
        appeals_strategy="""§267 turns on precise relationship analysis. Map all ownership
with attribution. Remember family attribution is limited to §267(c)(4) list. Cousins,
in-laws not included. Track disallowed losses for buyer's later use. For accrual/cash
matching, document when payee includes in income. McWilliams prohibits indirect sales
through intermediaries — substance over form applies.""",
        entity_scope=["individual", "c_corporation", "s_corporation", "partnership", "trust", "estate"],
        confidence="high"
    ),

    "installment_sales_453": DoctrineBlock(
        topic="Installment Sales - §453 Gain Deferral Method",
        keywords=["installment sale", "453", "installment method", "deferred gain",
                  "gross profit ratio", "installment note", "related party installment",
                  "453A interest", "dealer disposition"],
        conclusion_template="""§453 permits gain deferral on sales where at least one payment
is received after the year of sale. Gain is recognized proportionally as payments are
received using the gross profit ratio. The method is automatic unless elected out.
Special rules apply for related party resales, dealer dispositions, and depreciation
recapture. Interest charge applies to large installment obligations over $5 million.""",
        reasoning_framework="""
INSTALLMENT SALES — §453 ANALYSIS:

1. BASIC RULE (§453(a)-(b))
   Installment method applies automatically IF:
   □ At least one payment received after year of sale
   □ Gain realized on the sale
   □ Property is NOT dealer property (inventory)
   □ Taxpayer does NOT elect out

   Recognize gain proportionally as payments received

2. GROSS PROFIT RATIO COMPUTATION

   SELLING PRICE = Total contract price

   GROSS PROFIT = Selling price - Adjusted basis

   GROSS PROFIT RATIO = Gross Profit / Contract Price

   GAIN RECOGNIZED = Payment × Gross Profit Ratio

   Example:
   - Sell land: Basis $40K, Price $100K, $20K down, $80K note
   - Gross profit: $60K
   - Gross profit ratio: 60%
   - Year 1 gain: $20K × 60% = $12K

3. CONTRACT PRICE vs. SELLING PRICE
   Usually equal, BUT adjusted when buyer assumes seller's debt:

   If mortgage assumed ≤ basis:
   □ Contract price = Selling price - mortgage assumed

   If mortgage assumed > basis:
   □ Contract price = Selling price - basis
   □ Excess mortgage is "payment" in year of sale

4. EXCEPTIONS — INSTALLMENT METHOD NOT AVAILABLE

   □ Dealer dispositions (inventory, property held for sale)
   □ Depreciation recapture (§1245/§1250) — recognized in year of sale
   □ Publicly traded securities
   □ Elect out (election irrevocable)

5. RELATED PARTY RULES (§453(e)-(f))

   RESALE WITHIN 2 YEARS (§453(e)):
   If related buyer resells within 2 years:
   □ Original seller accelerates gain
   □ Amount received by related party triggers recognition
   □ Does NOT apply to sales after seller's death
   □ Does NOT apply if tax avoidance not principal purpose

   RELATED PARTY = §267(b) or §707(b) relationships

6. INTEREST CHARGE — LARGE OBLIGATIONS (§453A)
   For installment obligations over $5 million (aggregate):

   □ Interest charge on deferred tax
   □ Computed at underpayment rate
   □ Applies to "applicable installment obligations"
   □ Exceptions: personal use property, farm property

7. PLEDGING INSTALLMENT NOTES (§453A(d))
   If installment note pledged as collateral:
   □ Proceeds = payment received
   □ Accelerates gain recognition
   □ Applies to notes over $5 million threshold

8. DEPRECIATION RECAPTURE
   Installment method does NOT defer:
   □ §1245 recapture — 100% ordinary in year of sale
   □ §1250 recapture — recognized in year of sale
   □ Only §1231 gain portion eligible for deferral

9. AUDIT ISSUES
   - Gross profit ratio computation errors
   - Related party resale not reported
   - Depreciation recapture not recognized in year 1
   - Dealer property using installment method
   - Mortgage in excess of basis not treated as payment""",
        key_factors=[
            "Gross profit ratio correctly computed",
            "At least one payment after year of sale",
            "Depreciation recapture recognized in year 1",
            "Related party resale rules monitored",
            "Mortgage exceeding basis treated as payment"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §453", "relevance": "Installment method rules"},
            {"authority": "IRC", "reference": "IRC §453(e)", "relevance": "Related party resale"},
            {"authority": "IRC", "reference": "IRC §453A", "relevance": "Interest on large obligations"},
            {"authority": "Reg", "reference": "Reg. §15a.453-1", "relevance": "Computational rules"},
            {"authority": "IRC", "reference": "IRC §453(l)", "relevance": "Dealer exclusion"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges installment treatment when: (1) no payments
actually deferred (sham note); (2) gross profit ratio understates gain; (3) related party
resale within 2 years not reported; (4) depreciation recapture deferred improperly;
(5) dealer property treated as capital asset.""",
        counter_arguments=[
            "Note is bona fide debt obligation",
            "Gross profit ratio computation documented",
            "Related party resale occurred after 2 years",
            "Tax avoidance not principal purpose",
            "Property not held primarily for sale to customers"
        ],
        appeals_strategy="""Installment sales require careful documentation. Maintain note
terms, payment schedules, amortization. For related party sales, document non-tax
purpose for installment terms. Consider §453(e)(2) exceptions. Depreciation recapture
is mechanical — compute §1245/§1250 amounts separately. If mortgage exceeds basis,
that excess is payment in year 1 regardless of actual cash received.""",
        entity_scope=["individual", "c_corporation", "s_corporation", "partnership", "trust", "estate"],
        confidence="high"
    ),

    "like_kind_exchange_1031": DoctrineBlock(
        topic="Like-Kind Exchanges - §1031 Real Property Exchanges (Post-TCJA)",
        keywords=["1031 exchange", "like kind", "like-kind exchange", "qualified intermediary",
                  "deferred exchange", "reverse exchange", "boot", "1031 real estate",
                  "identification period", "exchange period", "45 days", "180 days"],
        conclusion_template="""After TCJA, §1031 applies ONLY to real property held for productive
use or investment. Personal property no longer qualifies. Gain is deferred if replacement
property is identified within 45 days and received within 180 days. Use of qualified
intermediary is essential for deferred exchanges. Boot (cash or unlike property) is
taxable to extent of gain. Basis carries over, reduced by boot received, increased
by boot paid.""",
        reasoning_framework="""
LIKE-KIND EXCHANGES — §1031 ANALYSIS (POST-TCJA):

1. FUNDAMENTAL RULE (§1031(a))
   NO GAIN OR LOSS recognized on exchange of:
   □ Real property held for productive use in trade/business
   □ OR Real property held for investment
   □ EXCHANGED for like-kind real property

   TCJA CHANGE (2018+): ONLY real property qualifies
   Personal property, vehicles, equipment — NO LONGER eligible

2. "LIKE-KIND" FOR REAL PROPERTY
   Very broad definition:
   □ Any real property for any real property
   □ Improved for unimproved (OK)
   □ Fee simple for leasehold 30+ years (OK)
   □ Commercial for residential (OK)
   □ Land for building (OK)

   NOT LIKE-KIND:
   □ U.S. real property for foreign real property
   □ Real property for personal property
   □ Inventory / dealer property

3. HELD FOR REQUIREMENT
   Both properties must be:
   □ Held for productive use in trade/business, OR
   □ Held for investment

   NOT QUALIFYING:
   □ Property held primarily for sale (dealer)
   □ Primary residence
   □ Second home / personal use (generally)

4. DEFERRED EXCHANGE — TIMING RULES
   For non-simultaneous exchanges (most common):

   IDENTIFICATION PERIOD:
   □ 45 days from transfer of relinquished property
   □ Must identify replacement property in writing
   □ Three-property rule OR 200% rule

   EXCHANGE PERIOD:
   □ 180 days from transfer OR due date of return (with extension)
   □ Whichever is EARLIER
   □ Replacement property must be received by this date

   NO EXTENSIONS — deadlines are absolute

5. IDENTIFICATION RULES
   Three alternatives:

   □ THREE-PROPERTY RULE: Identify up to 3 properties (any value)
   □ 200% RULE: Identify any number if total FMV ≤ 200% of relinquished
   □ 95% RULE: Any number if acquire 95% of identified FMV

6. QUALIFIED INTERMEDIARY (§1031 regulations)
   Deferred exchanges require QI:
   □ Cannot be related party
   □ Cannot be agent of taxpayer
   □ Holds proceeds during exchange period
   □ Direct deeding permitted

   DISQUALIFIED PERSONS: Attorney, accountant, broker who
   served taxpayer within 2 years

7. BOOT — TAXABLE AMOUNT (§1031(b)-(c))
   "Boot" = Unlike property or cash received

   Gain recognized = LESSER OF:
   □ Boot received, OR
   □ Gain realized on exchange

   MORTGAGE BOOT: Net relief from liability = boot
   Cash paid/liability assumed offsets mortgage boot

8. BASIS COMPUTATION (§1031(d))
   Basis in replacement property:

   Start: Basis in relinquished property
   Add: Boot paid (cash or liability assumed)
   Add: Gain recognized
   Subtract: Boot received (cash or liability relief)
   Subtract: Loss recognized (if any)

   = Basis in replacement property

9. REVERSE EXCHANGES
   Acquire replacement BEFORE selling relinquished:
   □ Must use Exchange Accommodation Titleholder (EAT)
   □ Rev. Proc. 2000-37 safe harbor
   □ 180-day limit for entire transaction

10. AUDIT ISSUES
    - Identification not timely or proper
    - Exchange period exceeded
    - QI disqualified (related party, prior relationship)
    - Boot not recognized
    - Property held for personal use
    - Dealer property exchanged""",
        key_factors=[
            "Both properties are qualifying real property",
            "45-day identification properly documented",
            "180-day exchange period satisfied",
            "Qualified intermediary properly engaged",
            "Boot correctly computed and recognized"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §1031", "relevance": "Like-kind exchange rules"},
            {"authority": "Reg", "reference": "Reg. §1.1031(k)-1", "relevance": "Deferred exchange rules"},
            {"authority": "Rev Proc", "reference": "Rev. Proc. 2000-37", "relevance": "Reverse exchange safe harbor"},
            {"authority": "IRC", "reference": "IRC §1031(a)(1)", "relevance": "TCJA real property limitation"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges §1031 treatment when: (1) identification
requirements not strictly met; (2) exchange period exceeded; (3) QI is disqualified
person; (4) property held for sale or personal use; (5) boot not properly recognized;
(6) basis inflated in replacement property.""",
        counter_arguments=[
            "Written identification within 45 days documented",
            "Replacement property received within 180 days",
            "QI independence verified (no prior 2-year relationship)",
            "Both properties held for investment/business use",
            "Boot computation correctly follows netting rules"
        ],
        appeals_strategy="""§1031 requirements are strictly interpreted. Document everything:
identification letters (sent within 45 days), QI agreement, closing dates. For held-for
requirement, show investment intent through holding period, no dealer activity, minimal
personal use. Boot netting requires careful computation — net mortgage relief against
cash paid. Post-TCJA, only real property qualifies; personal property assets must be
separately valued and recognized.""",
        entity_scope=["individual", "c_corporation", "s_corporation", "partnership", "trust"],
        confidence="high"
    ),

    "self_employment_tax_1401": DoctrineBlock(
        topic="Self-Employment Tax - §1401/§1402 SE Tax Computation",
        keywords=["self-employment tax", "1401", "1402", "SE tax", "self employed",
                  "net earnings", "limited partner", "LLC member SE tax",
                  "FICA alternative", "SE health insurance"],
        conclusion_template="""Self-employment tax under §1401 applies to net earnings from
self-employment at 15.3% (12.4% OASDI + 2.9% Medicare). Net earnings are computed under
§1402 with special rules for different entity types. Limited partners are generally
exempt except for guaranteed payments. S-Corp reasonable compensation must be paid.
LLC members' treatment depends on nature of services and ownership.""",
        reasoning_framework="""
SELF-EMPLOYMENT TAX — §1401/§1402 ANALYSIS:

1. FUNDAMENTAL RULE (§1401)
   Self-employment tax applies to net earnings from self-employment:

   RATES (2024):
   □ OASDI: 12.4% on first $168,600 (wage base, indexed)
   □ Medicare: 2.9% on all net SE earnings
   □ Additional Medicare: 0.9% on SE income over $200K/$250K (MFJ)

   TOTAL: 15.3% (up to wage base) + 2.9%/3.8% above

2. NET EARNINGS FROM SELF-EMPLOYMENT (§1402)

   INCLUDED:
   □ Net income from sole proprietorship (Schedule C)
   □ Distributive share of partnership income (general partner)
   □ Guaranteed payments for services (all partners)
   □ Net farm income (Schedule F)
   □ Director fees

   EXCLUDED:
   □ Limited partner's share of partnership income (§1402(a)(13))
   □ Rental income (generally)
   □ Dividends, interest, capital gains
   □ S-Corp distributions (NOT compensation)
   □ Retirement income

3. 92.35% DEDUCTION (§1402(a)(12))
   Net earnings multiplied by 92.35%
   □ Effectively mimics employer's share exclusion
   □ Applied before computing SE tax

4. DEDUCTION FOR 1/2 SE TAX (§164(f))
   Taxpayer deducts 1/2 of SE tax:
   □ Above-the-line deduction
   □ Reduces AGI (not Schedule C)
   □ Does not reduce net SE earnings for SE tax computation

5. S-CORPORATION — AVOIDING SE TAX
   S-Corp distributions NOT subject to SE tax BUT:
   □ Must pay reasonable compensation as W-2 wages
   □ IRS aggressively challenges inadequate salaries
   □ Watson factors apply for reasonable compensation
   □ See "reasonable_compensation" doctrine

6. LIMITED PARTNER EXCEPTION (§1402(a)(13))
   Limited partner's share EXCLUDED except:
   □ Guaranteed payments for services
   □ Not clearly defined for LLCs

   Proposed regulations (withdrawn): Member must have
   limited liability AND not be service partner

7. LLC MEMBER — UNCERTAIN TREATMENT
   No clear statutory guidance:

   POSITIONS:
   □ Treat like general partner (all subject to SE)
   □ Treat like limited partner if limited liability and passive
   □ Bifurcate: Service portion subject, investment portion not

   RENKEMEYER (Tax Court 2011): Members who perform services
   for LLC = subject to SE tax on allocable share

8. REAL ESTATE PROFESSIONALS
   Rental income GENERALLY excluded BUT:
   □ Real estate dealer income = SE income
   □ Short-term rentals with substantial services = SE income
   □ RE professional status alone doesn't create SE income

9. SE HEALTH INSURANCE DEDUCTION (§162(l))
   Self-employed may deduct health insurance:
   □ Above-the-line deduction
   □ Limited to net SE income
   □ Does NOT reduce SE income for SE tax
   □ Cannot deduct if eligible for employer plan

10. AUDIT ISSUES
    - S-Corp salary too low (SE tax avoidance)
    - LLC member improperly claims limited partner exception
    - Rental income improperly classified as SE
    - Farm losses offset other SE income
    - 92.35% and 1/2 deduction computed incorrectly""",
        key_factors=[
            "Net SE earnings correctly computed",
            "S-Corp pays reasonable compensation",
            "LLC member's services properly analyzed",
            "Limited partner exception properly applied",
            "Guaranteed payments included in SE base"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §1401", "relevance": "SE tax rates"},
            {"authority": "IRC", "reference": "IRC §1402", "relevance": "Net SE earnings definition"},
            {"authority": "IRC", "reference": "IRC §1402(a)(13)", "relevance": "Limited partner exception"},
            {"authority": "Case", "reference": "Renkemeyer v. Commissioner, 136 T.C. 137 (2011)", "relevance": "LLC member SE tax"},
            {"authority": "Case", "reference": "Watson v. Commissioner, 668 F.3d 1008 (8th Cir. 2012)", "relevance": "S-Corp reasonable comp"}
        ],
        burden_holder="taxpayer (for exclusions)",
        irs_typical_position="""The IRS asserts SE tax liability when: (1) S-Corp distributions
are disguised compensation; (2) LLC members providing services claim limited partner
exception; (3) rental income involves substantial services; (4) taxpayer takes aggressive
positions on limited partner status without statutory support.""",
        counter_arguments=[
            "S-Corp compensation is reasonable and documented",
            "LLC member is passive investor, not service provider",
            "Rental activities lack substantial personal services",
            "Limited partner status based on state law status",
            "Industry comparables support compensation level"
        ],
        appeals_strategy="""SE tax issues often overlap with entity choice planning. For S-Corps,
reasonable compensation is key — document with comparables, job descriptions, industry
data. For LLCs, Renkemeyer suggests service partners are subject to SE tax; structure
to segregate investment and service activities if possible. Limited partner exception
remains unsettled for LLCs — conservative approach is to include allocable share for
service partners.""",
        entity_scope=["individual", "sole_proprietorship", "partnership", "llc", "s_corporation"],
        confidence="high"
    ),

    "accuracy_related_penalty_6662": DoctrineBlock(
        topic="Accuracy-Related Penalties - §6662 Substantial Understatement",
        keywords=["accuracy penalty", "6662", "substantial understatement", "negligence",
                  "reasonable basis", "substantial authority", "reasonable cause",
                  "disclosure", "20% penalty", "penalty abatement"],
        conclusion_template="""The §6662 accuracy-related penalty is 20% of the underpayment
attributable to negligence, substantial understatement, or valuation misstatements.
Substantial understatement is the greater of $5,000 or 10% of required tax. The penalty
is avoided through adequate disclosure (reasonable basis) or substantial authority.
Reasonable cause and good faith is a complete defense. Documentation and professional
advice are critical for penalty defense.""",
        reasoning_framework="""
ACCURACY-RELATED PENALTIES — §6662 ANALYSIS:

1. THE PENALTY (§6662(a))
   20% of underpayment attributable to:
   □ Negligence or disregard of rules (§6662(b)(1))
   □ Substantial understatement of income tax (§6662(b)(2))
   □ Substantial valuation misstatement (§6662(b)(3))
   □ Substantial overstatement of pension liabilities (§6662(b)(4))
   □ Substantial estate/gift valuation understatement (§6662(b)(5))

   Increased to 40% for gross valuation misstatement

2. NEGLIGENCE (§6662(c))
   Defined as: Failure to make reasonable attempt to comply

   INCLUDES:
   □ Failure to keep adequate books/records
   □ Failure to substantiate items properly
   □ Disregard = careless, reckless, intentional

   DEFENSE: Reasonable cause and good faith

3. SUBSTANTIAL UNDERSTATEMENT (§6662(d))
   Understatement is "substantial" if it exceeds GREATER OF:
   □ $5,000 ($10,000 for corporations), OR
   □ 10% of tax required to be shown (5% for corps over $10M)

   REDUCTION OF UNDERSTATEMENT:
   Understatement reduced if:
   □ Substantial authority for position, OR
   □ Adequate disclosure AND reasonable basis

4. SUBSTANTIAL AUTHORITY (§6662(d)(2))
   Higher standard — must be SUBSTANTIAL weight of authorities:

   AUTHORITIES (Reg. §1.6662-4(d)):
   □ IRC, Treasury regulations
   □ Court cases, Revenue Rulings/Procedures
   □ Tax treaties, Congressional intent materials
   □ IRS notices, announcements
   □ Private letter rulings (to taxpayer)

   NOT AUTHORITIES: Conclusions in treatises, opinions

   STANDARD: Approximately 40% chance of success

5. REASONABLE BASIS (§6662(d)(2)(B))
   Lower standard — arguable position with some support:
   □ Not frivolous or patently improper
   □ Approximately 20% chance of success
   □ Requires ADEQUATE DISCLOSURE to use

6. ADEQUATE DISCLOSURE
   Required to use reasonable basis standard:

   FORM 8275: Disclosure Statement
   FORM 8275-R: Regulation contrary disclosure

   Disclosure must be specific:
   □ Identify item and facts
   □ State legal support for position
   □ Attach to return

7. REASONABLE CAUSE DEFENSE (§6664(c))
   NO PENALTY if taxpayer shows:
   □ Reasonable cause for underpayment, AND
   □ Taxpayer acted in good faith

   FACTORS CONSIDERED:
   □ Taxpayer's efforts to determine correct tax
   □ Experience, knowledge, education of taxpayer
   □ Reliance on professional advice
   □ Complexity of issue

8. RELIANCE ON PROFESSIONAL ADVICE
   Requires (Reg. §1.6664-4(c)):
   □ Advice from qualified tax professional
   □ All material facts disclosed to advisor
   □ Reasonable reliance in good faith
   □ Advisor had no conflict of interest

9. PENALTY STACKING
   Only one 20% penalty applies per item
   But different components can apply to different items
   Negligence and substantial understatement don't "stack"

10. AUDIT ISSUES / DEFENSE CHECKLIST
    □ Was disclosure made? (Form 8275)
    □ Is there substantial authority? (document authorities)
    □ Was professional advice obtained? (retain engagement letter)
    □ Were facts fully disclosed to advisor?
    □ Did taxpayer act in good faith?""",
        key_factors=[
            "Understatement amount quantified",
            "Authority analysis documented",
            "Disclosure made if required (Form 8275)",
            "Professional advice obtained and relied upon",
            "Good faith efforts demonstrated"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §6662", "relevance": "Accuracy penalty framework"},
            {"authority": "IRC", "reference": "IRC §6664(c)", "relevance": "Reasonable cause defense"},
            {"authority": "Reg", "reference": "Reg. §1.6662-4", "relevance": "Substantial understatement"},
            {"authority": "Reg", "reference": "Reg. §1.6664-4", "relevance": "Reasonable cause"},
            {"authority": "Case", "reference": "Neonatology Associates v. Commissioner, 115 T.C. 43 (2000)", "relevance": "Reliance on advisor"}
        ],
        burden_holder="IRS for penalty assertion; taxpayer for reasonable cause",
        irs_typical_position="""The IRS asserts §6662 penalties when: (1) underpayment exceeds
substantial understatement threshold; (2) no disclosure made for questionable position;
(3) authorities cited do not support position taken; (4) professional advice not obtained
or taxpayer did not fully disclose facts to advisor; (5) taxpayer is sophisticated and
should have known position was incorrect.""",
        counter_arguments=[
            "Position supported by substantial authority",
            "Adequate disclosure made on Form 8275",
            "Relied on qualified tax professional's advice",
            "All material facts disclosed to advisor",
            "Complex issue with reasonable interpretation"
        ],
        appeals_strategy="""Penalty defense requires preparation from day one. Document
authority analysis in file. Obtain written professional advice before filing. If
position is aggressive, consider disclosure (Form 8275) as insurance. At audit,
demonstrate good faith: records kept, efforts made to comply, professional consultation.
Reasonable cause is highly factual — taxpayer's education, experience, and efforts
all matter. Neonatology sets standard for reliance on advisors.""",
        entity_scope=["individual", "c_corporation", "s_corporation", "partnership", "trust", "estate"],
        confidence="high"
    ),

    "innocent_spouse_6015": DoctrineBlock(
        topic="Innocent Spouse Relief - §6015 Relief from Joint Liability",
        keywords=["innocent spouse", "6015", "joint liability", "injured spouse",
                  "equitable relief", "separation of liability", "understatement relief",
                  "joint return liability", "tax relief spouse"],
        conclusion_template="""§6015 provides three types of relief from joint and several
liability on joint returns: (1) Innocent spouse relief under §6015(b) for understatements;
(2) Separation of liability under §6015(c) for separated/divorced spouses; (3) Equitable
relief under §6015(f) when other relief unavailable. The requesting spouse must file
Form 8857 and demonstrate they did not know and had no reason to know of the understatement
or erroneous item.""",
        reasoning_framework="""
INNOCENT SPOUSE RELIEF — §6015 ANALYSIS:

1. JOINT AND SEVERAL LIABILITY
   Default rule for joint returns:
   □ BOTH spouses liable for ENTIRE tax
   □ IRS can collect from either spouse
   □ Divorce decree does NOT bind IRS
   □ §6015 provides relief in certain situations

2. THREE TYPES OF RELIEF

   A. INNOCENT SPOUSE RELIEF (§6015(b))
   B. SEPARATION OF LIABILITY (§6015(c))
   C. EQUITABLE RELIEF (§6015(f))

3. INNOCENT SPOUSE RELIEF — §6015(b)
   REQUIREMENTS (ALL must be met):

   □ Joint return filed
   □ Understatement of tax due to erroneous item of OTHER spouse
   □ Requesting spouse did not KNOW and had no REASON TO KNOW
   □ Considering all facts, inequitable to hold liable

   "ERRONEOUS ITEM":
   □ Unreported income
   □ Incorrect deduction, credit, or basis
   □ Must be attributable to other spouse

   "KNEW OR REASON TO KNOW":
   □ Actual knowledge of erroneous item
   □ OR constructive knowledge (should have known)
   □ Factors: education, involvement in finances, suspicious circumstances

4. SEPARATION OF LIABILITY — §6015(c)
   Allocates liability between spouses:

   ELIGIBLE IF (at time of election):
   □ No longer married to same spouse, OR
   □ Legally separated, OR
   □ Living apart for 12+ months

   ALLOCATION:
   □ Deficiency allocated as if separate returns filed
   □ Each spouse liable only for own portion
   □ Actual knowledge of item bars allocation of that item

   DISQUALIFICATION:
   □ Assets transferred to avoid tax (fraudulent transfer)
   □ Actual knowledge of erroneous item

5. EQUITABLE RELIEF — §6015(f)
   Available when §6015(b) or (c) don't apply:

   THRESHOLD CONDITIONS:
   □ Joint return filed
   □ Requesting spouse does not qualify under (b) or (c)
   □ Request timely (see timing below)
   □ No fraud with respect to underlying liability

   FACTORS CONSIDERED (Rev. Proc. 2013-34):
   □ Marital status
   □ Economic hardship
   □ Knowledge or reason to know
   □ Legal obligation of other spouse (divorce decree)
   □ Significant benefit
   □ Compliance with tax laws
   □ Mental or physical health issues

6. TIMING REQUIREMENTS

   §6015(b) and (c): Request within 2 years of first collection activity
   §6015(f): No statutory deadline (collection statute applies)

   "FIRST COLLECTION ACTIVITY":
   □ Levy or seizure
   □ Offset against refund
   □ Filing of suit against requesting spouse

7. FORM 8857 PROCEDURE
   □ File Form 8857, Request for Innocent Spouse Relief
   □ IRS must notify other spouse and allow response
   □ Request Tax Court review if denied (90 days)
   □ Burden of proof on requesting spouse

8. "INJURED SPOUSE" VS. "INNOCENT SPOUSE"
   DIFFERENT CONCEPTS:

   INJURED SPOUSE (Form 8379):
   □ Other spouse has past-due debt (child support, student loans)
   □ Refund offset to pay other spouse's debt
   □ Claim share of refund

   INNOCENT SPOUSE (Form 8857):
   □ Other spouse caused understatement
   □ Relief from joint liability
   □ §6015 analysis

9. AUDIT/APPEAL ISSUES
   - Did requesting spouse have actual knowledge?
   - Should requesting spouse have known (red flags)?
   - Economic hardship demonstrated?
   - Mental health / abuse factors present?
   - Was benefit from erroneous item significant?""",
        key_factors=[
            "Joint return filed",
            "Erroneous item attributable to other spouse",
            "No actual knowledge of understatement",
            "No reason to know (constructive knowledge)",
            "Inequitable to hold requesting spouse liable"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §6015", "relevance": "Relief from joint liability"},
            {"authority": "IRC", "reference": "IRC §6015(b)", "relevance": "Innocent spouse relief"},
            {"authority": "IRC", "reference": "IRC §6015(c)", "relevance": "Separation of liability"},
            {"authority": "IRC", "reference": "IRC §6015(f)", "relevance": "Equitable relief"},
            {"authority": "Rev Proc", "reference": "Rev. Proc. 2013-34", "relevance": "Equitable relief factors"}
        ],
        burden_holder="requesting spouse",
        irs_typical_position="""The IRS denies innocent spouse relief when: (1) requesting
spouse had actual or constructive knowledge of understatement; (2) requesting spouse
significantly benefited from erroneous items; (3) requesting spouse was involved in
business or financial decisions; (4) red flags should have prompted inquiry; (5) requesting
spouse failed to comply with own tax obligations.""",
        counter_arguments=[
            "No actual knowledge of other spouse's errors",
            "No access to financial records or business",
            "Abuse or control by other spouse",
            "Reasonable to trust other spouse's representations",
            "Minimal benefit from understatement"
        ],
        appeals_strategy="""Innocent spouse cases are intensely factual. Document separation
of financial responsibilities. If abuse present, this is heavily weighted. Economic
hardship strengthens equitable relief claim. File Form 8857 promptly. Be prepared for
other spouse's response — IRS must notify them. Tax Court review available if denied.
Rev. Proc. 2013-34 factors guide equitable relief analysis — address each explicitly.""",
        entity_scope=["individual"],
        confidence="high"
    ),

    "private_foundation_4940": DoctrineBlock(
        topic="Private Foundation Excise Taxes - §4940-§4945 Operational Rules",
        keywords=["private foundation", "4940", "4941", "4942", "4943", "4944", "4945",
                  "excise tax foundation", "self-dealing", "minimum distribution",
                  "excess business holdings", "jeopardizing investment", "taxable expenditure"],
        conclusion_template="""Private foundations face six Chapter 42 excise taxes: (1) §4940
net investment income tax (1.39%); (2) §4941 self-dealing prohibition; (3) §4942 minimum
distribution requirement (5%); (4) §4943 excess business holdings; (5) §4944 jeopardizing
investments; (6) §4945 taxable expenditures. Violations trigger first-tier and second-tier
taxes on both the foundation and disqualified persons. Correction and abatement provisions
exist but require prompt action.""",
        reasoning_framework="""
PRIVATE FOUNDATION EXCISE TAXES — §4940-§4945 ANALYSIS:

1. §4940 — NET INVESTMENT INCOME TAX

   RATE: 1.39% of net investment income (reduced from 2%)

   NET INVESTMENT INCOME:
   □ Interest, dividends, rents, royalties
   □ Capital gains (including short-term)
   □ MINUS: Expenses allocable to investment income

   EXEMPT OPERATING FOUNDATIONS: Not subject to §4940

2. §4941 — SELF-DEALING

   PROHIBITED TRANSACTIONS with disqualified persons:
   □ Sale/exchange/lease of property
   □ Lending money or extending credit
   □ Furnishing goods, services, or facilities
   □ Payment of compensation (except reasonable for services)
   □ Transfer or use of income/assets
   □ Payment to government official

   DISQUALIFIED PERSONS:
   □ Substantial contributors (and family)
   □ Foundation managers (and family)
   □ 20%+ owners of substantial contributor entities
   □ Family members of above
   □ Entities 35%+ owned by above

   TAXES:
   □ First-tier: 10% on self-dealer, 5% on manager
   □ Second-tier: 200% on self-dealer, 50% on manager

   NO DE MINIMIS — Any self-dealing is taxable

3. §4942 — MINIMUM DISTRIBUTION REQUIREMENT

   RULE: Must distribute 5% of non-charitable assets annually

   "DISTRIBUTABLE AMOUNT":
   □ 5% of average FMV of non-charitable assets
   □ Reduced by §4940 tax paid

   QUALIFYING DISTRIBUTIONS:
   □ Grants to public charities
   □ Direct charitable program expenses
   □ Set-asides for specific projects
   □ Administrative expenses (limited)

   TAXES:
   □ First-tier: 30% of undistributed amount
   □ Second-tier: 100% if not corrected

   5-YEAR CARRYFORWARD: Excess distributions carry forward

4. §4943 — EXCESS BUSINESS HOLDINGS

   RULE: Foundation + disqualified persons cannot hold >20%
   of voting stock in business enterprise (35% if independent control)

   EXCEPTIONS:
   □ Functionally related businesses
   □ Program-related investments
   □ De minimis holdings (2% or less)

   TAXES:
   □ First-tier: 10% of excess holdings
   □ Second-tier: 200% if not corrected

5. §4944 — JEOPARDIZING INVESTMENTS

   RULE: Cannot make investments that jeopardize charitable purpose

   STANDARD: Prudent trustee standard — would prudent person
   invest this way considering foundation's needs?

   NOT AUTOMATICALLY JEOPARDIZING:
   □ Program-related investments
   □ Properly diversified portfolio
   □ Mission-related investments with analysis

   TAXES:
   □ First-tier: 10% on foundation, 10% on manager
   □ Second-tier: 25% on foundation, 5% on manager

6. §4945 — TAXABLE EXPENDITURES

   PROHIBITED EXPENDITURES:
   □ Lobbying (direct or grassroots)
   □ Electioneering / political campaigns
   □ Grants to individuals without IRS-approved procedure
   □ Grants to non-charities without expenditure responsibility
   □ Non-charitable purposes

   EXPENDITURE RESPONSIBILITY:
   Required for grants to non-public charities:
   □ Pre-grant inquiry
   □ Written agreement with terms
   □ Separate fund accounting
   □ Annual reports to foundation

   TAXES:
   □ First-tier: 20% on foundation, 5% on manager
   □ Second-tier: 100% on foundation, 50% on manager

7. CORRECTION AND ABATEMENT

   CORRECTION: Undo the prohibited act
   □ Self-dealing: Rescind transaction
   □ Underdistribution: Distribute the amount
   □ Excess holdings: Dispose of holdings

   ABATEMENT: Second-tier taxes abated if:
   □ Correction made before notice of deficiency
   □ OR Correction made and reasonable cause shown

8. FORM 990-PF REPORTING
   All private foundations must file Form 990-PF:
   □ Report all Chapter 42 calculations
   □ List disqualified persons and transactions
   □ Report grants and distributions
   □ Compute minimum distribution requirement""",
        key_factors=[
            "Disqualified person status properly determined",
            "No self-dealing transactions occurred",
            "5% minimum distribution made annually",
            "Excess business holdings disposed timely",
            "Grant procedures followed (expenditure responsibility)"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §4940-§4945", "relevance": "Chapter 42 excise taxes"},
            {"authority": "IRC", "reference": "IRC §4946", "relevance": "Disqualified person definition"},
            {"authority": "Reg", "reference": "Reg. §53.4941-1", "relevance": "Self-dealing rules"},
            {"authority": "Reg", "reference": "Reg. §53.4942-1", "relevance": "Minimum distribution"},
            {"authority": "Reg", "reference": "Reg. §53.4945-4", "relevance": "Grants to individuals"}
        ],
        burden_holder="foundation (for showing compliance and reasonable cause)",
        irs_typical_position="""The IRS asserts Chapter 42 taxes when: (1) transactions with
disqualified persons not at arm's length or not excepted; (2) 5% distribution requirement
not met; (3) business holdings exceed permitted levels; (4) investments made without
proper analysis; (5) grants made without required procedures.""",
        counter_arguments=[
            "Transaction falls within statutory exception",
            "Reasonable cause for failure to distribute",
            "Holdings within permitted percentage",
            "Investment analysis documented jeopardizing investment defense",
            "Grant procedures followed and documented"
        ],
        appeals_strategy="""Private foundation issues require meticulous documentation.
Self-dealing has no de minimis — even small transactions with disqualified persons
create liability. For minimum distribution, document all qualifying distributions
including administrative costs. Excess business holdings have 5-year disposition
period for inherited interests. Jeopardizing investments require prudent trustee
analysis in writing BEFORE investment. Correct promptly to avoid second-tier taxes.""",
        entity_scope=["trust", "c_corporation"],
        confidence="high"
    ),

    "charitable_contribution_170": DoctrineBlock(
        topic="Charitable Contributions - §170 Substantiation and Valuation",
        keywords=["charitable contribution", "170", "charity deduction", "substantiation",
                  "qualified appraisal", "8283", "cash contribution", "vehicle donation",
                  "clothing donation", "fair market value"],
        conclusion_template="""Charitable contribution deductions under §170 require strict
substantiation and, for non-cash contributions over $5,000, a qualified appraisal.
Cash contributions require bank record or written acknowledgment from the charity.
Donations over $250 require contemporaneous written acknowledgment with specific content.
Claimed fair market value must be supportable; penalties apply for gross valuation
misstatements. Form 8283 required for non-cash contributions over $500.""",
        reasoning_framework="""
CHARITABLE CONTRIBUTIONS — §170 ANALYSIS:

1. FUNDAMENTAL REQUIREMENTS (§170(a))
   Deduction allowed for contributions to qualified organizations:
   □ 501(c)(3) organizations
   □ Government entities
   □ War veterans' organizations
   □ Domestic fraternal societies (if used for charitable purposes)

2. SUBSTANTIATION REQUIREMENTS — BY AMOUNT

   CASH CONTRIBUTIONS:
   □ Under $250: Bank record, receipt, or other reliable written record
   □ $250+: Contemporaneous written acknowledgment (CWA) from charity

   CWA MUST INCLUDE:
   □ Amount of cash contributed
   □ Description of non-cash property (no value required)
   □ Whether goods or services provided in exchange
   □ Good faith estimate of value of goods/services
   □ Statement that only intangible religious benefits provided (if applicable)

   "CONTEMPORANEOUS" = Obtained by earlier of:
   □ Return due date (including extensions), OR
   □ Date return actually filed

3. NON-CASH CONTRIBUTIONS — SUBSTANTIATION TIERS

   $250 - $500:
   □ CWA from charity required

   $501 - $5,000:
   □ CWA required
   □ Form 8283 Section A required
   □ Must describe property, date acquired, method of acquisition, cost basis

   OVER $5,000 (except publicly traded securities):
   □ CWA required
   □ Qualified appraisal required
   □ Form 8283 Section B with appraiser signature
   □ Donee acknowledgment on Form 8283

   OVER $500,000:
   □ All above requirements
   □ Attach actual appraisal to return

4. QUALIFIED APPRAISAL REQUIREMENTS (Reg. §1.170A-13(c))
   Appraisal must be:
   □ Made not earlier than 60 days before contribution
   □ Received before return due date (with extensions)
   □ Prepared by qualified appraiser

   MUST INCLUDE:
   □ Description of property
   □ Physical condition
   □ Date of contribution
   □ Terms of agreement with donee
   □ Appraiser qualifications
   □ Appraiser signature and statement
   □ FMV on date of contribution with method used

5. QUALIFIED APPRAISER (Reg. §1.170A-17)
   □ Earned designation from recognized appraiser organization, OR
   □ Met minimum education and experience requirements
   □ Regularly performs appraisals for compensation
   □ Not excluded person (donor, donee, party to transaction)

6. VEHICLES, BOATS, AIRCRAFT (§170(f)(12))
   If charity sells vehicle without material use:
   □ Deduction limited to gross proceeds
   □ CWA must state whether charity provided goods/services
   □ Form 1098-C required from charity

7. CLOTHING AND HOUSEHOLD ITEMS (§170(f)(16))
   Deduction allowed only if property in "good used condition or better"
   Exception: Items over $500 with qualified appraisal

8. VALUATION — FAIR MARKET VALUE
   Generally: Price willing buyer would pay willing seller

   COMMON ISSUES:
   □ Comparable sales for real estate
   □ Qualified appraisals for art, collectibles
   □ Blockage discounts for large securities holdings
   □ Conservation easements — before/after methodology

9. PENALTIES (§6662)
   □ Substantial valuation misstatement (150% of correct value): 20% penalty
   □ Gross valuation misstatement (200% of correct value): 40% penalty
   □ Appraiser penalty for gross overvaluation (§6695A)

10. AUDIT ISSUES
    - CWA not obtained before return filed
    - Appraisal does not meet requirements
    - Form 8283 incomplete or unsigned
    - FMV unsupportable or inflated
    - Quid pro quo not properly disclosed""",
        key_factors=[
            "Contemporaneous written acknowledgment obtained",
            "Qualified appraisal for non-cash over $5,000",
            "Form 8283 properly completed and signed",
            "Fair market value supportable with evidence",
            "Donee signature obtained on Form 8283 Section B"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §170", "relevance": "Charitable contribution rules"},
            {"authority": "IRC", "reference": "IRC §170(f)(8)", "relevance": "CWA requirements"},
            {"authority": "Reg", "reference": "Reg. §1.170A-13", "relevance": "Substantiation requirements"},
            {"authority": "Reg", "reference": "Reg. §1.170A-17", "relevance": "Qualified appraiser"},
            {"authority": "IRC", "reference": "IRC §6662(h)", "relevance": "Gross valuation misstatement"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS disallows charitable deductions when: (1) CWA not
obtained by return due date; (2) appraisal does not meet all requirements; (3) Form 8283
incomplete, missing signatures, or donee acknowledgment absent; (4) claimed FMV grossly
exceeds supportable value; (5) conservation easement valuations inflated.""",
        counter_arguments=[
            "CWA obtained before return due date (document date received)",
            "Appraisal meets all regulatory requirements",
            "Form 8283 complete with appraiser and donee signatures",
            "FMV supported by comparable sales or established methodology",
            "Appraiser qualifications documented"
        ],
        appeals_strategy="""Substantiation failures are often fatal — no deduction if CWA
requirements not met. Check date CWA obtained vs. return filed. Appraisal defects
may be technical or substantive; technical defects sometimes excused under reasonable
cause. FMV challenges require comparable evidence. Conservation easement cases are
high-scrutiny — be prepared for valuation experts.""",
        entity_scope=["individual", "c_corporation", "s_corporation", "partnership", "trust"],
        confidence="high"
    ),

    "worker_classification": DoctrineBlock(
        topic="Worker Classification - Employee vs. Independent Contractor",
        keywords=["employee", "independent contractor", "worker classification", "1099",
                  "W-2", "misclassification", "common law test", "employment tax",
                  "SS-8", "Section 530", "gig worker"],
        conclusion_template="""Worker classification as employee vs. independent contractor
is determined under common law factors focusing on the degree of control the payer
exercises. The IRS groups factors into behavioral control, financial control, and
relationship type. Misclassification triggers employment tax liability, penalties, and
potential criminal exposure. Section 530 provides relief if reasonable basis existed
for treatment as independent contractor.""",
        reasoning_framework="""
WORKER CLASSIFICATION — ANALYSIS FRAMEWORK:

1. WHY IT MATTERS
   Classification affects:
   □ Employment taxes (FICA, FUTA, withholding)
   □ Worker benefits eligibility
   □ Unemployment insurance
   □ Workers' compensation
   □ Deduction characterization (above/below line)
   □ Employer liability for actions

2. THE COMMON LAW TEST
   IRS evaluates degree of CONTROL using three categories:

   A. BEHAVIORAL CONTROL
   Does the payer control HOW work is done?
   □ Instructions given (when, where, how, tools used)
   □ Training provided
   □ Work sequence directed
   □ Supervision level

   More control = MORE LIKELY EMPLOYEE

   B. FINANCIAL CONTROL
   Does the payer control BUSINESS aspects?
   □ Investment in equipment/facilities
   □ Unreimbursed expenses
   □ Services available to general public
   □ Method of payment (hourly vs. flat fee)
   □ Profit/loss opportunity

   More business independence = MORE LIKELY CONTRACTOR

   C. TYPE OF RELATIONSHIP
   What is the nature of the relationship?
   □ Written contract terms
   □ Benefits provided (insurance, pension, vacation)
   □ Permanency of relationship
   □ Key activity of the business

3. NO SINGLE FACTOR CONTROLS
   Courts weigh totality of circumstances
   Different factors may point different directions
   Overall evaluation determines classification

4. SECTION 530 SAFE HARBOR (Revenue Act of 1978)
   Employer NOT liable for employment taxes IF:
   □ Reasonable basis for treating worker as contractor
   □ Consistent treatment of similar workers
   □ Timely Form 1099 filing

   REASONABLE BASIS:
   □ Judicial precedent, published ruling, or TAM
   □ Prior IRS audit with no reclassification
   □ Long-standing industry practice
   □ Other reasonable basis

5. SS-8 DETERMINATION
   Either party can request IRS determination via Form SS-8
   IRS analyzes facts, issues determination letter
   Not binding on courts, but IRS will follow

6. CONSEQUENCES OF MISCLASSIFICATION

   TO EMPLOYER:
   □ Back employment taxes (employer AND employee share)
   □ Failure to file penalties
   □ Failure to pay penalties
   □ Accuracy-related penalties
   □ Potential fraud penalties
   □ Interest on all of above

   MITIGATION: Voluntary Classification Settlement Program (VCSP)
   □ Pay 10% of employment tax liability for most recent year
   □ No penalties, no interest, no prior year audit
   □ Prospective reclassification required

7. RED FLAGS FOR MISCLASSIFICATION
   - Same worker, full-time, for years
   - Worker performs core business function
   - Worker uses company email/business cards
   - Worker has set schedule
   - Worker supervised like other employees
   - No contract or contract ignores reality

8. INDUSTRY-SPECIFIC CONSIDERATIONS
   - Construction: Often contractors, but control matters
   - Tech/IT: Evaluate project vs. ongoing work
   - Healthcare: Credentialing may suggest employee
   - Transportation: Gig economy issues
   - Entertainment: Long-standing contractor practices""",
        key_factors=[
            "Degree of behavioral control analyzed",
            "Financial control factors evaluated",
            "Relationship type considered",
            "Industry practice documented",
            "Section 530 reasonable basis available"
        ],
        primary_authority=[
            {"authority": "Common Law", "reference": "Rev. Rul. 87-41", "relevance": "20-factor test"},
            {"authority": "IRC", "reference": "IRC §3401, §3121", "relevance": "Employee definitions"},
            {"authority": "Statute", "reference": "Section 530, Revenue Act of 1978", "relevance": "Safe harbor"},
            {"authority": "Case", "reference": "Nationwide Mut. Ins. Co. v. Darden, 503 U.S. 318 (1992)", "relevance": "Common law test"},
            {"authority": "IRS", "reference": "Form SS-8", "relevance": "Classification determination"}
        ],
        burden_holder="IRS must show employee status; employer must show Section 530 relief",
        irs_typical_position="""The IRS asserts employee status when: (1) payer controls
manner and means of work; (2) worker integrated into business operations; (3) worker
has no entrepreneurial opportunity; (4) relationship is permanent or indefinite;
(5) 1099 treatment is form over substance.""",
        counter_arguments=[
            "Worker controls manner and means of work performance",
            "Worker has significant investment in equipment/facilities",
            "Worker markets services to general public",
            "Worker has opportunity for profit or loss",
            "Section 530 reasonable basis exists (industry practice, prior audit)"
        ],
        appeals_strategy="""Classification cases are highly factual. Document all factors
pointing to contractor status. Prepare detailed analysis of each factor. If misclassification
occurred, consider VCSP before IRS initiates audit. Section 530 requires consistent
treatment of similar workers — document who else is treated as 1099. Industry practice
is powerful; obtain industry publications or expert testimony.""",
        entity_scope=["sole_proprietorship", "c_corporation", "s_corporation", "partnership", "llc"],
        confidence="high"
    ),

    "wash_sale_1091": DoctrineBlock(
        topic="Wash Sale Rules - §1091 Loss Disallowance",
        keywords=["wash sale", "1091", "wash sale rule", "substantially identical",
                  "30 days", "loss disallowance", "securities", "stock loss",
                  "replacement shares", "basis adjustment"],
        conclusion_template="""Under §1091, a loss on sale of stock or securities is disallowed
if the taxpayer acquires substantially identical stock within 30 days before or after the
sale. The disallowed loss is added to the basis of the replacement shares, effectively
deferring (not eliminating) the loss. Applies to stock, securities, and options. Does not
apply to gains. Holding period of sold shares tacks to replacement shares.""",
        reasoning_framework="""
WASH SALE RULES — §1091 ANALYSIS:

1. BASIC RULE (§1091(a))
   Loss on sale of stock or securities is NOT DEDUCTIBLE if:
   □ Within 30 days BEFORE the sale, OR
   □ Within 30 days AFTER the sale
   □ Taxpayer acquires SUBSTANTIALLY IDENTICAL stock/securities
   □ OR enters into contract/option to acquire

   61-DAY WINDOW: 30 days before + sale day + 30 days after

2. "SUBSTANTIALLY IDENTICAL" STANDARD
   Same stock = definitely substantially identical

   NOT SUBSTANTIALLY IDENTICAL:
   □ Different companies in same industry
   □ Preferred stock for common (usually)
   □ Bond from same issuer with different terms
   □ Mutual fund for ETF tracking same index (gray area)

   SUBSTANTIALLY IDENTICAL:
   □ Same stock, same issuer
   □ Options to acquire same stock
   □ Convertible bonds for stock of same issuer
   □ Contracts to acquire same stock

3. EFFECT OF WASH SALE
   Loss is NOT LOST — only deferred:

   □ Disallowed loss added to basis of replacement shares
   □ Holding period of original shares tacks to replacement
   □ Loss recognized when replacement shares sold (if no new wash sale)

   Example:
   - Buy 100 shares at $50 (basis = $5,000)
   - Sell for $30 (realized loss = $2,000) — DISALLOWED
   - Buy 100 shares at $32 within 30 days
   - New basis = $32 + $20 = $52/share ($5,200 total)
   - When new shares sold, loss recognized (if no wash sale)

4. ACQUISITION METHODS THAT TRIGGER
   □ Direct purchase
   □ Dividend reinvestment plan (DRIP)
   □ Option exercise
   □ Short sale cover
   □ Contribution to IRA (acquiring in IRA)
   □ Gift of appreciated stock within 30 days

5. WHAT DOES NOT TRIGGER WASH SALE
   □ Sale at a GAIN (wash sale only applies to losses)
   □ Acquisition by unrelated party
   □ Different securities (not substantially identical)
   □ Acquisition more than 30 days before/after

6. RELATED PARTY ISSUES
   IRS may apply wash sale when:
   □ Spouse acquires substantially identical stock
   □ Controlled entity acquires stock
   □ IRA or Roth IRA acquires stock (loss permanently disallowed)

   WARNING: If sold at loss and IRA buys replacement,
   loss may be PERMANENTLY LOST (not added to IRA basis)

7. OPTIONS AND SHORT SALES
   ACQUIRING OPTIONS counts as acquisition
   WRITING OPTIONS may trigger if in-the-money and exercised
   SHORT SALES — covering short with replacement stock can trigger

8. PRACTICAL ISSUES
   Broker Form 1099-B may not properly adjust:
   □ Different brokers don't communicate
   □ Taxpayer must track and adjust manually
   □ Wash sale adjustments reported on Form 8949

9. PLANNING STRATEGIES
   - Wait 31 days before repurchasing
   - Purchase different (not substantially identical) security
   - Double-up strategy: Buy replacement, wait 31 days, sell original
   - Year-end tax-loss harvesting requires careful timing""",
        key_factors=[
            "Sale occurred at a loss",
            "Substantially identical stock acquired within 61-day window",
            "Replacement share basis adjusted for disallowed loss",
            "Holding period properly tacked",
            "Form 8949 correctly reports wash sale adjustment"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §1091", "relevance": "Wash sale rules"},
            {"authority": "Reg", "reference": "Reg. §1.1091-1", "relevance": "Implementation rules"},
            {"authority": "Reg", "reference": "Reg. §1.1091-2", "relevance": "Short sales"},
            {"authority": "Case", "reference": "McDonald v. Commissioner, 76 T.C. 972 (1981)", "relevance": "IRA wash sale"}
        ],
        burden_holder="IRS for asserting wash sale; taxpayer for basis adjustment",
        irs_typical_position="""The IRS disallows wash sale losses when: (1) acquisition of
substantially identical stock within 61-day window; (2) taxpayer fails to adjust basis
of replacement shares; (3) DRIP acquisitions not considered; (4) related party or IRA
acquisitions ignored; (5) year-end tax-loss harvesting violated rules.""",
        counter_arguments=[
            "Securities acquired were not substantially identical",
            "Acquisition occurred outside 61-day window",
            "Basis of replacement shares properly adjusted",
            "Form 8949 correctly reflects wash sale treatment",
            "No related party or IRA acquisition occurred"
        ],
        appeals_strategy="""Wash sale rules are mechanical. Focus on whether securities
are "substantially identical" — different class, issuer, or terms may avoid rule.
If wash sale applies, ensure basis adjustment properly computed and documented.
For IRA wash sales, loss may be permanently lost — not added to IRA basis. Consider
timing of year-end transactions carefully. Brokers may miss cross-broker wash sales.""",
        entity_scope=["individual", "trust", "estate"],
        confidence="high"
    ),

    "net_operating_loss_172": DoctrineBlock(
        topic="Net Operating Losses - §172 Carryback and Carryforward (Post-TCJA)",
        keywords=["net operating loss", "172", "NOL", "loss carryback", "loss carryforward",
                  "TCJA NOL", "80% limitation", "farming loss", "NOL deduction"],
        conclusion_template="""Post-TCJA, NOLs arising after 2017 can only be carried forward
(no carryback) and are limited to 80% of taxable income. Pre-2018 NOLs retain 20-year
carryforward with no percentage limitation. Exceptions exist for farming losses (2-year
carryback) and certain insurance company losses. CARES Act provided temporary relief for
2018-2020 NOLs. Tracking vintage years is critical for applying correct rules.""",
        reasoning_framework="""
NET OPERATING LOSS — §172 ANALYSIS (POST-TCJA):

1. FUNDAMENTAL RULES — BY VINTAGE

   PRE-2018 NOLs (Taxable years ending before 2018):
   □ 2-year carryback (general rule)
   □ 20-year carryforward
   □ NO percentage limitation (can offset 100% of taxable income)

   POST-2017 NOLs (Taxable years beginning after 2017):
   □ NO carryback (general rule)
   □ Indefinite carryforward
   □ 80% LIMITATION — Can only offset 80% of taxable income

2. CARES ACT TEMPORARY RELIEF (2018, 2019, 2020 NOLs)
   Special rules for NOLs from tax years 2018-2020:
   □ 5-year carryback allowed
   □ 80% limitation temporarily suspended
   □ Election to waive carryback

   NOTE: This relief has expired for NOLs after 2020

3. ORDERING RULES
   When multiple NOL vintages exist:
   □ Use oldest NOLs first (FIFO)
   □ Pre-2018 NOLs offset income first (no 80% limit)
   □ Post-2017 NOLs applied after (80% limit applies)

4. 80% LIMITATION — HOW IT WORKS (§172(a)(2))
   Post-2017 NOL deduction = LESSER OF:
   □ Available post-2017 NOL carryforward, OR
   □ 80% of taxable income (computed without §199A deduction)

   Example:
   - Taxable income (before NOL): $100,000
   - Available post-2020 NOL: $150,000
   - NOL deduction allowed: $80,000 (80% × $100,000)
   - Remaining NOL carryforward: $70,000

5. FARMING LOSSES (§172(b)(1)(B))
   Special carryback for farming NOLs:
   □ 2-year carryback allowed
   □ "Farming loss" = NOL attributable to farming business
   □ Computed separately from other NOL components
   □ Election to waive carryback available

6. COMPUTING THE NOL (§172(c)-(d))
   NOL = Negative taxable income WITH modifications:

   MODIFICATIONS:
   □ No NOL deduction from other years
   □ No §199A deduction
   □ No capital loss in excess of capital gains (individuals)
   □ Nonbusiness deductions limited to nonbusiness income

7. CORPORATE vs. INDIVIDUAL DIFFERENCES
   CORPORATIONS:
   □ Same general rules apply
   □ No capital loss limitation in NOL computation
   □ DRD computed before NOL

   PASS-THROUGH ENTITIES:
   □ NOL computed at partner/shareholder level
   □ Each owner applies their own NOL rules
   □ Partnership/S-Corp loss may create owner-level NOL

8. ELECTIONS
   □ Election to waive carryback (irrevocable once made)
   □ Must be made by return due date (with extensions)
   □ Election made on timely filed return for NOL year

9. CARRYBACK PROCEDURES
   □ File Form 1045 (quick refund) within 12 months
   □ OR file amended return (Form 1040-X or 1120-X)
   □ Carryback refund claims subject to examination

10. AUDIT ISSUES
    - Wrong vintage rules applied
    - 80% limitation not computed correctly
    - Pre-2018 and post-2017 NOLs not tracked separately
    - Farming loss carryback improperly claimed
    - NOL computation modifications incorrect""",
        key_factors=[
            "NOL vintage year correctly identified",
            "80% limitation properly applied to post-2017 NOLs",
            "Ordering rules followed (oldest NOL first)",
            "Farming loss separately computed if applicable",
            "NOL computation modifications correctly applied"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §172", "relevance": "NOL deduction rules"},
            {"authority": "IRC", "reference": "IRC §172(a)(2)", "relevance": "80% limitation"},
            {"authority": "IRC", "reference": "IRC §172(b)(1)(B)", "relevance": "Farming loss carryback"},
            {"authority": "Statute", "reference": "CARES Act §2303", "relevance": "Temporary 5-year carryback"},
            {"authority": "Reg", "reference": "Reg. §1.172-1", "relevance": "NOL computation"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges NOL deductions when: (1) 80% limitation
not applied to post-2017 NOLs; (2) NOL computation includes improper deductions;
(3) carryback claims lack substantiation; (4) vintage tracking is inadequate;
(5) farming loss exception improperly applied.""",
        counter_arguments=[
            "NOL vintage properly documented",
            "80% limitation correctly computed",
            "NOL computation modifications properly applied",
            "Carryforward schedule maintained by year",
            "Farming loss separately identified and substantiated"
        ],
        appeals_strategy="""NOL issues are often computational. Maintain detailed schedules
showing NOL by vintage year. Document 80% limitation calculation each year. For farming
losses, segregate farming and non-farming components. If CARES Act carryback was claimed,
ensure 2018-2020 year and proper procedures followed. Watch for interaction with §199A
deduction in computing limitation.""",
        entity_scope=["individual", "c_corporation", "trust", "estate"],
        confidence="high"
    ),

    "excess_business_loss_461l": DoctrineBlock(
        topic="Excess Business Loss Limitation - §461(l) TCJA Rules",
        keywords=["excess business loss", "461l", "EBL", "business loss limitation",
                  "threshold amount", "aggregated business income", "TCJA loss",
                  "noncorporate taxpayer"],
        conclusion_template="""Under §461(l), noncorporate taxpayers cannot deduct aggregate
business losses exceeding $305,000 (single) or $610,000 (MFJ) for 2024 (indexed annually).
The excess becomes a net operating loss carried forward. This limitation applies AFTER
at-risk and passive activity rules. All trades or businesses are aggregated. W-2 wages
may be included as business income. Extended through 2028 by the Inflation Reduction Act.""",
        reasoning_framework="""
EXCESS BUSINESS LOSS — §461(l) ANALYSIS:

1. FUNDAMENTAL RULE (§461(l)(1))
   Noncorporate taxpayers may NOT deduct excess business losses

   EXCESS BUSINESS LOSS = Aggregate deductions from trades/businesses
   EXCEEDING aggregate gross income/gain from trades/businesses
   PLUS threshold amount

   THRESHOLD AMOUNTS (2024, indexed):
   □ Single/HOH: $305,000
   □ Married Filing Jointly: $610,000
   □ Married Filing Separately: $305,000 (half of MFJ)

2. WHO IS AFFECTED?
   NONCORPORATE TAXPAYERS:
   □ Individuals
   □ Trusts
   □ Estates
   □ Partners (share of partnership loss)
   □ S-Corp shareholders (share of S-Corp loss)

   NOT AFFECTED:
   □ C Corporations
   □ Insurance companies

3. COMPUTATION STEPS

   STEP 1: Aggregate all trades/businesses
   □ Include all Schedule C, E, F income/loss
   □ Include pass-through income/loss (K-1s)
   □ Include §1231 gains/losses from business property
   □ Include W-2 wages as business income

   STEP 2: Compute net aggregate amount
   □ Total business income - Total business deductions
   □ If positive, no limitation applies
   □ If negative, proceed to Step 3

   STEP 3: Apply threshold
   □ If net loss ≤ threshold amount, fully deductible
   □ If net loss > threshold, excess is limited

   STEP 4: Disallowed amount becomes NOL
   □ Excess business loss treated as NOL carried forward
   □ Subject to 80% limitation (post-2017 NOL rules)

4. ORDERING RULES — CRITICAL SEQUENCE
   Apply limitations in this order:
   1. §704(d) — Partnership basis limitation
   2. §1366(d) — S-Corp basis limitation
   3. §465 — At-risk limitation
   4. §469 — Passive activity limitation
   5. §461(l) — EXCESS BUSINESS LOSS (this rule) — LAST

   Loss surviving all prior limitations may still be limited here

5. WHAT IS "TRADE OR BUSINESS"?
   Same as §162 trade or business definition:
   □ Regular and continuous activity
   □ Primary purpose is income or profit
   □ Employee wages = trade or business of being employee

   INCLUDES:
   □ Schedule C activities
   □ Partnership/S-Corp pass-through
   □ Farming operations
   □ W-2 wages

   EXCLUDES:
   □ Investment activities (portfolio income/loss)
   □ Rental activities that are not a trade/business

6. W-2 WAGES AS BUSINESS INCOME
   W-2 wages from employment included as business gross income
   □ Reduces excess business loss
   □ May offset business losses

7. CAPITAL GAINS/LOSSES
   §1231 gains/losses included if from business property
   Capital gains from investments NOT included
   Short-term capital gains from business may be included

8. DURATION
   Originally 2018-2025 (TCJA)
   Extended through 2028 (Inflation Reduction Act 2022)

9. AUDIT ISSUES
   - §461(l) limitation not computed
   - W-2 wages not included as business income
   - Threshold amount used incorrectly
   - Ordering rules not followed
   - Disallowed loss not carried as NOL""",
        key_factors=[
            "All trades or businesses aggregated",
            "W-2 wages included as business income",
            "Threshold amount applied (indexed annually)",
            "Ordering rules followed (§461(l) applied last)",
            "Excess treated as NOL carryforward"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §461(l)", "relevance": "Excess business loss rules"},
            {"authority": "IRS", "reference": "Notice 2018-61", "relevance": "Implementation guidance"},
            {"authority": "Statute", "reference": "Inflation Reduction Act §13903", "relevance": "Extension through 2028"},
            {"authority": "IRC", "reference": "IRC §172", "relevance": "Carryforward as NOL"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS asserts §461(l) limitation when: (1) noncorporate
taxpayer claims business losses exceeding threshold; (2) W-2 wages not included
in business income computation; (3) ordering rules not followed (passive loss
taken before §461(l) applied); (4) disallowed amount not treated as NOL carryforward.""",
        counter_arguments=[
            "All business income and loss properly aggregated",
            "W-2 wages correctly included",
            "Threshold amount correctly applied for filing status",
            "Ordering rules followed in correct sequence",
            "Disallowed loss properly converted to NOL"
        ],
        appeals_strategy="""§461(l) is computational. Document aggregation of all business
activities. Include W-2 wages to reduce excess loss. Apply limitation AFTER passive
activity rules. Threshold amount is indexed — use correct year's amount. Disallowed
loss becomes NOL subject to 80% limitation going forward. Consider whether loss is
from trade or business vs. investment activity.""",
        entity_scope=["individual", "trust", "estate", "partnership", "s_corporation"],
        confidence="high"
    ),

    "economic_substance_7701o": DoctrineBlock(
        topic="Economic Substance Doctrine - §7701(o) Codification",
        keywords=["economic substance", "7701o", "business purpose", "sham transaction",
                  "tax avoidance", "substance over form", "step transaction",
                  "reasonable possibility of profit", "nontax business purpose"],
        conclusion_template="""The economic substance doctrine, codified at §7701(o), requires
transactions to have meaningful change in economic position (apart from tax) AND a
substantial purpose (apart from tax) to be respected for tax purposes. Failure results
in disallowance of tax benefits plus a strict liability 20% penalty (40% if not disclosed).
The doctrine applies to transactions where economic substance is relevant; profit potential
must be reasonable and substantial relative to claimed tax benefits.""",
        reasoning_framework="""
ECONOMIC SUBSTANCE DOCTRINE — §7701(o) ANALYSIS:

1. CODIFICATION (§7701(o))
   Effective for transactions entered into after March 30, 2010

   Transaction treated as having economic substance ONLY IF:
   □ The transaction changes taxpayer's economic position
     in a meaningful way (apart from tax effects), AND
   □ The taxpayer has a substantial purpose (apart from tax effects)

   CONJUNCTIVE TEST: Both prongs must be satisfied

2. PRONG 1 — MEANINGFUL CHANGE IN ECONOMIC POSITION
   "Meaningful" = More than nominal
   "Economic position" = Wealth, assets, obligations

   EVALUATE:
   □ Real economic profit potential (apart from tax)
   □ Risk undertaken
   □ Business activity conducted
   □ Change in balance sheet position

   NOT MEANINGFUL:
   □ Circular cash flows returning to original position
   □ Offsetting positions eliminating risk
   □ Fees only equal to tax benefit generated

3. PRONG 2 — SUBSTANTIAL NON-TAX PURPOSE
   "Substantial" = Real, not just incidental
   Purpose that would exist even without tax benefit

   EXAMPLES OF NON-TAX PURPOSES:
   □ Risk hedging
   □ Business expansion
   □ Financing needs
   □ Succession planning
   □ Asset protection (if legitimate)

   NOT SUBSTANTIAL:
   □ Purpose is primarily to obtain tax benefit
   □ Business purpose is illusory or contrived
   □ Purpose would not exist but for tax benefit

4. PROFIT POTENTIAL ANALYSIS (§7701(o)(2)(A))
   Potential for profit evaluated:
   □ Present value of reasonably expected pre-tax profit
   □ Must be substantial relative to present value of tax benefits
   □ Fees and transaction costs considered

   IRS looks at:
   □ Financial projections at time of transaction
   □ Reasonable expectations based on known facts
   □ Comparison to tax benefit claimed

5. STATE OF MIND IRRELEVANT (§7701(o)(1) flush language)
   "Determination shall be made without regard to whether
   the taxpayer entered into the transaction under advice of counsel"

   Reliance on advisor opinion does NOT establish economic substance
   BUT may be relevant for reasonable cause defense

6. PENALTIES — STRICT LIABILITY (§6662(b)(6))
   If transaction lacks economic substance:

   □ 20% penalty on underpayment — STRICT LIABILITY
   □ 40% penalty if NOT ADEQUATELY DISCLOSED
   □ No reasonable cause defense for economic substance penalty
   □ Gross valuation misstatement rules apply

7. TRANSACTIONS WHERE DOCTRINE APPLIES
   Only where "economic substance is relevant to transaction"
   Not applied to:
   □ Choice of entity
   □ Choice of accounting method
   □ Choice between debt and equity
   □ Other Congressional elections

8. RELATED DOCTRINES
   □ STEP TRANSACTION: Collapse multiple steps into single transaction
   □ SUBSTANCE OVER FORM: True nature controls
   □ SHAM TRANSACTION: Transaction with no purpose but tax benefit
   □ BUSINESS PURPOSE: Gregory v. Helvering line of cases

9. RED FLAGS FOR SCRUTINY
   - Tax shelter with marketed "losses"
   - Circular cash flows
   - High fees relative to profit potential
   - Short holding periods
   - Contrived arrangements lacking commercial reality

10. AUDIT ISSUES
    - Transaction generates large losses or deductions
    - No realistic profit potential
    - Arrangement would not exist but for tax benefit
    - Promoted arrangement with multiple participants
    - No business records supporting non-tax purpose""",
        key_factors=[
            "Meaningful change in economic position (apart from tax)",
            "Substantial non-tax business purpose",
            "Pre-tax profit potential reasonable relative to tax benefit",
            "Transaction has commercial reality",
            "Not a promoted tax shelter"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §7701(o)", "relevance": "Economic substance codification"},
            {"authority": "IRC", "reference": "IRC §6662(b)(6)", "relevance": "Strict liability penalty"},
            {"authority": "Case", "reference": "Coltec Indus., Inc. v. United States, 454 F.3d 1340 (Fed. Cir. 2006)", "relevance": "Pre-codification standard"},
            {"authority": "Case", "reference": "ACM Partnership v. Commissioner, 157 F.3d 231 (3d Cir. 1998)", "relevance": "Pre-tax profit test"}
        ],
        burden_holder="taxpayer (to establish both prongs)",
        irs_typical_position="""The IRS invokes economic substance doctrine when: (1) transaction
generates tax benefits disproportionate to economic risk or profit; (2) cash flows are
circular with no meaningful change in position; (3) transaction is promoted tax shelter;
(4) no non-tax purpose would motivate the transaction; (5) fees or promoter commissions
suggest tax benefit is the product.""",
        counter_arguments=[
            "Transaction was motivated by legitimate business purpose",
            "Meaningful economic profit potential exists and is documented",
            "Economic position meaningfully changed by transaction",
            "Transaction was not promoted or marketed",
            "Commercial reality supports business treatment"
        ],
        appeals_strategy="""Economic substance challenges are serious — 40% penalty if
undisclosed. Document non-tax business purposes BEFORE transaction. Prepare financial
projections showing reasonable profit potential. Avoid circular cash flows. If challenged,
focus on what taxpayer knew and expected at time of transaction. Penalty is strict liability
— reasonable cause defense unavailable for this specific penalty.""",
        entity_scope=["individual", "c_corporation", "s_corporation", "partnership", "trust"],
        confidence="high"
    ),

    "conservation_easement_syndicated": DoctrineBlock(
        topic="Conservation Easements - Syndicated Transaction Scrutiny",
        keywords=["conservation easement", "syndicated easement", "listed transaction",
                  "qualified appraisal", "valuation", "2.5 to 1", "partnership easement",
                  "facade easement", "land preservation"],
        conclusion_template="""Syndicated conservation easements are listed transactions if
the deduction claimed exceeds 2.5× the investor's basis. The IRS is aggressively challenging
these transactions, asserting valuation overstatement, failure to meet qualified appraisal
requirements, and economic substance violations. Penalties are severe: 40% gross valuation
misstatement or 40% undisclosed economic substance. Many courts have sustained IRS
disallowance. Post-TCJA deduction is limited to 50% of AGI (15% for carryforward).""",
        reasoning_framework="""
SYNDICATED CONSERVATION EASEMENTS — RISK ANALYSIS:

1. WHAT IS A SYNDICATED CONSERVATION EASEMENT?
   □ Partnership formed to own land
   □ Investors acquire partnership interests
   □ Partnership donates conservation easement
   □ Investors claim pass-through charitable deduction
   □ Deduction exceeds 2.5× cash invested

2. LISTED TRANSACTION (Notice 2017-10)
   Syndicated conservation easement is LISTED TRANSACTION if:
   □ Investor receives pass-through deduction
   □ Exceeding 2.5× of investor's basis in partnership
   □ Within 2.5 years of becoming partner

   CONSEQUENCES:
   □ Must disclose on Form 8886
   □ Penalties for non-disclosure
   □ 6-year statute of limitations
   □ Material advisor reporting required

3. IRS SCRUTINY AREAS

   A. QUALIFIED APPRAISAL DEFECTS
   □ Appraiser not independent
   □ Appraisal methodology flawed
   □ "Before and after" analysis not supportable
   □ Comparable sales not truly comparable
   □ Enhancement value overstated

   B. VALUATION OVERSTATEMENT
   □ Claimed FMV grossly exceeds supportable value
   □ Before value inflated
   □ Highest and best use analysis wrong
   □ Conservation restriction understated

   C. ECONOMIC SUBSTANCE
   □ No meaningful change in position (land still held)
   □ No non-tax purpose for transaction
   □ Transaction would not occur but for tax benefits

   D. PERPETUITY REQUIREMENTS
   □ Easement not properly drafted
   □ Reserved rights too extensive
   □ Extinguishment provisions improper

4. PENALTIES

   IF DISALLOWED:
   □ 20% substantial valuation misstatement (150% of correct)
   □ 40% gross valuation misstatement (200% of correct)
   □ 40% undisclosed economic substance transaction
   □ Fraud penalty possible for promoters/appraisers

5. COURT DECISIONS — LARGELY UNFAVORABLE
   Tax Court has consistently sustained IRS:
   □ Overvaluation findings
   □ Economic substance failures
   □ Appraisal deficiencies
   □ Perpetuity requirement violations

   Cases: Bosque Canyon, Pine Mountain, Plateau Holdings,
   Champions Retreat, Glade Creek

6. LEGITIMATE CONSERVATION EASEMENTS
   Not all easements are problematic:
   □ Landowner donates easement on family land
   □ No syndication or partnership structure
   □ FMV supportable by independent appraisal
   □ Legitimate conservation purpose
   □ Deduction proportionate to actual value reduction

7. §170(h) REQUIREMENTS — ALL MUST BE MET
   □ Qualified organization (land trust, government)
   □ Conservation purpose (scenic, habitat, historic, recreation)
   □ Exclusively for conservation purpose
   □ Protected in perpetuity
   □ Proper subordination of mortgages
   □ Proceeds allocation on extinguishment

8. DEFENSIVE CONSIDERATIONS
   IF CLIENT HAS SYNDICATED EASEMENT:
   □ Review for listed transaction disclosure
   □ Evaluate statute of limitations
   □ Consider Voluntary Disclosure Practice
   □ Assess exposure and reserves
   □ Document any non-tax purpose

9. CURRENT STATUS
   □ IRS continues aggressive enforcement
   □ Legislation pending to further restrict
   □ Most courts sustaining IRS
   □ Extremely high audit risk""",
        key_factors=[
            "Deduction exceeds 2.5× investor basis (listed transaction)",
            "Appraisal meets qualified appraisal requirements",
            "Valuation methodology supportable",
            "§170(h) conservation purpose satisfied",
            "Perpetuity requirements met"
        ],
        primary_authority=[
            {"authority": "IRS", "reference": "Notice 2017-10", "relevance": "Listed transaction designation"},
            {"authority": "IRC", "reference": "IRC §170(h)", "relevance": "Conservation contribution requirements"},
            {"authority": "Case", "reference": "Bosque Canyon Ranch v. Commissioner, T.C. Memo 2021-88", "relevance": "Syndicated easement disallowed"},
            {"authority": "Case", "reference": "Champions Retreat Golf Founders v. Commissioner, T.C. Memo 2022-106", "relevance": "Valuation overstatement"},
            {"authority": "IRC", "reference": "IRC §6662(h)", "relevance": "Gross valuation misstatement penalty"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS disallows syndicated conservation easements when:
(1) deduction exceeds 2.5× investor basis (listed transaction); (2) valuation is grossly
overstated; (3) appraisal defects exist; (4) no economic substance apart from tax benefits;
(5) perpetuity or conservation purpose requirements not met.""",
        counter_arguments=[
            "Property legitimately has exceptional conservation value",
            "Appraisal methodology is sound and supportable",
            "Before and after values properly analyzed",
            "Conservation purpose is genuine and documented",
            "Easement drafted to meet §170(h) requirements"
        ],
        appeals_strategy="""Syndicated easement cases are extremely difficult to win.
Tax Court has sustained IRS in most cases. If client has such a position, consider:
(1) Voluntary Disclosure if not yet audited; (2) Concession with penalty abatement
request; (3) Valuation defense only if appraiser will testify and values supportable.
Penalties are severe — 40% is common. Assess promoter information reporting obligations.
Statute is extended to 6 years for listed transactions.""",
        entity_scope=["individual", "partnership", "trust"],
        confidence="high"
    ),

    "stock_compensation_iso_nso": DoctrineBlock(
        topic="Stock Compensation - ISO vs. NSO and §83(b) Elections",
        keywords=["stock options", "ISO", "NSO", "incentive stock option", "nonqualified option",
                  "83b election", "stock compensation", "exercise", "AMT adjustment",
                  "disqualifying disposition", "bargain element"],
        conclusion_template="""ISOs under §422 receive favorable tax treatment if holding period
requirements are met: no regular tax on exercise, capital gains on sale. NSOs are taxed
as ordinary income on exercise equal to the bargain element. §83(b) elections allow
taxation at grant rather than vesting for restricted stock, freezing ordinary income
at grant-date value. AMT preference applies to ISOs on exercise. Disqualifying dispositions
convert ISO treatment to ordinary income.""",
        reasoning_framework="""
STOCK COMPENSATION — ISO, NSO, §83(b) ANALYSIS:

1. NONQUALIFIED STOCK OPTIONS (NSO)

   AT GRANT:
   □ No income if option has no readily ascertainable FMV
   □ Most employee options have no ascertainable FMV at grant

   AT EXERCISE:
   □ ORDINARY INCOME = FMV of stock - Exercise price
   □ This is "bargain element" or "spread"
   □ Subject to withholding (FICA and income tax)
   □ Employer deduction equals employee income

   AT SALE:
   □ Basis = FMV at exercise
   □ Gain/loss = Sale price - Basis
   □ Short-term or long-term based on holding from exercise

2. INCENTIVE STOCK OPTIONS (ISO) — §422

   REQUIREMENTS (§422(b)):
   □ Granted under written plan approved by shareholders
   □ Exercise price ≥ FMV at grant
   □ 10-year maximum term
   □ Employee only (and within 3 months of termination)
   □ $100,000 annual limit on options becoming exercisable

   AT GRANT:
   □ No income

   AT EXERCISE:
   □ NO REGULAR TAX income
   □ BUT: Bargain element is AMT preference item
   □ May trigger AMT liability

   AT SALE (QUALIFYING DISPOSITION):
   □ Must hold 2+ years from grant AND 1+ year from exercise
   □ Entire gain = LONG-TERM CAPITAL GAIN
   □ No employer deduction

   DISQUALIFYING DISPOSITION:
   If sold before holding periods met:
   □ Bargain element at exercise = ORDINARY INCOME
   □ Remainder of gain = Capital gain
   □ Employer gets corresponding deduction

3. SECTION 83(b) ELECTIONS — RESTRICTED STOCK

   §83 GENERAL RULE:
   Property transferred in connection with services taxed when:
   □ Property is transferable, OR
   □ No longer subject to substantial risk of forfeiture

   §83(b) ELECTION:
   Elect to include in income at GRANT (not vesting):
   □ Include FMV at grant minus amount paid
   □ Lock in ordinary income at lower value (if stock appreciates)
   □ Future appreciation = Capital gain

   REQUIREMENTS:
   □ File with IRS within 30 DAYS of transfer
   □ Copy to employer
   □ Attach to tax return

   RISK: If stock forfeited after election, NO DEDUCTION

4. TIMING AND FILING

   §83(b) ELECTION:
   □ 30 days from transfer — ABSOLUTE DEADLINE
   □ No extensions, no excuses
   □ File with IRS service center where return filed
   □ Include copy with tax return

5. AMT CONSIDERATIONS FOR ISOs

   At exercise:
   □ Bargain element is AMT preference
   □ May create AMT liability
   □ AMT credit may carry forward

   Planning:
   □ Consider exercising in low-income years
   □ Consider partial exercises
   □ Monitor AMT crossover point
   □ Same-day sales avoid AMT (disqualifying disposition)

6. EMPLOYER DEDUCTION

   NSO: Employer deduction = Employee ordinary income (at exercise)
   ISO (qualifying): No employer deduction
   ISO (disqualifying): Employer deduction = Employee ordinary income
   §83(b): Employer deduction at time of employee inclusion

7. PRACTICAL ISSUES

   □ Track grant date, exercise date, sale date
   □ Maintain records of FMV at each point
   □ Form 3921 (ISO exercise) and Form 3922 (ESPP)
   □ W-2 reporting for NSO income
   □ Estimated tax payments for large exercises

8. AUDIT ISSUES
   - §83(b) election not timely filed
   - Holding periods not met for ISO
   - AMT adjustment not made on ISO exercise
   - Basis not properly tracked
   - Withholding requirements not met on NSO""",
        key_factors=[
            "Option type properly classified (ISO vs. NSO)",
            "§83(b) election filed within 30 days",
            "ISO holding periods tracked",
            "AMT adjustment made on ISO exercise",
            "Basis correctly computed at each stage"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §422", "relevance": "ISO requirements"},
            {"authority": "IRC", "reference": "IRC §83", "relevance": "Property transfers for services"},
            {"authority": "IRC", "reference": "IRC §83(b)", "relevance": "Election to include at grant"},
            {"authority": "Reg", "reference": "Reg. §1.83-2", "relevance": "§83(b) election procedures"},
            {"authority": "IRC", "reference": "IRC §56(b)(3)", "relevance": "ISO AMT preference"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges stock compensation when: (1) §83(b)
election not timely filed; (2) ISO holding periods not met; (3) AMT preference not
reported on ISO exercise; (4) NSO income not properly withheld; (5) basis improperly
computed resulting in underreported gain.""",
        counter_arguments=[
            "§83(b) election timely filed and documented",
            "ISO holding periods satisfied",
            "AMT preference properly reported",
            "Basis correctly tracked through exercise",
            "Disqualifying disposition properly reported as ordinary income"
        ],
        appeals_strategy="""Stock compensation issues are often timing-based. §83(b)
election deadline is absolute — no relief for late filing. For ISOs, maintain records
of grant date, exercise date, and sale date to prove holding periods. AMT adjustment
creates AMT credit — ensure credit utilized in later years. For large exercises, consider
estimated tax payments to avoid penalty. Disqualifying dispositions convert gain to
ordinary — may be preferable to avoid AMT.""",
        entity_scope=["individual"],
        confidence="high"
    ),

    "alimony_pre_post_2018": DoctrineBlock(
        topic="Alimony and Property Settlements - Pre and Post-2018 Rules",
        keywords=["alimony", "spousal support", "divorce", "property settlement",
                  "separation agreement", "TCJA alimony", "deductible alimony",
                  "pre-2019 divorce", "post-2018 divorce"],
        conclusion_template="""For divorces finalized before 2019, alimony is deductible by the
payor and includible by the recipient. For divorces after 2018, alimony is nondeductible
and not includible (treated like child support). Pre-2019 agreements can opt into new rules
by modification. The distinction between alimony and property settlement remains critical
for pre-2019 divorces. Recapture rules apply if payments decrease significantly in years
2-3 of pre-2019 arrangements.""",
        reasoning_framework="""
ALIMONY — PRE AND POST-2018 ANALYSIS:

1. THE GREAT DIVIDE — TCJA CHANGES

   PRE-2019 DIVORCES (executed before 1/1/2019):
   □ Alimony DEDUCTIBLE by payor (above-the-line)
   □ Alimony INCLUDIBLE by recipient
   □ Traditional alimony rules apply

   POST-2018 DIVORCES (executed after 12/31/2018):
   □ Alimony NOT DEDUCTIBLE by payor
   □ Alimony NOT INCLUDIBLE by recipient
   □ Treated like child support for tax purposes

2. PRE-2019 DIVORCE — ALIMONY REQUIREMENTS (§71)
   To be alimony (deductible/includible), payments must:

   □ Be in cash (or check, money order)
   □ Be made pursuant to divorce or separation instrument
   □ Instrument must not designate payment as non-alimony
   □ Parties not members of same household (if legally separated)
   □ No liability to continue payments after death of recipient
   □ Not be fixed as child support

   "DIVORCE OR SEPARATION INSTRUMENT":
   □ Decree of divorce or separate maintenance
   □ Written separation agreement
   □ Decree requiring support payments

3. ALIMONY vs. PROPERTY SETTLEMENT (Pre-2019)
   ALIMONY = Periodic support payments
   □ Deductible/includible
   □ Ends on death or remarriage
   □ Based on support needs

   PROPERTY SETTLEMENT = Division of marital assets
   □ Not deductible/includible
   □ Fixed obligation regardless of events
   □ Often secured by property

4. RECAPTURE RULES (§71(f)) — Pre-2019 ONLY
   Prevents front-loading alimony:

   If payments in Year 2 or 3 decrease by more than $15,000,
   excess is "recaptured" in Year 3:
   □ Payor includes recapture amount in income
   □ Recipient deducts recapture amount

   COMPUTATION:
   Year 3 recapture = Year 2 excess + Year 1 excess

   EXCEPTIONS:
   □ Death or remarriage of recipient
   □ Payments tied to fluctuating property income
   □ Payments under temporary support order

5. MODIFICATIONS AND OPT-IN
   Pre-2019 agreement MODIFIED after 2018:
   □ Generally retains pre-2019 treatment UNLESS
   □ Modification expressly provides new rules apply

   PARTIES CAN OPT INTO NEW RULES:
   □ Must expressly state new rules apply
   □ Modification must be executed after 2018

6. CHILD SUPPORT vs. ALIMONY
   CHILD SUPPORT:
   □ Never deductible, never includible
   □ Identified as child support in instrument
   □ Or contingent on child-related events

   CONTINGENCY RULE:
   Payment that reduces based on child's:
   □ Reaching certain age
   □ Leaving household
   □ Marrying, dying, becoming employed
   = Treated as child support (not alimony)

7. REPORTING

   PRE-2019 DIVORCES:
   Payor: Report on Form 1040, deduct from income
   Recipient: Report as income on Form 1040
   Must include recipient's SSN on payor's return

   POST-2018 DIVORCES:
   No reporting required by either party
   Payments are non-tax events

8. STATE LAW CONSIDERATIONS
   State income tax treatment may differ
   □ Some states follow federal rules
   □ Some states have own alimony rules
   □ Check state law for each party's residence

9. AUDIT ISSUES
   - Payment not meeting §71 requirements
   - Property settlement mischaracterized as alimony
   - Recapture rules not applied
   - Child contingency triggering child support treatment
   - Recipient's SSN not provided""",
        key_factors=[
            "Date divorce instrument was executed (pre or post 2019)",
            "Payments meet §71 requirements (cash, instrument, no designation)",
            "Not child support or property settlement",
            "Recapture rules applied if payments decrease",
            "No child-related contingencies on payments"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §71 (pre-2019)", "relevance": "Alimony inclusion"},
            {"authority": "IRC", "reference": "IRC §215 (pre-2019)", "relevance": "Alimony deduction"},
            {"authority": "IRC", "reference": "IRC §71(f)", "relevance": "Recapture rules"},
            {"authority": "Statute", "reference": "TCJA §11051", "relevance": "Repeal for post-2018"},
            {"authority": "Temp Reg", "reference": "Temp. Reg. §1.71-1T", "relevance": "Alimony requirements"}
        ],
        burden_holder="payor (for deduction); IRS (for recharacterization)",
        irs_typical_position="""The IRS recharacterizes payments as non-alimony when:
(1) payments are fixed regardless of recipient's life (property settlement); (2) payments
reduce on child-related events (child support); (3) recapture rules trigger due to
front-loading; (4) instrument designates payments as non-alimony; (5) cash requirement
not met.""",
        counter_arguments=[
            "Divorce executed before January 1, 2019",
            "All §71 requirements satisfied",
            "Payments terminate on recipient's death",
            "No child-related contingencies",
            "Recapture properly computed if applicable"
        ],
        appeals_strategy="""Alimony issues turn on instrument language and payment structure.
For pre-2019 divorces, verify all §71 requirements are met. Review instrument for child
support language or contingencies. Compute recapture if payments decreased in years 2-3.
For post-2018 divorces, payments simply are not tax-relevant. If converting pre-2019
agreement, ensure modification does not inadvertently opt into new rules unless intended.""",
        entity_scope=["individual"],
        confidence="high"
    ),

    "foreign_tax_credit_901": DoctrineBlock(
        topic="Foreign Tax Credit - §901 Credit for Foreign Taxes Paid",
        keywords=["foreign tax credit", "901", "FTC", "foreign income", "foreign tax",
                  "credit limitation", "separate baskets", "foreign source income",
                  "903", "in lieu of taxes"],
        conclusion_template="""The foreign tax credit under §901 allows a credit for foreign
income taxes paid or accrued, limited to the U.S. tax on foreign source income. The
limitation is computed separately for passive income and general income "baskets." Excess
credits carry back 1 year and forward 10 years. The credit is elective; taxpayers may
instead deduct foreign taxes. Source rules for income and expense allocation are critical
to computing the limitation. Treaty benefits may modify credit availability.""",
        reasoning_framework="""
FOREIGN TAX CREDIT — §901 ANALYSIS:

1. FUNDAMENTAL RULE (§901)
   Credit allowed for:
   □ Income taxes paid or accrued to foreign countries
   □ Taxes paid or accrued to U.S. possessions
   □ Taxes "in lieu of" income taxes (§903)

2. CREDITABLE TAX REQUIREMENTS
   Foreign levy must be:
   □ A tax (not a fee or payment for specific benefit)
   □ Based on income (not gross receipts, property, etc.)
   □ The legal liability of the taxpayer

   "IN LIEU OF" TAXES (§903):
   □ Substitute for income tax otherwise due
   □ Must be in lieu of, not in addition to

3. CREDIT vs. DEDUCTION ELECTION
   Taxpayer may ELECT to:
   □ Credit foreign taxes (§901), OR
   □ Deduct foreign taxes (§164)

   ELECTION:
   □ All-or-nothing (same treatment for all foreign taxes)
   □ Made annually
   □ Credit generally more valuable (dollar-for-dollar vs. marginal rate)

4. CREDIT LIMITATION (§904)
   Credit cannot exceed U.S. tax on foreign source income:

   LIMITATION = U.S. Tax × (Foreign Source Taxable Income / Worldwide Taxable Income)

   PURPOSE: Prevent credit for foreign taxes from offsetting
   U.S. tax on U.S. source income

5. SEPARATE LIMITATION CATEGORIES ("BASKETS")
   Credit computed separately for:
   □ PASSIVE CATEGORY INCOME: Dividends, interest, rents, royalties
   □ GENERAL CATEGORY INCOME: Active business income, wages

   Excess credits in one basket cannot offset tax in other basket

6. SOURCE OF INCOME RULES (§861-§865)
   Critical for limitation computation:

   INCOME TYPE          SOURCE RULE
   ─────────────────────────────────────────────────
   Interest             Residence of payor
   Dividends            Place of incorporation
   Personal services    Where services performed
   Rents/Royalties      Where property used
   Sales of inventory   Title passage
   Sales of intangibles Residence of seller (generally)

7. EXPENSE ALLOCATION (§861-§864)
   Expenses reduce foreign source income:
   □ Directly allocable expenses (traced to income)
   □ Definitely related expenses (allocated by formula)
   □ Interest expense allocation (assets method or gross income method)

   High expenses allocated to foreign = LOWER limitation

8. CARRYBACK AND CARRYFORWARD (§904(c))
   Excess credits (above limitation):
   □ Carry back 1 year
   □ Carry forward 10 years
   □ Use in basket from which derived

9. FOREIGN TAX CREDIT FOR INDIVIDUALS
   SIMPLIFIED RULES if:
   □ All foreign income is passive
   □ Qualified dividends and/or capital gains
   □ Total foreign taxes < $300 ($600 MFJ)
   □ Form 1116 not required (election)

10. COMMON ISSUES

    TIMING:
    □ Cash method: Credit in year paid
    □ Accrual method: Credit in year accrued
    □ Election to use cash even if accrual method (per country)

    CURRENCY:
    □ Convert foreign taxes to USD
    □ Use exchange rate when taxes paid/accrued

11. AUDIT ISSUES
    - Foreign taxes not creditable (not income tax)
    - Source rules misapplied
    - Limitation computation errors
    - Expense allocation not performed
    - Carryforward tracking inadequate""",
        key_factors=[
            "Foreign tax is creditable income tax",
            "Source of income correctly determined",
            "Limitation computed by separate basket",
            "Expenses properly allocated",
            "Carryforward/carryback tracked by basket"
        ],
        primary_authority=[
            {"authority": "IRC", "reference": "IRC §901", "relevance": "FTC allowance"},
            {"authority": "IRC", "reference": "IRC §904", "relevance": "Credit limitation"},
            {"authority": "IRC", "reference": "IRC §861-§865", "relevance": "Source rules"},
            {"authority": "Reg", "reference": "Reg. §1.861-8", "relevance": "Expense allocation"},
            {"authority": "IRC", "reference": "IRC §904(c)", "relevance": "Carryover rules"}
        ],
        burden_holder="taxpayer",
        irs_typical_position="""The IRS challenges FTC when: (1) foreign levy is not creditable
income tax; (2) income improperly sourced as foreign; (3) expenses not allocated to
foreign income; (4) limitation computation incorrect; (5) basket category misapplied.""",
        counter_arguments=[
            "Foreign tax is income tax under treaty or local law analysis",
            "Source rules properly applied to each income type",
            "Expense allocation follows §861-§864 regulations",
            "Limitation correctly computed for each basket",
            "Carryforward schedule properly maintained"
        ],
        appeals_strategy="""FTC issues often involve complex source and allocation rules.
Document nature of foreign tax (obtain local law analysis if needed). Source rules are
mechanical but often misapplied. Expense allocation can significantly reduce limitation —
prepare detailed allocation computations. Consider treaty positions if available.
Track carryforwards by basket and year. Consider simplified method for individuals
with modest foreign income.""",
        entity_scope=["individual", "c_corporation", "trust", "estate"],
        confidence="high"
    ),
}


# ============================================================================
# DOCTRINE MATCHING ENGINE
# ============================================================================

class DoctrineEngine:
    """Layer 1: Instant doctrine matching with authority hardening."""

    # Conflict threshold: doctrines within this % of top score are considered competing
    CONFLICT_THRESHOLD = 0.80  # 80% of top score

    def __init__(self):
        self.cache = DOCTRINE_CACHE
        self._build_keyword_index()

    def _build_keyword_index(self):
        """Build reverse index for fast keyword lookup."""
        self.keyword_index: Dict[str, List[str]] = {}
        for topic_key, doctrine in self.cache.items():
            for keyword in doctrine.keywords:
                kw_lower = keyword.lower()
                if kw_lower not in self.keyword_index:
                    self.keyword_index[kw_lower] = []
                self.keyword_index[kw_lower].append(topic_key)

    def _compute_determinism_hash(self, query: str, topic_key: str, candidates: List[Dict]) -> str:
        """Compute hash for determinism verification. Same inputs → same hash."""
        import hashlib
        import re
        # Normalize query: lowercase, collapse whitespace, strip
        query_normalized = re.sub(r'\s+', ' ', query.lower().strip())
        # Include sorted candidate keys for reproducibility
        candidate_keys = sorted([c["topic_key"] for c in candidates])
        hash_input = f"{query_normalized}|{topic_key}|{','.join(candidate_keys)}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def match(self, query: str, entity_type: Optional[str] = None) -> Optional[DoctrineBlock]:
        """Match query to doctrine block. Returns None if no match.

        DEPRECATED: Use match_with_resolution() for full conflict detection.
        This method maintains backward compatibility.
        """
        result = self.match_with_resolution(query, entity_type)
        return result.doctrine if result.is_match else None

    def match_with_resolution(self, query: str, entity_type: Optional[str] = None) -> MatchResult:
        """Match query with full conflict detection and authority weighting.

        AUTHORITY HARDENING:
        - Detects when multiple doctrines could apply (conflict detection)
        - Uses authority weighting as primary tiebreaker
        - Falls back to alphabetical topic_key for determinism
        - Returns explicit conflict resolution rationale
        - Normalizes whitespace for deterministic matching

        Returns:
            MatchResult with doctrine, conflict info, and determinism hash
        """
        import re
        # Normalize: lowercase, collapse whitespace, strip
        query_normalized = re.sub(r'\s+', ' ', query.lower().strip())
        query_lower = query_normalized  # Use normalized for matching

        # Score each doctrine
        candidates: List[Dict[str, Any]] = []
        for topic_key, doctrine in self.cache.items():
            score = 0

            # Keyword matching
            for keyword in doctrine.keywords:
                if keyword.lower() in query_lower:
                    score += len(keyword)  # Longer matches score higher

            # Entity scope filtering
            if entity_type and "all" not in doctrine.entity_scope:
                if entity_type not in doctrine.entity_scope:
                    score = 0  # Exclude if entity doesn't match

            if score > 0:
                candidates.append({
                    "topic_key": topic_key,
                    "doctrine": doctrine,
                    "keyword_score": score,
                    "authority_weight": doctrine.get_authority_weight(),
                    "confidence": doctrine.confidence_stratification.value
                })

        # No matches
        if not candidates:
            return MatchResult(
                doctrine=None,
                topic_key=None,
                match_score=0,
                authority_weight=0,
                conflict_detected=False,
                conflict_resolution=None,
                all_candidates=[],
                determinism_hash=self._compute_determinism_hash(query, "", [])
            )

        # Sort candidates: keyword_score DESC, authority_weight DESC, topic_key ASC (deterministic)
        candidates.sort(key=lambda c: (-c["keyword_score"], -c["authority_weight"], c["topic_key"]))

        top_candidate = candidates[0]
        top_score = top_candidate["keyword_score"]

        # Conflict detection: find all candidates within threshold of top score
        threshold_score = top_score * self.CONFLICT_THRESHOLD
        competing = [c for c in candidates if c["keyword_score"] >= threshold_score]

        conflict_detected = len(competing) > 1
        conflict_resolution = None

        if conflict_detected:
            # Build explicit resolution
            rejected = []
            for c in competing[1:]:  # All except winner
                rejected.append({
                    "topic_key": c["topic_key"],
                    "topic": c["doctrine"].topic,
                    "keyword_score": c["keyword_score"],
                    "authority_weight": c["authority_weight"],
                    "rejection_reason": self._build_rejection_reason(top_candidate, c)
                })

            # Determine authority basis
            winner_auth = top_candidate["doctrine"].primary_authority
            authority_basis = winner_auth[0]["reference"] if winner_auth else "Keyword relevance"

            conflict_resolution = ConflictResolution(
                competing_doctrines=[c["topic_key"] for c in competing],
                resolution_rationale=self._build_resolution_rationale(top_candidate, competing),
                authority_basis=authority_basis,
                rejected_alternatives=rejected
            )

        return MatchResult(
            doctrine=top_candidate["doctrine"],
            topic_key=top_candidate["topic_key"],
            match_score=top_candidate["keyword_score"],
            authority_weight=top_candidate["authority_weight"],
            conflict_detected=conflict_detected,
            conflict_resolution=conflict_resolution,
            all_candidates=[{
                "topic_key": c["topic_key"],
                "keyword_score": c["keyword_score"],
                "authority_weight": c["authority_weight"]
            } for c in candidates[:10]],  # Top 10 for audit
            determinism_hash=self._compute_determinism_hash(
                query, top_candidate["topic_key"], candidates
            )
        )

    def _build_rejection_reason(self, winner: Dict, loser: Dict) -> str:
        """Explain why one doctrine was rejected in favor of another."""
        reasons = []
        if winner["keyword_score"] > loser["keyword_score"]:
            reasons.append(f"Lower keyword relevance ({loser['keyword_score']} vs {winner['keyword_score']})")
        if winner["authority_weight"] > loser["authority_weight"]:
            reasons.append(f"Lower authority weight ({loser['authority_weight']} vs {winner['authority_weight']})")
        if not reasons:
            reasons.append(f"Alphabetical tiebreaker ({loser['topic_key']} > {winner['topic_key']})")
        return "; ".join(reasons)

    def _build_resolution_rationale(self, winner: Dict, competing: List[Dict]) -> str:
        """Build human-readable rationale for conflict resolution."""
        if len(competing) == 2:
            other = competing[1]
            if winner["keyword_score"] > other["keyword_score"]:
                return f"'{winner['doctrine'].topic}' selected over '{other['doctrine'].topic}' due to higher keyword relevance ({winner['keyword_score']} vs {other['keyword_score']})"
            elif winner["authority_weight"] > other["authority_weight"]:
                return f"'{winner['doctrine'].topic}' selected over '{other['doctrine'].topic}' due to higher authority weight (IRC/Reg basis vs lower authority)"
            else:
                return f"'{winner['doctrine'].topic}' selected over '{other['doctrine'].topic}' via deterministic tiebreaker (alphabetical)"
        else:
            others = [c["doctrine"].topic for c in competing[1:]]
            return f"'{winner['doctrine'].topic}' selected from {len(competing)} competing doctrines: {', '.join(others[:3])}{'...' if len(others) > 3 else ''}. Resolution based on keyword relevance + authority hierarchy."

    def list_topics(self) -> List[str]:
        """List all doctrine topics."""
        return [d.topic for d in self.cache.values()]

    def get_doctrine(self, topic_key: str) -> Optional[DoctrineBlock]:
        """Get doctrine by topic key."""
        return self.cache.get(topic_key)


# ============================================================================
# SEMANTIC RETRIEVAL ENGINE (LAYER 2)
# ============================================================================

class RetrievalEngine:
    """Layer 2: Fast RAG on doctrine cache miss."""

    def __init__(self):
        self._search = None

    @property
    def search(self):
        """Lazy load search engine."""
        if self._search is None:
            from tax_expert_search import TaxExpertSearch
            self._search = TaxExpertSearch()
        return self._search

    def retrieve(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant documents. Target: 200-700ms."""
        results = self.search.search(query, n_results=n_results)
        return [
            {
                "section": r.section,
                "text": r.text,
                "source": r.source,
                "relevance": 1.0 - r.distance if r.distance else 0.9
            }
            for r in results
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        return self.search.get_stats()


# ============================================================================
# RESPONSE FORMATTER
# ============================================================================

class ResponseFormatter:
    """Format responses based on mode."""

    @staticmethod
    def format_fast(doctrine: DoctrineBlock, query: str) -> Dict[str, Any]:
        """FAST mode: Concise, doctrine-driven."""
        return {
            "conclusion": doctrine.conclusion_template.strip(),
            "reasoning": doctrine.reasoning_framework.split("\n\n")[0].strip(),
            "key_factors": doctrine.key_factors[:3],
            "citations": [
                Citation(
                    authority=c["authority"],
                    reference=c["reference"],
                    relevance=c["relevance"]
                ) for c in doctrine.primary_authority[:2]
            ],
            "limitations": [
                "This is general guidance; specific facts may alter analysis.",
                "Consult primary sources for current law."
            ]
        }

    @staticmethod
    def format_defense(doctrine: DoctrineBlock, query: str) -> Dict[str, Any]:
        """DEFENSE mode: Audit-ready with burden analysis."""
        return {
            "conclusion": doctrine.conclusion_template.strip(),
            "reasoning": doctrine.reasoning_framework.strip(),
            "key_factors": doctrine.key_factors,
            "citations": [
                Citation(
                    authority=c["authority"],
                    reference=c["reference"],
                    relevance=c["relevance"]
                ) for c in doctrine.primary_authority
            ],
            "burden_analysis": f"Burden of proof rests with: {doctrine.burden_holder.upper()}",
            "irs_position": doctrine.irs_typical_position.strip(),
            "counter_arguments": doctrine.counter_arguments,
            "appeals_posture": doctrine.appeals_strategy.strip(),
            "limitations": [
                "Analysis assumes facts as stated; undisclosed facts may alter conclusion.",
                "IRS positions may vary by examiner and jurisdiction.",
                "Appeals outcome depends on hazards of litigation analysis."
            ]
        }

    @staticmethod
    def format_memo(doctrine: DoctrineBlock, query: str) -> Dict[str, Any]:
        """MEMO mode: Full documentation with all authorities."""
        return {
            "conclusion": doctrine.conclusion_template.strip(),
            "reasoning": doctrine.reasoning_framework.strip(),
            "key_factors": doctrine.key_factors,
            "citations": [
                Citation(
                    authority=c["authority"],
                    reference=c["reference"],
                    relevance=c["relevance"]
                ) for c in doctrine.primary_authority
            ],
            "burden_analysis": f"""
BURDEN OF PROOF ANALYSIS

The burden of proof in this matter rests with the {doctrine.burden_holder.upper()}.

Under IRC §7491, the burden of proof shifts to the IRS in court proceedings if the
taxpayer: (1) introduces credible evidence; (2) maintains required records; (3)
cooperates with reasonable IRS requests; and (4) meets net worth requirements for
individuals.

For this issue, the initial burden {"is on the IRS to establish deficiency" if doctrine.burden_holder == "irs" else "is on the taxpayer to substantiate the claimed position"}.
""".strip(),
            "irs_position": doctrine.irs_typical_position.strip(),
            "counter_arguments": doctrine.counter_arguments,
            "appeals_posture": f"""
APPEALS CONFERENCE STRATEGY

{doctrine.appeals_strategy.strip()}

RECOMMENDED APPROACH:
1. Request face-to-face conference with Appeals Officer
2. Submit written protest with all documentary evidence
3. Emphasize hazards of litigation from government's perspective
4. Quantify settlement range based on strength of position
5. Maintain flexibility on procedural matters while defending substance
""".strip(),
            "limitations": [
                "This memorandum is for internal use and does not constitute legal advice.",
                "Facts assumed as stated; variations may require different analysis.",
                "Law current as of date of memorandum; verify for subsequent changes.",
                "Consult with qualified tax counsel before relying on this analysis."
            ]
        }

    @staticmethod
    def format_retrieval_response(
        query: str,
        results: List[Dict[str, Any]],
        mode: ResponseMode
    ) -> Dict[str, Any]:
        """Format response from RAG results (Layer 2)."""
        if not results:
            return {
                "conclusion": "Insufficient information in knowledge base to provide analysis.",
                "reasoning": "The query did not match available doctrine or retrievable content.",
                "key_factors": [],
                "citations": [],
                "limitations": ["Query may require manual research or expert consultation."]
            }

        # Synthesize from top results
        primary = results[0]
        conclusion = f"Based on {primary['section']}: {primary['text'][:500]}..."

        citations = [
            Citation(
                authority="Knowledge Base",
                reference=r["section"],
                relevance=f"Relevance: {r['relevance']:.0%}"
            ) for r in results[:3]
        ]

        base_response = {
            "conclusion": conclusion,
            "reasoning": "Analysis derived from semantic retrieval of knowledge base content.",
            "key_factors": [r["section"] for r in results[:5]],
            "citations": citations,
            "limitations": [
                "Response synthesized from retrieved documents, not pre-compiled doctrine.",
                "Manual verification of primary sources recommended.",
                "Confidence level: MODERATE - doctrine cache did not match."
            ]
        }

        if mode in [ResponseMode.DEFENSE, ResponseMode.MEMO]:
            base_response["burden_analysis"] = "Burden analysis requires doctrine-level research."
            base_response["irs_position"] = "IRS position analysis not available for this query."
            base_response["counter_arguments"] = ["Consult primary sources for defense arguments."]

        return base_response


# ============================================================================
# AUDIT TRAIL
# ============================================================================

def log_audit_event(
    query_id: str,
    question: str,
    mode: str,
    response_layer: str,
    latency_ms: float,
    doctrine_match: bool
):
    """Log query to audit trail."""
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query_id": query_id,
        "question_hash": hashlib.sha256(question.encode()).hexdigest()[:16],
        "mode": mode,
        "response_layer": response_layer,
        "latency_ms": round(latency_ms, 2),
        "doctrine_match": doctrine_match
    }

    import json
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(event) + "\n")


# ============================================================================
# MAIN ENGINE
# ============================================================================

class TaxIntelligenceEngine:
    """Production tax intelligence engine."""

    def __init__(self):
        self.doctrine = DoctrineEngine()
        self.retrieval = RetrievalEngine()
        self.formatter = ResponseFormatter()
        self.telemetry = get_telemetry()
        self.start_time = time.time()
        logger.info(f"Tax Intelligence Engine initialized. Doctrine topics: {len(self.doctrine.cache)}")
        logger.info("Telemetry system active")

    def query(self, request: TaxQuery) -> TaxResponse:
        """Process tax query through layered architecture with full telemetry and authority hardening."""
        metrics = get_metrics()
        metrics.query_start()
        start = time.time()
        query_id = str(uuid.uuid4())[:8]

        # Start telemetry trace
        entity_str = request.entity_type.value if request.entity_type else None
        trace_id = trace_query(
            question=request.question,
            mode=request.mode.value,
            jurisdiction=request.jurisdiction,
            entity_type=entity_str
        )

        try:
            # Layer 1: Doctrine Cache with Authority Hardening (target: 0-200ms)
            match_result = self.doctrine.match_with_resolution(request.question, entity_str)

            if match_result.is_match:
                doctrine = match_result.doctrine
                # Doctrine hit - format based on mode
                if request.mode == ResponseMode.FAST:
                    formatted = self.formatter.format_fast(doctrine, request.question)
                elif request.mode == ResponseMode.DEFENSE:
                    formatted = self.formatter.format_defense(doctrine, request.question)
                else:  # MEMO
                    formatted = self.formatter.format_memo(doctrine, request.question)

                latency = (time.time() - start) * 1000
                metrics.record_query(latency, doctrine_hit=True)

                # Serialize conflict resolution if present
                conflict_dict = None
                if match_result.conflict_resolution:
                    cr = match_result.conflict_resolution
                    conflict_dict = {
                        "competing_doctrines": cr.competing_doctrines,
                        "resolution_rationale": cr.resolution_rationale,
                        "authority_basis": cr.authority_basis,
                        "rejected_alternatives": cr.rejected_alternatives
                    }

                # Map confidence to tier
                strat = doctrine.confidence_stratification
                if strat == ConfidenceStratification.DEFENSIBLE:
                    confidence_tier = "high"
                elif strat == ConfidenceStratification.AGGRESSIVE_SUPPORTABLE:
                    confidence_tier = "moderate"
                else:
                    confidence_tier = "requires_review"

                response = TaxResponse(
                    query_id=query_id,
                    question=request.question,
                    mode=request.mode,
                    conclusion=formatted["conclusion"],
                    reasoning=formatted["reasoning"],
                    key_factors=formatted["key_factors"],
                    citations=formatted["citations"],
                    burden_analysis=formatted.get("burden_analysis"),
                    irs_position=formatted.get("irs_position"),
                    counter_arguments=formatted.get("counter_arguments"),
                    appeals_posture=formatted.get("appeals_posture"),
                    doctrine_match=True,
                    confidence_tier=confidence_tier,
                    response_layer="doctrine",
                    latency_ms=round(latency, 2),
                    # Authority Hardening fields
                    conflict_detected=match_result.conflict_detected,
                    conflict_resolution=conflict_dict,
                    authority_weight=match_result.authority_weight,
                    confidence_stratification=doctrine.confidence_stratification.value,
                    controlling_precedent=doctrine.get_precedent_anchor(),
                    determinism_hash=match_result.determinism_hash,
                    limitations=formatted.get("limitations", []),
                    timestamp=datetime.now(timezone.utc).isoformat()
                )

                # Complete telemetry trace for doctrine hit
                complete_trace(
                    trace_id=trace_id,
                    doctrine_matched=True,
                    doctrine_id=match_result.topic_key,
                    doctrine_topic=doctrine.topic,
                    confidence_score=0.95 if doctrine.confidence == "high" else 0.75,
                    response_layer="doctrine",
                    rag_triggered=False,
                    deep_analysis_triggered=False,
                    response_length=len(formatted["conclusion"]),
                    citations_count=len(formatted["citations"])
                )

                # Store reasoning snapshot for audit replay (with conflict data)
                conflict_note = ""
                if match_result.conflict_detected:
                    conflict_note = f" [CONFLICT RESOLVED: {len(match_result.all_candidates)} candidates]"
                self.telemetry.reasoning_store.store_snapshot(
                    trace_id=trace_id,
                    doctrine_id=match_result.topic_key,
                    doctrine_content=doctrine.conclusion_template[:500],
                    framework_name=doctrine.topic + conflict_note,
                    reasoning_steps=doctrine.key_factors,
                    key_factors_applied=doctrine.key_factors,
                    authorities_cited=doctrine.primary_authority,
                    conclusion_basis=doctrine.conclusion_template[:200],
                    counter_arguments_considered=doctrine.counter_arguments[:3] if doctrine.counter_arguments else [],
                    confidence_rationale=f"Stratification: {doctrine.confidence_stratification.value} | Authority weight: {match_result.authority_weight}",
                    cache_keys=[match_result.topic_key]
                )

                log_audit_event(query_id, request.question, request.mode.value, "doctrine", latency, True)
                return response

            # Layer 2: Semantic Retrieval (target: 200-700ms)
            results = self.retrieval.retrieve(request.question, n_results=5)
            formatted = self.formatter.format_retrieval_response(request.question, results, request.mode)

            latency = (time.time() - start) * 1000
            metrics.record_query(latency, doctrine_hit=False)

            # No doctrine match - authority hardening fields are None/empty
            import hashlib
            rag_determinism_hash = hashlib.sha256(
                f"{request.question.lower().strip()}|rag_fallback".encode()
            ).hexdigest()[:16]

            response = TaxResponse(
                query_id=query_id,
                question=request.question,
                mode=request.mode,
                conclusion=formatted["conclusion"],
                reasoning=formatted["reasoning"],
                key_factors=formatted["key_factors"],
                citations=formatted["citations"],
                burden_analysis=formatted.get("burden_analysis"),
                irs_position=formatted.get("irs_position"),
                counter_arguments=formatted.get("counter_arguments"),
                doctrine_match=False,
                confidence_tier="moderate" if results else "requires_review",
                response_layer="retrieval",
                latency_ms=round(latency, 2),
                # Authority Hardening: No doctrine, so minimal metadata
                conflict_detected=False,
                conflict_resolution=None,
                authority_weight=None,
                confidence_stratification=None,
                controlling_precedent=None,
                determinism_hash=rag_determinism_hash,
                limitations=formatted.get("limitations", []),
                timestamp=datetime.now(timezone.utc).isoformat()
            )

            # Complete telemetry trace for RAG fallback
            complete_trace(
                trace_id=trace_id,
                doctrine_matched=False,
                doctrine_id=None,
                doctrine_topic=None,
                confidence_score=0.6 if results else 0.3,
                response_layer="retrieval",
                rag_triggered=True,
                deep_analysis_triggered=False,
                response_length=len(formatted["conclusion"]),
                citations_count=len(formatted["citations"])
            )

            log_audit_event(query_id, request.question, request.mode.value, "retrieval", latency, False)
            return response

        except Exception as e:
            metrics.record_error(str(e))
            # Log error to telemetry error spine
            log_error(
                error=e,
                domain=ErrorDomain.DOCTRINE_ENGINE,
                operation="query",
                trace_id=trace_id,
                question=request.question[:200]
            )
            raise
        finally:
            metrics.query_end()

    def _get_doctrine_key(self, doctrine) -> str:
        """Get the cache key for a doctrine block."""
        for key, doc in self.doctrine.cache.items():
            if doc.topic == doctrine.topic:
                return key
        return "unknown"

    def get_health(self) -> HealthResponse:
        """
        Fast, shallow health check. No blocking calls.
        Returns cached metrics - never stalls even if downstream systems are degraded.
        """
        import psutil

        metrics = get_metrics()
        uptime = round(time.time() - self.start_time, 2)

        # Memory (fast - from psutil cache)
        try:
            mem = psutil.virtual_memory()
            memory_info = {
                "used_mb": round(mem.used / 1024 / 1024, 1),
                "available_mb": round(mem.available / 1024 / 1024, 1),
                "percent": mem.percent
            }
        except Exception:
            memory_info = {"used_mb": 0, "available_mb": 0, "percent": 0}

        # Determine overall status from cached metrics (no live checks)
        error_stats = metrics.get_error_stats()
        latency_stats = metrics.get_latency_stats()

        if error_stats["last_hour"] > 10:
            status = "unhealthy"
        elif error_stats["last_hour"] > 3 or latency_stats["avg_ms"] > 2000:
            status = "degraded"
        else:
            status = "healthy"

        # Vector DB status from last known state (no live query)
        vector_status = "ready" if self._retrieval is not None else "not_initialized"

        return HealthResponse(
            status=status,
            engine="ECHO Tax Intelligence Engine",
            version="1.0.0",
            uptime_seconds=uptime,

            api_latency=latency_stats,

            doctrine_cache={
                "status": "ready",
                "topics": len(self.doctrine.cache),
                "hit_rate": metrics.get_doctrine_hit_rate()
            },

            vector_db={
                "status": vector_status,
                "documents": self._cached_doc_count,
                "last_query_ms": latency_stats["last_ms"] if not metrics.get_doctrine_hit_rate() == 1.0 else 0
            },

            memory_mb=memory_info,

            active_queries=metrics.active_queries,
            queries_last_hour=metrics.queries_last_hour(),

            error_rate=error_stats
        )

    @property
    def _cached_doc_count(self) -> int:
        """Return cached document count. Updated lazily."""
        if not hasattr(self, '_doc_count_cache'):
            try:
                stats = self.retrieval.get_stats()
                self._doc_count_cache = stats.get("total_documents", 0)
            except Exception:
                self._doc_count_cache = 0
        return self._doc_count_cache

    @property
    def _retrieval(self):
        """Check if retrieval engine is initialized."""
        return self.retrieval._search


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

# Global engine instance
_engine: Optional[TaxIntelligenceEngine] = None


def get_engine() -> TaxIntelligenceEngine:
    global _engine
    if _engine is None:
        _engine = TaxIntelligenceEngine()
    return _engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting Tax Intelligence Engine...")
    get_engine()  # Initialize on startup
    yield
    logger.info("Shutting down Tax Intelligence Engine...")


app = FastAPI(
    title="ECHO Tax Intelligence Engine",
    description="""
Professional-grade tax doctrine system for CPAs, attorneys, and audit teams.

## Architecture
- **Layer 1**: Doctrine Cache (0-200ms) - Pre-compiled expert reasoning
- **Layer 2**: Semantic Retrieval (200-700ms) - Fast RAG on cache miss
- **Layer 3**: Deep Analysis (on-demand) - Multi-source synthesis

## Response Modes
- **FAST**: Doctrine-driven, minimal citations, sub-2 seconds
- **DEFENSE**: Structured reasoning, audit-ready, burden analysis
- **MEMO**: Long-form, citation-heavy, firm documentation

## Design Principles
- Deterministic reasoning over creative output
- Speed signals competence
- Structured responses for professional use
    """,
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/", include_in_schema=False)
async def root():
    return {"service": "ECHO Tax Intelligence Engine", "docs": "/docs", "health": "/health"}


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health():
    """System health check."""
    return get_engine().get_health()


@app.post("/tax/query", response_model=TaxResponse, tags=["Query"])
async def tax_query(request: TaxQuery):
    """
    Primary query endpoint.

    Submit a tax question and receive structured analysis based on pre-compiled
    doctrine or semantic retrieval from the knowledge base.

    **Response Modes:**
    - `fast` (default): Quick doctrine-driven answer
    - `defense`: Audit-ready with burden analysis and counter-arguments
    - `memo`: Full documentation suitable for firm files
    """
    return get_engine().query(request)


@app.get("/doctrine/topics", response_model=List[str], tags=["Doctrine"])
async def list_doctrine_topics():
    """List all pre-compiled doctrine topics with instant response times."""
    return get_engine().doctrine.list_topics()


@app.get("/doctrine/{topic_key}", tags=["Doctrine"])
async def get_doctrine_detail(topic_key: str):
    """Get detailed doctrine block by topic key."""
    engine = get_engine()

    # Find matching doctrine
    for key, doctrine in engine.doctrine.cache.items():
        if key == topic_key or doctrine.topic.lower() == topic_key.lower():
            return {
                "topic": doctrine.topic,
                "keywords": doctrine.keywords,
                "conclusion": doctrine.conclusion_template,
                "primary_authority": doctrine.primary_authority,
                "burden_holder": doctrine.burden_holder,
                "entity_scope": doctrine.entity_scope,
                "confidence": doctrine.confidence
            }

    raise HTTPException(status_code=404, detail=f"Doctrine topic '{topic_key}' not found")


@app.get("/stats", tags=["System"])
async def get_stats():
    """Get detailed system statistics."""
    engine = get_engine()
    health = engine.get_health()

    return {
        "doctrine": {
            "topics": health.doctrine_topics,
            "topic_list": engine.doctrine.list_topics()
        },
        "knowledge_base": {
            "documents": health.knowledge_documents
        },
        "performance": {
            "uptime_seconds": health.uptime_seconds,
            "target_latency_doctrine_ms": "0-200",
            "target_latency_retrieval_ms": "200-700"
        },
        "version": health.version
    }


# ============================================================================
# TELEMETRY ENDPOINTS
# ============================================================================

@app.get("/telemetry/health", tags=["Telemetry"])
async def telemetry_health():
    """Check telemetry system health."""
    return get_telemetry().health_check()


@app.get("/telemetry/traces", tags=["Telemetry"])
async def get_traces(limit: int = 50):
    """Get recent query traces."""
    tm = get_telemetry()
    return tm.query_tracer.get_recent_traces(limit)


@app.get("/telemetry/traces/{trace_id}", tags=["Telemetry"])
async def get_trace(trace_id: str):
    """Get a specific query trace by ID."""
    tm = get_telemetry()
    trace = tm.query_tracer.get_trace(trace_id)
    if trace:
        return trace
    raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")


@app.get("/telemetry/errors", tags=["Telemetry"])
async def get_errors(limit: int = 50, domain: Optional[str] = None):
    """Get recent errors from the error spine."""
    tm = get_telemetry()
    errors = tm.error_spine.get_recent_errors(limit)
    if domain:
        errors = [e for e in errors if e.get("domain") == domain]
    return errors


@app.get("/telemetry/performance", tags=["Telemetry"])
async def get_performance():
    """Get performance telemetry metrics."""
    tm = get_telemetry()
    return tm.performance.get_current_metrics()


@app.get("/telemetry/mutations", tags=["Telemetry"])
async def get_mutations(limit: int = 50):
    """Get doctrine mutation history."""
    tm = get_telemetry()
    return tm.mutation_log.get_recent_mutations(limit)


@app.get("/audit/replay/{trace_id}", tags=["Audit"])
async def replay_trace(trace_id: str):
    """Replay a query trace for audit purposes."""
    tm = get_telemetry()
    return tm.audit.replay_query(trace_id)


@app.get("/audit/snapshot/{trace_id}", tags=["Audit"])
async def get_reasoning_snapshot(trace_id: str):
    """Get reasoning snapshot for a trace."""
    tm = get_telemetry()
    snapshot = tm.reasoning_store.get_snapshot(trace_id)
    if snapshot:
        return snapshot
    raise HTTPException(status_code=404, detail=f"Snapshot for {trace_id} not found")


@app.get("/audit/report", tags=["Audit"])
async def generate_audit_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Generate audit report for a date range."""
    tm = get_telemetry()
    return tm.audit.generate_report(start_date, end_date)


# ============================================================================
# AUTHORITY HARDENING ENDPOINTS
# ============================================================================

@app.post("/hardening/verify-determinism", tags=["Authority Hardening"])
async def verify_determinism(
    question: str,
    runs: int = 3,
    mode: ResponseMode = ResponseMode.FAST,
    entity_type: Optional[EntityType] = None
):
    """Verify determinism: same query returns materially identical results.

    Runs the query N times and compares:
    - determinism_hash (must be identical)
    - doctrine matched (must be same)
    - topic_key (must be same)
    - conflict_resolution (must be same)

    Returns:
        is_deterministic: True if all runs match
        runs: Details of each run
        discrepancies: Any differences found
    """
    results = []
    for i in range(runs):
        request = TaxQuery(
            question=question,
            mode=mode,
            entity_type=entity_type
        )
        response = engine.query(request)
        # Extract topic key from conflict_resolution if present
        topic_key = None
        if response.conflict_resolution and response.conflict_resolution.get("competing_doctrines"):
            topic_key = response.conflict_resolution["competing_doctrines"][0]
        results.append({
            "run": i + 1,
            "determinism_hash": response.determinism_hash,
            "doctrine_match": response.doctrine_match,
            "topic_key": topic_key,
            "conflict_detected": response.conflict_detected,
            "authority_weight": response.authority_weight,
            "confidence_stratification": response.confidence_stratification
        })

    # Check determinism
    hashes = [r["determinism_hash"] for r in results]
    doctrine_matches = [r["doctrine_match"] for r in results]
    topic_keys = [r["topic_key"] for r in results]

    is_deterministic = (
        len(set(hashes)) == 1 and
        len(set(doctrine_matches)) == 1 and
        len(set(str(t) for t in topic_keys)) == 1
    )

    discrepancies = []
    if len(set(hashes)) > 1:
        discrepancies.append(f"Hash mismatch: {hashes}")
    if len(set(doctrine_matches)) > 1:
        discrepancies.append(f"Doctrine match mismatch: {doctrine_matches}")
    if len(set(str(t) for t in topic_keys)) > 1:
        discrepancies.append(f"Topic key mismatch: {topic_keys}")

    return {
        "question": question,
        "runs_executed": runs,
        "is_deterministic": is_deterministic,
        "determinism_hash": hashes[0] if is_deterministic else None,
        "results": results,
        "discrepancies": discrepancies if discrepancies else None
    }


@app.get("/hardening/conflicts", tags=["Authority Hardening"])
async def get_conflict_statistics():
    """Get statistics on doctrine conflicts across queries.

    Returns aggregated data on:
    - Queries with conflicts detected
    - Most frequently conflicting doctrine pairs
    - Resolution patterns
    """
    # Query telemetry for conflict data
    tm = get_telemetry()
    traces = tm.trace_spine.get_traces(limit=100)

    conflict_count = 0
    total_queries = len(traces)

    return {
        "total_queries_analyzed": total_queries,
        "conflicts_detected": conflict_count,
        "conflict_rate": round(conflict_count / max(total_queries, 1), 4),
        "doctrine_topics_loaded": len(engine.doctrine.cache),
        "conflict_threshold": engine.doctrine.CONFLICT_THRESHOLD,
        "note": "Detailed conflict tracking coming in next iteration"
    }


@app.get("/hardening/authority-weights", tags=["Authority Hardening"])
async def get_authority_weights():
    """Get authority weight hierarchy used for conflict resolution."""
    return {
        "hierarchy": {
            AuthorityLevel.IRC.value: {
                "weight": AuthorityLevel.IRC.weight,
                "description": "Internal Revenue Code sections"
            },
            AuthorityLevel.TREASURY_REG.value: {
                "weight": AuthorityLevel.TREASURY_REG.weight,
                "description": "Treasury Regulations"
            },
            AuthorityLevel.COURT_CASE.value: {
                "weight": AuthorityLevel.COURT_CASE.weight,
                "description": "Federal court decisions"
            },
            AuthorityLevel.IRS_GUIDANCE.value: {
                "weight": AuthorityLevel.IRS_GUIDANCE.weight,
                "description": "Revenue Rulings, Procedures, Notices"
            },
            AuthorityLevel.PUBLICATION.value: {
                "weight": AuthorityLevel.PUBLICATION.weight,
                "description": "IRS Publications, informal guidance"
            }
        },
        "conflict_resolution_order": [
            "1. Keyword relevance score (higher wins)",
            "2. Authority weight (IRC > Regs > Cases > Guidance > Pubs)",
            "3. Alphabetical topic key (deterministic tiebreaker)"
        ],
        "conflict_threshold": f"{engine.doctrine.CONFLICT_THRESHOLD * 100}% of top score"
    }


@app.get("/hardening/confidence-stratification", tags=["Authority Hardening"])
async def get_confidence_stratification():
    """Get confidence stratification levels for conclusions."""
    return {
        "levels": {
            ConfidenceStratification.DEFENSIBLE.value: {
                "tier": "high",
                "description": "Solid authority support, low audit risk",
                "recommended_action": "Proceed with position"
            },
            ConfidenceStratification.AGGRESSIVE_SUPPORTABLE.value: {
                "tier": "moderate",
                "description": "Supportable but may draw IRS scrutiny",
                "recommended_action": "Document thoroughly, consider disclosure"
            },
            ConfidenceStratification.DISCLOSURE_RECOMMENDED.value: {
                "tier": "requires_review",
                "description": "Position requires disclosure on return",
                "recommended_action": "Form 8275/8275-R disclosure"
            },
            ConfidenceStratification.HIGH_AUDIT_RISK.value: {
                "tier": "requires_review",
                "description": "Position may not survive examination",
                "recommended_action": "Reconsider position or obtain opinion letter"
            }
        },
        "doctrine_stratification_summary": {
            level.value: sum(
                1 for d in engine.doctrine.cache.values()
                if d.confidence_stratification == level
            )
            for level in ConfidenceStratification
        }
    }


# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting ECHO Tax Intelligence Engine on port 8391...")

    uvicorn.run(
        "tax_intelligence_engine:app",
        host="0.0.0.0",
        port=8391,
        reload=False,
        log_level="info"
    )
