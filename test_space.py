import requests

base = "https://clonerbluff-sql-fixer-env.hf.space"
checks = []

# 1. Health
r = requests.get(f"{base}/health", timeout=30)
checks.append(("GET /health", r.status_code, r.status_code == 200))

# 2. POST /reset
r = requests.post(f"{base}/reset", json={}, timeout=30)
checks.append(("POST /reset", r.status_code, r.status_code == 200))
data = r.json()
obs = data.get("observation", {})
task_id = obs.get("task_id", "N/A")
broken = obs.get("broken_sql", "N/A")

# 3. GET /state
r = requests.get(f"{base}/state", timeout=30)
checks.append(("GET /state", r.status_code, r.status_code == 200))

# 4. GET /metadata
r = requests.get(f"{base}/metadata", timeout=30)
checks.append(("GET /metadata", r.status_code, r.status_code == 200))

# 5. GET /schema
r = requests.get(f"{base}/schema", timeout=30)
checks.append(("GET /schema", r.status_code, r.status_code == 200))

# 6. GET /openapi.json
r = requests.get(f"{base}/openapi.json", timeout=30)
checks.append(("GET /openapi.json", r.status_code, r.status_code == 200))

print("=== HF Space Validation ===")
for name, code, ok in checks:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name} -> {code}")

all_pass = all(ok for _, _, ok in checks)
print(f"\nAll checks passed: {all_pass}")
print(f"Task received: {task_id}")
print(f"Broken SQL: {broken[:50]}...")
