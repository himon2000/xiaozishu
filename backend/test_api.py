#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试小紫薯后端API"""
import requests
import json

BASE_URL = "http://localhost:8001"

def test_demo_login(role="provider"):
    """测试演示登录"""
    resp = requests.post(
        f"{BASE_URL}/api/v1/auth/demo-login",
        json={"role": role},
        timeout=10
    )
    print(f"\n=== Demo Login ({role}) ===")
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), ensure_ascii=False, indent=2)}")
    return resp.json()

def test_health():
    """测试健康检查"""
    resp = requests.get(f"{BASE_URL}/health", timeout=10)
    print(f"\n=== Health Check ===")
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")

def test_services():
    """测试服务列表"""
    resp = requests.get(f"{BASE_URL}/api/v1/services", timeout=10)
    print(f"\n=== Services ===")
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), ensure_ascii=False, indent=2)}")

def test_level_config():
    """测试境界配置"""
    resp = requests.get(f"{BASE_URL}/api/v1/level/config", timeout=10)
    print(f"\n=== Level Config ===")
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), ensure_ascii=False, indent=2)}")

if __name__ == "__main__":
    print("[TEST] Xiao Zi Shu API Test")
    print("=" * 40)

    try:
        test_health()
        test_level_config()
        test_demo_login("seeker")
        test_demo_login("provider")
        test_demo_login("elder")
        test_services()
        print("\n✅ 所有测试完成!")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
