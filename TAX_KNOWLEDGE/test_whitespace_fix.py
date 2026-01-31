"""Quick test for whitespace normalization fix."""
import sys
sys.path.insert(0, "O:/ECHO_OMEGA_PRIME/TAX_KNOWLEDGE")
import requests

BASE_URL = "http://localhost:8391"

def query(q):
    try:
        r = requests.post(f"{BASE_URL}/tax/query", json={"question": q, "mode": "fast"}, timeout=30)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

print("=== WHITESPACE NORMALIZATION TEST ===\n")

# Test 1: Reasonable compensation with whitespace variants
variants = [
    "reasonable compensation",
    "reasonable  compensation",
    "  reasonable compensation  ",
    "reasonable\tcompensation",
]

print("Query: 'reasonable compensation' variants")
print("-" * 50)

results = []
for v in variants:
    r = query(v)
    match = r.get("doctrine_match", False)
    hash_val = r.get("determinism_hash", "N/A")
    results.append((v.replace("\t", "\\t"), match, hash_val))
    print(f"'{v.replace(chr(9), '\\t')[:30]}' -> match={match}, hash={hash_val}")

# Check consistency
matches = set(r[1] for r in results)
hashes = set(r[2] for r in results)

print("\n" + "=" * 50)
if len(matches) == 1 and list(matches)[0]:
    print("PASS: All variants match same doctrine")
else:
    print(f"FAIL: Inconsistent matches: {matches}")

if len(hashes) == 1:
    print(f"PASS: All hashes identical: {list(hashes)[0]}")
else:
    print(f"FAIL: Different hashes: {hashes}")
