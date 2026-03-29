#!/usr/bin/env python3
"""测试prepare_results()函数"""
import sys
sys.path.insert(0, '.')

import pandas as pd
from server.services.scorer import filter_stocks, calculate_scores, prepare_results

# 创建测试数据
test_data = pd.DataFrame({
    'code': ['601919', '600036'],
    'name': ['中远海控', '招商银行'],
    'price': [14.5, 35.2],
    'pe': [4.7, 6.2],
    'pb': [1.1, 0.9],
    'market_cap': [1800.0, 8500.0],
    'industry': ['航运', '银行'],
    'basic_eps': [3.08, 5.66],
    'roe': [22.6, 14.49],
    'dividend_yield_ttm': [5.2, 5.1],
    'annual_vol': [35.2, 28.5],
    'dividend_years': [5, 5],
    'payout_ratio': [30.0, 32.0],
    'debt_ratio': [45.0, 92.0],
    'report_year': [2024, 2024],
})

print("测试数据:")
print(test_data[['code', 'name', 'roe', 'debt_ratio']].to_string(index=False))

print("\\n" + "=" * 60)
print("测试filter_stocks()")
print("=" * 60)
filtered = filter_stocks(test_data)
print(f"筛选后: {len(filtered)} 只")
if not filtered.empty:
    print(f"列名: {filtered.columns.tolist()}")
    if 'roe' in filtered.columns:
        print(f"ROE非空: {filtered['roe'].notna().sum()}/{len(filtered)}")
        print("✅ filter_stocks()保留ROE列")
    else:
        print("❌ filter_stocks()丢失ROE列")
else:
    print("⚠️ 所有股票被过滤")

print("\\n" + "=" * 60)
print("测试calculate_scores()")
print("=" * 60)
if not filtered.empty:
    scored = calculate_scores(filtered)
    print(f"评分后: {len(scored)} 只")
    if 'roe' in scored.columns:
        print(f"ROE非空: {scored['roe'].notna().sum()}/{len(scored)}")
        print("✅ calculate_scores()保留ROE列")
    else:
        print("❌ calculate_scores()丢失ROE列")

    print("\\n" + "=" * 60)
    print("测试prepare_results()")
    print("=" * 60)
    result = prepare_results(scored)
    print(f"最终结果: {len(result)} 只")
    print(f"列名: {result.columns.tolist()}")
    if 'roe' in result.columns:
        print(f"ROE非空: {result['roe'].notna().sum()}/{len(result)}")
        print("✅ prepare_results()保留ROE列")
        print("\\n最终数据:")
        print(result[['code', 'name', 'roe']].to_string(index=False))
    else:
        print("❌ prepare_results()丢失ROE列")
