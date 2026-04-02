#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8.4.1 真正的完整集成测试
模拟用户实际运行场景，真正启动Flask应用并执行完整流程
"""

import sys
import os
import time
import json
import signal
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))


class RealIntegrationTester:
    """真正的集成测试器 - 模拟用户实际运行"""
    
    def __init__(self):
        self.results = []
        self.start_time = datetime.now()
        self.server_process = None
    
    def log(self, level, message):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print("[{}] [{}] {}".format(timestamp, level, message))
        sys.stdout.flush()
    
    def start_flask_server(self):
        """启动Flask服务器"""
        try:
            self.log("INIT", "正在启动Flask服务器...")
            
            # 使用subprocess启动Flask应用
            self.server_process = subprocess.Popen(
                ['python3', 'app.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # 等待服务器启动
            time.sleep(5)
            
            # 检查进程是否还在运行
            if self.server_process.poll() is None:
                self.log("INIT", "✅ Flask服务器启动成功 (PID: {})".format(self.server_process.pid))
                return True
            else:
                # 读取错误输出
                stdout, stderr = self.server_process.communicate()
                self.log("ERROR", "❌ Flask服务器启动失败")
                self.log("ERROR", "stdout: {}".format(stdout))
                self.log("ERROR", "stderr: {}".format(stderr))
                return False
        except Exception as e:
            self.log("ERROR", "❌ Flask服务器启动异常: {}".format(str(e)))
            return False
    
    def stop_flask_server(self):
        """停止Flask服务器"""
        if self.server_process and self.server_process.poll() is None:
            self.log("CLEAN", "正在停止Flask服务器...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
                self.log("CLEAN", "✅ Flask服务器已停止")
            except subprocess.TimeoutExpired:
                self.log("CLEAN", "⚠️ Flask服务器未响应，强制终止")
                self.server_process.kill()
    
    def test_with_curl(self):
        """使用curl测试API"""
        try:
            import urllib.request
            import urllib.parse
            
            self.log("TEST", "使用urllib测试API...")
            
            # 测试POST /api/run
            url = 'http://127.0.0.1:5050/api/run'  # 修复：使用正确的端口5050
            data = urllib.parse.urlencode({}).encode('utf-8')
            
            req = urllib.request.Request(url, data=data, method='POST')
            
            with urllib.request.urlopen(req, timeout=300) as response:
                result = response.read().decode('utf-8')
                data = json.loads(result)
                
                if data.get('success'):
                    count = data.get('result_count', 0)
                    self.log("TEST", "✅ API调用成功，结果数: {}".format(count))
                    return True
                else:
                    error = data.get('error', '未知错误')
                    self.log("FAIL", "❌ API返回失败: {}".format(error))
                    return False
        except urllib.error.URLError as e:
            self.log("ERROR", "❌ URL错误: {}".format(str(e)))
            return False
        except Exception as e:
            self.log("ERROR", "❌ API测试异常: {}".format(str(e)))
            import traceback
            self.log("ERROR", "异常堆栈: {}".format(traceback.format_exc()))
            return False
    
    def test_config_api(self):
        """测试配置API"""
        try:
            import urllib.request
            
            url = 'http://127.0.0.1:5050/api/config'  # 修复：使用正确的端口5050
            
            with urllib.request.urlopen(url, timeout=10) as response:
                result = response.read().decode('utf-8')
                data = json.loads(result)
                
                if data.get('success'):
                    self.log("TEST", "✅ 配置API调用成功")
                    return True
                else:
                    self.log("FAIL", "❌ 配置API返回失败")
                    return False
        except Exception as e:
            self.log("ERROR", "❌ 配置API异常: {}".format(str(e)))
            return False
    
    def monitor_server_output(self, duration=30):
        """监控服务器输出"""
        try:
            self.log("MONITOR", "监控服务器输出（{}秒）...".format(duration))
            
            # 读取服务器输出（非阻塞）
            lines = []
            start_time = time.time()
            
            while time.time() - start_time < duration:
                if self.server_process.poll() is not None:
                    self.log("ERROR", "❌ 服务器进程意外退出")
                    break
                
                time.sleep(0.5)
            
            return True
        except Exception as e:
            self.log("ERROR", "❌ 监控异常: {}".format(str(e)))
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "="*80)
        print("V8.4.1 真正的完整集成测试")
        print("="*80 + "\n")
        
        # 测试1: 启动Flask服务器
        print("\n--- 测试1: 启动Flask服务器 ---")
        if not self.start_flask_server():
            print("\n❌ Flask服务器启动失败，无法继续测试")
            return False
        
        # 监控服务器启动
        self.monitor_server_output(duration=3)
        
        # 测试2: 配置API
        print("\n--- 测试2: 配置API ---")
        result = self.test_config_api()
        self.results.append({'name': '配置API', 'status': 'PASS' if result else 'FAIL'})
        
        # 测试3: 运行API（完整流程）
        print("\n--- 测试3: 运行API（完整流程）---")
        print("注意: 此测试可能需要3-5分钟（获取真实数据）...")
        start = time.time()
        result = self.test_with_curl()
        elapsed = time.time() - start
        self.results.append({'name': '运行API', 'status': 'PASS' if result else 'FAIL', 'time': elapsed})
        
        return True
    
    def cleanup(self):
        """清理资源"""
        self.stop_flask_server()
    
    def print_summary(self):
        """打印测试总结"""
        total = len(self.results)
        passed = len([r for r in self.results if r['status'] == 'PASS'])
        failed = len([r for r in self.results if r['status'] == 'FAIL'])
        duration = (datetime.now() - self.start_time).total_seconds()
        
        print("\n" + "="*80)
        print("V8.4.1 真正的完整集成测试总结")
        print("="*80)
        print("总测试数: {}".format(total))
        print("通过: {} ✅".format(passed))
        print("失败: {} ❌".format(failed))
        if total > 0:
            print("通过率: {:.1f}%".format(passed/total*100))
        else:
            print("通过率: N/A")
        print("总耗时: {:.2f}秒".format(duration))
        
        print("\n详细结果:")
        for r in self.results:
            status_icon = "✅" if r['status'] == 'PASS' else "❌"
            time_str = " ({:.2f}s)".format(r.get('time', 0)) if 'time' in r else ""
            print("  {} {}{}".format(status_icon, r['name'], time_str))
        
        print("="*80)
        
        return passed == total


def main():
    """主函数"""
    tester = RealIntegrationTester()
    
    try:
        success = tester.run_all_tests()
        all_passed = tester.print_summary()
        
        if all_passed:
            print("\n🎉 所有测试通过！v8.4.1修复成功！")
            return 0
        else:
            print("\n⚠️ 部分测试失败，请检查错误信息")
            return 1
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被中断")
        return 1
    except Exception as e:
        print("\n\n❌ 测试异常: {}".format(str(e)))
        import traceback
        traceback.print_exc()
        return 1
    finally:
        tester.cleanup()


if __name__ == '__main__':
    sys.exit(main())
