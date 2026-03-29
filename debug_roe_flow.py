#!/usr/bin/env python3
"""调试ROE数据流"""
import sys
sys.path.insert(0, '.')

import pandas as pd
from server.services.fetcher import fetch_all_quotes, fetch_eps_batch

print("=" * 60)
print("步骤1: 获取行情数据")
print("=" * 60)
quotes = fetch_all_quotes()
print(f"行情列名: {quotes.columns.tolist()}")
print(f"行情行数: {len(quotes)}")

print("\n" + "=" * 60)
print("步骤2: 获取EPS+ROE数据")
print("=" * 60)
eps_df = fetch_eps_batch()
print(f"EPS列名: {eps_df.columns.tolist()}")
print(f"EPS行数: {len(eps_df)}")

if 'roe' in eps_df.columns:
    roe_count = eps_df['roe'].notna().sum()
    print(f"✅ ROE列存在，非空数量: {roe_count}")
    print("\nROE示例数据:")
    sample = eps_df[eps_df['roe'].notna()][['code', 'basic_eps', 'roe']].head(5)
    print(sample.to_string(index=False))
else:
    print("❌ ROE列不存在！")

print("\n" + "=" * 60)
print("步骤3: 合并数据")
print("=" * 60)
merged = quotes.merge(eps_df, on='code', how='left')
print(f"合并后列名: {merged.columns.tolist()}")

if 'roe' in merged.columns:
    roe_count = merged['roe'].notna().sum()
    print(f"✅ 合并后ROE列存在，非空数量: {roe_count}")
else:
    print("❌ 合并后ROE列不存在！")

# 检查具体股票
print("\n检查中远海控(601919)的数据:")
row = merged[merged['code'] == '601919']
if not row.empty:
    print(f"  basic_eps: {row['basic_eps'].values[0]}")
    if 'roe' in merged.columns:
        print(f"  roe: {row['roe'].values[0]}")
    else:
        print("  roe: 列不存在")
else:
    print("  未找到该股票")

print("\n检查招商银行(600036)的数据:")
row = merged[merged['code'] == '600036']
if not row.empty:
    print(f"  basic_eps: {row['basic_eps'].values[0]}")
    if 'roe' in merged.columns:
        print(f"  roe: {row['roe'].values[0]}")
    else:
        print("  roe: 列不存在")
else:
    print("  未找到该股票")
