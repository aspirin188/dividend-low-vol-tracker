#!/usr/bin/env python3
"""
详细调试筛选逻辑
"""
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("调试筛选逻辑")
print("=" * 60)

# 模拟一条数据，检查筛选条件
import pandas as pd
import numpy as np
from server.services.scorer import (
    MIN_DIVIDEND_YIELD, MAX_DIVIDEND_YIELD, MIN_MARKET_CAP,
    MAX_PAYOUT_RATIO, MIN_EPS, MIN_DIVIDEND_YEARS, MIN_ROE,
    MAX_DEBT_RATIO, MAX_DEBT_RATIO_FINANCE, FINANCE_INDUSTRIES
)

print(f"\n筛选条件:")
print(f"  股息率: {MIN_DIVIDEND_YIELD}% - {MAX_DIVIDEND_YIELD}%")
print(f"  市值: ≥{MIN_MARKET_CAP}亿")
print(f"  EPS: >{MIN_EPS}")
print(f"  连续分红年数: ≥{MIN_DIVIDEND_YEARS}年")
print(f"  ROE: ≥{MIN_ROE}%")
print(f"  负债率: ≤{MAX_DEBT_RATIO}%(金融地产≤{MAX_DEBT_RATIO_FINANCE}%)")

# 创建测试数据
test_data = {
    'code': ['601919', '601166', '000001'],
    'name': ['中远海控', '兴业银行', '平安银行'],
    'dividend_yield_ttm': [5.0, 6.0, 7.0],
    'market_cap': [800.0, 1200.0, 900.0],
    'basic_eps': [1.5, 2.0, 1.8],
    'payout_ratio': [30.0, 25.0, 28.0],
    'annual_vol': [25.0, 20.0, 22.0],
    'dividend_years': [3, 5, 4],
    'roe': [12.0, 11.0, 10.0],
    'debt_ratio': [65.0, 92.0, 91.0],
    'industry': ['交运', '金融', '金融'],
    'price': [10.0, 15.0, 12.0],
    'pe': [6.67, 7.5, 6.67],
    'pb': [0.8, 0.6, 0.7],
}

df = pd.DataFrame(test_data)
print(f"\n测试数据 ({len(df)} 条):")
print(df[['code', 'name', 'dividend_yield_ttm', 'market_cap', 'roe', 'debt_ratio', 'industry']])

# 执行筛选
from server.services.scorer import filter_stocks

print("\n开始筛选...")
try:
    filtered = filter_stocks(df)
    print(f"✓ 筛选后 {len(filtered)} 条")
    if len(filtered) > 0:
        print(filtered[['code', 'name', 'roe', 'debt_ratio', 'industry']])
    else:
        print("✗ 没有符合条件的股票")
        print("\n逐条检查:")
        for idx, row in df.iterrows():
            print(f"\n{row['code']} {row['name']}:")
            print(f"  股息率 {row['dividend_yield_ttm']} >= {MIN_DIVIDEND_YIELD}: {row['dividend_yield_ttm'] >= MIN_DIVIDEND_YIELD}")
            print(f"  市值 {row['market_cap']} >= {MIN_MARKET_CAP}: {row['market_cap'] >= MIN_MARKET_CAP}")
            print(f"  EPS {row['basic_eps']} > {MIN_EPS}: {row['basic_eps'] > MIN_EPS}")
            print(f"  分红年数 {row['dividend_years']} >= {MIN_DIVIDEND_YEARS}: {row['dividend_years'] >= MIN_DIVIDEND_YEARS}")
            print(f"  ROE {row['roe']} >= {MIN_ROE}: {row['roe'] >= MIN_ROE}")
            
            # 检查负债率
            from server.services.scorer import normalize_industry
            industry_norm = normalize_industry(row['industry'])
            max_debt = MAX_DEBT_RATIO_FINANCE if industry_norm in FINANCE_INDUSTRIES else MAX_DEBT_RATIO
            print(f"  负债率 {row['debt_ratio']} <= {max_debt} ({industry_norm}): {row['debt_ratio'] <= max_debt}")
            
            # 检查是否因为负债率被过滤
            if industry_norm in FINANCE_INDUSTRIES and row['debt_ratio'] > MAX_DEBT_RATIO_FINANCE:
                print(f"  ❌ 金融地产负债率超标!")
except Exception as e:
    print(f"✗ 筛选错误: {e}")
    import traceback
    traceback.print_exc()
