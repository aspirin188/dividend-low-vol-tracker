#!/usr/bin/env python3
"""
真正的完整测试 - 简化版
"""

import subprocess
import sys
import time

print("=" * 80)
print("真正的完整测试 v2 - 启动Flask应用并测试API")
print("=" * 80)

# 步骤1: 语法检查
print("\n[1/4] 语法检查...")
result = subprocess.run(
    ['python3', '-m', 'py_compile', 'server/services/scorer.py'],
    capture_output=True,
    text=True
)
if result.returncode != 0:
    print(f"❌ 语法错误:\n{result.stderr}")
    sys.exit(1)
print("✅ 语法检查通过")

# 步骤2: PyFlakes检查
print("\n[2/4] PyFlakes静态分析...")
result = subprocess.run(
    ['python3', '-m', 'pyflakes', 'server/services/scorer.py'],
    capture_output=True,
    text=True
)
if result.returncode != 0:
    print(f"❌ PyFlakes错误:\n{result.stderr}")
    sys.exit(1)
print("✅ PyFlakes检查通过")

# 步骤3: 启动Flask应用
print("\n[3/4] 启动Flask应用...")
process = subprocess.Popen(
    [sys.executable, "app.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# 等待应用启动
print(f"等待应用启动 (端口 5050)...")
import requests
max_wait = 20
for i in range(max_wait):
    try:
        response = requests.get("http://127.0.0.1:5050/", timeout=2)
        if response.status_code == 200:
            print(f"✅ 应用已启动 (耗时 {i+1}秒)")
            break
    except:
        pass
    time.sleep(1)
    if (i + 1) % 5 == 0:
        print(f"   等待中... ({i+1}/{max_wait}秒)")
else:
    print("❌ 应用启动超时")
    process.terminate()
    process.wait()
    stdout, stderr = process.communicate()
    print("应用输出:")
    print(stdout)
    print("应用错误:")
    print(stderr)
    sys.exit(1)

# 步骤4: 调用API
print("\n[4/4] 调用API端点...")
try:
    print("发送请求到 /api/run")
    start_time = time.time()
    response = requests.post(
        "http://127.0.0.1:5050/api/run",
        json={"strategy": "balanced"},
        timeout=300
    )
    elapsed = time.time() - start_time

    print(f"✅ API响应时间: {elapsed:.2f}秒")
    print(f"状态码: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ API调用成功!")
        print(f"返回数据键: {list(data.keys())}")

        if 'data' in data and isinstance(data['data'], list):
            count = len(data['data'])
            print(f"筛选结果数量: {count}")
            if count > 0:
                print(f"前3条结果: {data['data'][:3]}")
    else:
        print(f"❌ API失败: {response.status_code}")
        print(f"响应内容: {response.text}")

except Exception as e:
    print(f"❌ API调用异常: {type(e).__name__}: {e}")

# 终止应用
process.terminate()
process.wait(timeout=5)
stdout, stderr = process.communicate()

print("\n应用日志:")
if stdout:
    print("标准输出:")
    print(stdout)
if stderr:
    print("错误输出:")
    print(stderr)

print("\n" + "=" * 80)
print("真正完整测试 - 完成!")
print("=" * 80)
