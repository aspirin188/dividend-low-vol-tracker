#!/usr/bin/env python3
"""
真正的完整测试 - 红利低波跟踪系统 v8.4.1

真正的测试应该是：
1. 启动 Flask 应用
2. 调用 /api/run 端点
3. 验证完整的执行流程
4. 检查是否有运行时错误

这不是静态分析，不是单元测试，而是真实的应用运行测试！
"""

import subprocess
import time
import requests
import signal
import sys
from pathlib import Path

# 配置
APP_SCRIPT = "app.py"
APP_HOST = "127.0.0.1"
APP_PORT = 5050
API_URL = f"http://{APP_HOST}:{APP_PORT}/api/run"
TIMEOUT = 300  # 5分钟超时

def start_flask_app():
    """启动 Flask 应用"""
    print("🚀 启动 Flask 应用...")
    process = subprocess.Popen(
        [sys.executable, APP_SCRIPT],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # 等待应用启动
    print(f"⏳ 等待应用启动 (端口 {APP_PORT})...")
    max_wait = 30  # 最多等待30秒
    for i in range(max_wait):
        try:
            response = requests.get(f"http://{APP_HOST}:{APP_PORT}/", timeout=2)
            if response.status_code == 200:
                print(f"✅ 应用已启动 (耗时 {i+1}秒)")
                return process
        except:
            pass
        time.sleep(1)
        if (i + 1) % 5 == 0:
            print(f"   仍在等待... ({i+1}/{max_wait}秒)")

    print("❌ 应用启动超时")
    return None

def test_api_call():
    """调用 API 端点"""
    print(f"\n📡 调用 API 端点: {API_URL}")

    payload = {
        "strategy": "balanced",
        "enable_growth_filter": True
    }

    try:
        print(f"📨 发送请求: {payload}")
        start_time = time.time()

        response = requests.post(
            API_URL,
            json=payload,
            timeout=TIMEOUT
        )

        elapsed = time.time() - start_time
        print(f"⏱️  响应时间: {elapsed:.2f}秒")
        print(f"📊 状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ API 调用成功!")
            print(f"   返回数据键: {list(data.keys())}")

            if 'data' in data and isinstance(data['data'], list):
                result_count = len(data['data'])
                print(f"   筛选结果数量: {result_count}")

                if result_count > 0:
                    print(f"   前3条结果:")
                    for i, item in enumerate(data['data'][:3], 1):
                        print(f"     {i}. {item}")
            return True
        else:
            print(f"❌ API 调用失败: {response.status_code}")
            print(f"   响应内容: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print(f"❌ 请求超时 (>{TIMEOUT}秒)")
        return False
    except Exception as e:
        print(f"❌ 请求异常: {type(e).__name__}: {e}")
        return False

def check_app_logs(process):
    """检查应用日志"""
    print(f"\n📝 检查应用日志...")

    # 终止应用
    process.terminate()
    process.wait(timeout=5)

    stdout, stderr = process.communicate()

    if stdout:
        print(f"标准输出:")
        print(stdout)

    if stderr:
        print(f"错误输出:")
        print(stderr)

    # 检查是否有错误
    error_keywords = ['Error', 'Exception', 'Traceback', 'Failed', 'error', 'exception']
    all_output = stdout + stderr

    errors = []
    for line in all_output.split('\n'):
        line_lower = line.lower()
        for keyword in error_keywords:
            if keyword.lower() in line_lower:
                errors.append(line)
                break

    if errors:
        print(f"\n⚠️  发现 {len(errors)} 条可能包含错误的日志:")
        for error in errors[:10]:  # 只显示前10条
            print(f"   {error}")
    else:
        print(f"✅ 未发现明显的错误日志")

def test_basic_syntax():
    """基本语法检查"""
    print("\n🔍 测试1: Python 语法检查")
    result = subprocess.run(
        ['python3', '-m', 'py_compile', 'server/services/scorer.py'],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("✅ 语法检查通过")
        return True
    else:
        print(f"❌ 语法检查失败: {result.stderr}")
        return False

def test_pyflakes():
    """PyFlakes 静态分析"""
    print("\n🔍 测试2: PyFlakes 静态分析")
    result = subprocess.run(
        ['python3', '-m', 'pyflakes', 'server/services/scorer.py'],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("✅ PyFlakes 检查通过")
        return True
    else:
        print(f"❌ PyFlakes 检查失败: {result.stderr}")
        return False

def main():
    print("=" * 80)
    print("真正的完整测试 - 红利低波跟踪系统 v8.4.1")
    print("=" * 80)

    # 静态检查
    syntax_ok = test_basic_syntax()
    pyflakes_ok = test_pyflakes()

    if not (syntax_ok and pyflakes_ok):
        print("\n❌ 静态检查失败，终止测试")
        return False

    # 启动应用
    process = start_flask_app()
    if process is None:
        print("\n❌ 应用启动失败，终止测试")
        return False

    try:
        # API 测试
        api_ok = test_api_call()

        # 检查日志
        check_app_logs(process)

        if api_ok:
            print("\n" + "=" * 80)
            print("✅ 真正完整测试 - 全部通过!")
            print("=" * 80)
            return True
        else:
            print("\n" + "=" * 80)
            print("❌ 真正完整测试 - 失败!")
            print("=" * 80)
            return False

    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        process.terminate()
        process.wait()
        return False
    except Exception as e:
        print(f"\n❌ 测试异常: {type(e).__name__}: {e}")
        if process:
            process.terminate()
            process.wait()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
