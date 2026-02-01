# PIE CANONICAL ARTIFACT TYPE DEFINITIONS
## Schema-Level Specification | No Content Analysis

**Version:** 1.0.0
**State:** ENGINEERING_OBSERVER_STATE
**Purpose:** Define what PIE accepts, not what PIE contains

---

## ARTIFACT TYPE 001: DEPENDENCY_MANIFEST

### Name
`DEPENDENCY_MANIFEST`

### Description
Declares explicit dependencies between software components.

### Required Metadata Fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `artifact_id` | string | YES | Unique identifier |
| `artifact_type` | enum | YES | Must be `DEPENDENCY_MANIFEST` |
| `source_system` | string | YES | Originating system (e.g., "npm", "cargo", "go") |
| `source_url` | string | YES | Retrieval location |
| `retrieved_at` | ISO8601 | YES | Timestamp of retrieval |
| `sha256_hash` | string(64) | YES | Content hash |
| `manifest_version` | string | YES | Version of the manifest format |
| `root_package` | string | YES | Top-level package name |
| `dependency_count` | integer | YES | Number of declared dependencies |
| `lockfile_present` | boolean | YES | Whether exact versions are pinned |

### Accepted Formats
| Format | Extension | Parser Required |
|--------|-----------|-----------------|
| npm package-lock | `.json` | npm-lockfile-parser |
| yarn.lock | `.lock` | yarn-lock-parser |
| Cargo.lock | `.lock` | cargo-lock-parser |
| go.sum | `.sum` | go-sum-parser |
| requirements.txt | `.txt` | pip-requirements-parser |
| Pipfile.lock | `.lock` | pipenv-parser |
| pom.xml | `.xml` | maven-pom-parser |
| build.gradle | `.gradle` | gradle-parser |

### Rejection Conditions
| Condition | Rejection Code | Action |
|-----------|----------------|--------|
| Missing `sha256_hash` | `REJECT_NO_HASH` | REFUSE |
| Missing `source_url` | `REJECT_NO_PROVENANCE` | REFUSE |
| Unsupported format | `REJECT_UNKNOWN_FORMAT` | REFUSE |
| Hash mismatch on verification | `REJECT_INTEGRITY_FAIL` | REFUSE |
| No `retrieved_at` timestamp | `REJECT_NO_TIMESTAMP` | REFUSE |
| Manifest older than 5 years without `legacy_override` | `REJECT_STALE` | REFUSE |

---

## ARTIFACT TYPE 002: SYSTEM_TOPOLOGY

### Name
`SYSTEM_TOPOLOGY`

### Description
Maps runtime service relationships, ports, and dependencies.

### Required Metadata Fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `artifact_id` | string | YES | Unique identifier |
| `artifact_type` | enum | YES | Must be `SYSTEM_TOPOLOGY` |
| `topology_source` | enum | YES | `STATIC_CONFIG`, `RUNTIME_DISCOVERY`, `MANUAL_DECLARATION` |
| `source_url` | string | YES | Retrieval location |
| `retrieved_at` | ISO8601 | YES | Timestamp of retrieval |
| `sha256_hash` | string(64) | YES | Content hash |
| `service_count` | integer | YES | Number of services in topology |
| `edge_count` | integer | YES | Number of dependency edges |
| `environment` | string | YES | `PRODUCTION`, `STAGING`, `DEVELOPMENT` |
| `topology_version` | string | YES | Version identifier |

### Accepted Formats
| Format | Extension | Parser Required |
|--------|-----------|-----------------|
| Kubernetes manifests | `.yaml`, `.yml` | k8s-manifest-parser |
| Docker Compose | `.yaml`, `.yml` | docker-compose-parser |
| Terraform state | `.tfstate` | terraform-state-parser |
| Helm values | `.yaml` | helm-values-parser |
| CloudFormation | `.yaml`, `.json` | cfn-parser |
| Custom JSON topology | `.json` | pie-topology-parser |

### Rejection Conditions
| Condition | Rejection Code | Action |
|-----------|----------------|--------|
| Missing `environment` | `REJECT_NO_ENVIRONMENT` | REFUSE |
| `service_count` = 0 | `REJECT_EMPTY_TOPOLOGY` | REFUSE |
| Missing `topology_source` | `REJECT_NO_SOURCE_TYPE` | REFUSE |
| Hash mismatch | `REJECT_INTEGRITY_FAIL` | REFUSE |
| Mixed environments in single artifact | `REJECT_ENVIRONMENT_MIXING` | REFUSE |

---

## ARTIFACT TYPE 003: CONTROL_CATALOG

### Name
`CONTROL_CATALOG`

### Description
Structured security or compliance control definitions with relationships.

### Required Metadata Fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `artifact_id` | string | YES | Unique identifier |
| `artifact_type` | enum | YES | Must be `CONTROL_CATALOG` |
| `framework` | string | YES | Framework name (e.g., "NIST_800_53", "SOC2", "PCI_DSS") |
| `framework_version` | string | YES | Version of the framework |
| `source_url` | string | YES | Official source URL |
| `retrieved_at` | ISO8601 | YES | Timestamp of retrieval |
| `sha256_hash` | string(64) | YES | Content hash |
| `authority` | string | YES | Issuing authority |
| `authority_level` | enum | YES | See Authority Levels below |
| `control_count` | integer | YES | Number of controls |
| `publication_date` | ISO8601 | YES | Official publication date |
| `supersedes` | string | NO | Previous version artifact_id |

### Authority Levels
| Level | Description |
|-------|-------------|
| `US_FEDERAL_GOVERNMENT` | NIST, CISA, etc. |
| `STANDARDS_BODY` | ISO, IETF, etc. |
| `INDUSTRY_CONSORTIUM` | PCI SSC, HITRUST |
| `REGULATORY_BODY` | SEC, FTC, HHS |

### Accepted Formats
| Format | Extension | Parser Required |
|--------|-----------|-----------------|
| OSCAL JSON | `.json` | oscal-json-parser |
| OSCAL XML | `.xml` | oscal-xml-parser |
| NIST Excel | `.xlsx` | nist-excel-parser |
| Custom structured | `.json` | control-catalog-parser |

### Rejection Conditions
| Condition | Rejection Code | Action |
|-----------|----------------|--------|
| Missing `authority` | `REJECT_NO_AUTHORITY` | REFUSE |
| Missing `framework_version` | `REJECT_NO_VERSION` | REFUSE |
| Unofficial source URL | `REJECT_UNOFFICIAL_SOURCE` | REFUSE |
| No `publication_date` | `REJECT_NO_PUB_DATE` | REFUSE |
| `authority_level` not in enum | `REJECT_UNKNOWN_AUTHORITY` | REFUSE |
| Hash mismatch | `REJECT_INTEGRITY_FAIL` | REFUSE |

---

## ARTIFACT TYPE 004: INCIDENT_REPORT

### Name
`INCIDENT_REPORT`

### Description
Postmortem or outage analysis documenting failure chains.

### Required Metadata Fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `artifact_id` | string | YES | Unique identifier |
| `artifact_type` | enum | YES | Must be `INCIDENT_REPORT` |
| `incident_id` | string | YES | Original incident identifier |
| `source_organization` | string | YES | Organization that published |
| `source_url` | string | YES | Public URL of report |
| `retrieved_at` | ISO8601 | YES | Timestamp of retrieval |
| `sha256_hash` | string(64) | YES | Content hash |
| `incident_date` | ISO8601 | YES | When incident occurred |
| `publication_date` | ISO8601 | YES | When report was published |
| `severity` | enum | YES | `SEV1`, `SEV2`, `SEV3`, `SEV4` |
| `services_affected` | array[string] | YES | List of affected services |
| `root_cause_identified` | boolean | YES | Whether root cause was found |

### Accepted Formats
| Format | Extension | Parser Required |
|--------|-----------|-----------------|
| Markdown | `.md` | incident-md-parser |
| HTML (public page) | `.html` | incident-html-parser |
| Structured JSON | `.json` | incident-json-parser |

### Rejection Conditions
| Condition | Rejection Code | Action |
|-----------|----------------|--------|
| Missing `incident_date` | `REJECT_NO_INCIDENT_DATE` | REFUSE |
| Missing `source_organization` | `REJECT_NO_ORG` | REFUSE |
| `services_affected` empty | `REJECT_NO_AFFECTED_SERVICES` | REFUSE |
| Non-public source URL | `REJECT_NON_PUBLIC` | REFUSE |
| No severity classification | `REJECT_NO_SEVERITY` | REFUSE |
| Hash mismatch | `REJECT_INTEGRITY_FAIL` | REFUSE |

---

## ARTIFACT TYPE 005: VERSION_HISTORY

### Name
`VERSION_HISTORY`

### Description
Changelog or release history documenting version evolution.

### Required Metadata Fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `artifact_id` | string | YES | Unique identifier |
| `artifact_type` | enum | YES | Must be `VERSION_HISTORY` |
| `package_name` | string | YES | Name of versioned component |
| `source_url` | string | YES | Retrieval location |
| `retrieved_at` | ISO8601 | YES | Timestamp of retrieval |
| `sha256_hash` | string(64) | YES | Content hash |
| `version_count` | integer | YES | Number of versions documented |
| `earliest_version` | string | YES | Oldest version in history |
| `latest_version` | string | YES | Newest version in history |
| `versioning_scheme` | enum | YES | `SEMVER`, `CALVER`, `CUSTOM` |
| `deprecation_notices` | integer | YES | Count of deprecation entries |

### Accepted Formats
| Format | Extension | Parser Required |
|--------|-----------|-----------------|
| CHANGELOG.md | `.md` | changelog-md-parser |
| HISTORY.rst | `.rst` | changelog-rst-parser |
| Release JSON (GitHub) | `.json` | github-releases-parser |
| npm versions | `.json` | npm-versions-parser |

### Rejection Conditions
| Condition | Rejection Code | Action |
|-----------|----------------|--------|
| Missing `versioning_scheme` | `REJECT_NO_VERSION_SCHEME` | REFUSE |
| `version_count` = 0 | `REJECT_EMPTY_HISTORY` | REFUSE |
| No `latest_version` | `REJECT_NO_LATEST` | REFUSE |
| Hash mismatch | `REJECT_INTEGRITY_FAIL` | REFUSE |

---

## ARTIFACT TYPE 006: AUTHORITY_DECLARATION

### Name
`AUTHORITY_DECLARATION`

### Description
Documents decision rights, RBAC policies, or governance hierarchies.

### Required Metadata Fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `artifact_id` | string | YES | Unique identifier |
| `artifact_type` | enum | YES | Must be `AUTHORITY_DECLARATION` |
| `scope` | string | YES | What the authority covers |
| `source_url` | string | YES | Retrieval location |
| `retrieved_at` | ISO8601 | YES | Timestamp of retrieval |
| `sha256_hash` | string(64) | YES | Content hash |
| `authority_type` | enum | YES | `RBAC`, `ABAC`, `ADR`, `POLICY`, `GOVERNANCE` |
| `effective_date` | ISO8601 | YES | When authority became effective |
| `issuing_authority` | string | YES | Who declared the authority |
| `role_count` | integer | NO | Number of roles (if RBAC/ABAC) |
| `decision_count` | integer | NO | Number of decisions (if ADR) |

### Accepted Formats
| Format | Extension | Parser Required |
|--------|-----------|-----------------|
| Kubernetes RBAC | `.yaml` | k8s-rbac-parser |
| ADR Markdown | `.md` | adr-md-parser |
| IAM Policy JSON | `.json` | iam-policy-parser |
| OPA Rego | `.rego` | opa-rego-parser |

### Rejection Conditions
| Condition | Rejection Code | Action |
|-----------|----------------|--------|
| Missing `authority_type` | `REJECT_NO_AUTH_TYPE` | REFUSE |
| Missing `effective_date` | `REJECT_NO_EFFECTIVE_DATE` | REFUSE |
| Missing `issuing_authority` | `REJECT_NO_ISSUER` | REFUSE |
| Hash mismatch | `REJECT_INTEGRITY_FAIL` | REFUSE |
| `effective_date` in future | `REJECT_FUTURE_DATED` | REFUSE |

---

## ARTIFACT TYPE 007: SPECIFICATION_DOCUMENT

### Name
`SPECIFICATION_DOCUMENT`

### Description
Formal technical specification (RFC, standard, protocol definition).

### Required Metadata Fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `artifact_id` | string | YES | Unique identifier |
| `artifact_type` | enum | YES | Must be `SPECIFICATION_DOCUMENT` |
| `spec_type` | enum | YES | `RFC`, `ISO`, `W3C`, `ECMA`, `IEEE` |
| `spec_number` | string | YES | Official specification number |
| `title` | string | YES | Specification title |
| `source_url` | string | YES | Official source URL |
| `retrieved_at` | ISO8601 | YES | Timestamp of retrieval |
| `sha256_hash` | string(64) | YES | Content hash |
| `publication_date` | ISO8601 | YES | Official publication date |
| `status` | enum | YES | `DRAFT`, `PROPOSED`, `STANDARD`, `OBSOLETE` |
| `obsoletes` | array[string] | NO | Spec numbers this obsoletes |
| `obsoleted_by` | string | NO | Spec number that obsoletes this |

### Accepted Formats
| Format | Extension | Parser Required |
|--------|-----------|-----------------|
| RFC text | `.txt` | rfc-text-parser |
| RFC XML | `.xml` | rfc-xml-parser |
| ISO PDF | `.pdf` | iso-pdf-parser |
| W3C HTML | `.html` | w3c-html-parser |

### Rejection Conditions
| Condition | Rejection Code | Action |
|-----------|----------------|--------|
| Non-official `source_url` | `REJECT_UNOFFICIAL_SOURCE` | REFUSE |
| Missing `spec_number` | `REJECT_NO_SPEC_NUMBER` | REFUSE |
| Missing `publication_date` | `REJECT_NO_PUB_DATE` | REFUSE |
| `status` = `OBSOLETE` without `obsoleted_by` | `REJECT_INCOMPLETE_OBSOLETE` | REFUSE |
| Hash mismatch | `REJECT_INTEGRITY_FAIL` | REFUSE |

---

## UNIVERSAL REJECTION CONDITIONS

These apply to ALL artifact types:

| Condition | Rejection Code | Description |
|-----------|----------------|-------------|
| Missing `artifact_id` | `REJECT_NO_ID` | Every artifact must be uniquely identified |
| Missing `artifact_type` | `REJECT_NO_TYPE` | Type must be explicitly declared |
| Missing `sha256_hash` | `REJECT_NO_HASH` | Integrity verification required |
| Missing `retrieved_at` | `REJECT_NO_TIMESTAMP` | Provenance timestamp required |
| Hash verification failure | `REJECT_INTEGRITY_FAIL` | Content does not match declared hash |
| Unsupported format | `REJECT_UNKNOWN_FORMAT` | No parser available |
| Schema validation failure | `REJECT_SCHEMA_INVALID` | Metadata does not match schema |

---

## PIE ARTIFACT ACCEPTANCE FLOW

```
┌─────────────────────────────────────────────────────────┐
│              PIE ARTIFACT ACCEPTANCE                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [Artifact Submitted]                                    │
│         │                                                │
│         ▼                                                │
│  ┌─────────────────┐                                     │
│  │ Has artifact_id? │──NO──► REJECT_NO_ID               │
│  └────────┬────────┘                                     │
│           │ YES                                          │
│           ▼                                              │
│  ┌─────────────────┐                                     │
│  │ Has artifact_type?│──NO──► REJECT_NO_TYPE            │
│  └────────┬────────┘                                     │
│           │ YES                                          │
│           ▼                                              │
│  ┌─────────────────┐                                     │
│  │ Type recognized? │──NO──► REJECT_UNKNOWN_TYPE        │
│  └────────┬────────┘                                     │
│           │ YES                                          │
│           ▼                                              │
│  ┌─────────────────┐                                     │
│  │ Has sha256_hash?│──NO──► REJECT_NO_HASH              │
│  └────────┬────────┘                                     │
│           │ YES                                          │
│           ▼                                              │
│  ┌─────────────────┐                                     │
│  │ Hash matches?   │──NO──► REJECT_INTEGRITY_FAIL       │
│  └────────┬────────┘                                     │
│           │ YES                                          │
│           ▼                                              │
│  ┌─────────────────┐                                     │
│  │ Type-specific   │──FAIL──► REJECT_{specific_code}    │
│  │ validation      │                                     │
│  └────────┬────────┘                                     │
│           │ PASS                                         │
│           ▼                                              │
│      [ACCEPTED]                                          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

**PIE: Schema defined. No content analyzed. No data ingested.**

**Version:** 1.0.0
**State:** ENGINEERING_OBSERVER_STATE
