#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8.0 系统功能验证 - 通过API测试
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:5050"

class V8Tester:
    def __init__(self):
        self.results = []
        self.start_time = datetime.now()
    
    def log(self, level, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print("[{}] [{}] {}".format(timestamp, level, message))
    
    def test_api(self, name, method, endpoint, data=None, expected_status=200):
        """测试API"""
        self.log("TEST", "测试: {}".format(name))
        
        url = BASE_URL + endpoint
        start = time.time()
        
        try:
            if method == "GET":
                response = requests.get(url, timeout=300)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=600)
            
            elapsed = time.time() - start
            
            if response.status_code == expected_status:
                self.log("PASS", "✅ {} ({:.2f}s)".format(name, elapsed))
                self.results.append({
                    'name': name,
                    'status': 'PASS',
                    'time': elapsed,
                    'response': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                })
                return True
            else:
                self.log("FAIL", "❌ {} - 状态码: {}".format(name, response.status_code))
                self.results.append({
                    'name': name,
                    'status': 'FAIL',
                    'time': elapsed,
                    'error': '状态码: {}'.format(response.status_code)
                })
                return False
                
        except Exception as e:
            elapsed = time.time() - start
            self.log("ERROR", "❌ {} - {}".format(name, str(e)))
            self.results.append({
                'name': name,
                'status': 'ERROR',
                'time': elapsed,
                'error': str(e)
            })
            return False
    
    def print_summary(self):
        total = len(self.results)
        passed = len([r for r in self.results if r['status'] == 'PASS'])
        failed = len([r for r in self.results if r['status'] == 'FAIL'])
        errors = len([r for r in self.results if r['status'] == 'ERROR'])
        duration = (datetime.now() - self.start_time).total_seconds()
        
        print("\n" + "="*80)
        print("V8.0 API测试总结")
        print("="*80)
        print("总测试数: {}".format(total))
        print("通过: {} ✅".format(passed))
        print("失败: {} ❌".format(failed))
        print("异常: {} ⚠️".format(errors))
        if total > 0:
            print("通过率: {:.1f}%".format(passed/total*100))
        print("总耗时: {:.2f}秒".format(duration))
        print("="*80)

def main():
    print("="*80)
    print("V8.0 系统功能验证 (API测试)")
    print("开始时间: {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    print("="*80)
    print()
    
    tester = V8Tester()
    
    # 测试1: 获取预设策略 (v8.0新增)
    print("\n" + "="*80)
    print("配置系统测试 (v8.0)")
    print("="*80)
    
    result = tester.test_api(
        "获取预设策略列表",
        "GET",
        "/api/config/strategies"
    )
    
    if result:
        strategies = tester.results[-1]['response'].get('strategies', {})
        print("  预设策略数量: {}种".format(len(strategies)))
        for key, value in strategies.items():
            print("    - {} ({})".format(value.get('name', key), key))
    
    # 测试2: 应用预设策略 (v8.0新增)
    tester.test_api(
        "应用均衡型策略",
        "POST",
        "/api/config/strategies",
        {"strategy_id": "balanced", "reason": "测试应用均衡策略"}
    )
    
    # 测试3: 获取参数历史 (v8.0新增)
    tester.test_api(
        "获取参数历史记录",
        "GET",
        "/api/config/history"
    )
    
    # 测试4: 获取配置 (v6.20)
    tester.test_api(
        "获取当前配置",
        "GET",
        "/api/config"
    )
    
    # 测试5: 首页加载 (基础)
    tester.test_api(
        "首页加载",
        "GET",
        "/"
    )
    
    # 测试6: 获取股票列表 (基础)
    stocks_result = tester.test_api(
        "获取股票列表",
        "GET",
        "/api/stocks"
    )
    
    if stocks_result:
        response = tester.results[-1]['response']
        if isinstance(response, list):
            stock_count = len(response)
        elif isinstance(response, dict):
            stock_count = len(response.get('stocks', []))
        else:
            stock_count = 0
        print("  当前股票数: {}只".format(stock_count))
    
    # 测试7: 配置管理页面 (v6.20)
    tester.test_api(
        "配置管理页面",
        "GET",
        "/config"
    )
    
    # 打印总结
    tester.print_summary()
    
    # 保存结果
    with open('V8.0_API_TEST_RESULTS.txt', 'w', encoding='utf-8') as f:
        f.write("V8.0 API测试结果\n")
        f.write("测试时间: {}\n".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        f.write("="*80 + "\n\n")
        
        for r in tester.results:
            f.write("{}\n".format(r['name']))
            f.write("  状态: {}\n".format(r['status']))
            f.write("  耗时: {:.2f}秒\n".format(r['time']))
            if 'error' in r:
                f.write("  异常: {}\n".format(r['error']))
            f.write("\n")
    
    print("\n测试结果已保存到: V8.0_API_TEST_RESULTS.txt")
    
    passed = len([r for r in tester.results if r['status'] == 'PASS'])
    failed = len([r for r in tester.results if r['status'] == 'FAIL'])
    
    if failed > 0:
        print("\n⚠️ 部分测试失败")
        return 1
    else:
        print("\n🎉 所有API测试通过!")
        return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
