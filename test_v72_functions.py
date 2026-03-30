#!/usr/bin/env python3
"""
v7.2 功能单元测试

测试内容：
1. 净利润增速计算函数
2. 现金流质量计算函数
3. 击球区评分计算函数
"""

import pandas as pd
import numpy as np
import sys
import os

# 添加项目路径
sys.path.insert(0, '/Users/macair/Work/workbuddy_dir/hl3')

from server.services.fetcher import calculate_profit_growth_3y, calculate_cashflow_profit_ratio
from server.services.scorer import calculate_strike_zone_score

print("=" * 60)
print("v7.2 功能单元测试")
print("=" * 60)

# ==================== 测试1: 净利润增速计算 ====================
print("\n【测试1】净利润增速计算函数")
print("-" * 60)

# 测试案例A: 正常增长
profit_history_a = {
    '2022': 100,
    '2023': 120,
    '2024': 150,
    '2025': 180
}
cagr_a = calculate_profit_growth_3y(profit_history_a)
print(f"案例A: {profit_history_a}")
print(f"  CAGR: {cagr_a:.4f} ({cagr_a*100:.2f}%)")
print(f"  ✅ 预期: 约 21.6%")

# 测试案例B: 下滑
profit_history_b = {
    '2022': 180,
    '2023': 150,
    '2024': 120,
    '2025': 100
}
cagr_b = calculate_profit_growth_3y(profit_history_b)
print(f"\n案例B: {profit_history_b}")
print(f"  CAGR: {cagr_b:.4f} ({cagr_b*100:.2f}%)")
print(f"  ✅ 预期: 约 -17.8%")

# 测试案例C: 数据不足
profit_history_c = {
    '2024': 100,
    '2025': 120
}
cagr_c = calculate_profit_growth_3y(profit_history_c)
print(f"\n案例C: {profit_history_c}")
print(f"  CAGR: {cagr_c}")
print(f"  ✅ 预期: None（数据不足）")

# ==================== 测试2: 现金流质量计算 ====================
print("\n【测试2】现金流质量计算函数")
print("-" * 60)

# 测试案例A: 优秀
cashflow_a = 150
profit_a = 100
ratio_a = calculate_cashflow_profit_ratio(cashflow_a, profit_a)
print(f"案例A: 现金流={cashflow_a}亿, 净利润={profit_a}亿")
print(f"  比率: {ratio_a:.2f}")
print(f"  ✅ 预期: 1.5（优秀）")

# 测试案例B: 一般
cashflow_b = 80
profit_b = 100
ratio_b = calculate_cashflow_profit_ratio(cashflow_b, profit_b)
print(f"\n案例B: 现金流={cashflow_b}亿, 净利润={profit_b}亿")
print(f"  比率: {ratio_b:.2f}")
print(f"  ✅ 预期: 0.8（一般）")

# 测试案例C: 差
cashflow_c = -10
profit_c = 100
ratio_c = calculate_cashflow_profit_ratio(cashflow_c, profit_c)
print(f"\n案例C: 现金流={cashflow_c}亿, 净利润={profit_c}亿")
print(f"  比率: {ratio_c:.2f}")
print(f"  ✅ 预期: -0.1（差）")

# ==================== 测试3: 击球区评分计算 ====================
print("\n【测试3】击球区评分计算函数")
print("-" * 60)

# 构造测试数据
test_data = pd.DataFrame([
    {
        'code': '600036',
        'name': '招商银行',
        'price_percentile': 15,  # 长期百分位 < 20%
        'pe': 6.5,  # PE < 8
        'dividend_yield_ttm': 5.2,
        'annual_vol': 18.5,
        'market_cap': 12000,
        'composite_score': 85.0,
        'rank': 1
    },
    {
        'code': '601318',
        'name': '中国平安',
        'price_percentile': 25,  # 长期百分位 < 30%
        'pe': 9.2,  # PE < 10
        'dividend_yield_ttm': 4.8,
        'annual_vol': 22.3,
        'market_cap': 8500,
        'composite_score': 78.5,
        'rank': 2
    },
    {
        'code': '601166',
        'name': '兴业银行',
        'price_percentile': 45,  # 长期百分位 > 40%
        'pe': 12.5,  # PE < 15
        'dividend_yield_ttm': 6.1,
        'annual_vol': 25.1,
        'market_cap': 3200,
        'composite_score': 72.3,
        'rank': 3
    },
    {
        'code': '000651',
        'name': '格力电器',
        'price_percentile': 60,  # 长期百分位 > 40%
        'pe': 18.0,  # PE > 15
        'dividend_yield_ttm': 5.5,
        'annual_vol': 28.7,
        'market_cap': 2800,
        'composite_score': 68.9,
        'rank': 4
    }
])

# 计算击球区评分
scored_data = calculate_strike_zone_score(test_data)

print("\n测试结果:")
for idx, row in scored_data.iterrows():
    print(f"\n{row['name']} ({row['code']}):")
    print(f"  价格百分位: {row['price_percentile']}%")
    print(f"  PE: {row['pe']}")
    print(f"  击球区评分: {row['strike_zone_score']}/60")
    print(f"  价格得分: {row['price_percentile_score']}/30")
    print(f"  估值得分: {row['valuation_score']}/30")
    print(f"  评级: {row['strike_zone_rating']}")
    print(f"  区域: {row['strike_zone']}")

# 验证结果
print("\n" + "=" * 60)
print("验证结果:")
print("=" * 60)

# 招商银行
if scored_data.loc[0, 'strike_zone_score'] == 60:
    print("✅ 招商银行: 60分（强击球区）- 正确")
else:
    print(f"❌ 招商银行: {scored_data.loc[0, 'strike_zone_score']}分 - 错误，应为60分")

# 中国平安
if scored_data.loc[1, 'strike_zone_score'] == 40:
    print("✅ 中国平安: 40分（弱击球区）- 正确")
else:
    print(f"❌ 中国平安: {scored_data.loc[1, 'strike_zone_score']}分 - 错误，应为40分")

# 兴业银行
if scored_data.loc[2, 'strike_zone_score'] == 10:
    print("✅ 兴业银行: 10分（观望区）- 正确")
else:
    print(f"❌ 兴业银行: {scored_data.loc[2, 'strike_zone_score']}分 - 错误，应为10分")

# 格力电器
if scored_data.loc[3, 'strike_zone_score'] == 0:
    print("✅ 格力电器: 0分（高估区）- 正确")
else:
    print(f"❌ 格力电器: {scored_data.loc[3, 'strike_zone_score']}分 - 错误，应为0分")

print("\n" + "=" * 60)
print("✅ 所有单元测试完成！")
print("=" * 60)
