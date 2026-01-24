# ECHO OMEGA PRIME - SYSTEMS (Infrastructure Services)

**Authority:** 11.0 SOVEREIGN | **Commander:** Bobby Don McWilliams II

---

## Overview

SYSTEMS/ contains all infrastructure services that power ECHO OMEGA PRIME. These are the backend services that both SENTINEL (the brain) and APPS (user products) consume.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        SENTINEL                              │
│                    (The Brain / AI)                          │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                        SYSTEMS                               │
│                 (Infrastructure Services)                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │  GS343   │ │ PHOENIX  │ │PROMETHEUS│ │   BREE   │       │
│  │  Error   │ │  Healer  │ │ Security │ │  Trust   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│  ┌───────────────────┐ ┌────────────────────────────┐      │
│  │   MEGA-GATEWAY    │ │         BRIDGES            │      │
│  │   35,000+ Tools   │ │   Multi-AI Routing         │      │
│  └───────────────────┘ └────────────────────────────┘      │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                         APPS                                 │
│                  (User-Facing Products)                      │
│     CLOSER | Echo Clip | GameLoop | Website | etc.          │
└─────────────────────────────────────────────────────────────┘
```

---

## Systems

### GS343 - Divine Overseer
**Port:** 5003 | **Templates:** 45,962+

Error handling and healing system. Provides:
- Error pattern matching
- Auto-fix suggestions
- Error template database
- Integration with Phoenix for healing

```python
from SYSTEMS.gs343 import analyze_error
result = await analyze_error("ImportError: No module named 'foo'")
```

---

### PHOENIX - Auto-Healer
**Port:** 8046

Automatic healing and recovery system. Works with GS343 to:
- Apply fixes automatically
- Recover from crashes
- Self-heal the system

```python
from SYSTEMS.phoenix import heal
result = await heal(gs343_analysis)
```

---

### PROMETHEUS - Security & OSINT
**IP:** 192.168.1.202 | **Port:** 8370 | **Endpoints:** 319

Security operations and OSINT platform running on dedicated Kali box:
- Email verification (holehe)
- Phone lookup (phoneinfoga)
- Network scanning
- Vulnerability assessment
- 206 tools across 25 categories

```python
from SYSTEMS.prometheus import PrometheusClient
client = PrometheusClient()
result = await client.verify_email("test@example.com")
```

---

### BREE - Human Trust Database
**Port:** 8047

Human recognition and trust scoring:
- Face recognition
- Voice recognition
- Trust levels (0-11)
- Relationship tracking

```python
from SYSTEMS.bree import get_trust_level
level = await get_trust_level(user_id)
```

---

### MEGA-GATEWAY - MCP Tools
**Tools:** 35,000+ | **Servers:** 1,873

Unified gateway to all MCP (Model Context Protocol) tools:
- Tool search and discovery
- Cross-server execution
- 12 categories

```python
from SYSTEMS.mega_gateway import search, execute
tools = await search("github")
result = await execute("github_gateway_mcp", "create_issue", params)
```

---

### BRIDGES - Multi-AI Routing

Routes requests to multiple AI providers:
- Claude (Anthropic)
- GPT-4 (OpenAI)
- Gemini (Google)
- Groq, Together, SambaNova (fast inference)
- Ollama (local)

```python
from SYSTEMS.bridges import route
response = await route("query", provider="groq", model="llama-3.3-70b")
```

---

## Service Ports

| System | Port | Status |
|--------|------|--------|
| GS343 | 5003 | Local |
| Phoenix | 8046 | Local |
| PROMETHEUS | 8370 | 192.168.1.202 |
| Bree | 8047 | Local |
| MEGA-GATEWAY | 8500 | Local |
| Bridges | 8600 | Local |

---

## Integration Pattern

All APPS and SENTINEL components should use SYSTEMS through the standard client pattern:

```python
# Standard import pattern
from SYSTEMS.gs343 import GS343Client
from SYSTEMS.phoenix import PhoenixClient
from SYSTEMS.prometheus import PrometheusClient
from SYSTEMS.bree import BreeClient
from SYSTEMS.mega_gateway import MegaGatewayClient
from SYSTEMS.bridges import AIBridgeClient

# Usage
async def handle_error(error: Exception):
    # 1. Analyze with GS343
    analysis = await GS343Client().analyze(str(error))

    # 2. Heal with Phoenix
    if analysis.healable:
        await PhoenixClient().heal(analysis)

    # 3. Log to trust system
    await BreeClient().log_event("error_handled", analysis)
```

---

*ECHO OMEGA PRIME | Authority 11.0 | SYSTEMS INFRASTRUCTURE*
