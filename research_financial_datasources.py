#!/usr/bin/env python3
"""
深入研究财务数据源 - 寻找ROE、负债率等财务指标

研究目标：
1. 新浪财务数据接口
2. 腾讯财务数据接口
3. 同花顺财务数据接口
4. 通过计算方式获取ROE
"""
import requests
import pandas as pd
import json
import re
from datetime import datetime

print("=" * 80)
print("财务数据源深度研究")
print("=" * 80)

# ============================================================
# 一、新浪财务数据接口研究
# ============================================================

print("\n【一】新浪财务数据接口研究")
print("-" * 80)

class SinaFinancialData:
    """新浪财务数据接口"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://finance.sina.com.cn'
        }
    
    def get_key_financial_indicator(self, code):
        """
        获取关键财务指标
        
        接口：
        http://money.finance.sina.com.cn/corp/go.php/vFD_FinancialGuideLineStock/stockid/{}/displaytype/4.phtml
        
        或JSON接口：
        http://hq.sinajs.cn/list={}_2  # 获取更详细的数据
        """
        # 转换代码格式
        if code.startswith('6'):
            sina_code = f'sh{code}'
        else:
            sina_code = f'sz{code}'
        
        # 方法1: 尝试获取详细行情数据（可能包含财务指标）
        url1 = f"http://hq.sinajs.cn/list={sina_code}_2"
        
        try:
            response = requests.get(url1, headers=self.headers, timeout=10)
            response.encoding = 'gbk'
            text = response.text
            
            print(f"  方法1 - 详细行情:")
            print(f"    响应: {text[:200]}...")
            
            # 解析数据
            match = re.search(r'="([^"]+)"', text)
            if match:
                data_str = match.group(1)
                fields = data_str.split(',')
                print(f"    字段数: {len(fields)}")
                if len(fields) > 20:
                    # 尝试识别关键字段
                    print(f"    前20字段: {fields[:20]}")
            
        except Exception as e:
            print(f"  ✗ 方法1失败: {e}")
        
        # 方法2: 尝试获取财务简表
        url2 = f"http://money.finance.sina.com.cn/corp/go.php/vFD_FinancialGuideLineStock/stockid/{code}/displaytype/4.phtml"
        
        try:
            response = requests.get(url2, headers=self.headers, timeout=10)
            response.encoding = 'gbk'
            html = response.text
            
            # 尝试从HTML中提取财务数据
            # 查找ROE相关数据
            roe_match = re.search(r'净资产收益率[^\d]+(\d+\.?\d*)', html)
            if roe_match:
                roe = float(roe_match.group(1))
                print(f"  ✓ 方法2 - 找到ROE: {roe}%")
                return {'roe': roe}
            else:
                print(f"  ✗ 方法2 - 未找到ROE数据")
                
        except Exception as e:
            print(f"  ✗ 方法2失败: {e}")
        
        return None


# 测试新浪财务接口
print("\n测试新浪财务数据接口:")
for code in ['601939', '600036']:
    print(f"\n{code}:")
    sina_fin = SinaFinancialData()
    result = sina_fin.get_key_financial_indicator(code)


# ============================================================
# 二、腾讯财务数据接口研究
# ============================================================

print("\n\n【二】腾讯财务数据接口研究")
print("-" * 80)

class TencentFinancialData:
    """腾讯财务数据接口"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://gu.qq.com'
        }
    
    def get_financial_summary(self, code):
        """
        获取财务摘要
        
        接口：
        http://qt.gtimg.cn/q=_s_{}
        或
        https://gu.qq.com/resources/web/data/hq_stock_zhongshuju/{}.js
        """
        # 转换代码格式
        if code.startswith('6'):
            tencent_code = f'sh{code}'
        else:
            tencent_code = f'sz{code}'
        
        # 方法1: 尝试获取详细数据
        url1 = f"http://qt.gtimg.cn/q=_s_{tencent_code}"
        
        try:
            response = requests.get(url1, headers=self.headers, timeout=10)
            response.encoding = 'gbk'
            text = response.text
            
            print(f"  方法1 - 详细数据:")
            print(f"    响应: {text[:300]}...")
            
            # 解析数据
            match = re.search(r'="([^"]+)"', text)
            if match:
                data_str = match.group(1)
                fields = data_str.split('~')
                print(f"    字段数: {len(fields)}")
                
                # 腾讯的数据字段很多，尝试找到财务数据
                if len(fields) > 50:
                    print(f"    关键字段（部分）:")
                    # 通常财务数据在后面的字段
                    for i, field in enumerate(fields[40:50]):
                        print(f"      字段{40+i}: {field}")
            
        except Exception as e:
            print(f"  ✗ 方法1失败: {e}")
        
        # 方法2: 尝试JSON接口
        url2 = f"https://gu.qq.com/resources/web/data/hq_stock_zhongshuju/{tencent_code}.js"
        
        try:
            response = requests.get(url2, headers=self.headers, timeout=10)
            text = response.text
            
            print(f"\n  方法2 - JSON数据:")
            
            # 尝试解析JSON
            json_match = re.search(r'\(([^)]+)\)', text)
            if json_match:
                json_str = json_match.group(1)
                data = json.loads(json_str)
                
                # 查找ROE相关字段
                if 'zhongshuju' in data:
                    zs_data = data['zhongshuju']
                    print(f"    找到重要数据:")
                    for key in ['roe', 'ROE', '净资产收益率', 'debt', '负债']:
                        if key in str(zs_data):
                            print(f"      {key}: {zs_data}")
                
        except Exception as e:
            print(f"  ✗ 方法2失败: {e}")
        
        return None


# 测试腾讯财务接口
print("\n测试腾讯财务数据接口:")
for code in ['601939', '600036']:
    print(f"\n{code}:")
    tencent_fin = TencentFinancialData()
    result = tencent_fin.get_financial_summary(code)


# ============================================================
# 三、通过计算方式获取ROE
# ============================================================

print("\n\n【三】通过计算方式获取ROE")
print("-" * 80)

class ROECalculator:
    """通过计算获取ROE"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0',
        }
    
    def get_net_profit_and_assets(self, code):
        """
        获取净利润和净资产
        
        公式：ROE = 净利润 / 净资产 * 100%
        
        数据源：
        1. akshare的财务报表接口
        2. 或从利润表和资产负债表计算
        """
        try:
            import akshare as ak
            
            # 获取利润表
            print(f"  获取 {code} 利润表...")
            profit_df = ak.stock_financial_report_sina(stock=code, symbol="利润表")
            
            if profit_df is not None and not profit_df.empty:
                # 找到净利润
                print(f"    利润表字段: {list(profit_df.columns)[:10]}")
                
                # 查找净利润行
                for idx, row in profit_df.iterrows():
                    if '净利润' in str(row.iloc[0]):
                        net_profit = row.iloc[1]  # 最新一期净利润
                        print(f"    找到净利润: {net_profit}")
                        break
            
            # 获取资产负债表
            print(f"  获取 {code} 资产负债表...")
            balance_df = ak.stock_financial_report_sina(stock=code, symbol="资产负债表")
            
            if balance_df is not None and not balance_df.empty:
                # 找到净资产（股东权益合计）
                print(f"    资产负债表字段: {list(balance_df.columns)[:10]}")
                
                # 查找净资产行
                for idx, row in balance_df.iterrows():
                    if '股东权益合计' in str(row.iloc[0]) or '所有者权益合计' in str(row.iloc[0]):
                        net_assets = row.iloc[1]  # 最新一期净资产
                        print(f"    找到净资产: {net_assets}")
                        break
            
            # 计算ROE
            if 'net_profit' in locals() and 'net_assets' in locals():
                # 转换为数值
                net_profit = self._parse_financial_value(net_profit)
                net_assets = self._parse_financial_value(net_assets)
                
                if net_profit and net_assets and net_assets > 0:
                    roe = (net_profit / net_assets) * 100
                    print(f"\n  ✓ 计算得到ROE: {roe:.2f}%")
                    return {
                        'net_profit': net_profit,
                        'net_assets': net_assets,
                        'roe': round(roe, 2)
                    }
            
        except Exception as e:
            print(f"  ✗ 获取失败: {e}")
            import traceback
            traceback.print_exc()
        
        return None
    
    def _parse_financial_value(self, value_str):
        """解析财务数值"""
        try:
            # 移除逗号、空格等
            value_str = str(value_str).replace(',', '').replace(' ', '').strip()
            
            # 处理单位（万、亿）
            if '亿' in value_str:
                value = float(value_str.replace('亿', '')) * 100000000
            elif '万' in value_str:
                value = float(value_str.replace('万', '')) * 10000
            else:
                value = float(value_str)
            
            return value
        except:
            return None


# 测试计算方式
print("\n测试通过计算获取ROE:")
for code in ['601939', '600036']:
    print(f"\n{code}:")
    calculator = ROECalculator()
    result = calculator.get_net_profit_and_assets(code)


# ============================================================
# 四、总结与建议
# ============================================================

print("\n\n【四】总结与建议")
print("-" * 80)

print("""
财务数据源研究结果：

1. 新浪财经财务接口
   ✗ 详细行情接口（_2）：字段较多，但需要进一步解析
   ✗ 财务简表页面：HTML解析复杂，不稳定
   评级：⭐⭐ 可作为补充数据源

2. 腾讯财经财务接口
   ✗ 详细数据接口：字段丰富，但财务指标不明确
   ✗ JSON接口：需要进一步研究数据结构
   评级：⭐⭐ 可作为补充数据源

3. 计算方式获取ROE
   ✓ akshare利润表 + 资产负债表
   ✓ 公式：ROE = 净利润 / 净资产 * 100%
   ✓ 数据来源明确，可验证
   评级：⭐⭐⭐⭐ 推荐作为第二数据源

建议方案：

**ROE数据源配置：**
1. 主数据源：akshare.stock_yjbb_em（直接获取）
2. 副数据源：计算方式（净利润/净资产）
   - 优点：数据来源明确，可验证
   - 缺点：需要获取两张财务报表
   - 可行性：高

**实施步骤：**
1. 使用akshare的stock_financial_report_sina获取利润表和资产负债表
2. 从利润表提取"净利润"
3. 从资产负债表提取"股东权益合计"或"所有者权益合计"
4. 计算ROE = 净利润 / 股东权益 * 100%
5. 与主数据源进行交叉验证

**其他建议：**
1. 对于负债率，可以同样通过资产负债表计算：
   负债率 = 总负债 / 总资产 * 100%
2. 实时行情数据可以使用新浪/腾讯作为多数据源验证
3. 建立数据质量监控，定期验证数据准确性
""")

print("\n" + "=" * 80)
print("研究完成")
print("=" * 80)
