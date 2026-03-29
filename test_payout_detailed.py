#!/usr/bin/env python3
"""
简化测试 - 只测试关键部分
"""
import sys
sys.path.insert(0, '.')

print("测试开始...", flush=True)

try:
    import pandas as pd
    import numpy as np

    # 模拟数据流
    print("\n[1] 模拟fetch_eps_batch数据", flush=True)
    eps_data = {
        'code': ['601939', '600036', '601318'],
        'basic_eps': [1.23, 5.67, 3.45],
        'roe': [10.69, 14.49, 13.8],
    }
    eps_df = pd.DataFrame(eps_data)
    print(eps_df, flush=True)

    print("\n[2] 模拟fetch_dividend_for_candidates数据", flush=True)
    div_data = {
        'code': ['601939', '600036', '601318'],
        'dividend_per_share': [0.397, 2.02, 1.5],
        'payout_ratio': [None, None, None],  # 可能是None
        'debt_ratio': [None, None, None],
    }
    div_df = pd.DataFrame(div_data)
    print(div_df, flush=True)

    print("\n[3] 合并数据", flush=True)
    merged = eps_df.merge(div_df, on='code', how='left')
    print(merged, flush=True)

    print("\n[4] 重新计算支付率", flush=True)

    # 这是修复后的逻辑
    merged['payout_ratio'] = None
    mask = (merged['dividend_per_share'].notna()) & (merged['basic_eps'] > 0)

    print(f"mask: {mask}", flush=True)
    print(f"dividend_per_share: {merged['dividend_per_share'].values}", flush=True)
    print(f"basic_eps: {merged['basic_eps'].values}", flush=True)

    # 计算支付率
    payout = merged.loc[mask, 'dividend_per_share'] / merged.loc[mask, 'basic_eps'] * 100
    print(f"计算出的支付率: {payout.values}", flush=True)

    merged.loc[mask, 'payout_ratio'] = payout.round(2)

    print("\n[5] 最终结果", flush=True)
    print(merged[['code', 'basic_eps', 'dividend_per_share', 'payout_ratio', 'roe']], flush=True)

    print("\n✅ 测试成功！", flush=True)

except Exception as e:
    print(f"\n❌ 错误: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)
