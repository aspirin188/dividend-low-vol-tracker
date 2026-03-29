#!/usr/bin/env python3
"""
测试改进后的 fetch_eps_batch 函数
"""
import sys
sys.path.insert(0, '.')

from server.services.fetcher import fetch_eps_batch

print("=" * 60)
print("测试改进后的 fetch_eps_batch 函数")
print("=" * 60)

result = fetch_eps_batch()

if not result.empty:
    print(f"\n✓ 成功获取 {len(result)} 条数据")
    print(f"列名: {result.columns.tolist()}")
    
    # ROE统计
    roe_not_null = result['roe'].notna().sum()
    print(f"ROE非空: {roe_not_null}/{len(result)}")
    
    # ROE>=8%的股票
    roe_ge_8 = result[result['roe'] >= 8.0]
    print(f"ROE>=8%: {len(roe_ge_8)} 只")
    
    # 显示几只股票
    print("\n示例股票:")
    sample_codes = ['601939', '600036', '601318', '000651', '601288']
    for code in sample_codes:
        row = result[result['code'] == code]
        if not row.empty:
            eps = row['basic_eps'].values[0]
            roe = row['roe'].values[0]
            print(f"  {code}: EPS={eps:.2f}, ROE={roe:.2f}%")
else:
    print("\n✗ 未获取到数据")
