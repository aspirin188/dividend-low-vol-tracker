#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8.0 实际数据验证测试
在真实网络环境下验证所有新增功能
"""

import sys
import time
from datetime import datetime

class RealDataTester:
    """实际数据测试器"""
    
    def __init__(self):
        self.results = []
        self.start_time = datetime.now()
    
    def log(self, level, message):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print("[{}] [{}] {}".format(timestamp, level, message))
    
    def run_test(self, category, test_name, test_func, priority="高"):
        """执行单个测试"""
        self.log("TEST", "开始测试: {} - {} [{}]".format(category, test_name, priority))
        
        try:
            start = time.time()
            result = test_func()
            elapsed = time.time() - start
            
            if result:
                self.log("PASS", "✅ {} - 通过 ({:.2f}s)".format(test_name, elapsed))
                self.results.append({
                    'category': category,
                    'name': test_name,
                    'status': 'PASS',
                    'priority': priority,
                    'time': elapsed,
                    'timestamp': str(datetime.now())
                })
                return True
            else:
                self.log("FAIL", "❌ {} - 失败 ({:.2f}s)".format(test_name, elapsed))
                self.results.append({
                    'category': category,
                    'name': test_name,
                    'status': 'FAIL',
                    'priority': priority,
                    'time': elapsed,
                    'timestamp': str(datetime.now())
                })
                return False
        except Exception as e:
            elapsed = time.time() - start
            self.log("ERROR", "❌ {} - 异常: {} ({:.2f}s)".format(test_name, str(e), elapsed))
            self.results.append({
                'category': category,
                'name': test_name,
                'status': 'ERROR',
                'priority': priority,
                'error': str(e),
                'time': elapsed,
                'timestamp': str(datetime.now())
            })
            return False
    
    def print_summary(self):
        """打印测试总结"""
        total = len(self.results)
        passed = len([r for r in self.results if r['status'] == 'PASS'])
        failed = len([r for r in self.results if r['status'] == 'FAIL'])
        errors = len([r for r in self.results if r['status'] == 'ERROR'])
        duration = (datetime.now() - self.start_time).total_seconds()
        
        print("\n" + "="*80)
        print("V8.0 实际数据验证测试总结")
        print("="*80)
        print("总测试数: {}".format(total))
        print("通过: {} ✅".format(passed))
        print("失败: {} ❌".format(failed))
        print("异常: {} ⚠️".format(errors))
        if total > 0:
            print("通过率: {:.1f}%".format(passed/total*100))
        else:
            print("通过率: N/A")
        print("总耗时: {:.2f}秒".format(duration))
        print("="*80)

def test_price_percentile_real():
    """测试价格百分位实际计算"""
    try:
        from server.services.screening_service import ScreeningService
        from server.services.data_service import DataService
        
        data_service = DataService()
        screening = ScreeningService(data_service)
        
        # 使用平安银行(000001)测试
        df = data_service.get_stock_history("000001")
        if df is None or len(df) < 250:
            print("  数据不足")
            return False
        
        # 计算百分位
        percentile = screening.calculate_price_percentile(df)
        
        # 验证结果
        if percentile is None:
            print("  百分位计算失败")
            return False
        if not (0 <= percentile <= 100):
            print("  百分位超出范围: {}".format(percentile))
            return False
        
        print("  价格百分位: {:.2f}%".format(percentile))
        return True
        
    except Exception as e:
        print("  异常: {}".format(str(e)))
        return False

def test_volatility_real():
    """测试波动率实际计算"""
    try:
        from server.services.screening_service import ScreeningService
        from server.services.data_service import DataService
        
        data_service = DataService()
        screening = ScreeningService(data_service)
        
        # 使用平安银行(000001)测试
        df = data_service.get_stock_history("000001")
        if df is None or len(df) < 20:
            print("  数据不足")
            return False
        
        # 计算波动率
        volatility = screening.calculate_volatility(df)
        
        # 验证结果
        if volatility is None:
            print("  波动率计算失败")
            return False
        if volatility < 0:
            print("  波动率为负: {}".format(volatility))
            return False
        
        print("  年化波动率: {:.2f}%".format(volatility * 100))
        return True
        
    except Exception as e:
        print("  异常: {}".format(str(e)))
        return False

def test_debt_ratio_real():
    """测试负债率实际获取"""
    try:
        from server.services.data_service import DataService
        
        data_service = DataService()
        
        # 使用平安银行(000001)测试
        debt_ratio = data_service.get_debt_ratio("000001")
        
        # 验证结果
        if debt_ratio is None:
            print("  负债率获取失败")
            return False
        if not (0 <= debt_ratio <= 100):
            print("  负债率超出范围: {}".format(debt_ratio))
            return False
        
        print("  资产负债率: {:.2f}%".format(debt_ratio))
        return True
        
    except Exception as e:
        print("  异常: {}".format(str(e)))
        return False

def test_dividend_years_real():
    """测试分红年数实际计算"""
    try:
        from server.services.screening_service import ScreeningService
        from server.services.data_service import DataService
        
        data_service = DataService()
        screening = ScreeningService(data_service)
        
        # 使用平安银行(000001)测试
        years = screening.calculate_dividend_years("000001", data_service)
        
        # 验证结果
        if years is None:
            print("  分红年数计算失败")
            return False
        if years < 0:
            print("  分红年数为负: {}".format(years))
            return False
        
        print("  分红年数: {}年".format(years))
        return True
        
    except Exception as e:
        print("  异常: {}".format(str(e)))
        return False

def test_buy_signal_real():
    """测试买入信号实际生成"""
    try:
        from server.services.screening_service import ScreeningService
        from server.services.data_service import DataService
        
        data_service = DataService()
        screening = ScreeningService(data_service)
        
        # 使用平安银行(000001)测试
        df = data_service.get_stock_history("000001")
        if df is None or len(df) < 50:
            print("  数据不足")
            return False
        
        # 生成买入信号
        signal = screening.generate_buy_signal(df)
        
        # 验证结果
        if signal is None:
            print("  信号生成失败")
            return False
        if not (0 <= signal <= 10):
            print("  信号级别超出范围: {}".format(signal))
            return False
        
        print("  买入信号级别: {}级".format(signal))
        return True
        
    except Exception as e:
        print("  异常: {}".format(str(e)))
        return False

def test_trend_real():
    """测试趋势判断"""
    try:
        from server.services.screening_service import ScreeningService
        from server.services.data_service import DataService
        
        data_service = DataService()
        screening = ScreeningService(data_service)
        
        # 使用平安银行(000001)测试
        df = data_service.get_stock_history("000001")
        if df is None or len(df) < 50:
            print("  数据不足")
            return False
        
        # 判断趋势
        trend = screening.judge_trend(df)
        
        # 验证结果
        if trend is None:
            print("  趋势判断失败")
            return False
        if trend not in ['up', 'down', 'sideways']:
            print("  趋势值无效: {}".format(trend))
            return False
        
        trend_map = {'up': '上升', 'down': '下降', 'sideways': '震荡'}
        print("  趋势: {}".format(trend_map[trend]))
        return True
        
    except Exception as e:
        print("  异常: {}".format(str(e)))
        return False

def test_preset_strategy_real():
    """测试预设策略实际应用"""
    try:
        from server.services.config_service import ConfigService
        import os
        
        # 创建临时配置服务
        db_path = os.path.join(os.path.dirname(__file__), 'data', 'screening.db')
        config_service = ConfigService(db_path)
        
        # 获取所有预设策略
        presets = config_service.get_preset_strategies()
        
        # 验证结果
        if presets is None or len(presets) == 0:
            print("  获取预设策略失败")
            return False
        
        print("  预设策略数量: {}种".format(len(presets)))
        for preset in presets:
            print("    - {}".format(preset['name']))
        
        return True
        
    except Exception as e:
        print("  异常: {}".format(str(e)))
        return False

def test_growth_cagr_real():
    """测试3年利润增长CAGR"""
    try:
        from server.services.screening_service import ScreeningService
        from server.services.data_service import DataService
        
        data_service = DataService()
        screening = ScreeningService(data_service)
        
        # 使用平安银行(000001)测试
        cagr = screening.calculate_3y_growth_cagr("000001", data_service)
        
        # 验证结果
        if cagr is None:
            print("  CAGR计算失败")
            return False
        
        print("  3年利润增长CAGR: {:.2f}%".format(cagr))
        return True
        
    except Exception as e:
        print("  异常: {}".format(str(e)))
        return False

def test_quality_score_real():
    """测试击球区评分"""
    try:
        from server.services.screening_service import ScreeningService
        from server.services.data_service import DataService
        
        data_service = DataService()
        screening = ScreeningService(data_service)
        
        # 使用平安银行(000001)测试
        score = screening.calculate_quality_score("000001", data_service)
        
        # 验证结果
        if score is None:
            print("  评分计算失败")
            return False
        if not (0 <= score <= 100):
            print("  评分超出范围: {}".format(score))
            return False
        
        print("  击球区评分: {:.2f}分".format(score))
        return True
        
    except Exception as e:
        print("  异常: {}".format(str(e)))
        return False

def test_full_performance():
    """完整性能测试"""
    try:
        from server.services.screening_service import ScreeningService
        from server.services.data_service import DataService
        
        data_service = DataService()
        screening = ScreeningService(data_service)
        
        # 获取股票池
        stocks = data_service.get_stock_list()
        if stocks is None or len(stocks) == 0:
            print("  获取股票池失败")
            return False
        
        # 只测试前5只股票
        test_stocks = stocks[:5]
        print("  测试股票数量: {}只".format(len(test_stocks)))
        
        # 执行筛选
        start = time.time()
        results = screening.screen_stocks(
            test_stocks,
            min_yield=4.0,
            max_debt_ratio=80.0,
            min_years=3
        )
        elapsed = time.time() - start
        
        # 验证结果
        if results is None:
            print("  筛选失败")
            return False
        
        print("  筛选结果: {}只股票".format(len(results)))
        print("  平均耗时: {:.3f}秒/只".format(elapsed / len(test_stocks)))
        print("  总耗时: {:.2f}秒".format(elapsed))
        
        return True
        
    except Exception as e:
        print("  异常: {}".format(str(e)))
        return False

def main():
    """主测试程序"""
    print("="*80)
    print("V8.0 实际数据验证测试")
    print("开始时间: {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    print("="*80)
    print()
    
    runner = RealDataTester()
    
    # 数据源增强测试
    print("\n" + "="*80)
    print("数据源增强测试")
    print("="*80)
    
    runner.run_test("数据源", "价格百分位实际计算", test_price_percentile_real, "高")
    runner.run_test("数据源", "波动率实际计算", test_volatility_real, "高")
    runner.run_test("数据源", "负债率实际获取", test_debt_ratio_real, "高")
    runner.run_test("数据源", "分红年数实际计算", test_dividend_years_real, "高")
    
    # 信号系统测试
    print("\n" + "="*80)
    print("信号系统测试")
    print("="*80)
    
    runner.run_test("信号系统", "买入信号实际生成", test_buy_signal_real, "高")
    runner.run_test("信号系统", "趋势判断", test_trend_real, "高")
    
    # 配置系统测试
    print("\n" + "="*80)
    print("配置系统测试")
    print("="*80)
    
    runner.run_test("配置系统", "预设策略实际应用", test_preset_strategy_real, "中")
    
    # 质量因子测试
    print("\n" + "="*80)
    print("质量因子测试")
    print("="*80)
    
    runner.run_test("质量因子", "3年利润增长CAGR", test_growth_cagr_real, "高")
    runner.run_test("质量因子", "击球区评分", test_quality_score_real, "高")
    
    # 性能测试
    print("\n" + "="*80)
    print("性能测试")
    print("="*80)
    
    runner.run_test("性能", "完整筛选性能", test_full_performance, "高")
    
    # 打印总结
    runner.print_summary()
    
    # 保存结果
    with open('V8.0_REAL_DATA_TEST_RESULTS.txt', 'w', encoding='utf-8') as f:
        f.write("V8.0 实际数据验证测试结果\n")
        f.write("测试时间: {}\n".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        f.write("="*80 + "\n\n")
        
        for r in runner.results:
            f.write("{} - {}\n".format(r['category'], r['name']))
            f.write("  状态: {}\n".format(r['status']))
            f.write("  优先级: {}\n".format(r['priority']))
            f.write("  耗时: {:.2f}秒\n".format(r['time']))
            f.write("  时间戳: {}\n".format(r['timestamp']))
            if 'error' in r:
                f.write("  异常: {}\n".format(r['error']))
            f.write("\n")
    
    print("\n测试结果已保存到: V8.0_REAL_DATA_TEST_RESULTS.txt")
    
    # 返回退出码
    passed = len([r for r in runner.results if r['status'] == 'PASS'])
    failed = len([r for r in runner.results if r['status'] == 'FAIL'])
    errors = len([r for r in runner.results if r['status'] == 'ERROR'])
    
    if failed > 0 or errors > 0:
        print("\n⚠️ 部分测试失败,请查看详细报告")
        return 1
    else:
        print("\n🎉 所有测试通过!")
        return 0

if __name__ == "__main__":
    sys.exit(main())
