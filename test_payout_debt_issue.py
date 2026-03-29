#!/usr/bin/env python3
"""
诊断支付率和负债率数据缺失问题
"""
import sys
sys.path.insert(0, '.')

print("=" * 60, flush=True)
print("诊断支付率和负债率数据缺失", flush=True)
print("=" * 60, flush=True)

# 测试1: 检查东方财富接口返回的数据
print("\n[测试1] 检查东方财富接口返回的数据", flush=True)

import requests

url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
params = {
    'reportName': 'RPT_LICO_FN_CPD',
    'columns': 'SECURITY_CODE,SECURITY_NAME_ABBR,BASIC_EPS,ASSIGNDSCRPT,ASSETLIABRATIO',
    'filter': '(DATEMMDD="年报")',
    'pageNumber': 1,
    'pageSize': 10,
    'sortTypes': -1,
    'sortColumns': 'REPORTDATE',
    'source': 'WEB',
    'client': 'WEB',
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://data.eastmoney.com/',
}

try:
    response = requests.get(url, params=params, headers=headers, timeout=30)
    data = response.json()

    if data.get('success'):
        items = data['result'].get('data', [])
        print(f"✓ 成功获取 {len(items)} 条数据", flush=True)

        # 检查字段
        import pandas as pd
        df = pd.DataFrame(items)
        print(f"\n列名: {df.columns.tolist()}", flush=True)

        # 检查ASSETLIABRATIO字段
        if 'ASSETLIABRATIO' in df.columns:
            print("\n✓ ASSETLIABRATIO 字段存在", flush=True)
            # 检查数据是否为空
            not_null = df['ASSETLIABRATIO'].notna().sum()
            print(f"ASSETLIABRATIO 非空: {not_null}/{len(df)}", flush=True)

            # 显示示例
            print("\n示例数据:", flush=True)
            print(df[['SECURITY_CODE', 'SECURITY_NAME_ABBR', 'BASIC_EPS', 'ASSETLIABRATIO']].head(), flush=True)
        else:
            print("\n✗ ASSETLIABRATIO 字段不存在", flush=True)

        # 检查BASIC_EPS字段
        if 'BASIC_EPS' in df.columns:
            print(f"\n✓ BASIC_EPS 字段存在", flush=True)
            eps_not_null = df['BASIC_EPS'].notna().sum()
            print(f"BASIC_EPS 非空: {eps_not_null}/{len(df)}", flush=True)
        else:
            print("\n✗ BASIC_EPS 字段不存在", flush=True)

    else:
        print(f"✗ 接口返回失败: {data.get('message')}", flush=True)

except Exception as e:
    print(f"✗ 错误: {e}", flush=True)
    import traceback
    traceback.print_exc()

# 测试2: 测试实际的支付率计算
print("\n" + "=" * 60, flush=True)
print("[测试2] 测试支付率计算", flush=True)
print("=" * 60, flush=True)

# 模拟数据
test_data = [
    {'code': '601939', 'name': '建设银行', 'desc': '10派3.97元(含税)', 'eps': 1.23},
    {'code': '600036', 'name': '招商银行', 'desc': '10派20.2元(含税)', 'eps': 5.67},
]

for item in test_data:
    code = item['code']
    name = item['name']
    desc = item['desc']
    eps = item['eps']

    # 解析每股派息
    import re
    m = re.search(r'派([\d.]+)元', desc)
    if m:
        dividend_per_share = float(m.group(1)) / 10.0
        # 计算支付率
        payout_ratio = (dividend_per_share / eps) * 100

        print(f"\n{name} ({code}):", flush=True)
        print(f"  分红方案: {desc}", flush=True)
        print(f"  每股派息: {dividend_per_share:.3f} 元", flush=True)
        print(f"  EPS: {eps:.2f} 元", flush=True)
        print(f"  支付率: {payout_ratio:.2f}%", flush=True)
    else:
        print(f"\n{name} ({code}): 无法解析分红方案", flush=True)

print("\n" + "=" * 60, flush=True)
print("诊断结论", flush=True)
print("=" * 60, flush=True)
print("\n1. ASSETLIABRATIO 字段:", flush=True)
print("   - 如果字段不存在，需要寻找其他数据源", flush=True)
print("   - 如果字段存在但数据为空，可能是接口限制", flush=True)
print("\n2. 支付率计算:", flush=True)
print("   - 计算公式正确", flush=True)
print("   - 问题可能在于:", flush=True)
print("     a) 东方财富接口的BASIC_EPS数据不准确", flush=True)
print("     b) 需要改用fetch_eps_batch()中的EPS数据", flush=True)
