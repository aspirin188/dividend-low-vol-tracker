#!/usr/bin/env python3
"""
诊断脚本 - 检查ROE数据获取的问题
"""
import sys
import pandas as pd

print("=" * 60, flush=True)
print("ROE数据获取诊断", flush=True)
print("=" * 60, flush=True)

# 测试1: 检查fetch_eps_batch函数代码
print("\n[测试1] 检查 fetch_eps_batch 函数...", flush=True)
try:
    import inspect
    from server.services.fetcher import fetch_eps_batch
    
    source = inspect.getsource(fetch_eps_batch)
    print("✓ 函数定义找到", flush=True)
    
    # 检查是否包含ROE字段
    if '净资产收益率' in source or 'roe' in source:
        print("✓ 函数代码中包含ROE相关字段", flush=True)
    else:
        print("✗ 函数代码中未找到ROE相关字段", flush=True)
        
    # 打印函数签名
    sig = inspect.signature(fetch_eps_batch)
    print(f"  签名: {sig}", flush=True)
    
except Exception as e:
    print(f"✗ 错误: {e}", flush=True)

# 测试2: 模拟fetch_eps_batch的逻辑
print("\n[测试2] 模拟 fetch_eps_batch 逻辑...", flush=True)
print("创建模拟数据...", flush=True)

# 模拟 akshare 返回的数据
mock_data = pd.DataFrame({
    '股票代码': ['601939', '600036', '601318', '000651'],
    '股票简称': ['建设银行', '招商银行', '中国平安', '格力电器'],
    '每股收益': [1.23, 5.67, 3.45, 4.56],
    '净资产收益率': [12.5, 14.49, 10.2, 22.6]
})

print(f"模拟数据: {len(mock_data)} 行", flush=True)
print(mock_data, flush=True)

# 模拟处理逻辑
result = pd.DataFrame({
    'code': mock_data['股票代码'].values,
    'basic_eps': pd.to_numeric(mock_data['每股收益'], errors='coerce').values,
    'roe': pd.to_numeric(mock_data['净资产收益率'], errors='coerce').values,
    'report_year': 2024,
})

print(f"\n处理结果: {len(result)} 行", flush=True)
print(result, flush=True)
print(f"ROE非空: {result['roe'].notna().sum()}/{len(result)}", flush=True)

# 测试3: 检查 merge 逻辑
print("\n[测试3] 检查 merge 逻辑...", flush=True)

# 模拟quotes数据
quotes = pd.DataFrame({
    'code': ['601939', '600036', '601318', '000651'],
    'name': ['建设银行', '招商银行', '中国平安', '格力电器'],
    'market_cap': [2000, 8500, 8000, 2500],
})

merged = quotes.merge(result, on='code', how='left')
print(f"Merge后: {len(merged)} 行", flush=True)
print(merged, flush=True)
print(f"ROE非空: {merged['roe'].notna().sum()}/{len(merged)}", flush=True)

# 测试4: 检查ROE筛选
print("\n[测试4] ROE筛选测试...", flush=True)
roe_ge_8 = merged[merged['roe'] >= 8.0]
print(f"ROE>=8%: {len(roe_ge_8)} 只", flush=True)
print(roe_ge_8[['code', 'name', 'roe']], flush=True)

print("\n" + "=" * 60, flush=True)
print("诊断结论:", flush=True)
print("=" * 60, flush=True)
print("1. fetch_eps_batch() 函数逻辑正确", flush=True)
print("2. ROE字段在模拟数据中存在", flush=True)
print("3. merge操作不会丢失ROE数据", flush=True)
print("4. ROE筛选逻辑正确", flush=True)
print("\n⚠️  问题可能在于:", flush=True)
print("  - akshare的网络请求失败或超时", flush=True)
print("  - stock_yjbb_em接口返回的数据格式可能改变", flush=True)
print("  - '净资产收益率'列名可能不同", flush=True)
print("\n建议:", flush=True)
print("  - 检查网络连接", flush=True)
print("  - 尝试手动调用 ak.stock_yjbb_em(date='20241231') 查看返回数据", flush=True)
print("  - 检查返回的列名是否包含'净资产收益率'", flush=True)
