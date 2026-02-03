# OPERATIONS LAYER

**Authority:** 11.0 SOVEREIGN
**Classification:** Operations

---

## PURPOSE

The Operations layer provides **deployment, monitoring, and maintenance** capabilities for Echo Prime Cloud.

**Philosophy:** Ops enables. Ops monitors. Ops automates.

---

## COMPONENTS

| Component | Purpose |
|-----------|---------|
| **Deployment** | Container orchestration, CI/CD |
| **Monitoring** | Health checks, metrics, alerts |
| **Maintenance** | Backups, rotation, cleanup |
| **Disaster Recovery** | Failover, restoration |

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         OPERATIONS LAYER                                 │
│                                                                          │
│   ┌────────────────────────────────────────────────────────────────┐    │
│   │                      DEPLOYMENT                                 │    │
│   │                                                                 │    │
│   │   Kubernetes │ Helm Charts │ CI/CD │ Blue-Green │ Canary       │    │
│   └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│   ┌────────────────────────────────────────────────────────────────┐    │
│   │                      MONITORING                                 │    │
│   │                                                                 │    │
│   │   Prometheus │ Grafana │ Alerts │ Logs │ Traces                │    │
│   └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│   ┌────────────────────────────────────────────────────────────────┐    │
│   │                     MAINTENANCE                                 │    │
│   │                                                                 │    │
│   │   Backups │ Key Rotation │ Log Cleanup │ Index Maintenance     │    │
│   └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│   ┌────────────────────────────────────────────────────────────────┐    │
│   │                  DISASTER RECOVERY                              │    │
│   │                                                                 │    │
│   │   Failover │ Restoration │ RTO/RPO │ Runbooks                  │    │
│   └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## DEPLOYMENT

### Container Architecture

| Component | Image | Replicas | Resources |
|-----------|-------|----------|-----------|
| API Gateway | `echo-prime/api:latest` | 2-5 | 2 CPU, 4GB |
| TIE Engine | `echo-prime/tie:latest` | 1-3 | 4 CPU, 8GB |
| LIE Engine | `echo-prime/lie:latest` | 1-3 | 4 CPU, 8GB |
| LANDMAN | `echo-prime/landman:latest` | 1-3 | 4 CPU, 8GB |
| Memory Service | `echo-prime/memory:latest` | 2 | 4 CPU, 16GB |
| 343 GS | `echo-prime/343gs:latest` | 1 | 2 CPU, 4GB |
| ASF | `echo-prime/asf:latest` | 1 | 2 CPU, 4GB |

### CI/CD Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CI/CD PIPELINE                                   │
│                                                                          │
│   ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐       │
│   │  Push  │──▶│  Test  │──▶│ Build  │──▶│ Stage  │──▶│  Prod  │       │
│   └────────┘   └────────┘   └────────┘   └────────┘   └────────┘       │
│       │            │            │            │            │              │
│       ▼            ▼            ▼            ▼            ▼              │
│   [Lint]      [Unit]       [Docker]    [Canary]    [Blue-Green]        │
│   [Format]    [Integration] [Push]     [Smoke]     [Full Deploy]       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## MONITORING

### Metrics (Prometheus)

| Metric | Type | Purpose |
|--------|------|---------|
| `api_requests_total` | Counter | Request count |
| `api_latency_seconds` | Histogram | Response time |
| `engine_processing_seconds` | Histogram | Engine time |
| `memory_queries_total` | Counter | Memory ops |
| `archive_operations_total` | Counter | Storage ops |
| `error_rate` | Gauge | Error percentage |

### Dashboards (Grafana)

| Dashboard | Metrics |
|-----------|---------|
| API Health | Requests, latency, errors |
| Engine Performance | Processing time, queue depth |
| Memory Layer | Queries, cache hits, size |
| Archive Layer | Write rate, storage used |
| Billing | Usage, revenue, customers |

### Alerting

| Alert | Condition | Severity |
|-------|-----------|----------|
| High Error Rate | > 5% | Critical |
| High Latency | > 2s p99 | Warning |
| Memory Full | > 90% | Critical |
| Engine Unhealthy | Failed health check | Critical |
| Storage Quota | > 80% | Warning |

---

## MAINTENANCE

### Scheduled Tasks

| Task | Frequency | Description |
|------|-----------|-------------|
| Backup | Daily | Full system backup |
| Key Rotation | Quarterly | Rotate KEKs |
| Log Cleanup | Weekly | Archive old logs |
| Index Rebuild | Monthly | Optimize indexes |
| Health Check | Every minute | Component health |

### Backup Strategy

| Data | RPO | RTO | Method |
|------|-----|-----|--------|
| Vault secrets | 0 | 1h | Real-time replication |
| Memory | 1h | 4h | Hourly snapshots |
| Archive | 24h | 8h | Daily B2 sync |
| Logs | 24h | 24h | Daily archive |

### Log Retention

| Log Type | Hot | Warm | Cold |
|----------|-----|------|------|
| API | 7 days | 30 days | 1 year |
| Engine | 7 days | 30 days | 1 year |
| Audit | 30 days | 1 year | 7 years |
| Security | 30 days | 1 year | 7 years |

---

## DISASTER RECOVERY

### Recovery Objectives

| Metric | Target |
|--------|--------|
| RTO (Recovery Time Objective) | 4 hours |
| RPO (Recovery Point Objective) | 1 hour |
| Availability Target | 99.9% |

### Failover Procedures

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      FAILOVER PROCEDURE                                  │
│                                                                          │
│   1. Detect failure (automated monitoring)                              │
│   2. Isolate failed component                                           │
│   3. Activate standby (if available)                                    │
│   4. Restore from backup (if needed)                                    │
│   5. Verify integrity                                                   │
│   6. Resume traffic                                                     │
│   7. Post-incident analysis                                             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Runbooks

| Scenario | Runbook |
|----------|---------|
| API outage | `runbooks/api-recovery.md` |
| Engine failure | `runbooks/engine-recovery.md` |
| Memory corruption | `runbooks/memory-recovery.md` |
| Vault unavailable | `runbooks/vault-recovery.md` |
| Cloud provider outage | `runbooks/cloud-failover.md` |

---

## INVARIANTS

| Invariant | Enforcement |
|-----------|-------------|
| **Backups tested monthly** | Restoration drill |
| **No single point of failure** | Replication |
| **All changes audited** | GitOps |
| **Rollback always possible** | Version control |

---

## SECURITY NOTES

### Access Control

| Role | Deployment | Monitoring | Maintenance |
|------|------------|------------|-------------|
| Sovereign | Full | Full | Full |
| Operator | Deploy | View | Limited |
| Developer | None | View | None |
| Customer | None | None | None |

### Secrets Management

- All secrets in Vault
- No secrets in config files
- No secrets in environment variables (except for bootstrap)
- Rotate on compromise

---

**Document Version:** 1.0.0
**Created:** 2026-02-03
