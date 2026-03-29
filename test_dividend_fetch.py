#!/usr/bin/env python3
"""
检查分红数据获取问题
"""
import sys
sys.path.insert(0, '.')

print("测试分红数据获取...", flush=True)

# 测试几只已知有分红的股票
test_codes = ['601939', '600036', '601318']

from server.services.fetcher import fetch_dividend_for_candidates
import pandas as pd

print(f"\n测试股票: {test_codes}", flush=True)
div_df = fetch_dividend_for_candidates(test_codes)

print(f"\n返回数据:", flush=True)
print(div_df, flush=True)

print(f"\n列名: {div_df.columns.tolist()}", flush=True)
print(f"行数: {len(div_df)}", flush=True)

if len(div_df) > 0:
    for col in ['dividend_per_share', 'payout_ratio', 'debt_ratio']:
        if col in div_df.columns:
            print(f"{col}: {div_df[col].tolist()}", flush=True)
else:
    print("\n⚠️ 分红数据返回为空！", flush=True)
    print("可能原因:", flush=True)
    print("  1. 股票代码不在接口返回的数据中", flush=True)
    print("  2. 接口查询失败", flush=True)
    print("  3. 这些股票没有分红数据", flush=True)
