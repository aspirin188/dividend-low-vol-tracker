#!/usr/bin/env python3
"""验证东方财富f115字段准确性"""

import requests
import re

print('=' * 70)
print('【Bug确认】东方财富f115字段数据不准确')
print('=' * 70)

# 1. 获取招商银行f115字段值
params = {
    'secid': '1.600036',
    'fields': 'f2,f12,f14,f115',
}

r = requests.get('https://push2.eastmoney.com/api/qt/stock/get', params=params, timeout=30)
data = r.json()

if data.get('data'):
    stock = data['data']
    f115 = stock.get('f115', 0)
    price = stock.get('f2', 0)
    
    print(f'\n招商银行(600036):')
    print(f'  股价(f2): {price} 元')
    print(f'  股息率TTM(f115): {f115}%')
    
    # 2. 获取真实分红数据
    params2 = {
        'reportName': 'RPT_LICO_FN_CPD',
        'columns': 'SECURITY_CODE,ASSIGNDSCRPT,REPORTDATE,DATATYPE',
        'filter': '(SECURITY_CODE="600036")',
        'pageNumber': 1,
        'pageSize': 10,
        'sortTypes': -1,
        'sortColumns': 'REPORTDATE',
        'source': 'WEB',
        'client': 'WEB',
    }
    
    r2 = requests.get('https://datacenter-web.eastmoney.com/api/data/v1/get', params=params2, timeout=30)
    resp2 = r2.json()
    
    if resp2.get('success'):
        items = resp2['result'].get('data', [])
        
        print(f'\n真实分红记录:')
        total_dividend = 0
        
        from datetime import datetime, timedelta
        one_year_ago = datetime.now() - timedelta(days=365)
        
        for item in items:
            report_date = item.get('REPORTDATE', '')[:10]
            data_type = item.get('DATATYPE', '')
            desc = item.get('ASSIGNDSCRPT', '')
            
            m = re.search(r'派([\d.]+)元', str(desc))
            if m:
                per_share = float(m.group(1)) / 10.0
                
                # 判断是否在TTM范围内
                rec_date = datetime.strptime(report_date, '%Y-%m-%d')
                if rec_date >= one_year_ago:
                    total_dividend += per_share
                    print(f'  ✓ {report_date} | {data_type} | 每股{per_share:.4f}元')
                else:
                    print(f'    {report_date} | {data_type} | 每股{per_share:.4f}元 (超出TTM)')
        
        # 3. 计算正确股息率
        correct_yield = (total_dividend / price) * 100 if price > 0 else 0
        
        print(f'\n【计算对比】')
        print(f'  TTM分红总额: 每股{total_dividend:.4f}元')
        print(f'  当前股价: {price}元')
        print(f'  正确股息率: {total_dividend:.4f} / {price} × 100 = {correct_yield:.2f}%')
        print(f'  东方财富f115: {f115}%')
        print(f'  差异: {abs(f115 - correct_yield):.2f}%')
        
        print(f'\n【结论】')
        if abs(f115 - correct_yield) > 0.5:
            print(f'  ❌ 东方财富f115字段数据不准确!')
            print(f'  ❌ 系统直接使用f115导致股息率错误!')
            print(f'  ❌ 需要改为自计算股息率!')
        else:
            print(f'  ✅ f115字段准确')

else:
    print('查询失败')
