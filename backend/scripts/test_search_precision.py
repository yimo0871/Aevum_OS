"""搜索精度测试 - 验证火山引擎 embedding 是否生效."""
import httpx
import uuid

BASE = "http://localhost:8000"
s = uuid.uuid4().hex[:8]

# 用户A注册 + 创建public经验
ra = httpx.post(f"{BASE}/api/v1/auth/register", json={"email": f"a{s}@t.com", "username": f"alice{s}", "password": "Test1234!"})
ta = ra.json()["access_token"]
re = httpx.post(f"{BASE}/api/v1/experiences", json={
    "context": {"domain": "后端开发", "task_type": "方案规划", "constraints": {}},
    "intent": "Python性能优化最佳实践",
    "outcome": {"success": True, "metrics": {}},
    "execution": {"steps": [{"name": "分析"}], "tools": ["cProfile"], "trace": {}},
    "reflection": {"what_worked": ["异步处理"], "what_failed": [], "why": "提高了并发"},
    "confidence_score": 0.9,
    "visibility": "public",
}, headers={"Authorization": f"Bearer {ta}"})
eid = re.json()["id"]
print(f"Created: id={eid[:8]}, intent={re.json()['intent']}")

# 用户B注册 + 搜索
rb = httpx.post(f"{BASE}/api/v1/auth/register", json={"email": f"b{s}@t.com", "username": f"bob{s}", "password": "Test1234!"})
tb = rb.json()["access_token"]
rs = httpx.post(f"{BASE}/api/v1/retrieval/search", json={"query": "Python性能优化", "limit": 10}, headers={"Authorization": f"Bearer {tb}"})
results = rs.json()
print(f"Search: {len(results)} results")
for r in results[:5]:
    exp = r.get("experience", {})
    print(f"  id={exp.get('id','')[:8]} intent={exp.get('intent','')[:30]} score={r.get('score',0):.3f}")

# 检查是否找到目标经验
target_found = any(r.get("experience", {}).get("id") == eid for r in results)
intent_found = any("Python" in r.get("experience", {}).get("intent", "") for r in results)
print(f"\nTarget ID found: {target_found}")
print(f"Intent 'Python' found in results: {intent_found}")
print(f"Result: {'🎉 火山引擎embedding搜索精度验证通过!' if target_found else '⚠️ 目标经验未在Top10中'}")
