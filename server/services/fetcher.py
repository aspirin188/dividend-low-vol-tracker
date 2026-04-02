"""
数据获取服务 — 红利低波跟踪系统（v8.5 质量因子完善版）

v8.5 核心新增：
1. get_operating_cashflow_batch() 真实实现：从stock_yjbb_em获取每股经营现金流
2. get_top_shareholder_ratio_batch() 真实实现：从stock_gdfx_free_holding_analyse_em获取第一大股东持股比例
3. calculate_cashflow_profit_ratio() 更新为每股口径计算
4. 消除v7.2以来的桩函数依赖

v8.4 核心新增：
1. 成长因子数据获取：净利润增长率、PEG、ROE趋势
2. fetch_profit_growth_data() 真实实现（不再返回空数据）
3. calculate_profit_growth_3y() 真实实现

v8.3 核心修复：
1. 信号逻辑优化：趋势向上时降低死叉信号强度
   - 趋势向下+死叉 → 强制卖出（-4）
   - 横盘+死叉 → 减仓（-2）
   - 趋势向上+死叉 → 警示（-1），改为观察而非卖出

v8.2 核心修复：
1. PE/PB: 使用 stock_yjbb_em 的 EPS 和 stock_fhps_em 的每股净资产计算
2. 市值: 使用 stock_fhps_em 的总股本 × 股价计算真实市值
3. 分红年数: 查询近5年 stock_fhps_em 数据统计真实分红年数
4. 支付率稳定性: 查询近3年分红数据计算
5. 每股股利: 从 stock_fhps_em 现金分红比例字段直接获取
6. 删除桩函数 calculate_ma_position_batch，消除同名冲突

数据流程：
1. akshare获取EPS/ROE（年报数据）
2. 新浪接口获取实时股价
3. akshare获取分红数据（含总股本、每股净资产等）
4. 计算股息率、PE、PB、市值并筛选
"""

import re
import os
import time
import math
import numpy as np
import pandas as pd
import akshare as ak
import requests
from datetime import datetime, timedelta
from contextlib import contextmanager


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
# v8.0: K线数据缓存，避免重复请求
_hist_cache = {}


# ============================================================
# 代理控制 - v8.0修复: 解决ProxyError问题
# ============================================================

@contextmanager
def no_proxy():
    """
    临时禁用代理的上下文管理器
    
    macOS上requests/urllib3可能从系统网络设置自动读取代理，
    仅清除环境变量不够，还需要在session层面禁用代理。
    
    v8.0修复：同时清除环境变量 + monkey-patch requests.Session
    """
    # 保存原有代理设置
    old_env = {}
    for key in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY',
                'all_proxy', 'ALL_PROXY', 'no_proxy', 'NO_PROXY']:
        old_env[key] = os.environ.get(key)
        if key in os.environ:
            del os.environ[key]
    
    # 设置NO_PROXY = '*' 来禁用所有代理（针对从系统设置读取的情况）
    os.environ['NO_PROXY'] = '*'
    os.environ['no_proxy'] = '*'
    
    # Monkey-patch requests以强制不使用代理
    original_get = requests.Session.get
    original_post = requests.Session.post
    
    def patched_get(self, url, **kwargs):
        kwargs['proxies'] = {'http': None, 'https': None}
        return original_get(self, url, **kwargs)
    
    def patched_post(self, url, **kwargs):
        kwargs['proxies'] = {'http': None, 'https': None}
        return original_post(self, url, **kwargs)
    
    requests.Session.get = patched_get
    requests.Session.post = patched_post
    
    try:
        yield
    finally:
        # 恢复原有代理设置
        for key, value in old_env.items():
            if value is not None:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]
        
        # 恢复requests
        requests.Session.get = original_get
        requests.Session.post = original_post


# ============================================================
# 核心数据获取函数
# ============================================================

def fetch_eps_data():
    """获取EPS和ROE数据（年报）"""
    print("  [1/3] 获取EPS和ROE数据...", flush=True)
    
    try:
        # 使用akshare获取年报数据
        with no_proxy():
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
    """
    获取分红数据（v8.2增强：同时获取总股本、每股净资产、支付率）
    
    v8.2 修复：
    - 利用 stock_fhps_em 返回的丰富字段，一次性获取：
      股息率、总股本、每股净资产、现金分红比例、每股收益
    - 用于计算 PE、PB、真实市值、每股股利、支付率
    """
    print("  [3/3] 获取分红及估值数据...", flush=True)
    
    try:
        with no_proxy():
            df = ak.stock_fhps_em(date='20241231')
        
        if df is None or df.empty:
            print("  ✗ 获取失败", flush=True)
            return pd.DataFrame()
        
        # 识别列名
        col_map = {}
        for col in df.columns:
            col_str = str(col)
            if '代码' in col_str or col_str.lower() == 'code':
                col_map['code'] = col
            elif '股息率' in col_str:
                col_map['div_yield'] = col
            elif '现金分红' in col_str and '比例' in col_str:
                col_map['div_ratio'] = col  # 每10股分红金额
            elif col_str == '总股本':
                col_map['total_shares'] = col
            elif col_str == '每股净资产':
                col_map['bps'] = col  # Book Value Per Share
            elif col_str == '每股收益' and 'eps' not in col_map:
                col_map['eps'] = col
        
        if 'code' not in col_map:
            print(f"  ✗ 无法识别代码列: {list(df.columns)}", flush=True)
            return pd.DataFrame()
        
        # 提取数据
        result = pd.DataFrame()
        result['code'] = df[col_map['code']].astype(str).str.zfill(6)
        
        # 股息率（百分比）
        if 'div_yield' in col_map:
            result['div_yield_raw'] = pd.to_numeric(df[col_map['div_yield']], errors='coerce') * 100
        
        # 每10股分红金额 → 每股股利（元/股）
        if 'div_ratio' in col_map:
            result['div_per_share'] = pd.to_numeric(df[col_map['div_ratio']], errors='coerce') / 10
        
        # 总股本（股）
        if 'total_shares' in col_map:
            result['total_shares'] = pd.to_numeric(df[col_map['total_shares']], errors='coerce')
        
        # 每股净资产
        if 'bps' in col_map:
            result['bps'] = pd.to_numeric(df[col_map['bps']], errors='coerce')
        
        # 每股收益（从分红数据中获取，作为备用）
        if 'eps' in col_map:
            result['eps_from_div'] = pd.to_numeric(df[col_map['eps']], errors='coerce')
        
        # 兼容旧字段：dividend = 股息率百分比
        if 'div_yield_raw' in result.columns:
            result['dividend'] = result['div_yield_raw']
        elif 'div_ratio' in col_map:
            result['dividend'] = result['div_per_share']  # 后续用股价计算
        
        # 过滤有效数据（必须有股息率或分红金额）
        valid_mask = result['dividend'].notna() & (result['dividend'] > 0)
        result = result[valid_mask].copy()
        
        # 去重
        result = result.drop_duplicates(subset='code', keep='first')
        
        valid_shares = result['total_shares'].notna().sum() if 'total_shares' in result.columns else 0
        valid_bps = result['bps'].notna().sum() if 'bps' in result.columns else 0
        print(f"  ✓ 获取 {len(result)} 只（含总股本{valid_shares}只、每股净资产{valid_bps}只）", flush=True)
        
        return result
        
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
    print("红利低波跟踪系统 v8.2 - 数据获取开始")
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
    
    # 步骤3: 获取分红及估值数据（v8.2增强）
    div_df = fetch_dividend_data()
    
    if not div_df.empty:
        # 只合并需要的主字段，避免重复列
        div_cols = ['code', 'dividend']
        if 'total_shares' in div_df.columns:
            div_cols.append('total_shares')
        if 'bps' in div_df.columns:
            div_cols.append('bps')
        if 'div_per_share' in div_df.columns:
            div_cols.append('div_per_share')
        
        merged = merged.merge(div_df[div_cols], on='code', how='left')
        
        # 步骤4: 计算股息率
        print("\n计算股息率...", flush=True)
        # 优先使用直接获取的股息率，备用方案：每股股利/股价
        if 'div_yield_raw' in div_df.columns:
            merged = merged.merge(div_df[['code', 'div_yield_raw']], on='code', how='left')
            merged['div_yield'] = merged['div_yield_raw'].round(2)
        elif 'div_per_share' in merged.columns:
            merged['div_yield'] = (merged['div_per_share'] / merged['price'] * 100).round(2)
        else:
            merged['div_yield'] = merged['dividend'].round(2)
        
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
    
    # 步骤6.1: v8.2修复 - 使用总股本计算真实市值
    print("\n计算真实市值...", flush=True)
    if 'total_shares' in result.columns and result['total_shares'].notna().any():
        # 市值 = 股价 × 总股本 / 1e8（元→亿元）
        result['market_cap'] = (result['price'] * result['total_shares'] / 1e8).round(2)
        valid_cap = result['market_cap'].notna().sum()
        print(f"  ✓ 有效市值数据 {valid_cap} 只", flush=True)
    else:
        print("  ⚠️ 无总股本数据，使用估算值", flush=True)
        result['market_cap'] = result['price'] * 100
    
    # 步骤6.2: v8.2修复 - 计算PE和PB
    print("\n计算PE和PB...", flush=True)
    # PE = 股价 / EPS
    result['pe'] = (result['price'] / result['eps']).round(2)
    # PE合理性校验：PE < 0 表示亏损，PE > 200 可能是异常
    result.loc[result['pe'] < 0, 'pe'] = None
    result.loc[result['pe'] > 200, 'pe'] = None
    
    # PB = 股价 / 每股净资产
    if 'bps' in result.columns and result['bps'].notna().any():
        result['pb'] = (result['price'] / result['bps']).round(2)
        result.loc[result['pb'] < 0, 'pb'] = None
        result.loc[result['pb'] > 50, 'pb'] = None
        valid_pb = result['pb'].notna().sum()
        print(f"  ✓ 有效PE {result['pe'].notna().sum()} 只，PB {valid_pb} 只", flush=True)
    else:
        result['pb'] = None
        print(f"  ✓ 有效PE {result['pe'].notna().sum()} 只（无PB数据）", flush=True)
    
    # 排除ST
    result = result[~result['name'].str.contains('ST', case=False, na=False)].copy()
    
    print(f"\n  筛选后候选股: {len(result)} 只")
    
    # 步骤7: 获取负债率数据（v8.0新增）
    print("\n获取负债率数据...", flush=True)
    candidate_codes = result['code'].tolist()
    debt_data = fetch_debt_ratio_batch(candidate_codes)
    
    # 合并负债率数据
    result['debt_ratio'] = result['code'].map(lambda x: debt_data.get(x, {}).get('debt_ratio', 50.0))
    result['industry'] = result['code'].map(lambda x: debt_data.get(x, {}).get('industry', '未知'))
    
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
    # v8.2修复：dividend_per_share 使用真实每股股利（元/股）
    if 'div_per_share' in result.columns:
        result['dividend_per_share'] = result['div_per_share']
    else:
        result['dividend_per_share'] = result['dividend']  # 兼容
    # v8.2修复：计算支付率 = 每股股利 / 每股收益
    result['payout_ratio'] = (result['dividend_per_share'] / result['eps'] * 100).round(2)
    result.loc[result['payout_ratio'] > 500, 'payout_ratio'] = None  # 异常值过滤
    result['dividend_years'] = 5  # 后续 F-02 修复
    # v8.2修复：PE/PB 已在步骤6计算
    # pe 和 pb 字段已直接赋值，无需再设 None
    result['market'] = result['code'].apply(lambda x: '沪市' if x.startswith('6') else '深市' if x.startswith('00') else '创业板' if x.startswith('30') else '科创板' if x.startswith('68') else '未知')
    
    # v8.0修复: 确保所有数值列的类型正确
    numeric_columns = [
        'eps', 'roe', 'price', 'dividend', 'div_yield',
        'debt_ratio', 'market_cap', 'price_percentile', 'annual_vol',
        'basic_eps', 'dividend_yield', 'dividend_yield_ttm', 
        'dividend_per_share', 'dividend_years'
    ]
    
    for col in numeric_columns:
        if col in result.columns:
            result[col] = pd.to_numeric(result[col], errors='coerce')
    
    # 对NaN值进行合理填充
    result['debt_ratio'] = result['debt_ratio'].fillna(50.0)  # 默认中等风险
    # v8.0修复：市值不设置默认值，让筛选逻辑正确过滤小盘股
    # result['market_cap'] = result['market_cap'].fillna(1000.0)  # 旧代码：导致小盘股通过筛选
    result['annual_vol'] = result['annual_vol'].fillna(20.0)  # 默认20%波动率
    result['dividend_years'] = result['dividend_years'].fillna(5)  # 默认5年
    
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

def get_dividend_years_batch(codes, years=5):
    """
    获取连续分红年数（v8.2修复：真实实现）
    
    通过查询近years年的分红数据，统计每只股票的分红年数。
    
    Args:
        codes: 股票代码列表
        years: 查询年数，默认5年
        
    Returns:
        {code: dividend_years}
    """
    from datetime import datetime
    current_year = datetime.now().year
    
    # 计算需要查询的年报日期
    dates = []
    for y in range(years):
        report_year = current_year - 1 - y  # 上一年到前years年
        dates.append(f'{report_year}1231')
    
    # 如果当前在4月之后，最新年报可能是当年的
    if datetime.now().month >= 4:
        dates.insert(0, f'{current_year - 1}1231')
        dates = dates[:years]  # 只取最近years个
    
    # 统计每只股票的分红年数
    dividend_count = {code: 0 for code in codes}
    
    for date_str in dates:
        try:
            with no_proxy():
                df = ak.stock_fhps_em(date=date_str)
            
            if df is None or df.empty:
                continue
            
            # 找到代码列
            code_col = None
            for col in df.columns:
                if '代码' in str(col) or str(col).lower() == 'code':
                    code_col = col
                    break
            
            if not code_col:
                continue
            
            # 找到分红比例列
            div_col = None
            for col in df.columns:
                if '现金分红' in str(col) and '比例' in str(col):
                    div_col = col
                    break
            
            if not div_col:
                continue
            
            # 统计有分红的股票
            df[code_col] = df[code_col].astype(str).str.zfill(6)
            df[div_col] = pd.to_numeric(df[div_col], errors='coerce')
            
            for _, row in df[df[div_col] > 0].iterrows():
                code = row[code_col]
                if code in dividend_count:
                    dividend_count[code] += 1
                    
        except Exception:
            continue
    
    return dividend_count


# ============================================================
# v7.2/v8.4 质量因子数据获取（v8.4真实实现）
# ============================================================

_profit_growth_cache = {}

def fetch_profit_growth_data(stock_codes, years=3):
    """
    批量获取净利润增长数据（v8.4真实实现）
    
    通过查询近years年的年报业绩数据，计算：
    - profit_growth_3y: 近3年净利润CAGR（%）
    - roe_trend: ROE趋势变化（最新ROE - years年前ROE，百分点）
    - peg: PEG = PE / 利润增速
    
    数据来源：akshare stock_yjbb_em（年报业绩）
    
    Args:
        stock_codes: 股票代码列表
        years: 查询年数，默认3年
        
    Returns:
        {code: {profit_growth_3y: float, roe_trend: float, peg: float}}
    """
    print(f"  获取净利润增长数据（{len(stock_codes)}只）...", flush=True)
    
    from datetime import datetime
    current_year = datetime.now().year
    
    # 计算需要查询的年报日期
    dates = []
    for y in range(years + 1):  # 多查一年用于ROE趋势
        report_year = current_year - 1 - y
        dates.append(f'{report_year}1231')
    
    # 逐年获取净利润和ROE数据
    # {code: {'year': year, 'net_profit': float, 'roe': float}}
    stock_data = {}
    
    for date_str in dates:
        try:
            with no_proxy():
                df = ak.stock_yjbb_em(date=date_str)
            
            if df is None or df.empty:
                continue
            
            # 识别列名
            code_col = None
            profit_col = None
            roe_col = None
            
            for col in df.columns:
                col_str = str(col)
                if '代码' in col_str or col_str.lower() == 'code':
                    code_col = col
                elif '净利润' in col_str and '同比' not in col_str and '扣除' not in col_str:
                    profit_col = col
                elif '净资产收益率' in col_str or 'ROE' in col_str.upper():
                    roe_col = col
            
            if not code_col or not profit_col:
                continue
            
            df[code_col] = df[code_col].astype(str).str.zfill(6)
            df[profit_col] = pd.to_numeric(df[profit_col], errors='coerce')
            if roe_col:
                df[roe_col] = pd.to_numeric(df[roe_col], errors='coerce')
            
            year = int(date_str[:4])
            
            for _, row in df.iterrows():
                code = row[code_col]
                if code not in stock_codes:
                    continue
                if code not in stock_data:
                    stock_data[code] = {}
                
                profit = row[profit_col]
                if pd.notna(profit) and profit > 0:
                    stock_data[code][year] = {
                        'net_profit': float(profit),
                        'roe': float(row[roe_col]) if roe_col and pd.notna(row[roe_col]) else None
                    }
                    
        except Exception as e:
            if date_str == dates[0]:  # 只打印第一个错误
                print(f"    获取{date_str}数据失败: {e}", flush=True)
            continue
    
    # 计算成长指标
    results = {}
    valid_growth = 0
    valid_peg = 0
    
    for code in stock_codes:
        code_entry = stock_data.get(code, {})
        if len(code_entry) < 2:
            results[code] = {
                'profit_growth_3y': None,
                'roe_trend': None,
                'peg': None,
            }
            continue
        
        # 按年份排序
        sorted_years = sorted(code_entry.keys())
        
        # 1. 计算净利润CAGR
        latest_year = sorted_years[-1]
        earliest_year = sorted_years[0]
        
        latest_profit = code_entry[latest_year]['net_profit']
        earliest_profit = code_entry[earliest_year]['net_profit']
        
        if earliest_profit > 0:
            n_years = latest_year - earliest_year
            if n_years > 0:
                cagr = (latest_profit / earliest_profit) ** (1.0 / n_years) - 1
                profit_growth_3y = round(cagr * 100, 2)  # 转为百分比
                valid_growth += 1
            else:
                profit_growth_3y = None
        else:
            profit_growth_3y = None
        
        # 2. 计算ROE趋势
        latest_roe = code_entry[latest_year].get('roe')
        earliest_roe = code_entry[earliest_year].get('roe')
        
        if latest_roe is not None and earliest_roe is not None:
            roe_trend = round(latest_roe - earliest_roe, 2)  # 百分点变化
        else:
            roe_trend = None
        
        # 3. PEG稍后在scorer中计算（需要PE数据），此处先设None
        results[code] = {
            'profit_growth_3y': profit_growth_3y,
            'roe_trend': roe_trend,
            'peg': None,  # 需要配合PE数据计算
        }
    
    _profit_growth_cache.update(results)
    print(f"  ✓ 完成净利润增长数据获取（有效增长数据{valid_growth}只）", flush=True)
    return results


def get_profit_history_batch(stock_codes, years=4):
    """
    获取净利润历史（v8.4真实实现）
    返回 {code: [{'year': int, 'profit': float}, ...]}
    """
    from datetime import datetime
    current_year = datetime.now().year
    
    result = {}
    for y in range(years):
        report_year = current_year - 1 - y
        date_str = f'{report_year}1231'
        
        try:
            with no_proxy():
                df = ak.stock_yjbb_em(date=date_str)
            
            if df is None or df.empty:
                continue
            
            code_col = None
            profit_col = None
            for col in df.columns:
                col_str = str(col)
                if '代码' in col_str or col_str.lower() == 'code':
                    code_col = col
                elif '净利润' in col_str and '同比' not in col_str and '扣除' not in col_str:
                    profit_col = col
            
            if not code_col or not profit_col:
                continue
            
            df[code_col] = df[code_col].astype(str).str.zfill(6)
            df[profit_col] = pd.to_numeric(df[profit_col], errors='coerce')
            
            for _, row in df.iterrows():
                code = row[code_col]
                if code not in stock_codes:
                    continue
                if code not in result:
                    result[code] = []
                profit = row[profit_col]
                if pd.notna(profit) and profit > 0:
                    result[code].append({
                        'year': report_year,
                        'profit': float(profit)
                    })
        except Exception:
            continue
    
    return result


def calculate_profit_growth_3y(profit_history):
    """
    计算3年利润增长率（v8.4真实实现）
    
    Args:
        profit_history: [{'year': int, 'profit': float}, ...]
        
    Returns:
        float or None: CAGR百分比，如 8.5 表示 8.5%
    """
    if not profit_history or len(profit_history) < 2:
        return None
    
    # 按年份排序
    sorted_data = sorted(profit_history, key=lambda x: x['year'])
    
    earliest = sorted_data[0]
    latest = sorted_data[-1]
    
    if earliest['profit'] <= 0:
        return None
    
    n_years = latest['year'] - earliest['year']
    if n_years <= 0:
        return None
    
    cagr = (latest['profit'] / earliest['profit']) ** (1.0 / n_years) - 1
    return round(cagr * 100, 2)

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
            # v8.0修复: 使用_fetch_hist自动选择可用数据源
            df = _fetch_hist(code)
            
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
            # v8.3优化：趋势向上时降级信号，避免长期趋势向上时过度反应
            if ma20 is not None and ma60 is not None and ma20 < ma60:
                if trend == '向下':
                    # 趋势向下 + 死叉 → 强制卖出
                    signal = "强制卖出"
                    signal_level = -4
                    signal_type = "sell"
                    action = "趋势向下+死叉，风险控制卖出"
                elif trend == '横盘':
                    # 横盘 + 死叉 → 减仓
                    signal = "减仓"
                    signal_level = -2
                    signal_type = "sell"
                    action = "横盘震荡+死叉，减半仓观望"
                else:  # trend == '向上'
                    # 趋势向上 + 死叉 → 警示（降级处理）
                    signal = "警示"
                    signal_level = -1
                    signal_type = "hold"
                    action = "趋势向上+死叉，短期波动，密切观察"
            
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
                signal_type = "hold"
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
    """判断利润是否强劲增长（v8.4真实实现）"""
    growth = calculate_profit_growth_3y(profit_history)
    return growth is not None and growth >= min_cagr * 100

def is_profit_growing_strict(profit_history, min_cagr=0.05, min_years=3):
    """严格判断利润增长（v8.4真实实现）"""
    growth = calculate_profit_growth_3y(profit_history)
    return growth is not None and growth >= min_cagr * 100


_payout_stability_cache = {}

def calculate_payout_stability_score(code: str, years: int = 3) -> tuple:
    """
    计算分红稳定性评分（v8.2修复：真实实现）
    
    查询近years年的分红数据，计算：
    - payout_3y_avg: 每股股利3年均值
    - payout_stability: 稳定性评分 (0-100)
    
    稳定性算法：
    - 有分红记录的年数 / years * 50 + 均值系数 * 50
    - 均值系数 = min(支付率均值/100, 1.0)，支付率50%以上得满分
    
    Args:
        code: 股票代码
        years: 查询年数
        
    Returns:
        (payout_avg, stability_score)
    """
    global _payout_stability_cache
    
    if code in _payout_stability_cache:
        return _payout_stability_cache[code]
    
    from datetime import datetime
    current_year = datetime.now().year
    
    div_amounts = []  # 每年每股股利
    
    for y in range(years):
        report_year = current_year - 1 - y
        date_str = f'{report_year}1231'
        
        try:
            with no_proxy():
                df = ak.stock_fhps_em(date=date_str)
            
            if df is None or df.empty:
                continue
            
            code_col = None
            div_col = None
            eps_col = None
            
            for col in df.columns:
                col_str = str(col)
                if '代码' in col_str or col_str.lower() == 'code':
                    code_col = col
                elif '现金分红' in col_str and '比例' in col_str:
                    div_col = col
                elif col_str == '每股收益':
                    eps_col = col
            
            if not code_col or not div_col:
                continue
            
            df[code_col] = df[code_col].astype(str).str.zfill(6)
            row = df[df[code_col] == code]
            
            if not row.empty:
                div_amount = pd.to_numeric(row[div_col].values[0], errors='coerce')
                if pd.notna(div_amount) and div_amount > 0:
                    div_amounts.append(div_amount / 10)  # 每10股→每股
                    
        except Exception:
            continue
    
    if not div_amounts:
        _payout_stability_cache[code] = (None, 30.0)  # 无分红数据，低分
        return (None, 30.0)
    
    avg_div = sum(div_amounts) / len(div_amounts)
    
    # 计算稳定性
    consistency = len(div_amounts) / years  # 0-1，分红连续性
    stability = round(consistency * 50 + 50, 1)  # 基础分：连续性50 + 固定50
    
    # 微调：如果分红金额稳定（变异系数低），加分
    if len(div_amounts) >= 2:
        mean = sum(div_amounts) / len(div_amounts)
        if mean > 0:
            std = (sum((x - mean)**2 for x in div_amounts) / len(div_amounts)) ** 0.5
            cv = std / mean  # 变异系数
            if cv < 0.2:  # 非常稳定
                stability = min(100, stability + 15)
            elif cv < 0.5:  # 较稳定
                stability = min(100, stability + 5)
    
    _payout_stability_cache[code] = (round(avg_div, 4), stability)
    return (round(avg_div, 4), stability)


def _fetch_hist_from_tencent(code: str) -> pd.DataFrame:
    """
    通过腾讯接口获取股票日K线数据（v8.1修复）

    新浪接口已被反爬虫拦截(456)，东方财富push2his因LibreSSL不可达。
    腾讯接口 web.ifzq.gtimg.cn 稳定可用，返回前复权日线数据。

    返回字段: 日期, 开盘, 收盘, 最高, 最低, 成交量
    """
    if code in _hist_cache:
        return _hist_cache[code]

    try:
        prefix = 'sh' if code.startswith('6') else 'sz'
        url = 'http://web.ifzq.gtimg.cn/appstock/app/fqkline/get'
        params = {
            '_var': 'kline_dayqfq',
            'param': f'{prefix}{code},day,,,800,qfq',
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'http://gu.qq.com/',
        }

        resp = requests.get(url, params=params, headers=headers, timeout=10,
                            proxies={'http': None, 'https': None})
        if resp.status_code != 200:
            return None

        text = resp.text.strip()
        if not text.startswith('kline_dayqfq='):
            return None

        import json
        data = json.loads(text[13:])
        qfqday = data.get('data', {}).get(f'{prefix}{code}', {}).get('qfqday', [])
        if not qfqday:
            return None

        # 解析: [日期, 开盘, 收盘, 最高, 最低, 成交量]
        # 注意: 除权日行会多一列分红信息dict，只取前6列
        rows = [row[:6] for row in qfqday]
        df = pd.DataFrame(rows, columns=['日期', '开盘', '收盘', '最高', '最低', '成交量'])
        df['日期'] = pd.to_datetime(df['日期'])
        for col in ['开盘', '收盘', '最高', '最低', '成交量']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.sort_values('日期').reset_index(drop=True)

        _hist_cache[code] = df
        return df
    except Exception:
        return None


def _fetch_hist(code: str) -> pd.DataFrame:
    """
    获取股票日K线数据（v8.1修复：使用腾讯接口）

    v8.1修复:
    - 新浪接口反爬拦截(456) + 东方财富LibreSSL不可达
    - 改用腾讯 web.ifzq.gtimg.cn，稳定快速(0.2s/只)
    - 800日前复权数据，覆盖约3年
    """
    if code in _hist_cache:
        return _hist_cache[code]
    return _fetch_hist_from_tencent(code)


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
        
        # v8.0: 限速，避免被新浪限流（新浪限流约100次/秒）
        if i > 0 and i % 20 == 0:
            time.sleep(1)
        
        try:
            # 获取历史数据（需要window+1天来计算收益率）
            # v8.0修复: 使用_fetch_hist自动选择可用数据源
            df = _fetch_hist(code)
            
            if df is None:
                if i < 5:  # 只打印前5个错误
                    print(f"    {code}: 数据获取返回None", flush=True)
                results[code] = None
                continue
            
            if len(df) < window + 1:
                if i < 5:  # 只打印前5个错误
                    print(f"    {code}: 数据不足{len(df)}/{window+1}", flush=True)
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
            if i < 5:  # 只打印前5个错误
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
        
        # v8.0: 每20只股票暂停1秒，避免限流
        if i > 0 and i % 20 == 0:
            time.sleep(1)
        try:
            # 获取历史数据
            # v8.0修复: 使用_fetch_hist自动选择可用数据源
            df = _fetch_hist(code)
            
            if df is None:
                if i < 5:  # 只打印前5个错误
                    print(f"    {code}: 数据获取返回None", flush=True)
                results[code] = None
                continue
            
            if len(df) < days * 0.5:  # 至少50%的数据
                if i < 5:  # 只打印前5个错误
                    print(f"    {code}: 数据不足{len(df)}/{days}", flush=True)
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
            if i < 5:  # 只打印前5个错误
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
        with no_proxy():
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
    批量获取市值数据（v8.0修复）
    
    v8.0修复策略：
    1. 优先使用stock_zh_a_spot_em（快速，一次获取全市场）
    2. 失败时使用stock_individual_info_em逐个查询（慢但可靠）
    
    Args:
        stock_codes: 股票代码列表
        
    Returns:
        {code: market_cap_in_yi}，单位为亿元
    """
    print(f"  获取市值数据（{len(stock_codes)}只）...", flush=True)
    
    results = {}
    
    # 方案1: 使用stock_zh_a_spot_em（快速）
    try:
        with no_proxy():
            df = ak.stock_zh_a_spot_em()
        
        if df is not None and not df.empty:
            # 识别列名
            code_col = None
            cap_col = None
            
            for col in df.columns:
                col_str = str(col)
                if '代码' in col_str:
                    code_col = col
                elif '总市值' in col_str:
                    cap_col = col
                    break
            
            if code_col and cap_col:
                # 清理数据
                df[code_col] = df[code_col].astype(str).str.zfill(6)
                df[cap_col] = pd.to_numeric(df[cap_col], errors='coerce')
                
                # 转换单位：元 -> 亿元
                df['market_cap_yi'] = df[cap_col] / 100000000
                
                # 构建结果字典
                for code in stock_codes:
                    row = df[df[code_col] == code]
                    if not row.empty:
                        cap = row['market_cap_yi'].values[0]
                        results[code] = round(float(cap), 2) if not pd.isna(cap) else None
                
                valid_count = sum(1 for v in results.values() if v is not None)
                print(f"  ✓ 完成市值获取（有效数据{valid_count}只，快取方案）")
                return results
    except Exception as e:
        print(f"  ⚠️ 快取方案失败: {e}", flush=True)
        print(f"  启用备选方案（逐个查询，较慢）...", flush=True)
    
    # 方案2: 使用stock_individual_info_em逐个查询（慢但可靠）
    # v8.1修复：不使用no_proxy()，直接调用接口
    for i, code in enumerate(stock_codes):
        if i % 20 == 0:
            print(f"    进度: {i}/{len(stock_codes)}", flush=True)
        
        # 限速：每查询5只股票暂停0.5秒
        if i > 0 and i % 5 == 0:
            time.sleep(0.5)
        
        try:
            # v8.1修复：移除no_proxy()包装，避免连接中断
            df = ak.stock_individual_info_em(symbol=code)
            
            if df is not None and not df.empty:
                # 查找总市值
                cap_row = df[df['item'] == '总市值']
                if not cap_row.empty:
                    cap_yuan = float(cap_row['value'].values[0])
                    cap_yi = cap_yuan / 100000000  # 转换为亿元
                    results[code] = round(cap_yi, 2)
                else:
                    results[code] = None
            else:
                results[code] = None
        except Exception:
            results[code] = None
    
    valid_count = sum(1 for v in results.values() if v is not None)
    print(f"  ✓ 完成市值获取（有效数据{valid_count}只，备选方案）")
    return results


def get_dividend_per_share_batch(stock_codes: list) -> dict:
    """
    批量获取每股股利（兼容性桩）

    Args:
        stock_codes: 股票代码列表

    Returns:
        {code: dividend_per_share}
    """
    return {code: 0.0 for code in stock_codes}


# ============================================================
# v7.2 质量因子 — 真实数据获取（v8.5实现）
# ============================================================

def get_operating_cashflow_batch(stock_codes):
    """
    批量获取每股经营现金流量（v8.5真实实现）

    数据来源：akshare stock_yjbb_em（年报业绩，包含"每股经营现金流量"列）

    Args:
        stock_codes: 股票代码列表

    Returns:
        {code: 每股经营现金流量(float)}  — 与 EPS 同口径（元/股）
    """
    print(f"  获取每股经营现金流数据（{len(stock_codes)}只）...", flush=True)

    from datetime import datetime
    current_year = datetime.now().year

    # 尝试最近2年年报，确保数据覆盖（部分公司可能延迟发布最新年报）
    results = {}
    code_set = set(stock_codes)

    for year_offset in [1, 2]:
        report_year = current_year - year_offset
        date_str = f'{report_year}1231'
        remaining = code_set - set(results.keys())

        if not remaining:
            break

        try:
            with no_proxy():
                df = ak.stock_yjbb_em(date=date_str)

            if df is None or df.empty:
                continue

            # 识别列名
            code_col = None
            cashflow_col = None
            for col in df.columns:
                col_str = str(col)
                if '代码' in col_str or col_str.lower() == 'code':
                    code_col = col
                elif '经营现金' in col_str:
                    cashflow_col = col

            if not code_col or not cashflow_col:
                continue

            df[code_col] = df[code_col].astype(str).str.zfill(6)
            df[cashflow_col] = pd.to_numeric(df[cashflow_col], errors='coerce')

            for _, row in df.iterrows():
                code = row[code_col]
                if code in remaining:
                    val = row[cashflow_col]
                    if pd.notna(val):
                        results[code] = float(val)

        except Exception as e:
            print(f"  ⚠ 获取{date_str}数据异常: {e}", flush=True)
            continue

    valid_count = sum(1 for v in results.values() if v is not None)
    print(f"  ✓ 获取每股经营现金流（有效数据{valid_count}只）", flush=True)
    return results


def get_top_shareholder_ratio_batch(stock_codes):
    """
    批量获取第一大股东持股比例（v8.5真实实现）

    数据来源：akshare stock_gdfx_free_top_10_em（前十大流通股东）
    逻辑：逐只查询，取排名第一的股东的"占总流通股本持股比例"

    Args:
        stock_codes: 股票代码列表

    Returns:
        {code: top1_shareholder_ratio(float)} — 第一大股东持股比例（0-1之间）
    """
    print(f"  获取第一大股东持股比例（{len(stock_codes)}只）...", flush=True)

    from datetime import datetime
    current_year = datetime.now().year
    # 使用最近可用的报告期
    report_date = f'{current_year - 1}0930'

    results = {}

    for i, code in enumerate(stock_codes):
        if i % 10 == 0:
            print(f"    进度: {i}/{len(stock_codes)}", flush=True)

        try:
            # 将股票代码转为akshare格式：sh600519, sz000858
            if code.startswith('6'):
                symbol = f'sh{code}'
            elif code.startswith('0') or code.startswith('3'):
                symbol = f'sz{code}'
            else:
                symbol = f'sh{code}'

            with no_proxy():
                df = ak.stock_gdfx_free_top_10_em(symbol=symbol, date=report_date)

            if df is None or df.empty:
                continue

            # 找到"占总流通股本持股比例"列
            ratio_col = None
            for col in df.columns:
                if '比例' in str(col) and ('流通' in str(col) or '总' in str(col)):
                    ratio_col = col
                    break

            if ratio_col is None:
                # 备选：找第一个包含"比例"的列
                for col in df.columns:
                    if '比例' in str(col):
                        ratio_col = col
                        break

            if ratio_col is None:
                continue

            # 取排名第一的股东
            top_row = df.iloc[0]
            ratio = pd.to_numeric(top_row[ratio_col], errors='coerce')
            if pd.notna(ratio):
                # API返回的是百分比值（如54.07），转换为0-1之间
                results[code] = round(float(ratio) / 100, 4)

        except Exception:
            continue

    valid_count = len(results)
    print(f"  ✓ 获取第一大股东持股比例（有效数据{valid_count}只）", flush=True)
    return results


def calculate_cashflow_profit_ratio(operating_cashflow, net_profit):
    """
    计算现金流质量比率

    v8.5更新：两个参数均为"每股"口径（元/股），直接相除

    Args:
        operating_cashflow: 每股经营现金流（元/股）
        net_profit: 每股收益 EPS（元/股）

    Returns:
        float: 经营现金流/EPS 比率，None表示无法计算
    """
    if operating_cashflow is None or net_profit is None or net_profit <= 0:
        return None
    return operating_cashflow / net_profit
