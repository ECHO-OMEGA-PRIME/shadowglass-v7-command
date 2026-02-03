# ECHO PRIME CLOUD — COST MODEL

**Storage + Compute Economics**
**Authority:** 11.0 SOVEREIGN

---

## EXECUTIVE SUMMARY

Echo Prime Cloud is designed for cost-efficient operation at scale:

- **Storage:** ~$6/TB/month (Backblaze B2)
- **Compute:** Pay-per-use containerized
- **Bandwidth:** Minimal egress (local caching)
- **Target:** 50-100TB at $300-600/month storage

---

## STORAGE COSTS

### Tier Economics

| Tier | Provider | Cost/TB/Month | Retrieval | Use Case |
|------|----------|---------------|-----------|----------|
| HOT | Local NVMe | $0 (owned) | Instant | Active processing |
| WARM | Local HDD | $0 (owned) | Fast | Recent artifacts |
| COLD | Backblaze B2 | $6 | Minutes | Standard archive |
| DEEP | Backblaze B2 | $6 | Minutes | Permanent custody |

### Backblaze B2 Pricing (Current)

| Item | Cost |
|------|------|
| Storage | $0.006/GB/month ($6/TB) |
| Download | $0.01/GB (first 1GB/day free) |
| API Class A | $0.004/10,000 calls |
| API Class B | $0.004/10,000 calls |
| API Class C | Free |

### Storage Projections

| Scenario | Raw Data | After Dedup | After Compress | Monthly Cost |
|----------|----------|-------------|----------------|--------------|
| Current | 50 TB | 40 TB | 28 TB | ~$168 |
| Growth 1Y | 100 TB | 80 TB | 56 TB | ~$336 |
| Growth 3Y | 250 TB | 200 TB | 140 TB | ~$840 |
| Growth 5Y | 500 TB | 400 TB | 280 TB | ~$1,680 |

**Assumptions:**
- 20% deduplication ratio
- 30% compression ratio (zstd-19)
- No significant egress (local caching)

---

## COMPUTE COSTS

### Container Sizing

| Component | CPU | Memory | Instances | Notes |
|-----------|-----|--------|-----------|-------|
| API Gateway | 2 | 4 GB | 2-5 | Auto-scale |
| TIE Engine | 4 | 8 GB | 1-3 | CPU-bound |
| LIE Engine | 4 | 8 GB | 1-3 | CPU-bound |
| LANDMAN | 4 | 8 GB | 1-3 | CPU-bound |
| PIE Engine | 2 | 4 GB | 1-2 | Light |
| Memory Service | 4 | 16 GB | 2 | Memory-bound |
| 343 Guilty Spark | 2 | 4 GB | 1 | Stateless |
| GS343 Analysis | 2 | 4 GB | 1 | Periodic |

### Cloud Compute Estimates (GCP/AWS/Azure)

| Configuration | Monthly Est. | Notes |
|---------------|--------------|-------|
| Minimum (dev) | $200-400 | 2-3 small instances |
| Standard | $800-1,200 | Production baseline |
| Scale | $2,000-5,000 | Multi-engine, HA |
| Enterprise | $10,000+ | Full redundancy |

---

## BANDWIDTH COSTS

### Egress Strategy

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       BANDWIDTH OPTIMIZATION                             │
│                                                                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  Customer Request                                                │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                │                                         │
│                                ▼                                         │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  Local Cache (Memory Layer)                     [HIT = $0]      │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                │ (miss)                                  │
│                                ▼                                         │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  Hot/Warm Local Storage                         [HIT = $0]      │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                │ (miss)                                  │
│                                ▼                                         │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  Cloud Retrieval (B2)                        [COST = $0.01/GB]  │   │
│   │  - Retrieve once                                                 │   │
│   │  - Cache locally                                                 │   │
│   │  - Serve from cache                                             │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Expected Egress Costs

| Pattern | Monthly Egress | Cost |
|---------|----------------|------|
| Normal ops | ~100 GB | ~$1 |
| Heavy retrieval | ~1 TB | ~$10 |
| Disaster recovery | ~10 TB | ~$100 |
| Full restore | ~50 TB | ~$500 |

---

## TOTAL COST OF OWNERSHIP

### 50 TB Deployment

| Category | Monthly | Annual |
|----------|---------|--------|
| Storage (B2) | $200 | $2,400 |
| Compute | $1,000 | $12,000 |
| Bandwidth | $10 | $120 |
| Monitoring | $50 | $600 |
| **Total** | **$1,260** | **$15,120** |

### 100 TB Deployment

| Category | Monthly | Annual |
|----------|---------|--------|
| Storage (B2) | $400 | $4,800 |
| Compute | $1,500 | $18,000 |
| Bandwidth | $20 | $240 |
| Monitoring | $100 | $1,200 |
| **Total** | **$2,020** | **$24,240** |

---

## COST OPTIMIZATION STRATEGIES

### 1. Deduplication
- Global hash index prevents duplicate storage
- Expected savings: 15-30%

### 2. Compression
- zstd compression by tier
- Expected savings: 20-40%

### 3. Tiering
- Automatic lifecycle migration
- Hot → Warm → Cold → Deep
- Minimizes cloud storage costs

### 4. Caching
- Aggressive local caching
- Minimizes egress costs
- Improves latency

### 5. Reserved Capacity
- For predictable workloads
- 30-50% savings on compute

---

## REVENUE MODEL (API Monetization)

### Pricing Tiers

| Tier | Queries/Month | Price/Month | Gross Margin |
|------|---------------|-------------|--------------|
| Starter | 1,000 | $99 | ~90% |
| Professional | 10,000 | $499 | ~85% |
| Enterprise | 100,000 | $2,999 | ~80% |
| Custom | Unlimited | Negotiated | ~70% |

### Product Bundles

| Bundle | Components | Price | Target |
|--------|------------|-------|--------|
| Title Report | LANDMAN + ENCORE | $50/report | Land professionals |
| Tax Defense | TIE + LIE | $200/analysis | CPAs, attorneys |
| Legal Research | LIE + ARCS | $100/query | Law firms |
| Full Platform | All engines | Custom | Enterprise |

### Break-Even Analysis

| Storage Size | TCO/Month | Break-Even Customers |
|--------------|-----------|---------------------|
| 50 TB | $1,260 | 13 @ Professional |
| 100 TB | $2,020 | 21 @ Professional |
| 250 TB | $4,000 | 41 @ Professional |

---

## COMPARISON: CLOUD VS LOCAL

| Factor | Local Only | Cloud Only | Hybrid (Current) |
|--------|------------|------------|------------------|
| Capital | High | None | Medium |
| Operating | Low | Medium | Low |
| Scalability | Limited | Unlimited | Best of both |
| Disaster Recovery | Expensive | Built-in | Built-in |
| Latency | Best | Variable | Good |
| **Recommendation** | — | — | **✓ OPTIMAL** |

---

**Document Version:** 1.0.0
**Created:** 2026-02-03
