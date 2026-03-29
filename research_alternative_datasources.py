#!/usr/bin/env python3
"""
深入研究新浪和腾讯财经数据接口
目标：寻找可靠的数据源用于双重验证

研究内容：
1. 新浪财经API接口
2. 腾讯财经API接口
3. 其他免费数据源
4. 测试数据完整性和准确性
"""
import requests
import pandas as pd
import json
import re
from datetime import datetime

print("=" * 80)
print("数据源深度研究 - 新浪、腾讯及其他")
print("=" * 80)

# ============================================================
# 一、新浪财经API研究
# ============================================================

print("\n【一】新浪财经API接口研究")
print("-" * 80)

class SinaFinanceAPI:
    """新浪财经API接口"""
    
    def __init__(self):
        self.base_url = "http://hq.sinajs.cn"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://finance.sina.com.cn'
        }
    
    def get_realtime_quote(self, code):
        """
        获取实时行情数据
        
        参数:
            code: 股票代码（如 'sh601939', 'sz000001'）
        
        返回:
            字符串数据，需要解析
        """
        # 转换代码格式
        if code.startswith('6'):
            sina_code = f'sh{code}'
        else:
            sina_code = f'sz{code}'
        
        url = f"{self.base_url}/list={sina_code}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'gbk'
            return response.text
        except Exception as e:
            print(f"  ✗ 请求失败: {e}")
            return None
    
    def parse_quote_data(self, text):
        """
        解析行情数据
        
        返回格式：
        var hq_str_sh601939="建设银行,10.69,10.68,10.75,10.60,10.55,10.74,10.75,12345678,1234567890,...";
        
        字段说明：
        0: 名称
        1: 今开
        2: 昨收
        3: 当前价
        4: 最高
        5: 最低
        6: 买一
        7: 卖一
        8: 成交量
        9: 成交额
        ...
        """
        if not text or 'hq_str_' not in text:
            return None
        
        try:
            # 提取数据部分
            match = re.search(r'="([^"]+)"', text)
            if not match:
                return None
            
            data_str = match.group(1)
            fields = data_str.split(',')
            
            if len(fields) < 10:
                return None
            
            return {
                'name': fields[0],
                'open': float(fields[1]) if fields[1] else None,
                'pre_close': float(fields[2]) if fields[2] else None,
                'current': float(fields[3]) if fields[3] else None,
                'high': float(fields[4]) if fields[4] else None,
                'low': float(fields[5]) if fields[5] else None,
                'volume': int(fields[8]) if fields[8] else None,
                'amount': float(fields[9]) if fields[9] else None,
            }
        except Exception as e:
            print(f"  ✗ 解析失败: {e}")
            return None
    
    def get_financial_data(self, code):
        """
        获取财务数据（高级接口）
        
        新浪财经的财务数据接口：
        http://finance.sina.com.cn/realstock/company/{}/nc.phtml
        """
        pass  # 需要进一步研究


# 测试新浪接口
print("\n1. 测试实时行情接口")
print("-" * 40)

sina = SinaFinanceAPI()

test_codes = ['601939', '600036', '000001']
sina_results = {}

for code in test_codes:
    print(f"\n测试 {code}...")
    text = sina.get_realtime_quote(code)
    
    if text:
        data = sina.parse_quote_data(text)
        if data:
            sina_results[code] = data
            print(f"  ✓ 名称: {data['name']}")
            print(f"  ✓ 当前价: {data['current']}")
            print(f"  ✓ 昨收: {data['pre_close']}")
        else:
            print(f"  ✗ 解析失败")
    else:
        print(f"  ✗ 请求失败")


# ============================================================
# 二、腾讯财经API研究
# ============================================================

print("\n\n【二】腾讯财经API接口研究")
print("-" * 80)

class TencentFinanceAPI:
    """腾讯财经API接口"""
    
    def __init__(self):
        self.base_url = "http://qt.gtimg.cn"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://gu.qq.com'
        }
    
    def get_realtime_quote(self, code):
        """
        获取实时行情数据
        
        参数:
            code: 股票代码
        """
        # 转换代码格式
        if code.startswith('6'):
            tencent_code = f'sh{code}'
        else:
            tencent_code = f'sz{code}'
        
        url = f"{self.base_url}/q={tencent_code}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'gbk'
            return response.text
        except Exception as e:
            print(f"  ✗ 请求失败: {e}")
            return None
    
    def parse_quote_data(self, text):
        """
        解析行情数据
        
        返回格式：
        v_sh601939="1~建设银行~601939~10.75~10.68~..."
        
        字段说明：
        0: 未知
        1: 名称
        2: 代码
        3: 当前价
        4: 昨收
        5: 今开
        ...
        """
        if not text or 'v_' not in text:
            return None
        
        try:
            # 提取数据部分
            match = re.search(r'="([^"]+)"', text)
            if not match:
                return None
            
            data_str = match.group(1)
            fields = data_str.split('~')
            
            if len(fields) < 10:
                return None
            
            return {
                'name': fields[1],
                'code': fields[2],
                'current': float(fields[3]) if fields[3] else None,
                'pre_close': float(fields[4]) if fields[4] else None,
                'open': float(fields[5]) if fields[5] else None,
                # 腾讯的数据字段更丰富，需要进一步研究
            }
        except Exception as e:
            print(f"  ✗ 解析失败: {e}")
            return None
    
    def get_financial_indicator(self, code):
        """
        获取财务指标数据
        
        腾讯财经财务数据接口：
        https://gu.qq.com/resources/web/data/hq_stock_zhongshuju/{}.js
        
        或使用：
        https://web.sqt.gtimg.cn/q=_s_{}
        """
        if code.startswith('6'):
            tencent_code = f'sh{code}'
        else:
            tencent_code = f'sz{code}'
        
        # 尝试获取详细数据
        url = f"https://web.sqt.gtimg.cn/q=_s_{tencent_code}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'gbk'
            return response.text
        except Exception as e:
            print(f"  ✗ 请求失败: {e}")
            return None


# 测试腾讯接口
print("\n1. 测试实时行情接口")
print("-" * 40)

tencent = TencentFinanceAPI()
tencent_results = {}

for code in test_codes:
    print(f"\n测试 {code}...")
    text = tencent.get_realtime_quote(code)
    
    if text:
        data = tencent.parse_quote_data(text)
        if data:
            tencent_results[code] = data
            print(f"  ✓ 名称: {data['name']}")
            print(f"  ✓ 当前价: {data['current']}")
            print(f"  ✓ 昨收: {data['pre_close']}")
        else:
            print(f"  ✗ 解析失败")
    else:
        print(f"  ✗ 请求失败")


# ============================================================
# 三、东方财富数据接口（补充研究）
# ============================================================

print("\n\n【三】东方财富数据接口补充研究")
print("-" * 80)

class EastMoneyAdvancedAPI:
    """东方财富高级API接口"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://data.eastmoney.com'
        }
    
    def get_financial_indicator(self, code):
        """
        获取财务指标
        
        接口：
        http://push2his.eastmoney.com/api/qt/stock/kline/get
        
        或：
        http://datacenter-web.eastmoney.com/api/data/v1/get
        """
        # 尝试获取财务数据
        url = "http://datacenter-web.eastmoney.com/api/data/v1/get"
        
        params = {
            'reportName': 'RPT_LICO_FN_CPD',  # 利润表
            'columns': 'SECURITY_CODE,SECURITY_NAME_ABBR,UPDATE_DATE,WEIGHTEDAVERAGEORE,BASIC_EPS',
            'filter': f'(SECURITY_CODE="{code}")',
            'pageNumber': 1,
            'pageSize': 10,
            'sortTypes': -1,
            'sortColumns': 'UPDATE_DATE',
            'source': 'WEB',
            'client': 'WEB',
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = response.json()
            
            if data.get('success') and data.get('result'):
                records = data['result'].get('data', [])
                if records:
                    return records[0]
            
            return None
        except Exception as e:
            print(f"  ✗ 请求失败: {e}")
            return None
    
    def get_balance_sheet(self, code):
        """
        获取资产负债表
        """
        url = "http://datacenter-web.eastmoney.com/api/data/v1/get"
        
        params = {
            'reportName': 'RPT_DMSK_FN_BALANCE',  # 资产负债表
            'columns': 'SECURITY_CODE,REPORT_DATE,TOTAL_ASSETS,TOTAL_LIAB',
            'filter': f'(SECURITY_CODE="{code}")',
            'pageNumber': 1,
            'pageSize': 10,
            'sortTypes': -1,
            'sortColumns': 'REPORT_DATE',
            'source': 'WEB',
            'client': 'WEB',
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = response.json()
            
            if data.get('success') and data.get('result'):
                records = data['result'].get('data', [])
                if records:
                    return records[0]
            
            return None
        except Exception as e:
            print(f"  ✗ 请求失败: {e}")
            return None


# 测试东方财富接口
print("\n1. 测试财务指标接口")
print("-" * 40)

eastmoney = EastMoneyAdvancedAPI()
eastmoney_results = {}

for code in test_codes:
    print(f"\n测试 {code}...")
    data = eastmoney.get_financial_indicator(code)
    
    if data:
        eastmoney_results[code] = data
        print(f"  ✓ 获取到数据:")
        print(f"    - 代码: {data.get('SECURITY_CODE')}")
        print(f"    - 名称: {data.get('SECURITY_NAME_ABBR')}")
        print(f"    - ROE: {data.get('WEIGHTEDAVERAGEORE')}")
        print(f"    - EPS: {data.get('BASIC_EPS')}")
    else:
        print(f"  ✗ 未获取到数据")


# ============================================================
# 四、网易财经API研究
# ============================================================

print("\n\n【四】网易财经API接口研究")
print("-" * 80)

class NetEaseFinanceAPI:
    """网易财经API接口"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
    
    def get_realtime_quote(self, code):
        """
        获取实时行情
        
        接口：
        http://api.money.126.net/data/feed/{}.moneyquote
        """
        # 转换代码格式
        if code.startswith('6'):
            netease_code = f'0{code}'  # 沪市
        else:
            netease_code = f'1{code}'  # 深市
        
        url = f"http://api.money.126.net/data/feed/{netease_code}.moneyquote"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            return response.text
        except Exception as e:
            print(f"  ✗ 请求失败: {e}")
            return None
    
    def parse_quote_data(self, text):
        """解析行情数据"""
        if not text:
            return None
        
        try:
            # 网易返回的是JSONP格式
            # _ntes_quote_callback({ "0601939": { ... } })
            match = re.search(r'\(([^)]+)\)', text)
            if not match:
                return None
            
            json_str = match.group(1)
            data = json.loads(json_str)
            
            # 提取第一个股票的数据
            for key, value in data.items():
                return {
                    'name': value.get('name'),
                    'current': float(value.get('price', 0)),
                    'pre_close': float(value.get('yestclose', 0)),
                    'open': float(value.get('open', 0)),
                }
            
            return None
        except Exception as e:
            print(f"  ✗ 解析失败: {e}")
            return None


# 测试网易接口
print("\n1. 测试实时行情接口")
print("-" * 40)

netease = NetEaseFinanceAPI()
netease_results = {}

for code in test_codes:
    print(f"\n测试 {code}...")
    text = netease.get_realtime_quote(code)
    
    if text:
        data = netease.parse_quote_data(text)
        if data:
            netease_results[code] = data
            print(f"  ✓ 名称: {data['name']}")
            print(f"  ✓ 当前价: {data['current']}")
        else:
            print(f"  ✗ 解析失败")
    else:
        print(f"  ✗ 请求失败")


# ============================================================
# 五、数据源对比分析
# ============================================================

print("\n\n【五】数据源对比分析")
print("-" * 80)

print("\n1. 实时行情数据对比")
print("-" * 40)

if sina_results and tencent_results and netease_results:
    for code in test_codes:
        print(f"\n{code}:")
        
        sina_data = sina_results.get(code, {})
        tencent_data = tencent_results.get(code, {})
        netease_data = netease_results.get(code, {})
        
        print(f"  新浪: {sina_data.get('current', 'N/A')}")
        print(f"  腾讯: {tencent_data.get('current', 'N/A')}")
        print(f"  网易: {netease_data.get('current', 'N/A')}")
        
        # 计算差异
        prices = [
            sina_data.get('current'),
            tencent_data.get('current'),
            netease_data.get('current')
        ]
        prices = [p for p in prices if p is not None]
        
        if len(prices) >= 2:
            avg_price = sum(prices) / len(prices)
            max_diff = max(abs(p - avg_price) for p in prices)
            print(f"  平均: {avg_price:.2f}, 最大差异: {max_diff:.2f}")


# ============================================================
# 六、总结
# ============================================================

print("\n\n【六】总结")
print("-" * 80)

print("""
数据源研究结果：

1. 新浪财经API
   ✓ 实时行情：可用，响应快
   ✗ 财务数据：接口不明确，需要进一步研究
   适用场景：实时行情、价格数据

2. 腾讯财经API
   ✓ 实时行情：可用，数据丰富
   ✗ 财务数据：接口不明确，需要进一步研究
   适用场景：实时行情、价格数据

3. 东方财富API
   ✓ 财务数据：有接口，但字段有限制
   ✗ ROE数据：WEIGHTEDAVERAGEORE字段返回空
   ✗ 负债率：ASSETLIABRATIO字段不支持
   适用场景：部分财务数据

4. 网易财经API
   ✓ 实时行情：可用，响应快
   ✗ 财务数据：接口不明确
   适用场景：实时行情、价格数据

建议：
1. 实时行情：使用新浪/腾讯/网易作为多数据源验证
2. ROE数据：继续寻找其他数据源
3. 财务数据：需要寻找专业的财务数据接口
""")

print("\n" + "=" * 80)
print("研究完成")
print("=" * 80)
