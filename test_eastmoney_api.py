#!/usr/bin/env python3
"""
直接测试东方财富业绩报表API
"""
import requests
import json
import pandas as pd

print("测试东方财富业绩报表API...\n", flush=True)

# 东方财富业绩报表接口 (stock_yjbb_em 的数据源)
url = "https://datacenter-web.eastmoney.com/api/data/v1/get"

params = {
    "reportName": "RPT_LICO_FN_CPD",
    "columns": "SECURITY_CODE,SECURITY_NAME_ABBR,UPDATE_DATE,BASIC_EPS,WEIGHTEDAVERAGEORE",
    "filter": '(DATEMMDD="年报")',
    "pageNumber": 1,
    "pageSize": 100,
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
    print(f"请求URL: {url}", flush=True)
    print(f"参数: reportName=RPT_LICO_FN_CPD", flush=True)
    print(f"查询字段: SECURITY_CODE, SECURITY_NAME_ABBR, BASIC_EPS, WEIGHTEDAVERAGEORE", flush=True)
    
    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    
    data = response.json()
    
    if data.get("success") and data.get("result"):
        items = data["result"].get("data", [])
        print(f"\n✓ 成功获取 {len(items)} 条数据", flush=True)
        
        # 转换为DataFrame
        df = pd.DataFrame(items)
        print(f"\n列名: {df.columns.tolist()}", flush=True)
        
        # 检查 WEIGHTEDAVERAGEORE 字段
        if 'WEIGHTEDAVERAGEORE' in df.columns:
            print(f"\n✓ 找到 WEIGHTEDAVERAGEORE (ROE) 字段", flush=True)
            
            # 查看前几行
            print("\n前5行数据:", flush=True)
            print(df[['SECURITY_CODE', 'SECURITY_NAME_ABBR', 'BASIC_EPS', 'WEIGHTEDAVERAGEORE']].head(), flush=True)
            
            # 检查ROE数据是否为空
            roe_not_null = df['WEIGHTEDAVERAGEORE'].notna().sum()
            print(f"\nROE非空: {roe_not_null}/{len(df)}", flush=True)
            
        else:
            print(f"\n✗ 未找到 WEIGHTEDAVERAGEORE 字段", flush=True)
            print(f"可用字段: {df.columns.tolist()}", flush=True)
            
    else:
        print(f"\n✗ 接口返回失败", flush=True)
        print(f"响应: {data}", flush=True)
        
except requests.exceptions.Timeout:
    print(f"\n✗ 请求超时", flush=True)
except requests.exceptions.RequestException as e:
    print(f"\n✗ 请求错误: {e}", flush=True)
except Exception as e:
    print(f"\n✗ 错误: {e}", flush=True)
    import traceback
    traceback.print_exc()

print("\n测试完成", flush=True)
