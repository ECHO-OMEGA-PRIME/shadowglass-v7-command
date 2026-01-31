# Test Authority Hardening
$body = @{
    question = "What is reasonable compensation for S-corp shareholders?"
    mode = "fast"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri 'http://localhost:8391/tax/query' -Method Post -Body $body -ContentType 'application/json'

Write-Host "=== AUTHORITY HARDENING TEST ==="
Write-Host ""
Write-Host "Doctrine Match: $($response.doctrine_match)"
Write-Host "Conflict Detected: $($response.conflict_detected)"
Write-Host "Authority Weight: $($response.authority_weight)"
Write-Host "Confidence Stratification: $($response.confidence_stratification)"
Write-Host "Controlling Precedent: $($response.controlling_precedent)"
Write-Host "Determinism Hash: $($response.determinism_hash)"
Write-Host "Latency: $($response.latency_ms) ms"
Write-Host "Version: $($response.version)"
Write-Host ""

if ($response.conflict_resolution) {
    Write-Host "=== CONFLICT RESOLUTION ==="
    Write-Host ($response.conflict_resolution | ConvertTo-Json -Depth 5)
}
