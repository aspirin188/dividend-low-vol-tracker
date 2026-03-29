#!/usr/bin/env python3
"""
测试东方财富接口支持的财务字段
"""
import requests
import pandas as pd

print("测试东方财富接口支持的财务字段...\n", flush=True)

url = "https://datacenter-web.eastmoney.com/api/data/v1/get"

# 常见的财务字段列表
fields_to_test = [
    # 基本字段
    "SECURITY_CODE", "SECURITY_NAME_ABBR", "UPDATE_DATE", "BASIC_EPS",
    # ROE相关
    "WEIGHTEDAVERAGEORE", "ROE", "ROEAVG", "ROEWEIGHT",
    # 财务指标
    "GROSSPROFITMARGIN", "NETPROFITMARGIN", "ASSETLIABRATIO",
    "CURRENTRATIO", "QUICKRATIO",
    # 其他常见字段
    "OPERATEREVE", "NETPROFIT", "TOTALASSETS", "TOTALLIAB",
]

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://data.eastmoney.com/",
}

print("逐个测试字段...\n", flush=True)

valid_fields = []
invalid_fields = []

# 测试每个字段
for field in fields_to_test:
    params = {
        "reportName": "RPT_LICO_FN_CPD",
        "columns": f"SECURITY_CODE,{field}",
        "filter": '(DATEMMDD="年报")',
        "pageNumber": 1,
        "pageSize": 1,
        "sortTypes": -1,
        "sortColumns": "UPDATE_DATE",
        "source": "WEB",
        "client": "WEB",
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        
        if data.get("success"):
            valid_fields.append(field)
            print(f"✓ {field}", flush=True)
        else:
            invalid_fields.append(field)
            print(f"✗ {field}: {data.get('message')}", flush=True)
            
    except Exception as e:
        invalid_fields.append(field)
        print(f"✗ {field}: 请求错误", flush=True)

print(f"\n总结:", flush=True)
print(f"有效字段 ({len(valid_fields)} 个): {valid_fields}", flush=True)
print(f"无效字段 ({len(invalid_fields)} 个): {invalid_fields}", flush=True)

# 使用有效字段查询数据
if valid_fields:
    print(f"\n使用有效字段查询数据...", flush=True)
    
    columns_str = "SECURITY_CODE,SECURITY_NAME_ABBR," + ",".join(valid_fields[:10])  # 限制字段数量
    params = {
        "reportName": "RPT_LICO_FN_CPD",
        "columns": columns_str,
        "filter": '(DATEMMDD="年报")',
        "pageNumber": 1,
        "pageSize": 10,
        "sortTypes": -1,
        "sortColumns": "UPDATE_DATE",
        "source": "WEB",
        "client": "WEB",
    }
    
    response = requests.get(url, params=params, headers=headers, timeout=30)
    data = response.json()
    
    if data.get("success"):
        items = data["result"].get("data", [])
        df = pd.DataFrame(items)
        print(f"\n成功获取 {len(df)} 条数据", flush=True)
        print(df, flush=True)

print("\n测试完成", flush=True)
