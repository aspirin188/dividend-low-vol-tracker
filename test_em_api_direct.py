#!/usr/bin/env python3
"""
直接测试东方财富分红数据接口
"""
import requests

url = "https://datacenter-web.eastmoney.com/api/data/v1/get"

params = {
    'reportName': 'RPT_LICO_FN_CPD',
    'columns': 'SECURITY_CODE,SECURITY_NAME_ABBR,BASIC_EPS,ASSIGNDSCRPT,REPORTDATE',
    'filter': '(DATEMMDD="年报")',
    'pageNumber': 1,
    'pageSize': 100,
    'sortTypes': -1,
    'sortColumns': 'REPORTDATE',
    'source': 'WEB',
    'client': 'WEB',
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://data.eastmoney.com/',
}

print("测试东方财富分红数据接口...", flush=True)

try:
    response = requests.get(url, params=params, headers=headers, timeout=30)
    print(f"状态码: {response.status_code}", flush=True)

    data = response.json()

    if data.get('success'):
        items = data['result'].get('data', [])
        print(f"\n✓ 成功获取 {len(items)} 条数据", flush=True)

        if len(items) > 0:
            print("\n前5条数据:", flush=True)
            import pandas as pd
            df = pd.DataFrame(items[:5])
            print(df[['SECURITY_CODE', 'SECURITY_NAME_ABBR', 'ASSIGNDSCRPT']], flush=True)

            # 检查是否有我们要的股票
            print("\n检查目标股票:", flush=True)
            target_codes = ['601939', '600036', '601318']
            for item in items[:50]:  # 只检查前50条
                if item.get('SECURITY_CODE') in target_codes:
                    print(f"  ✓ 找到: {item['SECURITY_CODE']} {item['SECURITY_NAME_ABBR']} - {item.get('ASSIGNDSCRPT', 'N/A')}", flush=True)

    else:
        print(f"\n✗ 接口返回失败", flush=True)
        print(f"消息: {data.get('message')}", flush=True)

except Exception as e:
    print(f"\n✗ 错误: {e}", flush=True)
    import traceback
    traceback.print_exc()
