# ARCS DOCTRINE EXPANSION PROTOCOL
## Version 1.0.0 | Classification: GOVERNANCE_TIER_ZERO

**Directive ID:** ARCS_DOCTRINE_EXPANSION_2026-02-01
**Authority:** Commander Bobby Don McWilliams II
**Purpose:** Define how ARCS knowledge base grows without mutating reasoning rules

---

## CORE PRINCIPLE

> ARCS can grow its knowledge. ARCS cannot grow its reasoning.

Doctrine expansion adds **facts**. It never adds **inference rules**.

---

## 1. WHO MAY ADD DOCTRINE?

| Authority Level | Expansion Rights | Scope |
|-----------------|------------------|-------|
| **TIER 100 (Commander)** | FULL | Any doctrine, any domain, override gates |
| **TIER 80 (Designated Legal Counsel)** | DOMAIN_LIMITED | Verified legal sources only |
| **TIER 60 (Trusted Contributor)** | PROPOSAL_ONLY | Must pass all review gates |
| **TIER 40 (System/Automated)** | METADATA_ONLY | Citations, cross-refs, formatting |
| **TIER 20 and below** | NONE | Read-only access |

### Authorization Chain
```
Contributor → Proposal → Review Gates → TIER 80+ Approval → Commander Notification → Commit
```

No doctrine enters without TIER 80+ explicit approval.

---

## 2. DOCTRINE VS COMMENTARY

| Category | Definition | Example | Allowed? |
|----------|------------|---------|----------|
| **DOCTRINE** | Binding legal text from authoritative source | IRC § 162(a) verbatim | YES |
| **CASE LAW** | Court holding with citation | *Gregory v. Helvering* holding | YES |
| **REGULATION** | Published regulatory text | Treas. Reg. § 1.162-1 | YES |
| **COMMENTARY** | Interpretive opinion without binding authority | "This suggests..." | NO |
| **SPECULATION** | Untested legal theory | "Courts might hold..." | NO |
| **SYNTHESIS** | Novel combination of sources | Merged interpretation | NO |

### Doctrine Requirements
- **Verbatim source text** (no paraphrase)
- **Full citation** (court, date, reporter)
- **Jurisdiction marker** (federal, state, circuit)
- **Effective date** (when law took effect)
- **Sunset clause** (if applicable)

### Commentary Prohibition
ARCS does not store opinions. If a source contains both doctrine and commentary, extract doctrine only. Commentary may be stored in separate `NOTES/` directory but is NEVER loaded into reasoning context.

---

## 3. REQUIRED AUTHORITY SOURCES

### Acceptable Primary Sources
| Source Type | Authority Level | Verification |
|-------------|-----------------|--------------|
| U.S. Code | BINDING | congress.gov or uscode.house.gov |
| Treasury Regulations | BINDING | ecfr.gov |
| Supreme Court | BINDING | supremecourt.gov or Westlaw |
| Circuit Courts | BINDING_IN_CIRCUIT | courtlistener.com or Westlaw |
| IRS Revenue Rulings | PERSUASIVE | irs.gov |
| IRS Revenue Procedures | PERSUASIVE | irs.gov |
| Tax Court | PERSUASIVE | ustaxcourt.gov |
| Private Letter Rulings | LIMITED (taxpayer-specific) | irs.gov |

### Unacceptable Sources
- Wikipedia
- Law firm blogs (unless citing primary source)
- AI-generated summaries
- Treatises (unless citing primary source)
- News articles
- Social media

### Source Verification Protocol
1. Retrieve from official government source
2. Hash original document (SHA-256)
3. Store hash with doctrine entry
4. Verify hash on each load
5. Flag if source modified upstream

---

## 4. REVIEW GATES

### Gate 1: CONFIDENCE
| Confidence Level | Action |
|------------------|--------|
| ≥ 0.95 | Auto-queue for TIER 80 review |
| 0.80 - 0.94 | Requires two TIER 60+ reviews |
| 0.60 - 0.79 | Requires TIER 80 + Commander notification |
| < 0.60 | REJECT - insufficient source quality |

Confidence = f(source_authority, citation_completeness, verification_status)

### Gate 2: CONFLICT DETECTION
Before any doctrine commits:
```
1. Scan existing doctrine for contradictions
2. Flag overlapping jurisdiction/subject matter
3. Identify superseded statutes
4. Check effective date conflicts
5. Verify no circular references
```

| Conflict Type | Resolution |
|---------------|------------|
| Direct contradiction | HALT - human review mandatory |
| Supersession (newer replaces older) | Mark old as SUPERSEDED, add new |
| Jurisdictional overlap | Add both with jurisdiction tags |
| Ambiguity | HALT - human review mandatory |

### Gate 3: NOVELTY ASSESSMENT
| Novelty Level | Definition | Action |
|---------------|------------|--------|
| KNOWN_DOMAIN | Existing subject area | Standard review |
| ADJACENT_DOMAIN | Related but new area | TIER 80 review required |
| NEW_DOMAIN | Entirely new legal area | Commander approval required |
| REASONING_ADJACENT | Could affect inference | PERMANENT BLOCK |

**CRITICAL:** Any doctrine that could modify HOW ARCS reasons (not just WHAT it knows) is permanently blocked. Reasoning rules are frozen.

---

## 5. VERSIONING & ROLLBACK RULES

### Version Schema
```
ARCS_DOCTRINE_v{MAJOR}.{MINOR}.{PATCH}

MAJOR: New legal domain added
MINOR: Significant doctrine additions within domain
PATCH: Corrections, citations, metadata updates
```

### Commit Requirements
Every doctrine commit includes:
```json
{
  "version": "1.2.3",
  "timestamp": "2026-02-01T00:00:00Z",
  "author_tier": 80,
  "author_id": "legal_counsel_001",
  "sources_added": ["IRC_162_a", "Reg_1_162_1"],
  "sources_modified": [],
  "sources_removed": [],
  "conflict_check": "PASS",
  "confidence_score": 0.97,
  "commander_notified": true,
  "rollback_hash": "abc123..."
}
```

### Rollback Protocol
| Trigger | Action |
|---------|--------|
| Doctrine found incorrect | Immediate rollback to previous version |
| Source invalidated (law changed) | Mark SUPERSEDED, do not delete |
| Conflict discovered post-commit | Rollback + conflict resolution |
| Commander order | Immediate rollback, no questions |

### Rollback Command
```
ARCS_ROLLBACK --to-version=1.2.2 --reason="Conflict detected" --authority=TIER_100
```

Rollbacks are logged permanently. No rollback erases history.

---

## 6. MANDATORY HUMAN REVIEW

### Always Requires Human Review

| Scenario | Minimum Authority |
|----------|-------------------|
| First doctrine in new legal domain | TIER 100 (Commander) |
| Conflict with existing doctrine | TIER 80 + Commander notification |
| Confidence score < 0.80 | TIER 80 |
| Source from non-government origin | TIER 80 |
| Doctrine affects multiple jurisdictions | TIER 80 |
| Any constitutional question | TIER 100 (Commander) |
| Any criminal law question | TIER 100 (Commander) |
| Any doctrine older than 10 years | TIER 80 (verify still valid) |
| Rollback request | TIER 80 |
| Emergency doctrine addition | TIER 100 (Commander) |

### Review Checklist
- [ ] Source verified from official government site
- [ ] Citation complete and accurate
- [ ] No commentary mixed with doctrine
- [ ] Conflict check passed
- [ ] Effective date confirmed
- [ ] Jurisdiction clearly marked
- [ ] No reasoning rule implications
- [ ] Hash recorded for verification

---

## 7. EXPANSION WORKFLOW

```
┌─────────────────────────────────────────────────────────────────┐
│                    DOCTRINE EXPANSION FLOW                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [Contributor] ──► [Proposal] ──► [Gate 1: Confidence]          │
│                                          │                       │
│                                          ▼                       │
│                                   [Gate 2: Conflicts]            │
│                                          │                       │
│                                          ▼                       │
│                                   [Gate 3: Novelty]              │
│                                          │                       │
│                        ┌─────────────────┼─────────────────┐     │
│                        ▼                 ▼                 ▼     │
│                   [STANDARD]        [ELEVATED]        [BLOCKED]  │
│                        │                 │                 │     │
│                        ▼                 ▼                 ▼     │
│                   [TIER 80]         [TIER 100]         [REJECT]  │
│                        │                 │                       │
│                        └────────┬────────┘                       │
│                                 ▼                                │
│                          [COMMIT + LOG]                          │
│                                 │                                │
│                                 ▼                                │
│                    [Commander Notification]                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. HARD PROHIBITIONS

The following are **permanently prohibited**:

1. Adding inference rules disguised as doctrine
2. Modifying existing reasoning weights
3. Adding doctrine without source verification
4. Bypassing conflict detection
5. Adding commentary as doctrine
6. Removing doctrine without audit trail
7. Backdating doctrine entries
8. Committing without version increment

---

## VERSION HISTORY

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-02-01 | Initial protocol |

---

**ECHO OMEGA PRIME | Authority 11.0 SOVEREIGN**
**ARCS: Knowledge grows. Reasoning is frozen.**
