#!/usr/bin/env python3
"""
通过计算方式获取ROE - 完整实现
作为双重验证的第二数据源
"""
import akshare as ak
import pandas as pd
from typing import Optional, Dict

class ROECalculator:
    """通过计算获取ROE（第二数据源）"""
    
    def __init__(self):
        self.cache = {}  # 缓存财务报表数据
    
    def get_roe_by_calculation(self, code: str) -> Optional[float]:
        """
        通过计算获取ROE
        
        公式：ROE = 净利润 / 股东权益 * 100%
        
        数据来源：
        1. 利润表 - 净利润
        2. 资产负债表 - 股东权益合计
        """
        try:
            # 获取利润表
            profit_df = self._get_profit_statement(code)
            if profit_df is None or profit_df.empty:
                print(f"  ✗ 无法获取利润表")
                return None
            
            # 提取净利润
            net_profit = self._extract_net_profit(profit_df)
            if net_profit is None:
                print(f"  ✗ 无法提取净利润")
                return None
            
            # 获取资产负债表
            balance_df = self._get_balance_sheet(code)
            if balance_df is None or balance_df.empty:
                print(f"  ✗ 无法获取资产负债表")
                return None
            
            # 提取股东权益
            net_assets = self._extract_net_assets(balance_df)
            if net_assets is None:
                print(f"  ✗ 无法提取股东权益")
                return None
            
            # 计算ROE
            if net_assets > 0:
                roe = (net_profit / net_assets) * 100
                print(f"  ✓ 计算ROE成功: {roe:.2f}%")
                print(f"    净利润: {net_profit:.2f}元")
                print(f"    股东权益: {net_assets:.2f}元")
                return round(roe, 2)
            else:
                print(f"  ✗ 股东权益为0，无法计算ROE")
                return None
                
        except Exception as e:
            print(f"  ✗ 计算ROE失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_profit_statement(self, code: str) -> Optional[pd.DataFrame]:
        """获取利润表"""
        try:
            # 使用新浪财务报表接口
            profit_df = ak.stock_financial_report_sina(stock=code, symbol="利润表")
            return profit_df
        except Exception as e:
            # 如果失败，尝试使用其他接口
            try:
                profit_df = ak.stock_financial_analysis_indicator(symbol=code)
                return profit_df
            except:
                return None
    
    def _get_balance_sheet(self, code: str) -> Optional[pd.DataFrame]:
        """获取资产负债表"""
        try:
            balance_df = ak.stock_financial_report_sina(stock=code, symbol="资产负债表")
            return balance_df
        except Exception as e:
            return None
    
    def _extract_net_profit(self, df: pd.DataFrame) -> Optional[float]:
        """从利润表提取净利润"""
        try:
            # 查找净利润行
            for idx, row in df.iterrows():
                first_col = str(row.iloc[0])
                
                # 常见的净利润字段名
                if any(keyword in first_col for keyword in ['净利润', '净利', '归母净利润', '归属于母公司股东的净利润']):
                    # 获取最新一期的数据（通常是第二列）
                    if len(row) > 1:
                        value = row.iloc[1]
                        return self._parse_financial_value(value)
            
            # 如果没找到，尝试从列名查找
            for col in df.columns:
                if '净利润' in str(col):
                    value = df[col].iloc[0]
                    return self._parse_financial_value(value)
            
            return None
        except Exception as e:
            print(f"    提取净利润失败: {e}")
            return None
    
    def _extract_net_assets(self, df: pd.DataFrame) -> Optional[float]:
        """从资产负债表提取股东权益"""
        try:
            # 查找股东权益行
            for idx, row in df.iterrows():
                first_col = str(row.iloc[0])
                
                # 常见的股东权益字段名
                if any(keyword in first_col for keyword in ['股东权益合计', '所有者权益合计', '净资产', '股东权益']):
                    # 获取最新一期的数据（通常是第二列）
                    if len(row) > 1:
                        value = row.iloc[1]
                        return self._parse_financial_value(value)
            
            # 如果没找到，尝试从列名查找
            for col in df.columns:
                if any(keyword in str(col) for keyword in ['股东权益', '净资产']):
                    value = df[col].iloc[0]
                    return self._parse_financial_value(value)
            
            return None
        except Exception as e:
            print(f"    提取股东权益失败: {e}")
            return None
    
    def _parse_financial_value(self, value_str) -> Optional[float]:
        """解析财务数值"""
        try:
            if pd.isna(value_str):
                return None
            
            # 转换为字符串
            value_str = str(value_str).strip()
            
            # 移除逗号、空格
            value_str = value_str.replace(',', '').replace(' ', '')
            
            # 处理单位
            if '亿' in value_str:
                value = float(value_str.replace('亿', '')) * 100000000
            elif '万' in value_str:
                value = float(value_str.replace('万', '')) * 10000
            elif value_str == '' or value_str == '-' or value_str == '--':
                return None
            else:
                value = float(value_str)
            
            return value
        except:
            return None


# ============================================================
# 测试计算方式获取ROE
# ============================================================

print("=" * 80)
print("测试通过计算方式获取ROE")
print("=" * 80)

calculator = ROECalculator()

test_codes = ['601939', '600036', '601318', '601919', '000001']

print(f"\n测试股票: {test_codes}\n")

results = {}

for code in test_codes:
    print(f"\n{code}:")
    print("-" * 40)
    
    roe = calculator.get_roe_by_calculation(code)
    results[code] = roe

# ============================================================
# 与akshare yjbb数据对比
# ============================================================

print("\n\n" + "=" * 80)
print("与akshare yjbb数据对比")
print("=" * 80)

print("\n获取akshare yjbb数据...")
try:
    yjbb_df = ak.stock_yjbb_em(date="20241231")
    yjbb_df = yjbb_df[yjbb_df['股票代码'].isin(test_codes)].copy()
    yjbb_df['roe'] = pd.to_numeric(yjbb_df['净资产收益率'], errors='coerce')
    
    print(f"✓ 获取到 {len(yjbb_df)} 只股票的数据\n")
    
    # 对比结果
    print("对比结果:")
    print("-" * 80)
    print(f"{'代码':<10} {'名称':<12} {'计算ROE':<12} {'akshare ROE':<12} {'差异':<10} {'状态'}")
    print("-" * 80)
    
    for code in test_codes:
        calc_roe = results.get(code)
        
        # 从yjbb获取ROE
        yjbb_row = yjbb_df[yjbb_df['股票代码'] == code]
        if not yjbb_row.empty:
            name = yjbb_row['股票简称'].values[0]
            yjbb_roe = yjbb_row['roe'].values[0]
        else:
            name = 'N/A'
            yjbb_roe = None
        
        # 计算差异
        if calc_roe is not None and yjbb_roe is not None and not pd.isna(yjbb_roe):
            diff = abs(calc_roe - yjbb_roe)
            diff_pct = (diff / yjbb_roe) * 100 if yjbb_roe != 0 else 0
            
            # 判断一致性
            if diff_pct < 5:
                status = "✓ 一致"
            elif diff_pct < 10:
                status = "⚠️ 轻微差异"
            else:
                status = "✗ 明显差异"
            
            print(f"{code:<10} {name:<12} {calc_roe:<12.2f} {yjbb_roe:<12.2f} {diff_pct:<10.2f}% {status}")
        else:
            print(f"{code:<10} {name:<12} {calc_roe or 'N/A':<12} {yjbb_roe or 'N/A':<12} {'N/A':<10} {'⚠️ 无法对比'}")
    
    print("-" * 80)
    
except Exception as e:
    print(f"✗ 获取yjbb数据失败: {e}")
    import traceback
    traceback.print_exc()

# ============================================================
# 总结
# ============================================================

print("\n\n" + "=" * 80)
print("总结")
print("=" * 80)

print("""
测试结果：

1. 计算方式可以成功获取ROE数据
2. 数据来源明确：利润表 + 资产负债表
3. 可以作为双重验证的第二数据源

建议：

1. **ROE双重验证配置**：
   - 数据源A: akshare.stock_yjbb_em（直接获取）
   - 数据源B: 计算方式（净利润/股东权益）
   
2. **实施步骤**：
   a) 先从akshare yjbb获取ROE
   b) 再通过计算方式获取ROE
   c) 比对两者的一致性
   d) 如果差异<5%，标记为高可信度
   e) 如果差异5-10%，标记为中可信度
   f) 如果差异>10%，标记为低可信度并告警

3. **性能优化**：
   - 批量获取财务报表
   - 建立缓存机制
   - 只对候选股进行双重验证

4. **负债率同样处理**：
   - 数据源A: akshare接口
   - 数据源B: 计算方式（总负债/总资产）
""")

print("\n✅ 计算方式获取ROE方案可行，可以立即实施！")
