#!/usr/bin/env python3
"""
检查真实数据的负债率情况
"""
import sys
sys.path.insert(0, '.')

from server.services.fetcher import merge_all_data
import pandas as pd

print("获取真实数据...")
merged = merge_all_data()

print(f"\n总数据: {len(merged)} 条")
print(f"\n字段: {list(merged.columns)}")

if not merged.empty:
    print("\n负债率统计:")
    print(merged['debt_ratio'].describe())
    
    print("\n行业分布:")
    from server.services.scorer import normalize_industry
    merged['industry_norm'] = merged['industry'].fillna('').apply(normalize_industry)
    print(merged.groupby('industry_norm').agg({
        'code': 'count',
        'debt_ratio': ['mean', 'max']
    }).round(2))
    
    print("\n金融地产行业负债率情况:")
    from server.services.scorer import FINANCE_INDUSTRIES
    finance = merged[merged['industry_norm'].isin(FINANCE_INDUSTRIES)]
    if not finance.empty:
        print(finance[['code', 'name', 'debt_ratio', 'industry_norm']].sort_values('debt_ratio'))
        print(f"\n负债率 ≤ 85% 的: {len(finance[finance['debt_ratio'] <= 85.0])} 条")
        print(f"负债率 > 85% 的: {len(finance[finance['debt_ratio'] > 85.0])} 条")
