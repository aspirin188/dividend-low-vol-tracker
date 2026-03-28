#!/usr/bin/env python3
"""验证招商银行股息率计算"""

import requests
import re
from datetime import datetime, timedelta

# 1. 获取分红方案
print('=' * 70)
print('招商银行(600036)股息率计算验证')
print('=' * 70)

params = {
    'reportName': 'RPT_LICO_FN_CPD',
    'columns': 'SECURITY_CODE,SECURITY_NAME_ABBR,ASSIGNDSCRPT,REPORTDATE,DATATYPE',
    'filter': '(SECURITY_CODE="600036")',
    'pageNumber': 1,
    'pageSize': 15,
    'sortTypes': -1,
    'sortColumns': 'REPORTDATE',
    'source': 'WEB',
    'client': 'WEB',
}

r = requests.get('https://datacenter-web.eastmoney.com/api/data/v1/get', params=params, timeout=30)
resp = r.json()

print('\n【招商银行最近分红方案】')
print('-' * 70)

dividend_records = []
if resp.get('success') and resp.get('result'):
    items = resp['result'].get('data', [])
    
    for item in items:
        report_date = item.get('REPORTDATE', '')
        data_type = item.get('DATATYPE', '')
        assign_desc = item.get('ASSIGNDSCRPT', '')
        
        m = re.search(r'派([\d.]+)元', str(assign_desc))
        if m:
            dividend_per_10 = float(m.group(1))
            dividend_per_share = dividend_per_10 / 10.0
            
            dividend_records.append({
                'date': report_date[:10],
                'type': data_type,
                'per_share': dividend_per_share
            })
            
            print(f'{report_date[:10]} | {data_type:6s} | {assign_desc:35s} | 每股{dividend_per_share:.4f}元')

# 2. 计算TTM股息率
print('\n【TTM股息率计算(过去12个月)】')
print('-' * 70)

now = datetime.now()
one_year_ago = now - timedelta(days=365)

print(f'计算范围: {one_year_ago.strftime("%Y-%m-%d")} 至 {now.strftime("%Y-%m-%d")}\n')

ttm_dividend = 0
for rec in dividend_records:
    rec_date = datetime.strptime(rec['date'], '%Y-%m-%d')
    if rec_date >= one_year_ago:
        ttm_dividend += rec['per_share']
        print(f'✓ {rec["date"]} | {rec["type"]} | 每股{rec["per_share"]:.4f}元')

price = 39.44  # 用户提供
ttm_yield = (ttm_dividend / price) * 100

print(f'\nTTM分红总额: 每股{ttm_dividend:.4f}元')
print(f'TTM股息率: {ttm_dividend:.4f} / {price} × 100 = {ttm_yield:.2f}%')

# 3. 用户计算
print('\n【用户计算(2025年预期)】')
print('-' * 70)

user_yield = ((10.13/10 + 10.03/10) / 39.44) * 100
print(f'中期: 10派10.13元')
print(f'年报: 10派10.03元')
print(f'合计: 每股2.016元')
print(f'股息率: 2.016 / 39.44 × 100 = {user_yield:.2f}%')

# 4. 差异说明
print('\n' + '=' * 70)
print('【差异原因】')
print('=' * 70)
print(f'手动TTM: {ttm_yield:.2f}%')
print(f'用户预期: {user_yield:.2f}%')
print(f'\n差异原因:')
print('1. TTM = 过去12个月已实施的分红')
print('2. 预期 = 未来一年已公告的分红')
print('3. 如果2025年分红已实施,应计入TTM')
