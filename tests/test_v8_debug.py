#!/usr/bin/env python3
"""
V8.0 增强调试脚本 - 详细追踪所有数据类型问题
"""
import os
import sys
import pandas as pd
import numpy as np
import traceback

sys.path.insert(0, os.path.dirname(__file__))

# 设置Flask应用上下文
from app import create_app
app = create_app()

print("="*70)
print("V8.0 增强调试测试")
print("="*70)

with app.app_context():
    # 测试1: 数据类型转换
    print("\n【测试1】数据类型转换测试")
    print("-"*70)
    
    test_df = pd.DataFrame({
        'code': ['000001', '000002'],
        'name': ['平安银行', '万科A'],
        'dividend_yield_ttm': ['4.5', '3.2'],  # 字符串类型
        'annual_vol': [20.5, 18.3],
        'dividend_years': ['10', '8']  # 字符串类型
    })
    
    print("原始数据类型:")
    for col in test_df.columns:
        print(f"  {col:20s} {test_df[col].dtype}")
    
    # 测试类型转换
    from server.services.scorer import min_max_normalize
    
    test_df['dividend_yield_ttm'] = pd.to_numeric(test_df['dividend_yield_ttm'], errors='coerce')
    test_df['dividend_years'] = pd.to_numeric(test_df['dividend_years'], errors='coerce')
    
    print("\n转换后数据类型:")
    for col in test_df.columns:
        print(f"  {col:20s} {test_df[col].dtype}")
    
    # 测试归一化
    values = test_df['dividend_yield_ttm'].values
    print(f"\n测试归一化:")
    print(f"  values类型: {values.dtype}")
    print(f"  values: {values}")
    
    result = min_max_normalize(values, values[0])
    print(f"  归一化结果: {result}")
    
    print("✓ 测试1通过")
    
    # 测试2: 筛选函数
    print("\n【测试2】筛选函数测试")
    print("-"*70)
    
    from server.services.scorer import filter_stocks
    
    test_data = {
        'code': ['000001', '000002', '600000'],
        'name': ['平安银行', '万科A', '浦发银行'],
        'dividend_yield_ttm': [4.5, 3.2, 4.0],
        'market_cap': [2500, 1800, 2000],
        'annual_vol': [20.5, 18.3, 22.0],
        'basic_eps': [1.2, 0.9, 1.1],
        'dividend_years': [10, 8, 12],
        'roe': [12.5, 15.0, 13.8],
        'debt_ratio': [85, 70, 88],
        'industry': ['银行', '地产', '银行'],
        'payout_ratio': [40, 35, 42]
    }
    
    df = pd.DataFrame(test_data)
    print(f"测试数据: {len(df)}条")
    
    try:
        result = filter_stocks(df)
        print(f"✓ 筛选成功: {len(result)}条")
    except Exception as e:
        print(f"✗ 筛选失败: {e}")
        traceback.print_exc()
        result = pd.DataFrame()
    
    # 测试3: 评分函数
    print("\n【测试3】评分函数测试")
    print("-"*70)
    
    from server.services.scorer import calculate_scores
    
    if not result.empty:
        try:
            scored = calculate_scores(result)
            print(f"✓ 评分成功: {len(scored)}条")
            if not scored.empty:
                print(f"评分范围: {scored['composite_score'].min():.2f} - {scored['composite_score'].max():.2f}")
        except Exception as e:
            print(f"✗ 评分失败: {e}")
            traceback.print_exc()

print("\n"+"="*70)
print("所有基础测试完成!")
print("="*70)
