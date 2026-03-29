#!/usr/bin/env python3
"""
完整的端到端测试 - 包含ROE数据
"""
import sys
sys.path.insert(0, '.')

print("=" * 60, flush=True)
print("完整流程测试 - ROE数据获取", flush=True)
print("=" * 60, flush=True)

try:
    # 步骤1: 获取行情数据
    print("\n[步骤1] 获取行情数据...", flush=True)
    from server.services.fetcher import fetch_all_quotes
    quotes = fetch_all_quotes()
    print(f"✓ 获取到 {len(quotes)} 只股票的行情", flush=True)
    
    # 步骤2: 获取EPS和ROE数据
    print("\n[步骤2] 获取EPS和ROE数据...", flush=True)
    from server.services.fetcher import fetch_eps_batch
    eps_df = fetch_eps_batch()
    
    if eps_df.empty:
        print("✗ 未获取到EPS和ROE数据", flush=True)
        sys.exit(1)
    
    print(f"✓ 获取到 {len(eps_df)} 只股票的EPS和ROE", flush=True)
    
    # 检查ROE数据
    roe_not_null = eps_df['roe'].notna().sum()
    print(f"ROE非空: {roe_not_null}/{len(eps_df)}", flush=True)
    
    # 步骤3: 合并数据
    print("\n[步骤3] 合并数据...", flush=True)
    merged = quotes.merge(eps_df, on='code', how='left')
    print(f"✓ 合并后 {len(merged)} 行", flush=True)
    
    roe_not_null_after_merge = merged['roe'].notna().sum()
    print(f"合并后ROE非空: {roe_not_null_after_merge}/{len(merged)}", flush=True)
    
    # 步骤4: 初步筛选
    print("\n[步骤4] 初步筛选...", flush=True)
    merged = merged[~merged['name'].str.contains('ST', case=False, na=False)]
    for col in ['market_cap', 'basic_eps']:
        merged[col] = pd.to_numeric(merged[col], errors='coerce')
    
    pre_filtered = merged[
        (merged['market_cap'] >= 500.0) &
        (merged['basic_eps'] > 0) &
        (merged['market_cap'].notna()) &
        (merged['basic_eps'].notna()) &
        (merged['price'].notna()) &
        (merged['price'] > 0)
    ].copy()
    
    print(f"初筛后: {len(pre_filtered)} 只候选股", flush=True)
    print(f"初筛后ROE非空: {pre_filtered['roe'].notna().sum()}/{len(pre_filtered)}", flush=True)
    
    # 步骤5: 检查ROE筛选
    print("\n[步骤5] ROE筛选测试...", flush=True)
    roe_ge_8 = pre_filtered[pre_filtered['roe'] >= 8.0]
    print(f"ROE>=8%: {len(roe_ge_8)} 只", flush=True)
    
    if len(roe_ge_8) > 0:
        print("\n前5只ROE>=8%的股票:", flush=True)
        print(roe_ge_8[['code', 'name', 'roe', 'market_cap']].head().to_string(index=False), flush=True)
        
        print("\n" + "=" * 60, flush=True)
        print("✓ 测试成功! ROE数据获取和筛选正常", flush=True)
        print("=" * 60, flush=True)
    else:
        print("\n✗ 没有股票ROE>=8%", flush=True)
        print("\nROE分布:", flush=True)
        print(pre_filtered['roe'].describe(), flush=True)
        
except Exception as e:
    print(f"\n✗ 测试失败: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

import pandas as pd
