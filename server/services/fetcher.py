"""
数据获取服务 — 红利低波跟踪系统（v6.6 Bug修复版）

数据来源：
1. 东方财富 push2 接口（分页）：全A股实时行情（股价、PE、PB、总市值、行业）
2. akshare stock_yjbb_em：全A股年报 EPS（一次性5200条）
3. 东方财富数据中心：候选股的分红方案（查几十只）+ 自计算TTM股息率
4. akshare stock_zh_a_hist：120日历史K线（计算波动率）

v6.6 修复:
- 废弃 f115 字段（股息率TTM不准确）
- 改为从分红方案自计算TTM股息率
- 招商银行案例: f115返回6.62%(错误) → 自计算5.11%(正确)

数据流: 行情全量 → EPS全量 → 客户端初筛 → 候选股分红查+股息率计算 → 波动率计算
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

_A_STOCK_FS = 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23'
_EM_PUSH2_URL = 'https://push2.eastmoney.com/api/qt/clist/get'
_EM_DC_URL = 'https://datacenter-web.eastmoney.com/api/data/v1/get'
_HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
_TIMEOUT = 30

_VOL_WINDOW = 120
_VOL_ANNUALIZE = math.sqrt(242)


# ============================================================
# 1. 获取全A股实时行情（分页拉取）
# ============================================================

def fetch_all_quotes() -> pd.DataFrame:
    """
    从东方财富 push2 接口分页获取全 A 股实时数据。
    接口单次最多返回 100 条，需要分页。

    v6.6 修改: 不再获取 f115 字段(股息率TTM不准确),改为后续自计算

    返回 DataFrame：code, name, price, pe, pb, market_cap, industry
    """
    all_rows = []
    page = 1
    page_size = 100

    while True:
        params = {
            'pn': str(page),
            'pz': str(page_size),
            'po': '1',
            'np': '1',
            'fltt': '2',
            'invt': '2',
            'fid': 'f12',  # 按代码排序保证稳定分页
            'fs': _A_STOCK_FS,
            'fields': 'f2,f12,f14,f9,f23,f20,f100',  # v6.6: 移除f115
        }
        r = requests.get(_EM_PUSH2_URL, params=params, headers=_HEADERS, timeout=_TIMEOUT)
        r.raise_for_status()
        data = r.json()

        diff = data['data'].get('diff', [])
        if not diff:
            break

        for item in diff:
            code = item.get('f12', '')
            name = item.get('f14', '')

            # 股价 (f2)
            price = item.get('f2')
            if price is not None:
                try:
                    price = float(price)
                except (ValueError, TypeError):
                    price = None
            else:
                price = None

            # 市盈率 PE (f9)
            pe = item.get('f9')
            if pe is not None:
                try:
                    pe = float(pe)
                    pe = round(pe, 2)
                except (ValueError, TypeError):
                    pe = None
            else:
                pe = None

            # 市净率 PB (f23)
            pb = item.get('f23')
            if pb is not None:
                try:
                    pb = float(pb)
                    pb = round(pb, 2)
                except (ValueError, TypeError):
                    pb = None
            else:
                pb = None

            # 总市值 (f20)
            cap_raw = item.get('f20', 0) or 0
            try:
                cap_raw = float(cap_raw)
            except (ValueError, TypeError):
                cap_raw = 0
            cap_yi = round(cap_raw / 1e8, 2) if cap_raw > 0 else None

            industry = item.get('f100', '') or ''

            all_rows.append({
                'code': code,
                'name': name,
                'price': price,
                'pe': pe,
                'pb': pb,
                'market_cap': cap_yi,
                'industry': industry,
            })

        total = data['data'].get('total', 0)
        if page * page_size >= total:
            break
        page += 1
        # 无延时，push2 接口很快

    df = pd.DataFrame(all_rows)
    print(f"  行情分页: {page}页, 共 {len(df)} 只股票")
    return df


# ============================================================
# 2. 获取全A股年报 EPS（akshare 一次拉取）
# ============================================================

def fetch_eps_batch() -> pd.DataFrame:
    """
    用 akshare stock_yjbb_em 一次性获取全 A 股最新年报 EPS 和 ROE。
    约 5200 条数据，1-2 秒。

    v6.11新增: 同时获取ROE（净资产收益率）
    v6.12修复: 使用线程实现超时控制，确保ROE数据能正常获取

    返回 DataFrame：code, basic_eps, roe, report_year
    """
    import threading
    import time
    
    # 用于存储结果的全局变量
    result_container = {'data': None, 'error': None, 'year': None}
    
    def fetch_data(year_end):
        """在线程中获取数据"""
        try:
            df = ak.stock_yjbb_em(date=year_end)
            
            if df is None or df.empty:
                return
            
            # 检查列名是否包含ROE
            if '净资产收益率' not in df.columns:
                result_container['error'] = "未找到'净资产收益率'列"
                return

            # 只保留主板 A 股
            df = df[df['股票代码'].str.startswith(('0', '3', '6'))].copy()

            if df.empty:
                return

            result = pd.DataFrame({
                'code': df['股票代码'].values,
                'basic_eps': pd.to_numeric(df['每股收益'], errors='coerce').values,
                'roe': pd.to_numeric(df['净资产收益率'], errors='coerce').values,
                'report_year': int(year_end[:4]),
            })
            
            result_container['data'] = result
            result_container['year'] = year_end
            
        except Exception as e:
            result_container['error'] = str(e)
    
    # 尝试最近3个年报日期
    for year_end in ['20241231', '20231231', '20221231']:
        print(f"  正在获取 {year_end[:4]} 年报数据...", end=' ', flush=True)
        
        # 清空容器
        result_container = {'data': None, 'error': None, 'year': None}
        
        # 启动线程
        thread = threading.Thread(target=fetch_data, args=(year_end,))
        thread.start()
        
        # 等待最多60秒
        thread.join(timeout=60)
        
        # 检查线程是否完成
        if thread.is_alive():
            print("✗ 超时", flush=True)
            continue
        
        # 检查结果
        if result_container['error']:
            print(f"✗ {result_container['error']}", flush=True)
            continue
        
        if result_container['data'] is not None:
            result = result_container['data']
            roe_not_null = result['roe'].notna().sum()
            print(f"✓ 获取 {len(result)} 只股票, ROE非空 {roe_not_null}/{len(result)}", flush=True)
            return result
        
        print("未获取到数据", flush=True)
    
    print("  ✗ 所有日期都失败，返回空DataFrame", flush=True)
    return pd.DataFrame(columns=['code', 'basic_eps', 'roe', 'report_year'])


# ============================================================
# 3. 计算TTM股息率（v6.6 新增）
# ============================================================

def calculate_ttm_dividend_yield(code: str, current_price: float) -> float:
    """
    自计算TTM股息率（过去12个月的分红总额 ÷ 当前股价）。

    数据源：东方财富数据中心 RPT_LICO_FN_CPD 接口

    v6.6 新增：替代不准确的 f115 字段

    参数：
        code: 股票代码
        current_price: 当前股价

    返回：股息率（%），保留2位小数。如果无法计算返回 None。
    """
    if not current_price or current_price <= 0:
        return None

    try:
        # 计算时间范围：过去12个月
        now = datetime.now()
        one_year_ago = now - timedelta(days=365)

        # 查询分红方案
        params = {
            'reportName': 'RPT_LICO_FN_CPD',
            'columns': 'SECURITY_CODE,ASSIGNDSCRPT,REPORTDATE',
            'filter': f'(SECURITY_CODE="{code}")',
            'pageNumber': 1,
            'pageSize': 20,  # 最近20条足够
            'sortTypes': -1,
            'sortColumns': 'REPORTDATE',
            'source': 'WEB',
            'client': 'WEB',
        }

        r = requests.get(_EM_DC_URL, params=params, headers=_HEADERS, timeout=_TIMEOUT)
        r.raise_for_status()
        resp = r.json()

        if not resp.get('success') or not resp.get('result'):
            return None

        items = resp['result'].get('data', [])
        if not items:
            return None

        # 累加过去12个月的每股派息
        total_dividend = 0.0

        for item in items:
            report_date_str = item.get('REPORTDATE', '')[:10]
            if not report_date_str:
                continue

            try:
                report_date = datetime.strptime(report_date_str, '%Y-%m-%d')
            except ValueError:
                continue

            # 只计入过去12个月的分红
            if report_date < one_year_ago:
                continue

            # 解析分红方案
            desc = item.get('ASSIGNDSCRPT', '')
            per_share = _parse_dividend_per_share(desc)
            if per_share and per_share > 0:
                total_dividend += per_share

        # 计算股息率
        if total_dividend <= 0:
            return None

        dividend_yield = (total_dividend / current_price) * 100
        return round(dividend_yield, 2)

    except Exception as e:
        print(f"  股息率计算失败 {code}: {e}")
        return None


def calculate_ttm_dividend_batch(codes: list, prices: dict) -> dict:
    """
    批量计算TTM股息率。

    参数：
        codes: 股票代码列表
        prices: {code: price} 字典

    返回：{code: dividend_yield}
    """
    result = {}
    total = len(codes)

    for i, code in enumerate(codes):
        price = prices.get(code)
        div_yield = calculate_ttm_dividend_yield(code, price)
        if div_yield is not None:
            result[code] = div_yield

        if (i + 1) % 20 == 0:
            print(f"  股息率进度: {i + 1}/{total}")
            time.sleep(0.3)  # 防限流

    return result


# ============================================================
# 4. 获取候选股的分红方案（只查几十只）
# ============================================================

def fetch_dividend_from_akshare(year: str = '2024') -> pd.DataFrame:
    """
    从akshare获取分红数据（v6.14新增）。
    
    使用stock_fhps_em接口获取每股股利数据。
    该接口返回每10股派息金额，需要除以10得到每股股利。
    
    参数:
        year: 年份，如'2024'，对应日期为'{year}1231'
    
    返回 DataFrame：code, dividend_per_share
    """
    import threading
    
    result_container = {'data': None, 'error': None}
    
    def fetch_data():
        try:
            df = ak.stock_fhps_em(date=f"{year}1231")
            
            if df is None or df.empty:
                result_container['error'] = "未获取到数据"
                return
            
            # 筛选A股
            a_stock = df[df['代码'].str.startswith(('0', '3', '6'))].copy()
            
            if a_stock.empty:
                result_container['error'] = "无A股数据"
                return
            
            # 计算每股股利：现金分红比例 / 10
            # "现金分红-现金分红比例" 是每10股派息金额
            a_stock['每股股利'] = pd.to_numeric(a_stock['现金分红-现金分红比例'], errors='coerce') / 10
            
            result = pd.DataFrame({
                'code': a_stock['代码'].values,
                'dividend_per_share': a_stock['每股股利'].values,
            })
            
            result_container['data'] = result
            
        except Exception as e:
            result_container['error'] = str(e)
    
    # 启动线程（60秒超时）
    thread = threading.Thread(target=fetch_data)
    thread.start()
    thread.join(timeout=60)
    
    if thread.is_alive():
        print(f"  ✗ 分红数据获取超时", flush=True)
        return pd.DataFrame(columns=['code', 'dividend_per_share'])
    
    if result_container['error']:
        print(f"  ✗ 分红数据获取失败: {result_container['error']}", flush=True)
        return pd.DataFrame(columns=['code', 'dividend_per_share'])
    
    if result_container['data'] is not None:
        df = result_container['data']
        valid = df['dividend_per_share'].notna().sum()
        print(f"  ✓ 获取 {len(df)} 只股票的分红数据，有每股股利 {valid}/{len(df)}", flush=True)
        return df
    
    return pd.DataFrame(columns=['code', 'dividend_per_share'])


def fetch_dividend_for_candidates(codes: list) -> pd.DataFrame:
    """
    从东方财富数据中心获取候选股的最新年报分红方案及财务数据。
    按 REPORTDATE 降序拉取，拉6页即可覆盖所有最新年报。
    同一只股票取最新年报。

    v6.11新增：同时获取资产负债率

    返回 DataFrame：code, dividend_per_share, payout_ratio, debt_ratio
    """
    if not codes:
        return pd.DataFrame(columns=['code', 'dividend_per_share', 'payout_ratio', 'debt_ratio'])

    code_set = set(codes)
    stock_data = {}  # {code: item}

    for page in range(1, 8):  # 7页足够
        params = {
            'reportName': 'RPT_LICO_FN_CPD',
            'columns': 'SECURITY_CODE,SECURITY_NAME_ABBR,BASIC_EPS,ASSIGNDSCRPT,REPORTDATE,DATATYPE,ASSETLIABRATIO',
            'filter': '(DATEMMDD="年报")',
            'pageNumber': page,
            'pageSize': 5000,
            'sortTypes': -1,
            'sortColumns': 'REPORTDATE',
            'source': 'WEB',
            'client': 'WEB',
        }

        try:
            r = requests.get(_EM_DC_URL, params=params, headers=_HEADERS, timeout=_TIMEOUT)
            r.raise_for_status()
            resp = r.json()

            if not resp.get('success') or not resp.get('result'):
                break

            items = resp['result'].get('data', [])
            if not items:
                break

            for item in items:
                code = item.get('SECURITY_CODE', '')
                if code not in code_set or code in stock_data:
                    continue
                if not code.startswith(('0', '3', '6')):
                    continue
                stock_data[code] = item

            # 已收集完所有候选股，提前退出
            if len(stock_data) >= len(code_set):
                break

        except Exception as e:
            print(f"  分红数据获取失败 (page {page}): {e}")
            break

    results = []
    for code, item in stock_data.items():
        eps = item.get('BASIC_EPS')
        desc = item.get('ASSIGNDSCRPT') or ''
        dividend_per_share = _parse_dividend_per_share(desc)

        payout_ratio = None
        if dividend_per_share and eps and eps > 0:
            payout_ratio = round((dividend_per_share / eps) * 100, 2)

        # v6.12修改：移除ROE（东方财富接口不支持WEIGHTEDAVERAGEORE字段）
        # ROE数据在fetch_eps_batch()中通过akshare获取
        
        debt_ratio = item.get('ASSETLIABRATIO')
        if debt_ratio is not None:
            try:
                debt_ratio = round(float(debt_ratio), 2)
            except (ValueError, TypeError):
                debt_ratio = None

        results.append({
            'code': code,
            'dividend_per_share': dividend_per_share,
            'payout_ratio': payout_ratio,
            'debt_ratio': debt_ratio,
        })

    # v6.12修复：确保返回的 DataFrame 有正确的列（即使 results 为空）
    if not results:
        df = pd.DataFrame(columns=['code', 'dividend_per_share', 'payout_ratio', 'debt_ratio'])
    else:
        df = pd.DataFrame(results)
    
    print(f"  分红数据: {len(df)}/{len(code_set)} 只")
    return df


def _parse_dividend_per_share(desc: str) -> float:
    """
    从分红方案描述中解析每股派息金额。

    示例：
    - "10派3.62元(含税)" → 0.362
    - "10转24.80派75.00元(含税)" → 7.5
    - "不分配不转增" → None
    """
    if not desc:
        return None
    m = re.search(r'派([\d.]+)元', str(desc))
    if m:
        return float(m.group(1)) / 10.0
    return None


# ============================================================
# 4. 获取分红稳定性数据（v6.10 新增）
# ============================================================

def get_dividend_years(code: str) -> int:
    """
    获取股票连续分红年数（v6.11修复）。

    从最近一个有分红的年份开始，往前连续有分红的年份数。
    如果中间断开，则只计连续部分。

    v6.11修复：
    - 改为"连续"分红逻辑，而非累计年份数
    - 分红判断增加"送"字（股票分红）

    返回：连续分红年数（1-5），如果没有分红记录返回0。
    """
    try:
        now = datetime.now()
        five_years_ago = now - timedelta(days=5*365)

        # 查询分红方案
        params = {
            'reportName': 'RPT_LICO_FN_CPD',
            'columns': 'SECURITY_CODE,ASSIGNDSCRPT,REPORTDATE',
            'filter': f'(SECURITY_CODE="{code}")',
            'pageNumber': 1,
            'pageSize': 30,  # 5年足够
            'sortTypes': -1,
            'sortColumns': 'REPORTDATE',
            'source': 'WEB',
            'client': 'WEB',
        }

        r = requests.get(_EM_DC_URL, params=params, headers=_HEADERS, timeout=_TIMEOUT)
        r.raise_for_status()
        resp = r.json()

        if not resp.get('success') or not resp.get('result'):
            return 0

        items = resp['result'].get('data', [])
        if not items:
            return 0

        # 统计有分红的年份（v6.11: 增加"送"字判断）
        dividend_years = set()

        for item in items:
            report_date_str = item.get('REPORTDATE', '')[:10]
            if not report_date_str:
                continue

            try:
                report_date = datetime.strptime(report_date_str, '%Y-%m-%d')
            except ValueError:
                continue

            # 只统计过去5年
            if report_date < five_years_ago:
                continue

            # v6.11修复: 检查是否有分红（包含"派"或"送"字样）
            desc = item.get('ASSIGNDSCRPT', '')
            if desc and ('派' in str(desc) or '送' in str(desc)):
                dividend_years.add(report_date.year)

        if not dividend_years:
            return 0

        # v6.11修复: 计算连续分红年数
        # 从最近一年往前检查，遇到断开则停止
        sorted_years = sorted(dividend_years, reverse=True)
        current_year = now.year

        # 找到最近有分红的年份
        start_year = None
        for y in sorted_years:
            if y <= current_year:
                start_year = y
                break

        if start_year is None:
            return 0

        # 从start_year往前数连续年份数
        consecutive_count = 0
        expected_year = start_year

        for y in sorted_years:
            if y == expected_year:
                consecutive_count += 1
                expected_year -= 1
            else:
                # 断开了，停止计数
                break

        return consecutive_count

    except Exception as e:
        print(f"  分红年数获取失败 {code}: {e}")
        return 0


def get_dividend_years_batch(codes: list) -> dict:
    """
    批量获取股票连续分红年数。

    返回：{code: dividend_years}
    """
    result = {}
    total = len(codes)

    for i, code in enumerate(codes):
        years = get_dividend_years(code)
        result[code] = years

        if (i + 1) % 20 == 0:
            print(f"  分红年数进度: {i + 1}/{total}")
            time.sleep(0.3)  # 防限流

    return result


# ============================================================
# 5. 计算波动率（120日对数收益率年化）
# ============================================================

def calculate_volatility(code: str, end_date: str = None) -> float:
    """计算单只股票的年化波动率（%）。"""
    try:
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')

        start_dt = datetime.now() - timedelta(days=400)
        start_date = start_dt.strftime('%Y%m%d')

        df = ak.stock_zh_a_hist(
            symbol=code,
            period='daily',
            start_date=start_date,
            end_date=end_date,
            adjust='qfq',
        )

        if df is None or len(df) < _VOL_WINDOW:
            return None

        close = df['收盘'].tail(_VOL_WINDOW).values
        log_returns = np.log(close[1:] / close[:-1])
        vol = np.std(log_returns, ddof=1) * _VOL_ANNUALIZE

        return round(vol * 100, 2)

    except Exception:
        return None


def calculate_volatility_batch(codes: list) -> dict:
    """批量计算波动率。返回 {code: annual_vol}。"""
    result = {}
    total = len(codes)

    for i, code in enumerate(codes):
        vol = calculate_volatility(code)
        if vol is not None:
            result[code] = vol

        if (i + 1) % 50 == 0:
            print(f"  波动率进度: {i + 1}/{total}")
        if (i + 1) % 20 == 0:
            time.sleep(0.5)  # 防限流

    return result


# ============================================================
# 5. 合并数据（优化流程）
# ============================================================

def merge_all_data() -> pd.DataFrame:
    """
    主流程：
    1. 分页拉全量行情（~55页）→ 股价、PE、PB、市值、行业
    2. 一次拉 EPS（~5200条）→ 基本每股收益
    3. 客户端初筛（市值>=500亿 & EPS>0 & 非ST）
    4. 对候选股自计算TTM股息率
    5. 二次筛选（股息率>=3%）
    6. 对候选股查分红方案 → 股利支付率
    7. 对候选股计算分红年数 → 分红稳定性（v6.10新增）
    8. 对候选股计算波动率 → 年化波动率
    """
    print("步骤1/8: 获取全A股实时行情...")
    quotes = fetch_all_quotes()
    print(f"  获取 {len(quotes)} 只股票")

    print("步骤2/8: 获取EPS...")
    eps_df = fetch_eps_batch()
    print(f"  获取 {len(eps_df)} 只股票的EPS")

    # 初步合并行情 + EPS
    merged = quotes.merge(eps_df, on='code', how='left')

    # 排除 ST
    merged = merged[~merged['name'].str.contains('ST', case=False, na=False)]

    # 第一次筛选：减少后续计算量
    for col in ['market_cap', 'basic_eps']:
        merged[col] = pd.to_numeric(merged[col], errors='coerce')

    pre_filtered = merged[
        (merged['market_cap'] >= 500.0) &
        (merged['basic_eps'] > 0) &
        (merged['market_cap'].notna()) &
        (merged['basic_eps'].notna()) &
        (merged['price'].notna()) &
        (merged['price'] > 0)
    ].copy()

    candidate_codes = pre_filtered['code'].tolist()
    print(f"步骤3/8: 初筛后 {len(candidate_codes)} 只候选股（市值≥500亿、EPS>0、非ST）")

    # 自计算TTM股息率
    print("步骤4/8: 计算候选股TTM股息率（自计算,这需要几分钟）...")
    prices = dict(zip(pre_filtered['code'], pre_filtered['price']))
    div_yields = calculate_ttm_dividend_batch(candidate_codes, prices)
    print(f"  完成 {len(div_yields)} 只股票的股息率计算")

    # 合并股息率数据
    div_df = pd.DataFrame(list(div_yields.items()), columns=['code', 'dividend_yield_ttm'])
    merged = merged.merge(div_df, on='code', how='left')

    # 第二次筛选：股息率>=3%
    merged = merged[
        (merged['dividend_yield_ttm'].notna()) &
        (merged['dividend_yield_ttm'] >= 3.0)
    ].copy()

    candidate_codes = merged['code'].tolist()
    print(f"步骤5/8: 二次筛选后 {len(candidate_codes)} 只候选股（股息率≥3%）")

    print("步骤6/8: 获取分红数据（计算股利支付率）...")
    
    # v6.14修复：使用akshare的stock_fhps_em接口获取分红数据
    # 原因：东方财富RPT_LICO_FN_CPD接口返回空数据
    div_df = fetch_dividend_from_akshare('2024')
    merged = merged.merge(div_df, on='code', how='left')
    
    # 计算支付率：每股股利 / 每股收益 * 100
    print("  计算股利支付率...", flush=True)
    
    # 确保字段为数值类型
    for col in ['dividend_per_share', 'basic_eps']:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors='coerce')
    
    merged['payout_ratio'] = None
    mask = (merged['dividend_per_share'].notna()) & (merged['basic_eps'] > 0)
    merged.loc[mask, 'payout_ratio'] = (
        merged.loc[mask, 'dividend_per_share'] / merged.loc[mask, 'basic_eps'] * 100
    ).round(2)
    payout_count = merged['payout_ratio'].notna().sum()
    print(f"  ✓ 成功计算 {payout_count}/{len(merged)} 只股票的支付率", flush=True)
    
    # v6.14：负债率数据暂时不可用
    if 'debt_ratio' not in merged.columns:
        merged['debt_ratio'] = None
    print("  ⚠️  负债率数据源暂不可用", flush=True)

    # v6.10新增：获取分红年数
    print("步骤7/8: 获取候选股分红年数（计算分红稳定性）...")
    div_years = get_dividend_years_batch(candidate_codes)
    print(f"  完成 {len(div_years)} 只股票的分红年数计算")
    div_years_df = pd.DataFrame(list(div_years.items()), columns=['code', 'dividend_years'])
    merged = merged.merge(div_years_df, on='code', how='left')

    print("步骤8/8: 计算候选股波动率（这需要几分钟）...")
    vols = calculate_volatility_batch(candidate_codes)
    print(f"  完成 {len(vols)} 只股票的波动率计算")

    vol_df = pd.DataFrame(list(vols.items()), columns=['code', 'annual_vol'])
    merged = merged.merge(vol_df, on='code', how='left')

    return merged
