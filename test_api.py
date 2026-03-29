#!/usr/bin/env python3
"""
测试 API 接口
"""
import requests
import json

print("测试 API 接口...")

try:
    # 测试首页
    print("\n[1] 测试首页 GET /")
    resp = requests.get('http://localhost:5050/', timeout=5)
    print(f"状态码: {resp.status_code}")
    
    # 测试运行接口
    print("\n[2] 测试运行 POST /api/run")
    print("开始运行（这可能需要几分钟）...")
    resp = requests.post('http://localhost:5050/api/run', timeout=600)
    print(f"状态码: {resp.status_code}")
    data = resp.json()
    print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
except requests.exceptions.Timeout:
    print("✗ 请求超时（10分钟）")
except requests.exceptions.ConnectionError:
    print("✗ 连接失败，请检查服务器是否启动")
except Exception as e:
    print(f"✗ 发生错误: {e}")
