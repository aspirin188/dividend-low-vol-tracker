#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试ROE数据
"""
import sys
import pandas as pd
import akshare as ak

print("开始测试ROE数据获取...", flush=True)

# 测试1: 直接获取数据
print("\n=== 测试1: akshare.stock_yjbb_em ===", flush=True)
try:
    df = ak.stock_yjbb_em(date='20241231')
    print(f"获取 {len(df)} 行数据", flush=True)
    print(f"列名: {df.columns.tolist()}", flush=True)
    
    if '净资产收益率' in df.columns:
        print("✓ 找到'净资产收益率'列", flush=True)
        # 测试几只股票
        for code in ['601939', '600036', '601318']:
            row = df[df['股票代码'] == code]
            if not row.empty:
                print(f"  {code} {row['股票简称'].values[0]}: ROE={row['净资产收益率'].values[0]}", flush=True)
    else:
        print("✗ 未找到'净资产收益率'列", flush=True)
        print(f"实际列名: {df.columns.tolist()}", flush=True)
        
except Exception as e:
    print(f"错误: {e}", flush=True)
    import traceback
    traceback.print_exc()

print("\n测试完成", flush=True)
