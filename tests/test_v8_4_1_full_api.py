#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8.4.1 完整API集成测试
测试所有修复后的功能是否正常工作
"""

import sys
import os
import time
import json
from datetime import datetime

# 确保能导入server模块
sys.path.insert(0, os.path.dirname(__file__))


class APITester:
    """API集成测试器"""
    
    def __init__(self):
        self.results = []
        self.start_time = datetime.now()
        self.app = None
        self.client = None
    
    def log(self, level, message):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print("[{}] [{}] {}".format(timestamp, level, message))
    
    def init_app(self):
        """初始化Flask应用"""
        try:
            from app import create_app
            
            self.log("INIT", "正在初始化Flask应用...")
            self.app = create_app()
            self.client = self.app.test_client()
            
            self.log("INIT", "✅ Flask应用初始化成功")
            return True
        except Exception as e:
            self.log("ERROR", "❌ Flask应用初始化失败: {}".format(str(e)))
            return False
    
    def test_config_endpoint(self):
        """测试配置API"""
        try:
            response = self.client.get('/api/config')
            
            if response.status_code == 200:
                data = json.loads(response.data)
                self.log("TEST", "✅ 配置API返回正常，配置项数: {}".format(len(data.get('config', {}))))
                return True
            else:
                self.log("FAIL", "❌ 配置API状态码: {}".format(response.status_code))
                return False
        except Exception as e:
            self.log("ERROR", "❌ 配置API异常: {}".format(str(e)))
            return False
    
    def test_run_endpoint_quick(self):
        """测试运行API（快速模式，只测试不报错）"""
        try:
            # Flask test client不支持timeout参数，直接调用
            response = self.client.post('/api/run')
            
            if response.status_code == 200:
                data = json.loads(response.data)
                
                if data.get('success'):
                    result_count = data.get('result_count', 0)
                    self.log("TEST", "✅ 运行API返回正常，结果数: {}".format(result_count))
                    return True
                else:
                    error = data.get('error', '未知错误')
                    self.log("FAIL", "❌ 运行API返回失败: {}".format(error))
                    return False
            else:
                self.log("FAIL", "❌ 运行API状态码: {}".format(response.status_code))
                return False
        except Exception as e:
            self.log("ERROR", "❌ 运行API异常: {}".format(str(e)))
            import traceback
            self.log("ERROR", "异常堆栈: {}".format(traceback.format_exc()))
            return False
    
    def test_results_endpoint(self):
        """测试结果API（/api/stocks）"""
        try:
            response = self.client.get('/api/stocks')
            
            if response.status_code == 200:
                data = json.loads(response.data)
                results = data.get('stocks', [])
                self.log("TEST", "✅ 结果API返回正常，结果数: {}".format(len(results)))
                return True
            else:
                self.log("FAIL", "❌ 结果API状态码: {}".format(response.status_code))
                return False
        except Exception as e:
            self.log("ERROR", "❌ 结果API异常: {}".format(str(e)))
            return False
    
    def test_data_flow(self):
        """测试数据流完整性"""
        try:
            # 导入关键模块，检查是否有导入错误
            from server.services.scorer import calculate_scores
            from server.services.fetcher import fetch_profit_growth_data
            from server.services.config_service import ConfigService
            
            self.log("TEST", "✅ 关键模块导入正常")
            
            # 测试成长因子计算
            from server.services.scorer import _calculate_growth_factor
            gf = _calculate_growth_factor(10.0, 20.0, 1.0)
            
            if gf > 30:
                self.log("TEST", "✅ 成长因子计算正常: {}".format(gf))
                return True
            else:
                self.log("FAIL", "❌ 成长因子计算异常: {}".format(gf))
                return False
        except Exception as e:
            self.log("ERROR", "❌ 数据流测试异常: {}".format(str(e)))
            import traceback
            self.log("ERROR", "异常堆栈: {}".format(traceback.format_exc()))
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "="*80)
        print("V8.4.1 完整API集成测试")
        print("="*80 + "\n")
        
        # 测试1: 应用初始化
        if not self.init_app():
            print("\n❌ 应用初始化失败，无法继续测试")
            return False
        
        # 测试2: 配置API
        print("\n--- 测试1: 配置API ---")
        result = self.test_config_endpoint()
        self.results.append({'name': '配置API', 'status': 'PASS' if result else 'FAIL'})
        
        # 测试3: 数据流
        print("\n--- 测试2: 数据流完整性 ---")
        result = self.test_data_flow()
        self.results.append({'name': '数据流完整性', 'status': 'PASS' if result else 'FAIL'})
        
        # 测试4: 运行API（完整流程）
        print("\n--- 测试3: 运行API（完整流程）---")
        print("注意: 此测试可能需要1-2分钟...")
        start = time.time()
        result = self.test_run_endpoint_quick()
        elapsed = time.time() - start
        self.results.append({'name': '运行API', 'status': 'PASS' if result else 'FAIL', 'time': elapsed})
        
        # 测试5: 结果API
        print("\n--- 测试4: 结果API ---")
        result = self.test_results_endpoint()
        self.results.append({'name': '结果API', 'status': 'PASS' if result else 'FAIL'})
        
        return True
    
    def print_summary(self):
        """打印测试总结"""
        total = len(self.results)
        passed = len([r for r in self.results if r['status'] == 'PASS'])
        failed = len([r for r in self.results if r['status'] == 'FAIL'])
        duration = (datetime.now() - self.start_time).total_seconds()
        
        print("\n" + "="*80)
        print("V8.4.1 完整API集成测试总结")
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


if __name__ == '__main__':
    tester = APITester()
    
    try:
        success = tester.run_all_tests()
        all_passed = tester.print_summary()
        
        if all_passed:
            print("\n🎉 所有测试通过！V8.4.1修复成功！")
            sys.exit(0)
        else:
            print("\n⚠️ 部分测试失败，请检查错误信息")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被中断")
        sys.exit(1)
    except Exception as e:
        print("\n\n❌ 测试异常: {}".format(str(e)))
        import traceback
        traceback.print_exc()
        sys.exit(1)
