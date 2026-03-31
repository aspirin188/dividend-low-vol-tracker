"""
数据获取服务 — 红利低波跟踪系统（v7.6 极简稳定版）

v7.6 核心原则：
1. 简单可靠 > 性能优化
2. 稳定运行 > 功能完整
3. 只使用经过验证的稳定接口

数据流程：
1. akshare获取EPS/ROE（年报数据）
2. 新浪接口获取实时股价
3. akshare获取分红数据
4. 计算股息率并筛选
"""

import re
import time
import math
import numpy as np
import pandas as pd
import akshare as ak
import requests
from datetime import datetime, timedelta


# ============================================================
# 配置
# ============================================================

_SINA_BASE_URL = 'http://hq.sinajs.cn/list='

_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'http://finance.sina.com.cn/',
}

_TIMEOUT = 30
_PROXIES = {'http': None, 'https': None}


# ============================================================
# 核心数据获取函数
# ============================================================

def fetch_eps_data():
    """获取EPS和ROE数据（年报）"""
    print("  [1/3] 获取EPS和ROE数据...", flush=True)
    
    try:
        # 使用akshare获取年报数据
        df = ak.stock_yjbb_em(date='20241231')
        
        if df is None or df.empty:
            print("  ✗ 获取失败", flush=True)
            return pd.DataFrame()
        
        # 重命名列
        df = df.rename(columns={
            '股票代码': 'code',
            '股票简称': 'name',
            '每股收益': 'eps',
            '净资产收益率': 'roe'
        })
        
        # 清理数据
        df['code'] = df['code'].astype(str).str.zfill(6)
        df['eps'] = pd.to_numeric(df['eps'], errors='coerce')
        df['roe'] = pd.to_numeric(df['roe'], errors='coerce')
        
        # 只保留A股
        df = df[df['code'].str.match(r'^(00|30|60|68)\d{4}$')].copy()
        
        # 过滤有效数据
        df = df[
            (df['eps'].notna()) &
            (df['roe'].notna()) &
            (df['eps'] > 0)
        ].copy()
        
        print(f"  ✓ 获取 {len(df)} 只股票", flush=True)
        return df[['code', 'name', 'eps', 'roe']]
        
    except Exception as e:
        print(f"  ✗ 错误: {e}", flush=True)
        return pd.DataFrame()


def fetch_realtime_prices(stock_codes):
    """获取实时股价（新浪接口）"""
    print(f"  [2/3] 获取实时股价（{len(stock_codes)}只）...", flush=True)
    
    results = []
    batch_size = 100
    
    for i in range(0, len(stock_codes), batch_size):
        batch = stock_codes[i:i+batch_size]
        
        # 构建URL
        symbols = []
        for code in batch:
            if code.startswith('6'):
                symbols.append(f'sh{code}')
            else:
                symbols.append(f'sz{code}')
        
        url = f"{_SINA_BASE_URL}{','.join(symbols)}"
        
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT, proxies=_PROXIES)
            resp.encoding = 'gbk'
            
            # 解析数据
            for line in resp.text.strip().split('\n'):
                if not line or '=""' in line:
                    continue
                
                try:
                    # 提取代码和内容
                    match = re.match(r'var hq_str_(?:sh|sz)(\d+)="(.*)";', line)
                    if not match:
                        continue
                    
                    code = match.group(1)
                    content = match.group(2)
                    
                    if not content:
                        continue
                    
                    fields = content.split(',')
                    if len(fields) < 4:
                        continue
                    
                    # 提取当前价格
                    price = float(fields[3]) if fields[3] else 0
                    
                    if price > 0:
                        results.append({'code': code, 'price': price})
                        
                except:
                    continue
            
            # 显示进度
            progress = min(i + batch_size, len(stock_codes))
            if progress % 500 == 0 or progress == len(stock_codes):
                print(f"    进度: {progress}/{len(stock_codes)}", flush=True)
            
            # 短暂延迟
            time.sleep(0.05)
            
        except Exception as e:
            print(f"    批次失败: {e}", flush=True)
            continue
    
    print(f"  ✓ 成功获取 {len(results)} 只", flush=True)
    return pd.DataFrame(results)


def fetch_dividend_data():
    """获取分红数据"""
    print("  [3/3] 获取分红数据...", flush=True)
    
    try:
        df = ak.stock_fhps_em(date='20241231')
        
        if df is None or df.empty:
            print("  ✗ 获取失败", flush=True)
            return pd.DataFrame()
        
        # 识别列名
        code_col = None
        div_col = None
        
        for col in df.columns:
            if '代码' in col or col.lower() == 'code':
                code_col = col
            elif '股利' in col or '派息' in col or 'dividend' in col.lower():
                div_col = col
        
        if not code_col or not div_col:
            # 尝试使用默认列
            if len(df.columns) >= 2:
                code_col = df.columns[0]
                # 查找数值列
                for col in df.columns[1:]:
                    if df[col].dtype in ['float64', 'int64']:
                        div_col = col
                        break
        
        if not code_col or not div_col:
            print(f"  ✗ 无法识别列名: {list(df.columns)}", flush=True)
            return pd.DataFrame()
        
        # 重命名
        df = df.rename(columns={code_col: 'code', div_col: 'dividend'})
        
        # 清理数据
        df['code'] = df['code'].astype(str).str.zfill(6)
        df['dividend'] = pd.to_numeric(df['dividend'], errors='coerce')
        
        # 过滤有效数据
        df = df[
            (df['dividend'].notna()) &
            (df['dividend'] > 0)
        ].copy()
        
        # 去重
        df = df.drop_duplicates(subset='code', keep='first')
        
        print(f"  ✓ 获取 {len(df)} 只", flush=True)
        return df[['code', 'dividend']]
        
    except Exception as e:
        print(f"  ✗ 错误: {e}", flush=True)
        return pd.DataFrame()


# ============================================================
# 主流程
# ============================================================

def merge_all_data():
    """
    主流程（极简版）
    
    步骤：
    1. 获取EPS/ROE数据
    2. 获取实时股价
    3. 获取分红数据
    4. 计算股息率
    5. 筛选（股息率≥3%）
    
    预计耗时：1-2分钟
    """
    start_time = time.time()
    
    print("\n" + "="*60)
    print("红利低波跟踪系统 v7.6 - 数据获取开始")
    print("="*60 + "\n")
    
    # 步骤1: 获取EPS数据
    eps_df = fetch_eps_data()
    if eps_df.empty:
        print("\n✗ 无法继续，返回空数据")
        return pd.DataFrame()
    
    # 步骤2: 获取实时股价
    price_df = fetch_realtime_prices(eps_df['code'].tolist())
    if price_df.empty:
        print("\n✗ 无法继续，返回空数据")
        return pd.DataFrame()
    
    # 合并数据
    merged = eps_df.merge(price_df, on='code', how='inner')
    print(f"\n  合并后: {len(merged)} 只股票")
    
    # 步骤3: 获取分红数据
    div_df = fetch_dividend_data()
    
    if not div_df.empty:
        merged = merged.merge(div_df, on='code', how='left')
        
        # 步骤4: 计算股息率
        print("\n计算股息率...", flush=True)
        merged['div_yield'] = (merged['dividend'] / merged['price'] * 100).round(2)
        
        # 步骤5: 筛选
        print("\n筛选（股息率≥3%）...", flush=True)
        result = merged[
            (merged['div_yield'].notna()) &
            (merged['div_yield'] >= 3.0)
        ].copy()
    else:
        print("\n⚠️ 无分红数据，返回基础数据")
        result = merged.copy()
        result['div_yield'] = None
        result['dividend'] = None
    
    # 排除ST
    result = result[~result['name'].str.contains('ST', case=False, na=False)].copy()
    
    # 计算耗时
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    
    print("\n" + "="*60)
    print(f"✓ 完成！共 {len(result)} 只候选股")
    print(f"✓ 耗时: {minutes}分{seconds}秒")
    print("="*60 + "\n")
    
    # 添加兼容性字段
    result['basic_eps'] = result['eps']
    result['dividend_yield'] = result['div_yield']
    result['dividend_yield_ttm'] = result['div_yield']
    result['dividend_per_share'] = result['dividend']
    result['price_percentile'] = None
    result['annual_vol'] = None
    result['payout_ratio'] = None
    result['debt_ratio'] = None
    result['dividend_years'] = 5  # 默认值
    
    return result


# ============================================================
# 兼容性函数（保持接口不变）
# ============================================================

def fetch_all_quotes():
    """兼容性函数"""
    return merge_all_data()

def fetch_eps_batch():
    """兼容性函数"""
    return fetch_eps_data()

def fetch_dividend_from_akshare(year='2024'):
    """兼容性函数"""
    return fetch_dividend_data()

def _fetch_quotes_batch_sina(codes, batch_size=500):
    """兼容性函数"""
    df = fetch_realtime_prices(codes)
    return df.to_dict('records')

def calculate_ttm_dividend_batch(codes, prices):
    """兼容性函数"""
    return {}

def get_dividend_years_batch(codes):
    """兼容性函数"""
    return {code: 5 for code in codes}


# ============================================================
# v7.2 质量因子增强函数（兼容性桩）
# ============================================================

def get_profit_history_batch(stock_codes, years=4):
    """获取净利润历史（兼容性桩）"""
    return {}

def get_operating_cashflow_batch(stock_codes):
    """获取经营现金流（兼容性桩）"""
    return {}

def get_top_shareholder_ratio_batch(stock_codes):
    """获取第一大股东持股比例（兼容性桩）"""
    return {}

def calculate_profit_growth_3y(profit_history):
    """计算3年利润增长率（兼容性桩）"""
    return None

def calculate_cashflow_profit_ratio(operating_cashflow, net_profit):
    """计算现金流质量比率（兼容性桩）"""
    return None

def calc_ma_position_batch(stock_codes):
    """计算均线位置（兼容性桩）"""
    return {}

def is_profit_growing_strong(profit_history, min_cagr=0.1):
    """判断利润是否强劲增长（兼容性桩）"""
    return False

def is_profit_growing_strict(profit_history, min_cagr=0.05, min_years=3):
    """严格判断利润增长（兼容性桩）"""
    return False
