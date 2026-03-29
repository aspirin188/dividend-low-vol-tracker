#!/usr/bin/env python3
"""
最小化测试 - 只测试merge_all_data的前几步
"""
import sys
sys.path.insert(0, '.')

print("测试 merge_all_data 前几步...", flush=True)

try:
    from server.services.fetcher import fetch_all_quotes, fetch_eps_batch
    import pandas as pd

    print("\n[1] fetch_all_quotes", flush=True)
    quotes = fetch_all_quotes()
    print(f"✓ 获取 {len(quotes)} 只股票", flush=True)

    print("\n[2] fetch_eps_batch", flush=True)
    eps_df = fetch_eps_batch()
    if eps_df.empty:
        print("✗ 未获取到EPS数据", flush=True)
        sys.exit(1)
    print(f"✓ 获取 {len(eps_df)} 只股票的EPS和ROE", flush=True)

    print("\n[3] merge", flush=True)
    merged = quotes.merge(eps_df, on='code', how='left')
    print(f"✓ 合并后 {len(merged)} 行", flush=True)

    print("\n[4] 检查数据类型", flush=True)
    print(f"  basic_eps dtype: {merged['basic_eps'].dtype}", flush=True)
    print(f"  roe dtype: {merged['roe'].dtype}", flush=True)

    print("\n[5] 初步筛选", flush=True)
    merged = merged[~merged['name'].str.contains('ST', case=False, na=False)]

    for col in ['market_cap', 'basic_eps']:
        print(f"  转换 {col} 为数值类型...", flush=True)
        merged[col] = pd.to_numeric(merged[col], errors='coerce')
        print(f"    {col} dtype after conversion: {merged[col].dtype}", flush=True)

    pre_filtered = merged[
        (merged['market_cap'] >= 500.0) &
        (merged['basic_eps'] > 0) &
        (merged['market_cap'].notna()) &
        (merged['basic_eps'].notna()) &
        (merged['price'].notna()) &
        (merged['price'] > 0)
    ].copy()

    print(f"✓ 初筛后 {len(pre_filtered)} 只候选股", flush=True)

    print("\n✅ 测试成功！前几步没有错误", flush=True)

except Exception as e:
    print(f"\n❌ 错误: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)
