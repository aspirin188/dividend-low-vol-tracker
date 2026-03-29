#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试ROE数据 - 使用已有的测试数据"""
import pandas as pd

# 创建一个简单的测试DataFrame
test_data = {
    '股票代码': ['601939', '600036', '601318'],
    '股票简称': ['建设银行', '招商银行', '中国平安'],
    '每股收益': [1.23, 5.67, 3.45],
    '净资产收益率': [12.5, 14.49, 10.2]
}

df = pd.DataFrame(test_data)
print("测试DataFrame:")
print(df)
print(f"\n列名: {df.columns.tolist()}")
print(f"ROE数据: {df['净资产收益率'].tolist()}")

# 模拟 fetch_eps_batch 的逻辑
result = pd.DataFrame({
    'code': df['股票代码'].values,
    'basic_eps': pd.to_numeric(df['每股收益'], errors='coerce').values,
    'roe': pd.to_numeric(df['净资产收益率'], errors='coerce').values,
})
print("\n模拟 fetch_eps_batch 结果:")
print(result)
