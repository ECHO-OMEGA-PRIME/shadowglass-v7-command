"""
PROGRAMMING INTELLIGENCE ENGINE - Server Launcher

Launches the PIE API on port 8390.

System Class: ISOLATED_REASONING_ENGINE
Governance Tier: ZERO
"""

import uvicorn
import asyncio
import requests
from pathlib import Path
from datetime import datetime
from loguru import logger

# Configure logging
log_path = Path(__file__).parent / "logs"
log_path.mkdir(exist_ok=True)
logger.add(log_path / "pie_{time}.log", rotation="100 MB")


def register_with_omniscient():
    """Register PIE with OMNISCIENT Sync."""
    try:
        response = requests.post(
            "https://omniscient-sync.bmcii1976.workers.dev/sessions/register",
            json={
                "instance_type": "programming_intelligence_engine",
                "system_class": "ISOLATED_REASONING_ENGINE",
                "governance_tier": "ZERO",
                "current_task": "PIE Server Operational",
                "port": 8390,
                "endpoints": [
                    "/engineering/query",
                    "/engineering/version-check",
                    "/engineering/migration-path",
                    "/engineering/conflict-resolution",
                    "/engineering/deprecation-alert",
                    "/engineering/authority-report"
                ],
                "capabilities": [
                    "authority_hierarchy",
                    "version_awareness",
                    "semantic_graph",
                    "deterministic_doctrine",
                    "drift_sentinel",
                    "document_ingestion"
                ]
            },
            timeout=10
        )
        if response.status_code == 200:
            logger.info("Registered with OMNISCIENT Sync")
            return response.json()
        else:
            logger.warning(f"OMNISCIENT registration returned: {response.status_code}")
    except Exception as e:
        logger.warning(f"Could not register with OMNISCIENT: {e}")
    return None


def submit_commander_insight():
    """Submit Commander insight to governance."""
    try:
        response = requests.post(
            "https://omniscient-sync.bmcii1976.workers.dev/governance/insight",
            json={
                "insight": "Code changes. Authority endures. Build systems that understand the difference.",
                "author": "Bobby Don McWilliams II",
                "context": "Programming Intelligence Engine deployment",
                "timestamp": datetime.now().isoformat(),
                "system": "PIE",
                "tier": "ZERO"
            },
            timeout=10
        )
        if response.status_code == 200:
            logger.info("Commander insight stored in governance")
    except Exception as e:
        logger.warning(f"Could not submit insight: {e}")


def main():
    """Launch the PIE server."""
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║     PROGRAMMING INTELLIGENCE ENGINE (PIE)                                 ║
║     System Class: ISOLATED_REASONING_ENGINE                               ║
║     Governance Tier: ZERO                                                 ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║     Four-Layer Cognitive Stack:                                           ║
║     ├── Layer 1: Authority Hierarchy Engine                               ║
║     ├── Layer 2: Version Awareness Engine                                 ║
║     ├── Layer 3: Semantic Engineering Graph                               ║
║     └── Layer 4: Deterministic Doctrine Engine                            ║
║                                                                           ║
║     REASONING_ISOLATION_PROTOCOL: ACTIVE                                  ║
║     No OMNISCIENT memory calls during cognition.                          ║
║                                                                           ║
║     "Code changes. Authority endures."                                    ║
║     — Commander Bobby Don McWilliams II                                   ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
    """)

    logger.info("Starting Programming Intelligence Engine...")

    # Register with OMNISCIENT
    register_with_omniscient()

    # Submit Commander insight
    submit_commander_insight()

    # Launch server
    uvicorn.run(
        "api.endpoints:app",
        host="0.0.0.0",
        port=8390,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()
