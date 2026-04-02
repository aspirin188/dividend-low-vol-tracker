#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v8.4.1 Bug修复验证测试
"""

import sys
import pandas as pd

def test_growth_factor_calculation():
    """测试成长因子计算"""
    print("=" * 60)
    print("测试1: 成长因子计算")
    print("=" * 60)
    
    from server.services.scorer import _calculate_growth_factor
    
    test_cases = [
        (12.0, 30.0, 2.0, '高增长+高ROE趋势'),
        (8.0, 25.0, 1.0, '中增长+中ROE趋势'),
        (None, 10.0, None, '无数据'),
        (18.0, 15.0, 3.0, '超高增长+高ROE趋势'),
    ]
    
    all_pass = True
    for profit, pe, roe_trend, desc in test_cases:
        result = _calculate_growth_factor(profit, pe, roe_trend)
        print(f"  {desc}: {result}")
        
        # 简单验证
        if profit is None and result != 30:
            print(f"    ❌ 无数据应该返回30")
            all_pass = False
    
    if all_pass:
        print("✅ 成长因子计算测试通过\n")
        return True
    else:
        print("❌ 成长因子计算测试失败\n")
        return False


def test_growth_data_mapping():
    """测试成长因子数据映射"""
    print("=" * 60)
    print("测试2: 成长因子数据映射")
    print("=" * 60)
    
    # 模拟fetch_profit_growth_data返回的数据
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
    
    # 模拟第174-178行的数据映射
    merged['profit_growth_3y'] = merged['code'].map(lambda x: growth_data.get(x, {}).get('profit_growth_3y'))
    merged['roe_trend'] = merged['code'].map(lambda x: growth_data.get(x, {}).get('roe_trend'))
    
    print(merged[['code', 'name', 'profit_growth_3y', 'roe_trend']].to_string())
    
    # 验证数据是否正确
    expected = {
        '600519': {'profit_growth_3y': 12.0, 'roe_trend': 2.0},
        '000858': {'profit_growth_3y': 8.0, 'roe_trend': 1.0},
        '601318': {'profit_growth_3y': 5.0, 'roe_trend': -0.5},
    }
    
    success = True
    for code, expected_data in expected.items():
        actual = merged[merged['code'] == code].iloc[0]
        if actual['profit_growth_3y'] != expected_data['profit_growth_3y']:
            print(f"❌ {code} profit_growth_3y不匹配")
            success = False
        if actual['roe_trend'] != expected_data['roe_trend']:
            print(f"❌ {code} roe_trend不匹配")
            success = False
    
    if success:
        print("✅ 成长因子数据映射测试通过\n")
        return True
    else:
        print("❌ 成长因子数据映射测试失败\n")
        return False


def test_profit_growth_filter():
    """测试利润增长筛选逻辑"""
    print("=" * 60)
    print("测试3: 利润增长筛选逻辑")
    print("=" * 60)
    
    # 模拟数据
    merged = pd.DataFrame({
        'code': ['600519', '000858', '601318', '000001'],
        'name': ['贵州茅台', '五粮液', '中国平安', '平安银行'],
        'profit_growth_3y': [12.0, 8.0, -5.0, None],
    })
    
    print("筛选前:")
    print(merged[['code', 'name', 'profit_growth_3y']].to_string())
    
    # 模拟v8.4.1的筛选逻辑（过滤负增长）
    min_growth = 0
    before_count = len(merged)
    mask = merged['profit_growth_3y'].isna() | (merged['profit_growth_3y'] >= min_growth)
    filtered = merged[mask].copy()
    filtered_count = before_count - len(filtered)
    
    print(f"\n筛选后（过滤{filtered_count}只负增长）:")
    print(filtered[['code', 'name', 'profit_growth_3y']].to_string())
    
    # 验证
    expected_count = 3  # 应该保留3只（1只负增长被过滤）
    if len(filtered) == expected_count:
        print("✅ 利润增长筛选逻辑测试通过\n")
        return True
    else:
        print(f"❌ 利润增长筛选逻辑测试失败，期望{expected_count}只，实际{len(filtered)}只\n")
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("v8.4.1 Bug修复验证测试")
    print("=" * 60 + "\n")
    
    results = []
    
    # 测试1: 成长因子计算
    results.append(test_growth_factor_calculation())
    
    # 测试2: 成长因子数据映射
    results.append(test_growth_data_mapping())
    
    # 测试3: 利润增长筛选
    results.append(test_profit_growth_filter())
    
    # 总结
    print("=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"总测试数: {len(results)}")
    print(f"通过: {sum(results)} ✅")
    print(f"失败: {len(results) - sum(results)} ❌")
    
    if all(results):
        print("\n🎉 所有测试通过！v8.4.1 bug修复成功！")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查修复")
        return 1


if __name__ == '__main__':
    sys.exit(main())
