# PIE Internal Architecture
## Programming Intelligence Engine - Complete System Documentation

**System Class:** ISOLATED_REASONING_ENGINE
**Governance Tier:** ZERO
**Version:** 2.0.0
**Last Updated:** 2026-01-31

---

## 1. Overview

PIE is a **deterministic cognitive architecture for engineering decisions**. It is NOT a chatbot. It is NOT a vector QA system. It is an institutional engineering cognition engine that:

- Reasons deterministically (same input → same output)
- Is version-aware before answering
- Treats documentation as evidence, not truth
- Detects dependency chains, lifecycle breakage, authority conflicts
- Does NOT generate code by default
- Does NOT "learn" at runtime

---

## 2. Core Principles

### 2.1 Determinism
Every query produces identical results given identical inputs. This is enforced through:
- Content hashing at every layer
- Determinism hashes on all judgments
- No stochastic processes in reasoning

### 2.2 Authority Hierarchy
Higher authority sources always win in conflicts. No ambiguity tolerated.

| Tier | Weight | Description | Examples |
|------|--------|-------------|----------|
| PRIMARY_SOURCE | 100 | Official vendor documentation | docs.google.com, developer.apple.com |
| CANONICAL_ENGINEERING | 80 | Established infrastructure | kubernetes.io, docs.docker.com |
| STRUCTURED_TECHNICAL | 60 | Standards and specifications | RFCs, W3C, OWASP |
| VERIFIED_EXPERT | 40 | Maintainer content | Deep dives, expert blogs |
| COMMUNITY_KNOWLEDGE | 20 | Community content | Stack Overflow, GitHub issues |

### 2.3 Version Awareness
PIE REFUSES to answer without version clarity. Every doctrine must have version metadata. Missing version = flagged uncertainty.

### 2.4 Read-Only Operation
In ENGINEERING_OBSERVER mode, PIE does not:
- Modify production systems
- Auto-remediate issues
- Perform structural changes
- Ingest new data

---

## 3. Architecture Layers

```
┌──────────────────────────────────────────────────────────────┐
│                    JUDGMENT OUTPUT LAYER                      │
│  EngineeringJudgmentFormatter → Structured Decisions          │
├──────────────────────────────────────────────────────────────┤
│                    ANALYSIS LAYER                             │
│  AuthorityClassifier | VersionLifecycle | DependencyGraph     │
│  FailureMode | DriftSentinel (Read-Only)                      │
├──────────────────────────────────────────────────────────────┤
│                    REGISTRY LAYER                             │
│  AuthorityRegistry → Immutable Classifications                │
├──────────────────────────────────────────────────────────────┤
│                    COGNITIVE LAYERS (Original)                │
│  Layer 1: Authority Hierarchy Engine                          │
│  Layer 2: Version Awareness Engine                            │
│  Layer 3: Semantic Engineering Graph                          │
│  Layer 4: Deterministic Doctrine Engine                       │
├──────────────────────────────────────────────────────────────┤
│                    SENTINEL LAYER                             │
│  DriftSentinel → Monitoring | StrategicAnalyzer → Briefings   │
├──────────────────────────────────────────────────────────────┤
│                    DATA LAYER                                 │
│  Models | Doctrines | Graph | Config                          │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. Subsystems

### 4.1 Authority Classification Engine
**Location:** `analyzers/authority_classifier.py`

Classifies sources by both **type** and **tier**:

**Source Types:**
- `SPEC` - Formal specifications (RFC, W3C, IEEE)
- `VENDOR_DOCS` - Official vendor documentation
- `RUNTIME_REALITY` - Observed production behavior
- `DEPRECATION_NOTICE` - Lifecycle announcements
- `REFERENCE_IMPL` - Canonical implementations
- `FAILURE_NARRATIVE` - Postmortems, CVEs, incidents

**Epistemological Properties:**
- `can_contradict_docs` - Runtime reality can override docs
- `lifecycle_authoritative` - Deprecation notices are definitive
- `requires_version_context` - Most sources need version info

### 4.2 Version & Lifecycle Engine
**Location:** `analyzers/version_lifecycle.py`

**REFUSAL CONDITIONS:**
- Cannot parse version string
- Missing version metadata on doctrine
- Unknown lifecycle state for specified technology

**Capabilities:**
- Semantic version parsing (major.minor.patch-prerelease+build)
- Constraint parsing (>=, <, ^, ~)
- Lifecycle state tracking (DEVELOPMENT → STABLE → EOL → REMOVED)
- Migration path computation
- Breaking change detection

### 4.3 Dependency Graph Analyzer
**Location:** `analyzers/dependency_graph.py`

Analyzes graph structures to identify:

| Risk Type | Description |
|-----------|-------------|
| **SPOF** | Single Points of Failure - nodes with many dependents |
| **Cascade Risk** | Chains where one failure triggers many others |
| **Circular Dependencies** | Dependency cycles that complicate changes |
| **Hidden Orchestrators** | Nodes controlling many others without designation |
| **Fragmentation** | Disconnected graph components |

### 4.4 Drift Sentinel (Read-Only)
**Location:** `analyzers/drift_sentinel.py`

**Observer-only variant** that:
- Detects version metadata drift
- Detects content hash changes
- Detects source staleness
- Logs all observations

**Does NOT:**
- Auto-remediate
- Modify doctrines
- Archive versions
- Trigger mutations

### 4.5 Failure Mode Analyzer
**Location:** `analyzers/failure_mode.py`

Consumes failure narratives:
- Postmortem documents
- CVE advisories
- Incident reports
- Outage analyses

Extracts:
- **Behavior Discrepancies** - "Docs say X, reality does Y"
- **Failure Modes** - Categorized failure patterns
- **Root Causes** - Why failures occurred
- **Mitigations** - What worked to fix issues

### 4.6 Authority Registry
**Location:** `registry/authority_registry.py`

**Immutable** classification storage:
- Sources classified once, recorded permanently
- Updates create new records (supersede, don't modify)
- Full audit trail maintained
- Conflict resolution is deterministic

### 4.7 Engineering Judgment Formatter
**Location:** `judgment/engineering_judgment.py`

Produces structured output with:

| Component | Description |
|-----------|-------------|
| **CLAIM** | What is being asserted |
| **EVIDENCE** | Sources supporting the claim |
| **AUTHORITY TIER** | Weight of the evidence |
| **CONFIDENCE** | Certainty level (DETERMINISTIC → REQUIRES_REVIEW) |
| **KNOWN UNKNOWNS** | Explicit gaps in knowledge |
| **REFUSAL CONDITIONS** | When NOT to trust this judgment |

---

## 5. File Structure

```
CORE/PIE/
├── __init__.py                 # Main exports
├── serve.py                    # FastAPI server
├── START_PIE.bat               # Launcher
│
├── analyzers/                  # Enhanced analysis subsystems
│   ├── __init__.py
│   ├── authority_classifier.py # Source type + tier classification
│   ├── version_lifecycle.py    # Version parsing + lifecycle
│   ├── dependency_graph.py     # SPOF + cascade analysis
│   ├── drift_sentinel.py       # Read-only drift observation
│   └── failure_mode.py         # Postmortem + CVE analysis
│
├── analyzer/                   # Original strategic analyzer
│   └── strategic_analyzer.py   # Architectural briefings
│
├── judgment/                   # Judgment formatting
│   ├── __init__.py
│   └── engineering_judgment.py # Structured output
│
├── registry/                   # Immutable registries
│   ├── __init__.py
│   └── authority_registry.py   # Source classification
│
├── layers/                     # Original cognitive layers
│   ├── authority_hierarchy.py  # Layer 1
│   ├── version_awareness.py    # Layer 2
│   ├── semantic_graph.py       # Layer 3
│   └── deterministic_doctrine.py # Layer 4
│
├── sentinel/                   # Original drift sentinel
│   └── drift_sentinel.py       # Full (mutation-capable)
│
├── engine/                     # Core data models
│   └── models.py
│
├── config/                     # Configuration
│   ├── authority_tiers.json
│   └── observer_state.json
│
├── doctrine/                   # Doctrine storage
│   └── archive/                # Archived versions
│
├── docs/                       # Documentation
│   └── PIE_INTERNAL_ARCHITECTURE.md
│
└── api/                        # API layer
    └── endpoints.py
```

---

## 6. Usage Patterns

### 6.1 Classifying a Source
```python
from CORE.PIE.analyzers import AuthorityClassificationEngine

engine = AuthorityClassificationEngine()

result = engine.classify(
    source_id="my_source",
    content="RFC 2119 defines MUST, SHALL, SHOULD...",
    url="https://tools.ietf.org/html/rfc2119"
)

# result.source_type == SourceType.SPEC
# result.authority_tier == AuthorityTier.STRUCTURED_TECHNICAL
# result.can_contradict_docs == False
```

### 6.2 Checking Version Compatibility
```python
from CORE.PIE.analyzers import VersionLifecycleEngine

engine = VersionLifecycleEngine()

result = engine.check_version("3.11", technology="python")

if result.refused:
    print(f"REFUSED: {result.refusal_reason}")
else:
    print(f"Valid: {result.is_valid}, Recommended: {result.is_recommended}")
```

### 6.3 Analyzing Dependencies
```python
from CORE.PIE.analyzers import DependencyGraphAnalyzer
from CORE.PIE.layers import SemanticEngineeringGraph

graph = SemanticEngineeringGraph()
# ... populate graph ...

analyzer = DependencyGraphAnalyzer(graph)
report = analyzer.analyze()

print(f"SPOFs: {len(report.spofs)}")
print(f"Cascade risks: {len(report.cascade_risks)}")
print(f"Risk score: {report.overall_risk_score}")
```

### 6.4 Creating an Engineering Judgment
```python
from CORE.PIE.judgment import EngineeringJudgmentFormatter, JudgmentType

formatter = EngineeringJudgmentFormatter()

judgment = formatter.create_judgment(
    claim="The API requires OAuth 2.0 authentication",
    judgment_type=JudgmentType.ASSERTION,
    doctrines=[doctrine1, doctrine2]
)

print(formatter.format_for_output(judgment, "full"))
```

### 6.5 Creating a Refusal
```python
from CORE.PIE.judgment import EngineeringJudgmentFormatter, RefusalReason

formatter = EngineeringJudgmentFormatter()

refusal = formatter.create_refusal(
    reason=RefusalReason.MISSING_VERSION,
    explanation="Cannot determine compatibility without SDK version",
    original_query="Is this API safe to use?",
    what_would_help=["Specify SDK version", "Provide target platform"]
)
```

---

## 7. Success Criteria

PIE should be able to:

1. **Explain WHY** something is risky, not just THAT it is risky
2. **Refuse to answer** without version truth
3. **Surface architectural contradictions** clearly
4. **Feel like a senior systems engineer**, not Stack Overflow

---

## 8. Observer State

When in `ENGINEERING_OBSERVER` mode:

```json
{
  "OBSERVER_STATE": "ENGINEERING_OBSERVER",
  "FLAGS": {
    "ENGINEERING_OBSERVER": true,
    "MUTATION_ENGINE": false,
    "AUTONOMOUS_REFACTOR": false
  },
  "RESTRICTIONS": [
    "No write operations",
    "No structural changes",
    "No ingestion",
    "No drift corrections"
  ]
}
```

---

## 9. Self-Tests

All subsystems include self-test methods:

```bash
python -c "from CORE.PIE.analyzers.authority_classifier import _self_test; _self_test()"
python -c "from CORE.PIE.analyzers.version_lifecycle import _self_test; _self_test()"
python -c "from CORE.PIE.analyzers.dependency_graph import _self_test; _self_test()"
python -c "from CORE.PIE.analyzers.failure_mode import _self_test; _self_test()"
python -c "from CORE.PIE.judgment.engineering_judgment import _self_test; _self_test()"
python -c "from CORE.PIE.registry.authority_registry import _self_test; _self_test()"
```

---

## 10. Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2026-01-31 | Added enhanced analyzers, judgment formatter, authority registry |
| 1.0.0 | 2026-01-30 | Initial PIE implementation with four cognitive layers |

---

**ECHO OMEGA PRIME | Authority 11.0 SOVEREIGN**
**PIE: Institutional Engineering Cognition**
