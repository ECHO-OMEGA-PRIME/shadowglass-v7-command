# API LAYER

**Authority:** 11.0 SOVEREIGN
**Classification:** Monetization Gateway

---

## PURPOSE

The API Layer is the **monetization gateway** for Echo Prime Cloud. It provides authenticated, metered, rate-limited access to engine capabilities. No raw data ever leaves this layer.

**Philosophy:** API is the product. API is metered. API never leaks raw data.

---

## COMPONENTS

| Component | Purpose |
|-----------|---------|
| **Auth Gateway** | OAuth 2.0 / API key authentication |
| **Rate Limiter** | Request throttling by tier |
| **Billing Hooks** | Usage tracking for monetization |
| **Customer Interfaces** | Scoped API endpoints |

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           API LAYER                                      │
│                                                                          │
│   ┌────────────────────────────────────────────────────────────────┐    │
│   │                      AUTH GATEWAY                               │    │
│   │                                                                 │    │
│   │   OAuth 2.0 │ API Keys │ JWT Tokens │ mTLS (Enterprise)        │    │
│   └────────────────────────────────────────────────────────────────┘    │
│                              │                                           │
│   ┌────────────────────────────────────────────────────────────────┐    │
│   │                     RATE LIMITER                                │    │
│   │                                                                 │    │
│   │   Starter: 100/hour │ Pro: 1000/hour │ Enterprise: Custom      │    │
│   └────────────────────────────────────────────────────────────────┘    │
│                              │                                           │
│   ┌────────────────────────────────────────────────────────────────┐    │
│   │                    BILLING HOOKS                                │    │
│   │                                                                 │    │
│   │   Usage Tracking │ Metering │ Invoice Generation               │    │
│   └────────────────────────────────────────────────────────────────┘    │
│                              │                                           │
│   ┌────────────────────────────────────────────────────────────────┐    │
│   │                 CUSTOMER INTERFACES                             │    │
│   │                                                                 │    │
│   │   /tax/* │ /legal/* │ /land/* │ /title/* │ /analysis/*        │    │
│   └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│   NEVER EXPOSES: Raw data │ Archive access │ Internal endpoints        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## INPUTS

| Input | Source | Format |
|-------|--------|--------|
| API requests | Customers | HTTPS |
| Auth credentials | Customers | OAuth/API Key |
| Engine responses | Engines | Structured JSON |

---

## OUTPUTS

| Output | Destination | Format |
|--------|-------------|--------|
| API responses | Customers | JSON |
| Usage metrics | Billing | Events |
| Audit logs | Vault | JSONL |

---

## INVARIANTS

| Invariant | Enforcement |
|-----------|-------------|
| **All requests authenticated** | Auth middleware |
| **All requests metered** | Billing hooks |
| **All requests rate-limited** | Rate limiter |
| **No raw data exposure** | Response filtering |
| **Customer scoping enforced** | Access control |

---

## AUTHENTICATION

### Methods

| Method | Use Case | Security |
|--------|----------|----------|
| API Key | Simple integrations | Rotate quarterly |
| OAuth 2.0 | Web applications | Standard flow |
| JWT | Session-based | Short expiry |
| mTLS | Enterprise | Certificate-based |

### Token Format

```json
{
  "sub": "customer_id",
  "iss": "echo-prime",
  "scope": ["tax:read", "legal:read"],
  "tier": "professional",
  "exp": 1706918400,
  "rate_limit": 1000
}
```

---

## RATE LIMITING

| Tier | Requests/Hour | Burst | Overage |
|------|---------------|-------|---------|
| Starter | 100 | 20 | Block |
| Professional | 1,000 | 100 | Throttle |
| Enterprise | 10,000 | 1,000 | Throttle |
| Custom | Negotiated | Negotiated | Negotiated |

### Response Headers

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 847
X-RateLimit-Reset: 1706918400
```

---

## PRICING TIERS

| Tier | Queries/Month | Price/Month | Features |
|------|---------------|-------------|----------|
| Starter | 1,000 | $99 | Basic access |
| Professional | 10,000 | $499 | Priority support |
| Enterprise | 100,000 | $2,999 | Dedicated support |
| Custom | Unlimited | Negotiated | Custom SLA |

### Product Bundles

| Bundle | Components | Price | Target |
|--------|------------|-------|--------|
| Title Report | LANDMAN + ENCORE | $50/report | Land professionals |
| Tax Defense | TIE + LIE | $200/analysis | CPAs, attorneys |
| Legal Research | LIE + ARCS | $100/query | Law firms |
| Full Platform | All engines | Custom | Enterprise |

---

## API ENDPOINTS

### Tax Intelligence (TIE)

```http
POST /api/v1/tax/analyze
Authorization: Bearer {token}
Content-Type: application/json

{
  "type": "position_analysis",
  "data": {
    "transaction": "vehicle_purchase",
    "amount": 75000,
    "usage": "business",
    "year": 2025
  }
}

Response:
{
  "analysis_id": "uuid",
  "conclusion": "QUALIFIED",
  "confidence": 0.95,
  "authorities": [...],
  "recommendations": [...]
}
```

### Legal Intelligence (LIE)

```http
POST /api/v1/legal/research
Authorization: Bearer {token}

{
  "topic": "oil_gas_lease_termination",
  "jurisdiction": "TX",
  "depth": "comprehensive"
}

Response:
{
  "research_id": "uuid",
  "summary": "...",
  "cases": [...],
  "statutes": [...]
}
```

### Land Intelligence (LANDMAN)

```http
POST /api/v1/land/chain
Authorization: Bearer {token}

{
  "legal_description": "Section 15, Block A-42, PSL Survey",
  "county": "Midland",
  "state": "TX",
  "chain_type": "mineral"
}

Response:
{
  "chain_id": "uuid",
  "current_owners": [...],
  "conveyances": [...],
  "encumbrances": [...]
}
```

### Title Reports (ENCORE)

```http
POST /api/v1/title/surface
Authorization: Bearer {token}

{
  "legal_description": "...",
  "search_depth": "30_year"
}

Response:
{
  "title_id": "uuid",
  "status": "CLEAR",
  "owners": [...],
  "exceptions": [...]
}
```

---

## RESPONSE FILTERING

The API layer **never exposes raw data**. All responses are:

1. **Scoped** - Only data customer has access to
2. **Filtered** - Internal fields removed
3. **Summarized** - Raw sources not exposed
4. **Attributed** - Provenance included

### Example: Raw vs API Response

**Raw (Internal):**
```json
{
  "hash": "sha256:abc123...",
  "storage_uri": "asf://cold/abc123...",
  "internal_score": 0.973,
  "debug_trace": [...],
  "raw_text": "..."
}
```

**API (External):**
```json
{
  "id": "uuid",
  "conclusion": "QUALIFIED",
  "confidence": 0.95,
  "sources": ["IRC § 162", "Treas. Reg. § 1.162-1"]
}
```

---

## FAILURE MODES

| Failure | Detection | Response | Recovery |
|---------|-----------|----------|----------|
| Auth failure | Invalid token | 401 Unauthorized | Re-authenticate |
| Rate exceeded | Counter | 429 Too Many Requests | Wait |
| Engine timeout | Timer | 504 Gateway Timeout | Retry |
| Invalid input | Validation | 400 Bad Request | Fix input |
| Server error | Exception | 500 Internal Error | Retry |

### Error Response Format

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Request limit exceeded",
    "retry_after": 3600
  }
}
```

---

## SECURITY NOTES

### Data Protection

| Protection | Implementation |
|------------|----------------|
| TLS 1.3 | All connections |
| Input validation | Schema validation |
| Output filtering | No raw data |
| SQL injection | Parameterized queries |
| XSS | Output encoding |

### Audit Logging

All API calls logged:

```json
{
  "timestamp": "2026-02-03T06:30:00Z",
  "customer_id": "cust_123",
  "endpoint": "/api/v1/tax/analyze",
  "method": "POST",
  "status": 200,
  "duration_ms": 450,
  "metered_units": 1,
  "request_id": "uuid"
}
```

---

## SDK & DOCUMENTATION

### Official SDKs

| Language | Package |
|----------|---------|
| Python | `pip install echo-prime` |
| JavaScript | `npm install @echo-prime/sdk` |
| Go | `go get github.com/echo-prime/sdk` |
| Java | Maven: `com.echoprime:sdk` |

### Documentation

- API Reference: `https://docs.echo-op.com/api`
- Tutorials: `https://docs.echo-op.com/tutorials`
- Examples: `https://github.com/echo-prime/examples`

---

**Document Version:** 1.0.0
**Created:** 2026-02-03
