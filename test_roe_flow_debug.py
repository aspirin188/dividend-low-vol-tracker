#!/usr/bin/env python3
"""
调试ROE数据流 - 不依赖网络，只检查逻辑
"""
import pandas as pd
import numpy as np

print("=" * 60)
print("ROE数据流调试")
print("=" * 60)

# 模拟数据流
# 阶段1: fetch_eps_batch() 返回的数据
print("\n[阶段1] fetch_eps_batch() 返回:")
eps_data = pd.DataFrame({
    'code': ['601939', '600036', '601318', '000651'],
    'basic_eps': [1.23, 5.67, 3.45, 4.56],
    'roe': [12.5, 14.49, 10.2, 22.6],
    'report_year': [2024, 2024, 2024, 2024]
})
print(eps_data)

# 阶段2: merge with quotes
print("\n[阶段2] merge with quotes:")
quotes_data = pd.DataFrame({
    'code': ['601939', '600036', '601318', '000651'],
    'name': ['建设银行', '招商银行', '中国平安', '格力电器'],
    'price': [8.52, 35.6, 45.2, 42.1],
    'market_cap': [2000, 8500, 8000, 2500],
    'industry': ['银行Ⅱ', '银行Ⅱ', '保险Ⅱ', '白色家电']
})
merged = quotes_data.merge(eps_data, on='code', how='left')
print(merged)
print(f"ROE非空: {merged['roe'].notna().sum()}/{len(merged)}")

# 阶段3: 初筛（市值>=500, EPS>0）
print("\n[阶段3] 初筛后:")
pre_filtered = merged[
    (merged['market_cap'] >= 500.0) &
    (merged['basic_eps'] > 0)
].copy()
print(pre_filtered)
print(f"ROE非空: {pre_filtered['roe'].notna().sum()}/{len(pre_filtered)}")

# 阶段4: fetch_dividend_for_candidates() 返回的数据
print("\n[阶段4] fetch_dividend_for_candidates() 返回:")
dividend_data = pd.DataFrame({
    'code': ['601939', '600036', '601318', '000651'],
    'dividend_per_share': [0.397, 2.02, 1.5, 3.0],
    'payout_ratio': [32.3, 35.6, 43.5, 65.8],
    'debt_ratio': [93.2, 91.5, 89.2, 62.1]
    # 注意：v6.12移除了roe字段
})
print(dividend_data)

# 阶段5: merge dividend
print("\n[阶段5] merge dividend后:")
merged2 = pre_filtered.merge(dividend_data, on='code', how='left')
print(merged2)
print(f"ROE非空: {merged2['roe'].notna().sum()}/{len(merged2)}")

# 阶段6: 检查ROE筛选
print("\n[阶段6] ROE筛选:")
roe_filtered = merged2[merged2['roe'] >= 8.0]
print(f"ROE>=8%: {len(roe_filtered)} 只")
print(roe_filtered[['code', 'name', 'roe', 'market_cap']])

print("\n" + "=" * 60)
print("结论:")
print("=" * 60)
print("1. 如果 fetch_eps_batch() 返回了 ROE 数据")
print("2. 第一次 merge 后 ROE 数据仍然存在")
print("3. fetch_dividend_for_candidates() 不再返回 ROE（v6.12修复）")
print("4. 第二次 merge 后 ROE 数据应该保留")
print("5. ROE筛选应该能正常工作")
print("\n问题可能在于:")
print("- fetch_eps_batch() 没有返回ROE数据")
print("- 或者数据在某个merge环节丢失")
