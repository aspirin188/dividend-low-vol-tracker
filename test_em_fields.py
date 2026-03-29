#!/usr/bin/env python3
"""
检查东方财富接口支持的字段
"""
import requests
import pandas as pd

print("检查东方财富业绩报表接口支持的字段...\n", flush=True)

url = "https://datacenter-web.eastmoney.com/api/data/v1/get"

# 测试1: 不指定columns，获取所有字段
params = {
    "reportName": "RPT_LICO_FN_CPD",
    "filter": '(DATEMMDD="年报")',
    "pageNumber": 1,
    "pageSize": 10,
    "sortTypes": -1,
    "sortColumns": "UPDATE_DATE",
    "source": "WEB",
    "client": "WEB",
}

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://data.eastmoney.com/",
}

try:
    print("测试1: 获取所有可用字段", flush=True)
    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()
    
    if data.get("success") and data.get("result"):
        items = data["result"].get("data", [])
        if items:
            print(f"✓ 获取到 {len(items)} 条数据", flush=True)
            df = pd.DataFrame(items)
            print(f"\n所有可用字段 ({len(df.columns)} 个):", flush=True)
            for col in sorted(df.columns):
                print(f"  - {col}", flush=True)
            
            # 查看示例数据
            print("\n示例数据 (前3行):", flush=True)
            print(df.head(3), flush=True)
            
            # 查找ROE相关字段
            roe_fields = [col for col in df.columns if 'ROE' in col.upper() or 'ROA' in col.upper() or '收益' in col or 'ROE' in col]
            if roe_fields:
                print(f"\n✓ 找到ROE相关字段:", flush=True)
                for field in roe_fields:
                    print(f"  - {field}", flush=True)
            else:
                print(f"\n✗ 未找到ROE相关字段", flush=True)
    else:
        print(f"✗ 获取失败: {data.get('message')}", flush=True)
        
except Exception as e:
    print(f"✗ 错误: {e}", flush=True)
    import traceback
    traceback.print_exc()

print("\n测试完成", flush=True)
