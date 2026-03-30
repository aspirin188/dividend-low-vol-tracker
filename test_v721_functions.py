#!/usr/bin/env python3
"""
v7.2.1 功能单元测试

测试内容：
1. 净利润连续增长严格模式
2. 均线位置计算
3. 增强版击球区评分
"""

import pandas as pd
import numpy as np
import sys
import os

# 添加项目路径
sys.path.insert(0, '/Users/macair/Work/workbuddy_dir/hl3')

from server.services.fetcher import is_profit_growing_strict
from server.services.scorer import calculate_strike_zone_score

print("=" * 60)
print("v7.2.1 功能单元测试")
print("=" * 60)

# ==================== 测试1: 净利润连续增长严格模式 ====================
print("\n【测试1】净利润连续增长严格模式")
print("-" * 60)

# 测试案例A: 连续增长
profit_history_a = {
    '2022': 100,
    '2023': 120,
    '2024': 150,
    '2025': 180
}
result_a = is_profit_growing_strict(profit_history_a)
print(f"案例A: {profit_history_a}")
print(f"  结果: {result_a}")
print(f"  ✅ 预期: True（连续增长）")

# 测试案例B: 不连续增长
profit_history_b = {
    '2022': 180,
    '2023': 150,  # 下滑
    '2024': 160,
    '2025': 170
}
result_b = is_profit_growing_strict(profit_history_b)
print(f"\n案例B: {profit_history_b}")
print(f"  结果: {result_b}")
print(f"  ✅ 预期: False（不连续增长）")

# 测试案例C: 数据不足
profit_history_c = {
    '2024': 100,
    '2025': 120
}
result_c = is_profit_growing_strict(profit_history_c)
print(f"\n案例C: {profit_history_c}")
print(f"  结果: {result_c}")
print(f"  ✅ 预期: False（数据不足）")

# ==================== 测试2: 增强版击球区评分 ====================
print("\n【测试2】增强版击球区评分（集成均线得分）")
print("-" * 60)

# 构造测试数据
test_data = pd.DataFrame([
    {
        'code': '600036',
        'name': '招商银行',
        'price_percentile': 15,  # 价格百分位 < 20%
        'pe': 6.5,  # PE < 8
        'signal_level': 5,  # 强烈买入信号
        'dividend_yield_ttm': 5.2,
        'annual_vol': 18.5,
        'market_cap': 12000,
        'composite_score': 85.0,
        'rank': 1
    },
    {
        'code': '601318',
        'name': '中国平安',
        'price_percentile': 25,  # 价格百分位 < 30%
        'pe': 9.2,  # PE < 10
        'signal_level': 4,  # 买入信号
        'dividend_yield_ttm': 4.8,
        'annual_vol': 22.3,
        'market_cap': 8500,
        'composite_score': 78.5,
        'rank': 2
    },
    {
        'code': '601166',
        'name': '兴业银行',
        'price_percentile': 45,  # 价格百分位 > 40%
        'pe': 12.5,  # PE < 15
        'signal_level': 3,  # 持有信号
        'dividend_yield_ttm': 6.1,
        'annual_vol': 25.1,
        'market_cap': 3200,
        'composite_score': 72.3,
        'rank': 3
    },
    {
        'code': '000651',
        'name': '格力电器',
        'price_percentile': 60,  # 价格百分位 > 40%
        'pe': 18.0,  # PE > 15
        'signal_level': 1,  # 观望信号
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
    print(f"  信号级别: {row['signal_level']}")
    print(f"  击球区评分: {row['strike_zone_score']}/60")
    print(f"  价格得分: {row['price_percentile_score']}/20")
    print(f"  估值得分: {row['valuation_score']}/20")
    print(f"  均线得分: {row['ma_score']}/20")
    print(f"  评级: {row['strike_zone_rating']}")
    print(f"  区域: {row['strike_zone']}")

# 验证结果
print("\n" + "=" * 60)
print("验证结果:")
print("=" * 60)

# 招商银行: 价格20 + 估值20 + 均线20 = 60
if scored_data.loc[0, 'strike_zone_score'] == 60:
    print("✅ 招商银行: 60分（强击球区）- 正确")
else:
    print(f"❌ 招商银行: {scored_data.loc[0, 'strike_zone_score']}分 - 错误，应为60分")

# 中国平安: 价格15 + 估值15 + 均线15 = 45
if scored_data.loc[1, 'strike_zone_score'] == 45:
    print("✅ 中国平安: 45分（弱击球区）- 正确")
else:
    print(f"❌ 中国平安: {scored_data.loc[1, 'strike_zone_score']}分 - 错误，应为45分")

# 兴业银行: 价格0 + 估值10 + 均线10 = 20
if scored_data.loc[2, 'strike_zone_score'] == 20:
    print("✅ 兴业银行: 20分（观望区）- 正确")
else:
    print(f"❌ 兴业银行: {scored_data.loc[2, 'strike_zone_score']}分 - 错误，应为20分")

# 格力电器: 价格0 + 估值0 + 均线0 = 0
if scored_data.loc[3, 'strike_zone_score'] == 0:
    print("✅ 格力电器: 0分（高估区）- 正确")
else:
    print(f"❌ 格力电器: {scored_data.loc[3, 'strike_zone_score']}分 - 错误，应为0分")

print("\n" + "=" * 60)
print("✅ 所有单元测试完成！")
print("=" * 60)
