"""Phase 2 API 测试"""
import sys
sys.path.insert(0, ".")
from main import app
from fastapi.testclient import TestClient
from models import init_db

init_db()
client = TestClient(app)

tests = [
    ("GET", "/health", None),
    ("GET", "/api/v1/resources", None),
    ("GET", "/api/v1/resources/school-guides", None),
    ("GET", "/api/v1/mentorships/mentors", None),
    ("GET", "/api/v1/level/config", None),
]

passed = 0
for method, path, body in tests:
    r = client.get(path)
    ok = r.status_code == 200
    if ok:
        passed += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {method} {path} -> {r.status_code}")
    if not ok:
        print("   ERROR:", r.json())

print(f"\n{passed}/{len(tests)} 测试通过")
