#!/usr/bin/env python3
"""
完整追踪测试 - 找出"Expected numeric dtype, got object instead"错误
"""
import os
import sys
import pandas as pd
import numpy as np
import traceback

sys.path.insert(0, os.path.dirname(__file__))

print("=" * 60)
print("步骤1: 测试数据获取")
print("=" * 60)

try:
    from server.services.fetcher import merge_all_data
    
    print("正在调用 merge_all_data()...")
    df = merge_all_data()
    
    if df is None:
        print("✗ merge_all_data() 返回 None")
        sys.exit(1)
    
    if df.empty:
        print("✗ merge_all_data() 返回空DataFrame")
        sys.exit(1)
    
    print(f"✓ 数据获取成功: {len(df)}条")
    print(f"列名: {list(df.columns)}")
    print("\n各列数据类型:")
    for col in df.columns:
        dtype = df[col].dtype
        print(f"  {col:30s} {dtype}")
        if dtype == 'object':
            # 显示object类型列的样本值
            sample = df[col].dropna().head(3).tolist()
            print(f"    样本值: {sample}")
    
except Exception as e:
    print(f"✗ 数据获取失败: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("步骤2: 测试筛选")
print("=" * 60)

try:
    from server.services.scorer import filter_stocks
    
    print("正在调用 filter_stocks()...")
    result = filter_stocks(df)
    
    print(f"✓ 筛选成功: {len(result)}条")
    
except Exception as e:
    print(f"✗ 筛选失败: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("步骤3: 测试评分")
print("=" * 60)

try:
    from server.services.scorer import calculate_scores
    
    print("正在调用 calculate_scores()...")
    result = calculate_scores(result)
    
    print(f"✓ 评分成功: {len(result)}条")
    
except Exception as e:
    print(f"✗ 评分失败: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("所有测试通过!")
print("=" * 60)
