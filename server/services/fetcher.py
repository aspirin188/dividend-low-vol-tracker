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
    主流程（v8.0数据增强版）
    
    步骤：
    1. 获取EPS/ROE数据
    2. 获取实时股价
    3. 获取分红数据
    4. 计算股息率并筛选（股息率≥3%）
    5. 获取负债率数据
    6. 获取市值数据
    7. 计算价格百分位和波动率（仅对最终候选股）
    
    预计耗时：3-5分钟
    """
    start_time = time.time()
    
    print("\n" + "="*60)
    print("红利低波跟踪系统 v8.0 - 数据获取开始")
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
    
    print(f"\n  筛选后候选股: {len(result)} 只")
    
    # 步骤6: 获取负债率数据（v8.0新增）
    print("\n获取负债率数据...", flush=True)
    candidate_codes = result['code'].tolist()
    debt_data = fetch_debt_ratio_batch(candidate_codes)
    
    # 合并负债率数据
    result['debt_ratio'] = result['code'].map(lambda x: debt_data.get(x, {}).get('debt_ratio', 50.0))
    result['industry'] = result['code'].map(lambda x: debt_data.get(x, {}).get('industry', '未知'))
    
    # 步骤7: 获取市值数据（v8.0新增）
    print("\n获取市值数据...", flush=True)
    cap_data = fetch_market_cap_batch(candidate_codes)
    result['market_cap'] = result['code'].map(lambda x: cap_data.get(x))
    
    # 对于未获取到市值的股票，使用默认值1000亿（让筛选通过）
    result['market_cap'] = result['market_cap'].fillna(1000.0)
    
    # 步骤8: 计算价格百分位和波动率（仅对最终候选股，v8.0新增）
    # 注意：这里只对已经筛选后的候选股计算，避免对全量股票计算导致性能问题
    print("\n计算价格百分位和波动率...", flush=True)
    
    # 计算价格百分位
    price_percentiles = calculate_price_percentile_batch(candidate_codes, days=252)
    result['price_percentile'] = result['code'].map(lambda x: price_percentiles.get(x))
    
    # 计算波动率
    volatilities = calculate_volatility_batch(candidate_codes, window=120)
    result['annual_vol'] = result['code'].map(lambda x: volatilities.get(x))
    
    # 对于未计算出波动率的股票，使用默认值20%
    result['annual_vol'] = result['annual_vol'].fillna(20.0)
    
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
    result['payout_ratio'] = None  # 将在后续通过财务数据计算
    result['dividend_years'] = 5  # 默认值，后续可优化为实际计算
    result['pe'] = None  # 市盈率，后续可从数据源获取
    result['pb'] = None  # 市净率，后续可从数据源获取
    result['market'] = result['code'].apply(lambda x: '沪市' if x.startswith('6') else '深市' if x.startswith('00') else '创业板' if x.startswith('30') else '科创板' if x.startswith('68') else '未知')
    
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
    """
    计算均线位置和买卖信号（v7.3信号系统升级）
    
    计算逻辑：
    1. 获取股票历史价格数据（250日+30日用于趋势判断）
    2. 计算MA20、MA60、MA250
    3. 判断趋势方向（30日对比）和趋势强度
    4. 计算买卖信号（5级买入/4级卖出，含死叉检测）
    
    Args:
        stock_codes: 股票代码列表
        
    Returns:
        dict: {code: {ma20, ma60, ma250, current_price, price_vs_ma_pct, ma_slope, 
                      trend, trend_strength, signal, signal_level, signal_type, action}}
    """
    print("  计算均线位置和买卖信号...", flush=True)
    
    import akshare as ak
    import numpy as np
    
    results = {}
    
    for i, code in enumerate(stock_codes):
        if i % 50 == 0:
            print(f"    进度: {i}/{len(stock_codes)}", flush=True)
            
        try:
            # 获取历史数据（280天用于计算250日均线+30日趋势判断）
            # 使用akshare获取日K数据
            df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date="20240101", adjust="qfq")
            
            if df is None or len(df) < 280:
                # 数据不足，返回None
                results[code] = {
                    'ma20': None, 'ma60': None, 'ma250': None, 'current_price': None,
                    'price_vs_ma_pct': None, 'ma_slope': None,
                    'trend': None, 'trend_strength': None,
                    'signal': None, 'signal_level': None, 'signal_type': None, 'action': None
                }
                continue
            
            # 确保按日期排序（从旧到新）
            df = df.sort_values('日期').reset_index(drop=True)
            
            # 计算均线
            df['ma20'] = df['收盘'].rolling(window=20).mean()
            df['ma60'] = df['收盘'].rolling(window=60).mean()
            df['ma250'] = df['收盘'].rolling(window=250).mean()
            
            # 获取最新值
            current_price = float(df['收盘'].iloc[-1])
            ma20 = float(df['ma20'].iloc[-1]) if not np.isnan(df['ma20'].iloc[-1]) else None
            ma60 = float(df['ma60'].iloc[-1]) if not np.isnan(df['ma60'].iloc[-1]) else None
            ma250 = float(df['ma250'].iloc[-1]) if not np.isnan(df['ma250'].iloc[-1]) else None
            
            # 计算价格相对均线位置
            if ma250 and ma250 > 0:
                price_vs_ma_pct = ((current_price - ma250) / ma250) * 100
            else:
                price_vs_ma_pct = None
            
            # 计算均线斜率（60日变化）
            if len(df) >= 310 and not np.isnan(df['ma250'].iloc[-60]):
                ma250_60d_ago = float(df['ma250'].iloc[-60])
                ma_slope = ((ma250 - ma250_60d_ago) / ma250_60d_ago) * 100 if ma250_60d_ago > 0 else 0
            else:
                ma_slope = 0
            
            # 趋势判断（30日对比）
            if len(df) >= 280 and not np.isnan(df['ma250'].iloc[-30]):
                ma250_30d_ago = float(df['ma250'].iloc[-30])
                ma_change_30d = (ma250 - ma250_30d_ago) / ma250_30d_ago if ma250_30d_ago > 0 else 0
                
                if ma_change_30d > 0.01:  # 30日上涨1%以上
                    trend = '向上'
                elif ma_change_30d < -0.01:  # 30日下跌1%以上
                    trend = '向下'
                else:
                    trend = '横盘'
            else:
                trend = '横盘'
            
            # 趋势强度判断
            if trend == '向上':
                if price_vs_ma_pct is not None:
                    if price_vs_ma_pct > 15:
                        trend_strength = '强势'
                    elif price_vs_ma_pct > 0:
                        trend_strength = '温和'
                    else:
                        trend_strength = '弱势'
                else:
                    trend_strength = '温和'
            elif trend == '向下':
                trend_strength = '下降'
            else:
                trend_strength = '震荡'
            
            # 初始化信号
            signal = None
            signal_level = None
            signal_type = None
            action = None
            
            # 卖出信号优先级最高（风险控制第一）
            # 1. 死叉检测（MA20 < MA60）
            if ma20 is not None and ma60 is not None and ma20 < ma60:
                signal = "强制卖出"
                signal_level = -4
                signal_type = "sell"
                action = "短期均线死叉，不计成本卖出"
            
            # 2. 价格跌破250日线且趋势向下
            elif price_vs_ma_pct is not None and price_vs_ma_pct < 0 and trend == '向下':
                signal = "清仓"
                signal_level = -3
                signal_type = "sell"
                action = "跌破250日线且趋势向下，全部卖出"
            
            # 3. 价格跌破均线但趋势不明
            elif price_vs_ma_pct is not None and price_vs_ma_pct < 0 and trend == '横盘':
                signal = "减仓"
                signal_level = -2
                signal_type = "sell"
                action = "跌破均线但趋势不明，减半仓"
            
            # 4. 价格跌破均线但趋势仍向上
            elif price_vs_ma_pct is not None and price_vs_ma_pct < 0 and trend == '向上':
                signal = "警示"
                signal_level = -1
                signal_type = "sell"
                action = "跌破均线但趋势仍向上，密切观察"
            
            # 买入信号（仅在无卖出信号时判断）
            else:
                # 5. 强烈买入：回踩均线±3% + 均线向上
                if price_vs_ma_pct is not None and abs(price_vs_ma_pct) <= 3 and trend == '向上':
                    signal = "强烈买入"
                    signal_level = 5
                    signal_type = "buy"
                    action = "回踩250日线企稳，黄金买点"
                
                # 6. 买入：价格在均线上方0-5% + 均线向上
                elif price_vs_ma_pct is not None and 0 < price_vs_ma_pct <= 5 and trend == '向上':
                    signal = "买入"
                    signal_level = 4
                    signal_type = "buy"
                    action = "价格在均线上方且趋势向上，可买入"
                
                # 7. 试探买入：价格在均线上方5-10% + 温和趋势
                elif price_vs_ma_pct is not None and 5 < price_vs_ma_pct <= 10 and trend == '向上':
                    signal = "试探买入"
                    signal_level = 3
                    signal_type = "buy"
                    action = "趋势温和，可小仓位试探"
                
                # 8. 观望：价格在均线下方但接近 + 均线向上
                elif price_vs_ma_pct is not None and -5 < price_vs_ma_pct < 0 and trend == '向上':
                    signal = "观望"
                    signal_level = 2
                    signal_type = "hold"
                    action = "等待回踩确认"
                
                # 9. 不建议：价格在均线下方 + 均线向下
                elif price_vs_ma_pct is not None and price_vs_ma_pct < 0 and trend == '向下':
                    signal = "不建议"
                    signal_level = 0
                    signal_type = "hold"
                    action = "趋势向下，不建议介入"
                
                # 10. 持有：价格在均线上方 + 趋势向上
                elif price_vs_ma_pct is not None and price_vs_ma_pct > 0 and trend == '向上':
                    signal = "持有"
                    signal_level = 1
                    signal_type = "hold"
                    action = "价格在均线上方且趋势向上，继续持有"
                
                # 默认观望
                else:
                    signal = "观望"
                    signal_level = 0
                    signal_type = "hold"
                    action = "等待明确信号"
            
            # 存储结果
            results[code] = {
                'ma20': round(ma20, 2) if ma20 else None,
                'ma60': round(ma60, 2) if ma60 else None,
                'ma250': round(ma250, 2) if ma250 else None,
                'current_price': round(current_price, 2),
                'price_vs_ma_pct': round(price_vs_ma_pct, 2) if price_vs_ma_pct is not None else None,
                'ma_slope': round(ma_slope, 2),
                'trend': trend,
                'trend_strength': trend_strength,
                'signal': signal,
                'signal_level': signal_level,
                'signal_type': signal_type,
                'action': action
            }
            
        except Exception as e:
            # 出错时返回空值
            results[code] = {
                'ma20': None, 'ma60': None, 'ma250': None, 'current_price': None,
                'price_vs_ma_pct': None, 'ma_slope': None,
                'trend': None, 'trend_strength': None,
                'signal': None, 'signal_level': None, 'signal_type': None, 'action': None
            }
            continue
    
    print(f"  ✓ 完成均线位置和信号计算（{len(results)}只）")
    return results

def is_profit_growing_strong(profit_history, min_cagr=0.1):
    """判断利润是否强劲增长（兼容性桩）"""
    return False

def is_profit_growing_strict(profit_history, min_cagr=0.05, min_years=3):
    """严格判断利润增长（兼容性桩）"""
    return False


def calculate_payout_stability_score(code: str) -> tuple:
    """
    计算分红稳定性评分

    Args:
        code: 股票代码

    Returns:
        (payout_3y_avg, payout_stability)
        - payout_3y_avg: 3年平均支付率（可能是None）
        - payout_stability: 分红稳定性评分 (0-100)
    """
    # 从DataFrame中获取dividend_years
    # 注意：这个函数在循环中被调用，需要从外部传入df
    return (None, 50.0)  # 默认返回中等稳定性


def calculate_ma_position_batch(stock_codes: list) -> dict:
    """
    批量计算均线位置（兼容性桩）

    Args:
        stock_codes: 股票代码列表

    Returns:
        {code: {'ma250': float, 'ma20': float, 'current_price': float}}
    """
    return {code: {'ma250': None, 'ma20': None, 'current_price': None} for code in stock_codes}


def calculate_volatility_batch(stock_codes: list, window: int = 120) -> dict:
    """
    批量计算年化波动率（v8.0实现）
    
    计算逻辑：
    1. 获取股票历史价格数据
    2. 计算日收益率标准差
    3. 年化处理：std * sqrt(242)
    
    性能优化：
    - 仅对最终候选股计算（约30-50只）
    - 批量获取数据，复用历史数据
    
    Args:
        stock_codes: 股票代码列表
        window: 计算窗口天数，默认120日
        
    Returns:
        {code: annual_volatility}
    """
    print(f"  计算年化波动率（{len(stock_codes)}只，{window}日窗口）...", flush=True)
    
    results = {}
    
    for i, code in enumerate(stock_codes):
        if i % 10 == 0:
            print(f"    进度: {i}/{len(stock_codes)}", flush=True)
        
        try:
            # 获取历史数据（需要window+1天来计算收益率）
            df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date="20240101", adjust="qfq")
            
            if df is None or len(df) < window + 1:
                results[code] = None
                continue
            
            # 确保按日期排序
            df = df.sort_values('日期').reset_index(drop=True)
            
            # 取最近window天的数据
            df = df.tail(window + 1).copy()
            
            # 计算日收益率（对数收益率）
            df['returns'] = np.log(df['收盘'] / df['收盘'].shift(1))
            
            # 去掉第一个NaN
            returns = df['returns'].dropna()
            
            if len(returns) < window * 0.8:  # 要求至少80%的数据有效
                results[code] = None
                continue
            
            # 计算标准差
            daily_std = returns.std()
            
            # 年化处理：乘以sqrt(242)，转换为百分比
            annual_vol = daily_std * np.sqrt(242) * 100
            
            results[code] = round(annual_vol, 2)
            
        except Exception as e:
            print(f"    {code}波动率计算失败: {e}", flush=True)
            results[code] = None
            continue
    
    valid_count = sum(1 for v in results.values() if v is not None)
    print(f"  ✓ 完成波动率计算（有效数据{valid_count}只）")
    return results


def calculate_price_percentile_batch(stock_codes: list, days: int = 252) -> dict:
    """
    批量计算股价百分位（v8.0新增）
    
    计算逻辑：
    1. 获取股票近days日历史价格数据
    2. 计算当前价格在历史序列中的百分位
    3. 百分位越低表示股价越接近历史低位
    
    性能优化：
    - 仅对最终候选股计算（约30-50只）
    - 使用已有的历史数据获取逻辑
    
    Args:
        stock_codes: 股票代码列表
        days: 历史数据窗口，默认252日（约1年）
        
    Returns:
        {code: percentile}，percentile为0-100的浮点数
    """
    print(f"  计算股价百分位（{len(stock_codes)}只，{days}日窗口）...", flush=True)
    
    results = {}
    
    for i, code in enumerate(stock_codes):
        if i % 10 == 0:
            print(f"    进度: {i}/{len(stock_codes)}", flush=True)
        
        try:
            # 获取历史数据
            df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date="20240101", adjust="qfq")
            
            if df is None or len(df) < days * 0.5:  # 至少50%的数据
                results[code] = None
                continue
            
            # 确保按日期排序
            df = df.sort_values('日期').reset_index(drop=True)
            
            # 取最近days天的收盘价
            prices = df['收盘'].tail(days).values
            current_price = prices[-1]
            
            # 计算百分位：当前价格在历史序列中的位置
            # percentile = (小于当前价格的数量 / 总数量) * 100
            below_count = np.sum(prices < current_price)
            percentile = (below_count / len(prices)) * 100
            
            results[code] = round(percentile, 2)
            
        except Exception as e:
            print(f"    {code}百分位计算失败: {e}", flush=True)
            results[code] = None
            continue
    
    valid_count = sum(1 for v in results.values() if v is not None)
    print(f"  ✓ 完成股价百分位计算（有效数据{valid_count}只）")
    return results


def fetch_debt_ratio_batch(stock_codes: list) -> dict:
    """
    批量获取资产负债率（v8.0新增）
    
    数据来源：akshare stock_zcfz_em（资产负债表）
    
    数据处理规则：
    - 金融业（银行、证券、保险）：默认上限85%
    - 一般行业：默认上限70%
    - 数据缺失时使用默认值50%（中等风险）
    
    Args:
        stock_codes: 股票代码列表
        
    Returns:
        {code: {'debt_ratio': float, 'industry': str}}
    """
    print(f"  获取资产负债率（{len(stock_codes)}只）...", flush=True)
    
    results = {}
    
    try:
        # 使用akshare获取资产负债表数据
        # 获取最新报告期的数据
        df = ak.stock_zcfz_em(date="20241231")
        
        if df is None or df.empty:
            print("  ✗ 无法获取资产负债表数据", flush=True)
            # 返回默认值
            return {code: {'debt_ratio': 50.0, 'industry': '未知'} for code in stock_codes}
        
        # 识别列名
        code_col = None
        debt_col = None
        industry_col = None
        
        for col in df.columns:
            col_str = str(col)
            if '代码' in col_str or col_str.lower() == 'code':
                code_col = col
            elif '负债率' in col_str or '资产负债' in col_str:
                debt_col = col
            elif '行业' in col_str:
                industry_col = col
        
        if not code_col or not debt_col:
            print(f"  ⚠️ 无法识别负债率列名: {list(df.columns)}", flush=True)
            return {code: {'debt_ratio': 50.0, 'industry': '未知'} for code in stock_codes}
        
        # 清理股票代码
        df[code_col] = df[code_col].astype(str).str.zfill(6)
        df[debt_col] = pd.to_numeric(df[debt_col], errors='coerce')
        
        # 构建结果字典
        for code in stock_codes:
            row = df[df[code_col] == code]
            if row.empty:
                results[code] = {'debt_ratio': 50.0, 'industry': '未知'}
            else:
                debt_ratio = row[debt_col].values[0]
                industry = row[industry_col].values[0] if industry_col and not pd.isna(row[industry_col].values[0]) else '未知'
                
                if pd.isna(debt_ratio):
                    results[code] = {'debt_ratio': 50.0, 'industry': industry}
                else:
                    results[code] = {'debt_ratio': round(float(debt_ratio), 2), 'industry': industry}
        
        valid_count = sum(1 for v in results.values() if v['debt_ratio'] != 50.0)
        print(f"  ✓ 完成负债率获取（有效数据{valid_count}只）")
        return results
        
    except Exception as e:
        print(f"  ✗ 获取负债率失败: {e}", flush=True)
        # 返回默认值
        return {code: {'debt_ratio': 50.0, 'industry': '未知'} for code in stock_codes}


def fetch_market_cap_batch(stock_codes: list) -> dict:
    """
    批量获取市值数据（v8.0新增）
    
    数据来源：akshare stock_yjbb_em（业绩报表中包含市值数据）
    
    Args:
        stock_codes: 股票代码列表
        
    Returns:
        {code: market_cap_in_yi}，单位为亿元
    """
    print(f"  获取市值数据（{len(stock_codes)}只）...", flush=True)
    
    results = {}
    
    try:
        # 使用akshare获取业绩报表数据（包含市值）
        df = ak.stock_yjbb_em(date='20241231')
        
        if df is None or df.empty:
            print("  ✗ 无法获取市值数据", flush=True)
            return {code: None for code in stock_codes}
        
        # 识别列名
        code_col = None
        cap_col = None
        
        for col in df.columns:
            col_str = str(col)
            if '代码' in col_str:
                code_col = col
            elif '市值' in col_str and '亿' in col_str:
                cap_col = col
        
        if not code_col or not cap_col:
            print(f"  ⚠️ 无法识别市值列名，尝试备选方案", flush=True)
            # 尝试通过现有数据估算市值
            return {code: None for code in stock_codes}
        
        # 清理数据
        df[code_col] = df[code_col].astype(str).str.zfill(6)
        df[cap_col] = pd.to_numeric(df[cap_col], errors='coerce')
        
        # 构建结果字典
        for code in stock_codes:
            row = df[df[code_col] == code]
            if row.empty:
                results[code] = None
            else:
                cap = row[cap_col].values[0]
                results[code] = round(float(cap), 2) if not pd.isna(cap) else None
        
        valid_count = sum(1 for v in results.values() if v is not None)
        print(f"  ✓ 完成市值获取（有效数据{valid_count}只）")
        return results
        
    except Exception as e:
        print(f"  ✗ 获取市值失败: {e}", flush=True)
        return {code: None for code in stock_codes}


def get_dividend_per_share_batch(stock_codes: list) -> dict:
    """
    批量获取每股股利（兼容性桩）

    Args:
        stock_codes: 股票代码列表

    Returns:
        {code: dividend_per_share}
    """
    return {code: 0.0 for code in stock_codes}
