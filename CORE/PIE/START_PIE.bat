@echo off
title PROGRAMMING INTELLIGENCE ENGINE - Tier ZERO
color 0A

echo.
echo ===============================================================================
echo    PROGRAMMING INTELLIGENCE ENGINE (PIE)
echo    System Class: ISOLATED_REASONING_ENGINE
echo    Governance Tier: ZERO
echo ===============================================================================
echo.
echo    Four-Layer Cognitive Stack:
echo    [1] Authority Hierarchy Engine
echo    [2] Version Awareness Engine
echo    [3] Semantic Engineering Graph
echo    [4] Deterministic Doctrine Engine
echo.
echo    REASONING_ISOLATION_PROTOCOL: ACTIVE
echo.
echo ===============================================================================
echo.

cd /d O:\ECHO_OMEGA_PRIME\CORE\PIE

echo Starting PIE Server on port 8390...
echo.

H:\Tools\PyManager\Python311\python.exe -m uvicorn api.endpoints:app --host 0.0.0.0 --port 8390 --reload

pause
