# PIE AUTHORITATIVE SOURCES REGISTRY
## Version 1.0.0 | Classification: GOVERNANCE_TIER_ZERO

**Directive ID:** PIE_SOURCES_REGISTRY_2026-02-01
**Authority:** Commander Bobby Don McWilliams II
**Status:** SOURCES DEFINED — INGESTION NOT YET AUTHORIZED

---

## CORE PRINCIPLE

> PIE does not read documents. PIE consumes structural artifacts.

Documents describe. Artifacts embody.

---

## 1. FORMAL SPECIFICATIONS

### IETF RFCs (Internet Engineering Task Force)
| Source | URL | Artifact Type |
|--------|-----|---------------|
| RFC Index | https://www.rfc-editor.org/rfc-index.html | Protocol specifications |
| HTTP/2 (RFC 7540) | https://www.rfc-editor.org/rfc/rfc7540 | Transport structure |
| TLS 1.3 (RFC 8446) | https://www.rfc-editor.org/rfc/rfc8446 | Security protocol |
| DNS (RFC 1035) | https://www.rfc-editor.org/rfc/rfc1035 | Resolution hierarchy |
| OAuth 2.0 (RFC 6749) | https://www.rfc-editor.org/rfc/rfc6749 | Auth flow structure |

**Extraction Focus:**
- State machines
- Protocol dependencies
- Version compatibility matrices
- Failure mode enumerations

### ISO Standards
| Standard | Domain | Artifact Type |
|----------|--------|---------------|
| ISO 27001 | Information Security | Control hierarchies |
| ISO 9001 | Quality Management | Process dependencies |
| ISO 22301 | Business Continuity | Recovery structures |

### NIST Special Publications
| Publication | Domain | Artifact Type |
|-------------|--------|---------------|
| NIST SP 800-53 | Security Controls | Control catalog structure |
| NIST SP 800-171 | CUI Protection | Requirement dependencies |
| NIST SP 800-37 | Risk Management | Lifecycle stages |
| NIST SP 800-61 | Incident Response | Response flow structure |
| NIST CSF | Cybersecurity Framework | Function/Category/Subcategory hierarchy |

**Why NIST:**
- Versioned
- Checksummed (official PDFs)
- Provenance clear (US Government)
- Structured (machine-parseable mappings available)

---

## 2. REAL SYSTEM ARTIFACTS

### Open-Source Monorepo Manifests
| System | Repository | Artifact Type |
|--------|------------|---------------|
| Kubernetes | github.com/kubernetes/kubernetes | go.mod, go.sum |
| Linux Kernel | kernel.org | Kconfig, Makefile deps |
| PostgreSQL | github.com/postgres/postgres | configure.ac, Makefile.am |
| Chromium | chromium.googlesource.com | BUILD.gn, DEPS |
| Node.js | github.com/nodejs/node | deps/, binding.gyp |

**Extraction Focus:**
- Dependency graphs
- Build order constraints
- Version pinning policies
- Platform-specific branches

### Dependency Lockfiles
| Ecosystem | Lockfile | Structure |
|-----------|----------|-----------|
| Node/npm | package-lock.json | Dependency tree with integrity hashes |
| Python/pip | requirements.txt + pip-compile | Pinned versions with hashes |
| Rust/Cargo | Cargo.lock | Exact versions with checksums |
| Go | go.sum | Module hashes |
| Java/Maven | pom.xml + dependency:tree | Transitive closure |

**Why Lockfiles:**
- Exact version truth
- Transitive dependency revelation
- Hash verification built-in
- Historical versions available (git)

### Infrastructure-as-Code Repositories
| Type | Examples | Artifact Structure |
|------|----------|-------------------|
| Terraform | AWS provider, GCP provider | Resource dependencies, state structure |
| Helm Charts | Bitnami, official charts | values.yaml dependencies |
| Kubernetes Manifests | production configs | Resource references, RBAC hierarchies |
| Ansible Playbooks | Galaxy roles | Task dependencies, variable precedence |
| CloudFormation | AWS samples | Resource dependencies, export/import |

---

## 3. POSTMORTEMS & INCIDENT ANALYSIS

### Cloud Provider Outage Reports
| Provider | Source | Artifact Type |
|----------|--------|---------------|
| AWS | aws.amazon.com/message/ | Service dependency failures |
| GCP | status.cloud.google.com/incidents | Cascade analysis |
| Azure | status.azure.com/history | Regional dependency maps |
| Cloudflare | blog.cloudflare.com (postmortems) | Edge infrastructure failures |

**Extraction Focus:**
- Root cause chains
- Blast radius patterns
- Recovery dependency order
- Time-to-detection metrics

### CVE Analyses
| Source | URL | Artifact Type |
|--------|-----|---------------|
| NVD | nvd.nist.gov | Vulnerability dependency chains |
| CVE Details | cvedetails.com | Version-to-vulnerability mappings |
| GitHub Security | github.com/advisories | Dependency graph impact |
| Snyk | snyk.io/vuln | Transitive vulnerability paths |

**Why CVEs:**
- Version-specific
- Dependency-chain aware
- Severity hierarchies (CVSS)
- Patch dependency requirements

### SRE Incident Writeups
| Organization | Source | Artifact Type |
|--------------|--------|---------------|
| Google SRE | sre.google (public chapters) | Failure mode taxonomies |
| Meta/Facebook | engineering.fb.com | Scale failure patterns |
| Netflix | netflixtechblog.com | Chaos engineering results |
| Uber | eng.uber.com | Distributed system failures |
| Stripe | stripe.com/blog/engineering | Payment system resilience |

---

## 4. GOVERNANCE DOCUMENTS

### Architectural Decision Records (ADRs)
| Source | Repository | Artifact Type |
|--------|------------|---------------|
| ADR GitHub | github.com/joelparkerhenderson/architecture-decision-record | ADR templates |
| Kubernetes KEPs | github.com/kubernetes/enhancements | Enhancement proposals |
| Rust RFCs | github.com/rust-lang/rfcs | Language evolution decisions |
| Python PEPs | peps.python.org | Enhancement proposals |
| TC39 Proposals | github.com/tc39/proposals | JavaScript evolution |

**Extraction Focus:**
- Decision dependencies
- Supersession chains
- Rationale structures
- Rejection reasons

### Compliance Frameworks
| Framework | Domain | Artifact Type |
|-----------|--------|---------------|
| SOC 2 | Service Organization Controls | Control mapping hierarchies |
| HIPAA | Healthcare | Safeguard dependencies |
| FedRAMP | Federal Cloud | Control inheritance |
| PCI DSS | Payment Card | Requirement dependencies |
| GDPR | Data Protection | Rights/obligations hierarchy |

**Why Compliance:**
- Structured control relationships
- Explicit dependency chains
- Version history (framework updates)
- Audit trail requirements

---

## 5. ARTIFACT REQUIREMENTS

### Before Any Ingestion

Every artifact MUST have:

```json
{
  "artifact_id": "NIST_SP_800_53_R5",
  "source_url": "https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final",
  "version": "Rev 5",
  "retrieved_at": "2026-02-01T00:00:00Z",
  "sha256_hash": "abc123...",
  "provenance": {
    "authority": "NIST",
    "authority_level": "US_FEDERAL_GOVERNMENT",
    "publication_date": "2020-09-23",
    "supersedes": "NIST_SP_800_53_R4"
  },
  "artifact_class": "SECURITY_CONTROLS",
  "extraction_status": "PENDING"
}
```

### Artifact Classes for PIE

| Class | Description | Example Queries |
|-------|-------------|-----------------|
| `DEPENDENCY_STRUCTURE` | What depends on what | "Which components have implicit dependencies?" |
| `VERSION_LIFECYCLE` | How versions evolve | "What would break under version skew?" |
| `AUTHORITY_HIERARCHY` | Who decides what | "Where is authority implicit but undocumented?" |
| `FAILURE_MODE` | How systems fail | "Which dependency assumptions are unstable?" |
| `CONTROL_MAPPING` | How controls relate | "Which controls have circular dependencies?" |

---

## 6. INGESTION PILOT CANDIDATES

### Recommended First Corpus: NIST 800-Series

**Rationale:**
- Bounded (finite set of publications)
- Versioned (Rev 1, 2, 3, etc.)
- Checksummed (official PDFs have hashes)
- Provenance clear (US Government)
- Structured (control catalogs in XML/JSON)
- Cross-referenced (controls reference each other)

**Pilot Scope:**
```
NIST SP 800-53 Rev 5 (Security Controls)
NIST SP 800-53A Rev 5 (Assessment Procedures)
NIST SP 800-53B (Control Baselines)
NIST CSF 2.0 (Cybersecurity Framework)
```

**PIE Questions for Pilot:**
1. "Which controls have circular dependencies?"
2. "Where is control authority implicit but undocumented?"
3. "Which baseline assumptions would break under framework version skew?"
4. "What control relationships are unstable across revisions?"

### Alternative Pilot: Kubernetes Architecture

**Rationale:**
- Single large system
- Extensive ADRs (KEPs)
- Dependency lockfiles (go.mod, go.sum)
- Well-documented failure modes
- Active incident history

### Alternative Pilot: PostgreSQL

**Rationale:**
- Decades of version history
- Clear dependency structure
- Extensive postmortem culture
- Configuration hierarchy well-defined

---

## 7. INGESTION PROHIBITION

**UNTIL COMMANDER AUTHORIZES:**

| Action | Status |
|--------|--------|
| Download artifacts | PROHIBITED |
| Parse structures | PROHIBITED |
| Feed to PIE | PROHIBITED |
| Store locally | PROHIBITED |

**This document defines WHAT to ingest.**
**Commander approval required for WHEN to ingest.**

---

## VERSION HISTORY

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-02-01 | Initial sources registry |

---

**ECHO OMEGA PRIME | Authority 11.0 SOVEREIGN**
**PIE: Sources defined. Ingestion awaits authorization.**
