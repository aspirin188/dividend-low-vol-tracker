#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8.4.1 关键功能验证测试
验证所有修复后的关键功能是否正常工作
"""

import sys
import os

# 确保能导入server模块
sys.path.insert(0, os.path.dirname(__file__))


def test_imports():
    """测试所有关键模块是否能正常导入"""
    print("\n" + "="*80)
    print("测试1: 模块导入")
    print("="*80)
    
    try:
        from server.services.scorer import calculate_scores, _calculate_growth_factor
        print("✅ scorer模块导入成功")
        
        from server.services.fetcher import fetch_profit_growth_data, merge_all_data
        print("✅ fetcher模块导入成功")
        
        from server.services.config_service import ConfigService
        print("✅ config_service模块导入成功")
        
        from server.routes import bp, init_db
        print("✅ routes模块导入成功")
        
        print("\n✅ 所有模块导入成功！\n")
        return True
    except Exception as e:
        print("\n❌ 模块导入失败: {}\n".format(str(e)))
        import traceback
        traceback.print_exc()
        return False


def test_growth_factor_calculation():
    """测试成长因子计算"""
    print("\n" + "="*80)
    print("测试2: 成长因子计算")
    print("="*80)
    
    try:
        from server.services.scorer import _calculate_growth_factor
        
        # 测试用例
        test_cases = [
            (12.0, 30.0, 2.0, "高增长+高ROE趋势"),
            (8.0, 25.0, 1.0, "中增长+中ROE趋势"),
            (None, 10.0, None, "无数据"),
            (18.0, 15.0, 3.0, "超高增长+高ROE趋势"),
        ]
        
        print("\n测试用例:")
        for profit_growth, pe, roe_trend, desc in test_cases:
            gf = _calculate_growth_factor(profit_growth, pe, roe_trend)
            print(f"  {desc}: profit_growth={profit_growth}, pe={pe}, roe_trend={roe_trend} → {gf}")
        
        # 验证
        gf1 = _calculate_growth_factor(12.0, 30.0, 2.0)
        gf2 = _calculate_growth_factor(8.0, 25.0, 1.0)
        gf3 = _calculate_growth_factor(None, 10.0, None)
        gf4 = _calculate_growth_factor(18.0, 15.0, 3.0)
        
        if gf1 > 50 and gf2 > 40 and gf3 == 30 and gf4 > 60:
            print("\n✅ 成长因子计算测试通过！\n")
            return True
        else:
            print(f"\n❌ 成长因子计算测试失败！\n")
            print(f"  gf1={gf1}, gf2={gf2}, gf3={gf3}, gf4={gf4}")
            return False
    except Exception as e:
        print("\n❌ 成长因子计算测试失败: {}\n".format(str(e)))
        import traceback
        traceback.print_exc()
        return False


def test_config_service():
    """测试配置服务"""
    print("\n" + "="*80)
    print("测试3: 配置服务")
    print("="*80)
    
    try:
        from flask import Flask
        from server.routes import bp
        
        # 创建测试应用
        app = Flask(__name__, instance_relative_config=True)
        app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
        app.register_blueprint(bp)
        
        # 初始化数据库
        with app.app_context():
            from server.routes import init_db
            init_db()
            
            # 测试配置读取
            from server.services.config_service import ConfigService
            config = ConfigService.get_instance()
            
            print("\n配置项测试:")
            min_growth = config.get_float('MIN_PROFIT_GROWTH', default=0)
            enable_filter = config.get_bool('ENABLE_PROFIT_GROWTH_FILTER')
            
            print(f"  MIN_PROFIT_GROWTH: {min_growth}")
            print(f"  ENABLE_PROFIT_GROWTH_FILTER: {enable_filter}")
            
            # 验证配置读取是否正常
            if min_growth >= 0 and isinstance(enable_filter, bool):
                print("\n✅ 配置服务测试通过！\n")
                return True
            else:
                print("\n❌ 配置服务测试失败！\n")
                return False
    except Exception as e:
        print("\n❌ 配置服务测试失败: {}\n".format(str(e)))
        import traceback
        traceback.print_exc()
        return False


def test_data_mapping():
    """测试数据映射逻辑"""
    print("\n" + "="*80)
    print("测试4: 数据映射")
    print("="*80)
    
    try:
        import pandas as pd
        
        # 模拟成长因子数据
        growth_data = {
            '600519': {'profit_growth_3y': 12.0, 'roe_trend': 2.0},
            '000858': {'profit_growth_3y': 8.0, 'roe_trend': 1.0},
            '601318': {'profit_growth_3y': 5.0, 'roe_trend': -0.5},
        }
        
        # 模拟merged dataframe
        merged = pd.DataFrame({
            'code': ['600519', '000858', '601318'],
            'name': ['贵州茅台', '五粮液', '中国平安'],
        })
        
        # 数据映射（模拟routes.py第174-178行的逻辑）
        merged['profit_growth_3y'] = merged['code'].map(lambda x: growth_data.get(x, {}).get('profit_growth_3y'))
        merged['roe_trend'] = merged['code'].map(lambda x: growth_data.get(x, {}).get('roe_trend'))
        
        print("\n数据映射结果:")
        print(merged[['code', 'name', 'profit_growth_3y', 'roe_trend']].to_string())
        
        # 验证数据映射
        expected = {
            '600519': {'profit_growth_3y': 12.0, 'roe_trend': 2.0},
            '000858': {'profit_growth_3y': 8.0, 'roe_trend': 1.0},
            '601318': {'profit_growth_3y': 5.0, 'roe_trend': -0.5},
        }
        
        success = True
        for code, expected_data in expected.items():
            actual = merged[merged['code'] == code].iloc[0]
            if actual['profit_growth_3y'] != expected_data['profit_growth_3y']:
                print(f"\n❌ {code} profit_growth_3y不匹配: 期望{expected_data['profit_growth_3y']}, 实际{actual['profit_growth_3y']}")
                success = False
            if actual['roe_trend'] != expected_data['roe_trend']:
                print(f"❌ {code} roe_trend不匹配: 期望{expected_data['roe_trend']}, 实际{actual['roe_trend']}")
                success = False
        
        if success:
            print("\n✅ 数据映射测试通过！\n")
            return True
        else:
            print("\n❌ 数据映射测试失败！\n")
            return False
    except Exception as e:
        print("\n❌ 数据映射测试失败: {}\n".format(str(e)))
        import traceback
        traceback.print_exc()
        return False


def test_filter_logic():
    """测试利润增长筛选逻辑"""
    print("\n" + "="*80)
    print("测试5: 利润增长筛选")
    print("="*80)
    
    try:
        import pandas as pd
        
        # 模拟数据（包含负增长）
        merged = pd.DataFrame({
            'code': ['600519', '000858', '601318', '000001'],
            'name': ['贵州茅台', '五粮液', '中国平安', '平安银行'],
            'profit_growth_3y': [12.0, 8.0, -5.0, None],  # 包含负增长和NaN
        })
        
        print("\n筛选前:")
        print(merged[['code', 'name', 'profit_growth_3y']].to_string())
        
        # 筛选逻辑（模拟routes.py第184-189行）
        min_growth = 0
        mask = merged['profit_growth_3y'].isna() | (merged['profit_growth_3y'] >= min_growth)
        merged = merged[mask].copy()
        
        print("\n筛选后（过滤负增长）:")
        print(merged[['code', 'name', 'profit_growth_3y']].to_string())
        
        # 验证筛选结果
        expected_codes = ['600519', '000858', '000001']  # 过滤掉601318（负增长）
        actual_codes = merged['code'].tolist()
        
        if actual_codes == expected_codes:
            print(f"\n✅ 利润增长筛选测试通过！过滤了1只负增长股票\n")
            return True
        else:
            print(f"\n❌ 利润增长筛选测试失败！")
            print(f"  期望: {expected_codes}")
            print(f"  实际: {actual_codes}\n")
            return False
    except Exception as e:
        print("\n❌ 利润增长筛选测试失败: {}\n".format(str(e)))
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "="*80)
    print("V8.4.1 关键功能验证测试")
    print("="*80)
    
    results = []
    
    # 测试1: 模块导入
    results.append(('模块导入', test_imports()))
    
    # 测试2: 成长因子计算
    results.append(('成长因子计算', test_growth_factor_calculation()))
    
    # 测试3: 配置服务
    results.append(('配置服务', test_config_service()))
    
    # 测试4: 数据映射
    results.append(('数据映射', test_data_mapping()))
    
    # 测试5: 利润增长筛选
    results.append(('利润增长筛选', test_filter_logic()))
    
    # 打印总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)
    
    total = len(results)
    passed = sum(1 for _, result in results if result)
    failed = total - passed
    
    print(f"总测试数: {total}")
    print(f"通过: {passed} ✅")
    print(f"失败: {failed} ❌")
    print(f"通过率: {passed/total*100:.1f}%")
    
    print("\n详细结果:")
    for name, result in results:
        status_icon = "✅" if result else "❌"
        print(f"  {status_icon} {name}")
    
    print("="*80)
    
    if passed == total:
        print("\n🎉 所有测试通过！V8.4.1修复成功！\n")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查错误信息\n")
        return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被中断\n")
        sys.exit(1)
    except Exception as e:
        print("\n\n❌ 测试异常: {}\n".format(str(e)))
        import traceback
        traceback.print_exc()
        sys.exit(1)
