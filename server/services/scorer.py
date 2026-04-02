"""
四因子评分服务 — 红利低波跟踪系统

评分模型：
  综合评分 = 股息率归一化 × W1 + (1 - 波动率归一化) × W2 + 稳定性归一化 × W3 + 成长因子 × W4
  归一化方式：min-max，映射到 0-100 分

v8.4 重大升级：
  - 三因子 → 四因子：新增成长因子（净利润增长率、PEG、ROE趋势）
  - 成长红利预设策略
  - 新增 growth_factor 字段（0-100分）

v6.20 重大改造：
  - 参数化配置：所有硬编码参数改为从配置服务读取
  - 配置灵活化：用户可通过配置页面调整筛选条件

v6.9 新增：
  - 简拼搜索：计算股票名称拼音首字母缩写

v6.8 调整：
  - 股息率下限：4% → 3%
  - 市值下限：100亿 → 500亿

v6.5 新增：
  - 行业归并：申万一级 50+ 细分行业 → 16 个大类行业
  - 市场类型：从股票代码推断（沪市/深市/创业板/科创板）
"""

import pandas as pd
import numpy as np
from datetime import datetime
from pypinyin import lazy_pinyin

# v6.20: 导入配置服务
from server.services.config_service import ConfigService


# ============================================================
# v6.20: 参数化配置（从配置服务读取，废弃硬编码）
# ============================================================
# 以下常量已废弃，保留仅供参考
# MIN_DIVIDEND_YIELD = 3.0
# MIN_MARKET_CAP = 500.0
# ...

# 金融地产行业列表（用于资产负债率差异化筛选）
FINANCE_INDUSTRIES = {'金融', '地产基建'}


# ============================================================
# 行业归并映射表（v6.5 新增）
# ============================================================

# 申万一级细分行业 → 大类行业
INDUSTRY_MAPPING = {
    # 金融
    '银行Ⅱ': '金融', '证券Ⅱ': '金融', '保险Ⅱ': '金融', '多元金融': '金融',
    # 能源
    '煤炭开采': '能源', '电力': '能源', '燃气Ⅱ': '能源', '炼化及贸易': '能源',
    # 化工
    '化学制品': '化工', '化学原料': '化工', '化学纤维': '化工', '农化制品': '化工', '塑料': '化工', '橡胶': '化工',
    # 医药
    '化学制药': '医药', '中药Ⅱ': '医药', '生物制品': '医药', '医疗器械': '医药', '医药商业': '医药', '医疗服务': '医药',
    # 交运
    '航运港口': '交运', '铁路公路': '交运', '航空机场': '交运', '物流': '交运', '公共交通': '交运',
    # 科技
    '消费电子': '科技', '光学光电子': '科技', '计算机设备': '科技', '通信设备': '科技', '通信服务': '科技',
    '游戏Ⅱ': '科技', '软件开发': '科技', 'IT服务': '科技', '半导体': '科技', '元件': '科技', '电子化学品': '科技',
    # 制造
    '汽车零部件': '制造', '商用车': '制造', '乘用车': '制造', '通用设备': '制造', '专用设备': '制造',
    '工程机械': '制造', '自动化设备': '制造', '轨交设备Ⅱ': '制造', '电池': '制造', '电机': '制造', '仪器仪表': '制造',
    # 钢铁有色
    '工业金属': '钢铁有色', '普钢': '钢铁有色', '贵金属': '钢铁有色', '特钢': '钢铁有色', '金属新材料': '钢铁有色',
    # 地产基建
    '房地产开发': '地产基建', '基础建设': '地产基建', '环境治理': '地产基建', '专业工程': '地产基建',
    '装修装饰': '地产基建', '房屋建设': '地产基建', '工程咨询服务': '地产基建',
    # 食品饮料
    '白酒Ⅱ': '食品饮料', '饮料乳品': '食品饮料', '食品加工': '食品饮料', '调味发酵品Ⅱ': '食品饮料',
    '非白酒': '食品饮料', '休闲食品': '食品饮料',
    # 家电家居
    '小家电': '家电家居', '家居用品': '家电家居', '白色家电': '家电家居', '黑家电': '家电家居', '照明设备': '家电家居',
    # 商贸服务
    '出版': '商贸服务', '贸易Ⅱ': '商贸服务', '一般零售': '商贸服务', '专业连锁': '商贸服务', '商业物业经营': '商贸服务',
    # 农牧
    '养养殖业': '农牧', '种植业': '农牧', '农产品加工': '农牧', '饲料': '农牧', '渔业': '农牧',
    # 公用事业
    '环保': '公用事业', '水务': '公用事业', '供热': '公用事业',
    # 传媒
    '影视院线': '传媒', '数字媒体': '传媒', '营销传播': '传媒', '电视广播': '传媒',
    # 纺织服装
    '纺织制造': '纺织服装', '服装家纺': '纺织服装', '饰品': '纺织服装',
    # 建材
    '水泥': '建材', '玻璃玻纤': '建材', '装修建材': '建材',
    # 军工
    '航天装备': '军工', '航空装备': '军工', '地面兵装': '军工', '航海装备': '军工',
    # 其他
    '综合': '其他',
}

# 大类行业列表（用于筛选器排序）
INDUSTRY_CATEGORIES = [
    '金融', '能源', '化工', '医药', '交运', '科技', '制造',
    '钢铁有色', '地产基建', '食品饮料', '家电家居', '商贸服务',
    '农牧', '公用事业', '传媒', '纺织服装', '建材', '军工', '其他',
]


def normalize_industry(industry: str) -> str:
    """
    将申万一级细分行业归并到大类行业。
    未映射的行业归入"其他"。
    """
    if not industry:
        return '其他'
    # 直接匹配
    if industry in INDUSTRY_MAPPING:
        return INDUSTRY_MAPPING[industry]
    # 模糊匹配（处理可能的后缀变化）
    for key, value in INDUSTRY_MAPPING.items():
        if key in industry or industry in key:
            return value
    return '其他'


# ============================================================
# 市场类型推断（v6.5 新增）
# ============================================================

def infer_market(code: str) -> str:
    """
    从股票代码推断市场类型。

    规则：
    - 60 开头 → 沪市主板
    - 00 开头 → 深市主板
    - 30 开头 → 创业板
    - 68 开头 → 科创板
    """
    if not code or len(code) < 2:
        return '未知'
    prefix = code[:2]
    if prefix == '60':
        return '沪市'
    elif prefix == '00':
        return '深市'
    elif prefix == '30':
        return '创业板'
    elif prefix == '68':
        return '科创板'
    else:
        return '未知'


# ============================================================
# 拼音首字母计算（v6.9 新增）
# ============================================================

def get_pinyin_abbr(name: str) -> str:
    """
    获取股票名称的拼音首字母缩写。
    
    例如：
    - "建设银行" → "jsyh"
    - "中国银行" → "zgyh"
    - "招商银行" → "zsyh"
    """
    if not name:
        return ''
    try:
        # lazy_pinyin 返回每个字的拼音列表
        pinyin_list = lazy_pinyin(name)
        # 取每个拼音的首字母，拼接成缩写
        abbr = ''.join([p[0].lower() for p in pinyin_list if p])
        return abbr
    except Exception:
        return ''


def filter_stocks(df: pd.DataFrame, config: ConfigService = None) -> pd.DataFrame:
    """
    硬性筛选：股息率≥X%、市值≥Y亿、支付率≤Z%、EPS>0、非ST、连续分红≥N年、ROE≥M%、负债率≤P%。
    
    原则：宁可少，不可错。数据不全直接过滤。
    
    v6.20改造：所有参数从配置服务读取
    v6.11新增：ROE、资产负债率筛选
    """
    # v6.20: 从配置服务获取参数
    if config is None:
        config = ConfigService.get_instance()
    
    MIN_DIVIDEND_YIELD = config.get_float('MIN_DIVIDEND_YIELD')
    MAX_DIVIDEND_YIELD = config.get_float('MAX_DIVIDEND_YIELD')
    MIN_MARKET_CAP = config.get_float('MIN_MARKET_CAP')
    MAX_PAYOUT_RATIO = config.get_float('MAX_PAYOUT_RATIO')
    MIN_EPS = 0.0  # EPS固定为0
    MIN_DIVIDEND_YEARS = config.get_int('MIN_DIVIDEND_YEARS')
    MIN_ROE = config.get_float('MIN_ROE')
    MAX_DEBT_RATIO = config.get_float('MAX_DEBT_RATIO')
    MAX_DEBT_RATIO_FINANCE = config.get_float('MAX_DEBT_RATIO_FINANCE')
    
    # 确保关键字段为数值类型
    num_cols = ['dividend_yield_ttm', 'market_cap', 'annual_vol', 'basic_eps', 'dividend_years', 'roe', 'debt_ratio']
    df = df.copy()
    
    # 只处理存在的列
    existing_num_cols = [col for col in num_cols if col in df.columns]
    for col in existing_num_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # 硬性条件筛选 - 检查列是否存在
    conditions = []
    
    # 排除 ST
    if 'name' in df.columns:
        df = df[~df['name'].str.contains('ST', case=False, na=False)]
    
    # 基础条件
    if 'dividend_yield_ttm' in df.columns:
        conditions.append((df['dividend_yield_ttm'] >= MIN_DIVIDEND_YIELD) &
                         (df['dividend_yield_ttm'] <= MAX_DIVIDEND_YIELD) &
                         (df['dividend_yield_ttm'].notna()))
    
    if 'market_cap' in df.columns:
        conditions.append((df['market_cap'] >= MIN_MARKET_CAP) &
                         (df['market_cap'].notna()))
    
    if 'basic_eps' in df.columns:
        conditions.append((df['basic_eps'] > MIN_EPS) &
                         (df['basic_eps'].notna()))
    
    if 'annual_vol' in df.columns:
        conditions.append(df['annual_vol'].notna())
    
    if 'dividend_years' in df.columns:
        conditions.append(df['dividend_years'] >= MIN_DIVIDEND_YEARS)
    
    if 'roe' in df.columns:
        conditions.append((df['roe'].notna()) &
                         (df['roe'] >= MIN_ROE))
    
    # 应用所有条件
    if conditions:
        df = df[pd.Series(conditions[0])]
        for cond in conditions[1:]:
            df = df[cond]
        df = df.copy()

    # 股利支付率筛选（允许为空但不超过上限）
    if 'payout_ratio' in df.columns:
        df.loc[:, 'payout_ratio'] = pd.to_numeric(df['payout_ratio'], errors='coerce')
        df = df[
            (df['payout_ratio'].isna()) |
            (df['payout_ratio'] <= MAX_PAYOUT_RATIO)
        ].copy()

    # v7.1修复：恢复资产负债率筛选功能
    # 数据来源：financial_calculator.calculate_debt_ratio_batch()
    # 数据已在fetcher.py主流程中计算并合并
    # v7.1改进：允许数据缺失的股票通过筛选，但给出警告
    
    # 先归并行业
    industry_norms = df['industry'].fillna('').apply(normalize_industry)
    
    # v8.1修复：对行业为"其他"的股票，根据名称补充金融行业判断
    _FINANCE_KEYWORDS = {'银行', '保险', '证券', '信托', '租赁', '期货'}
    def _is_finance_by_name(idx):
        name = str(df.loc[idx, 'name']) if 'name' in df.columns and pd.notna(df.loc[idx, 'name']) else ''
        return any(kw in name for kw in _FINANCE_KEYWORDS)
    
    def check_debt_ratio(idx):
        """检查资产负债率是否符合要求"""
        debt = df.loc[idx, 'debt_ratio']
        if pd.isna(debt):
            return True
        industry = industry_norms.loc[idx]
        # v8.1修复：行业为"其他"时，通过名称识别金融股
        if industry == '其他' and _is_finance_by_name(idx):
            return debt <= MAX_DEBT_RATIO_FINANCE
        if industry in FINANCE_INDUSTRIES:
            return debt <= MAX_DEBT_RATIO_FINANCE
        else:
            return debt <= MAX_DEBT_RATIO
    
    df = df[df.index.map(check_debt_ratio)].copy()

    # v7.2新增：质量因子增强筛选

    # 1. 净利润增速筛选
    try:
        enable_growth_filter = config.get('ENABLE_PROFIT_GROWTH_FILTER') == 'True'
    except KeyError:
        enable_growth_filter = False

    if enable_growth_filter and 'profit_growth_3y' in df.columns:
        try:
            min_profit_growth = config.get_float('MIN_PROFIT_GROWTH') / 100  # 转换为小数
        except KeyError:
            min_profit_growth = 0.0  # 默认值

        def check_profit_growth(idx):
            """检查近3年净利润增速"""
            growth = df.loc[idx, 'profit_growth_3y']
            if pd.isna(growth):
                return True  # 数据缺失，允许通过
            return growth >= min_profit_growth
        
        df = df[df.index.map(check_profit_growth)].copy()

    # 2. 现金流质量筛选
    try:
        enable_cashflow_filter = config.get('ENABLE_CASHFLOW_QUALITY_FILTER') == 'True'
    except KeyError:
        enable_cashflow_filter = False

    if enable_cashflow_filter and 'cashflow_profit_ratio' in df.columns:
        try:
            min_cashflow_ratio = config.get_float('MIN_CASHFLOW_PROFIT_RATIO')
        except KeyError:
            min_cashflow_ratio = 0.5  # 默认值

        def check_cashflow_quality(idx):
            """检查现金流质量"""
            ratio = df.loc[idx, 'cashflow_profit_ratio']
            if pd.isna(ratio):
                return True  # 数据缺失，允许通过
            return ratio >= min_cashflow_ratio
        
        df = df[df.index.map(check_cashflow_quality)].copy()
    
    # 3. 股权结构稳定性筛选
    try:
        enable_shareholder_filter = config.get('ENABLE_SHAREHOLDER_STABILITY_FILTER') == 'True'
    except KeyError:
        enable_shareholder_filter = False

    if enable_shareholder_filter and 'top1_shareholder_ratio' in df.columns:
        try:
            min_shareholder_ratio = config.get_float('MIN_TOP1_SHAREHOLDER_RATIO')
        except KeyError:
            min_shareholder_ratio = 0.2  # 默认值
        
        def check_shareholder_stability(idx):
            """检查股权结构稳定性"""
            ratio = df.loc[idx, 'top1_shareholder_ratio']
            if pd.isna(ratio):
                return True  # 数据缺失，允许通过
            return ratio >= min_shareholder_ratio
        
        df = df[df.index.map(check_shareholder_stability)].copy()

    return df


# ============================================================
# Min-Max 归一化
# ============================================================

def min_max_normalize(values: np.ndarray, target: float) -> float:
    """
    Min-Max 归一化，将值映射到 [0, 1]。

    边界情况：
    - 空列表或单个元素：返回 0.5
    - 所有值相同：返回 0.5
    
    v8.0修复：增加数据类型检查，确保处理数值类型
    """
    # v8.0: 确保values是数值类型
    try:
        values = np.array(values, dtype=float)
        target = float(target)
    except (ValueError, TypeError) as e:
        # 转换失败，返回默认值
        return 0.5
    
    if len(values) <= 1:
        return 0.5

    # 移除NaN值
    values = values[~np.isnan(values)]
    if len(values) <= 1:
        return 0.5

    min_val = np.min(values)
    max_val = np.max(values)

    if min_val == max_val:
        return 0.5

    # 检查target是否在范围内
    if target < min_val or target > max_val:
        return 0.5
    
    return (target - min_val) / (max_val - min_val)


# ============================================================
# 综合评分（v6.10 三因子模型）
# ============================================================

# v6.20: 权重从配置服务读取，以下常量已废弃
# WEIGHT_DIVIDEND = 0.5
# WEIGHT_VOL = 0.3
# WEIGHT_STABILITY = 0.2


def calculate_scores(df: pd.DataFrame, config: ConfigService = None) -> pd.DataFrame:
    """
    四因子评分：股息率 × W1 + 波动率(取反) × W2 + 分红稳定性 × W3 + 成长因子 × W4。
    
    v8.4升级：三因子→四因子，新增成长因子
    v7.0升级：稳定性评分增强（分红年数 + 支付率稳定性）
    v6.20改造：权重从配置服务读取
    v6.10升级：两因子 → 三因子
    """
    if df.empty:
        return df
    
    # v6.20: 从配置服务获取权重
    if config is None:
        config = ConfigService.get_instance()
    
    WEIGHT_DIVIDEND = config.get_float('WEIGHT_DIVIDEND')
    WEIGHT_VOL = config.get_float('WEIGHT_VOL')
    WEIGHT_STABILITY = config.get_float('WEIGHT_STABILITY')
    WEIGHT_GROWTH = config.get_float('WEIGHT_GROWTH')  # v8.4新增

    # v8.0修复: 强制转换关键字段为数值类型
    df = df.copy()
    numeric_cols = ['dividend_yield_ttm', 'annual_vol', 'dividend_years']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 过滤掉包含NaN的行
    df = df[df['dividend_yield_ttm'].notna() & df['annual_vol'].notna()].copy()
    
    if df.empty:
        return df

    div_values = df['dividend_yield_ttm'].values.astype(float)
    vol_values = df['annual_vol'].values.astype(float)
    div_years_values = df['dividend_years'].values.astype(float)

    div_norms = []
    vol_norms = []
    stability_scores = []
    growth_factors = []  # v8.4新增
    
    # v7.0新增：支付率稳定性评分
    from server.services.fetcher import calculate_payout_stability_score
    payout_stability_scores = []
    payout_3y_avgs = []

    for i in range(len(df)):
        # 股息率归一化
        d_norm = min_max_normalize(div_values, div_values[i])
        # 波动率归一化
        v_norm = min_max_normalize(vol_values, vol_values[i])
        
        # 分红稳定性评分
        years = div_years_values[i]
        if years >= 5:
            years_score = 100.0
        elif years == 4:
            years_score = 80.0
        elif years == 3:
            years_score = 60.0
        else:
            years_score = 0.0
        
        # 支付率稳定性
        code = df.iloc[i]['code']
        payout_3y_avg, payout_stability = calculate_payout_stability_score(code)
        
        payout_3y_avgs.append(payout_3y_avg)
        payout_stability_scores.append(payout_stability)
        
        s_score = years_score * 0.6 + payout_stability * 0.4

        div_norms.append(d_norm)
        vol_norms.append(v_norm)
        stability_scores.append(s_score)
        
        # v8.4新增：成长因子计算
        growth_factor = _calculate_growth_factor(
            df.iloc[i].get('profit_growth_3y'),
            df.iloc[i].get('pe'),
            df.iloc[i].get('roe_trend'),
        )
        growth_factors.append(growth_factor)

    df = df.copy()
    df['div_norm'] = div_norms
    df['vol_norm'] = vol_norms
    df['stability_score'] = stability_scores
    df['vol_score'] = [1.0 - v for v in vol_norms]
    df['growth_factor'] = growth_factors  # v8.4新增
    
    # v7.0新增
    df['payout_3y_avg'] = payout_3y_avgs
    df['payout_stability_score'] = payout_stability_scores

    # 四因子综合评分 0-100
    df['composite_score'] = (
        df['div_norm'] * WEIGHT_DIVIDEND +
        df['vol_score'] * WEIGHT_VOL +
        df['stability_score'] / 100.0 * WEIGHT_STABILITY +
        df['growth_factor'] / 100.0 * WEIGHT_GROWTH
    ) * 100
    df['composite_score'] = df['composite_score'].round(2)

    # 按综合评分降序排名
    df = df.sort_values('composite_score', ascending=False).reset_index(drop=True)
    df['rank'] = range(1, len(df) + 1)

    return df


def _calculate_growth_factor(profit_growth_3y, pe, roe_trend):
    """
    计算成长因子综合得分（v8.4新增）
    
    三个子指标加权：
    - 净利润增长率评分 (40%)
    - PEG评分 (30%)
    - ROE趋势评分 (30%)
    
    Args:
        profit_growth_3y: 近3年净利润CAGR（%），如 8.5
        pe: 市盈率
        roe_trend: ROE趋势变化（百分点），如 2.5
    
    Returns:
        float: 成长因子得分 0-100
    """
    # 子指标1：净利润增长率评分
    if profit_growth_3y is not None and not pd.isna(profit_growth_3y):
        growth = float(profit_growth_3y)
        if growth >= 15:
            growth_score = 100
        elif growth >= 10:
            growth_score = 80
        elif growth >= 5:
            growth_score = 60
        elif growth >= 0:
            growth_score = 40
        else:
            growth_score = 0
    else:
        growth_score = 30  # 无数据给中等分
    
    # 子指标2：PEG评分
    if profit_growth_3y is not None and not pd.isna(profit_growth_3y) and pe is not None and not pd.isna(pe) and pe > 0 and profit_growth_3y > 0:
        peg = float(pe) / float(profit_growth_3y)
        if peg <= 0.5:
            peg_score = 100
        elif peg <= 0.8:
            peg_score = 80
        elif peg <= 1.0:
            peg_score = 60
        elif peg <= 1.5:
            peg_score = 30
        else:
            peg_score = 0
    else:
        peg_score = 30  # 无数据给中等分
    
    # 子指标3：ROE趋势评分
    if roe_trend is not None and not pd.isna(roe_trend):
        trend = float(roe_trend)
        if trend > 2:
            roe_trend_score = 100
        elif trend > 0:
            roe_trend_score = 70
        elif trend > -2:
            roe_trend_score = 30
        else:
            roe_trend_score = 0
    else:
        roe_trend_score = 30  # 无数据给中等分
    
    # 加权综合
    total = growth_score * 0.4 + peg_score * 0.3 + roe_trend_score * 0.3
    return round(total, 2)


# ============================================================
# 结果处理
# ============================================================

def prepare_results(df: pd.DataFrame, data_date: str = None) -> pd.DataFrame:
    """
    整理最终结果，只保留需要入库的字段。

    v7.2.1 更新：
    - 新增 ma250, price_vs_ma_pct, ma_slope, signal, signal_level, ma_score

    v7.2 更新：
    - 新增 profit_growth_3y, cashflow_profit_ratio, top1_shareholder_ratio
    - 新增 strike_zone_score, strike_zone_rating, strike_zone

    v7.0 更新：
    - 新增 payout_3y_avg 字段（支付率3年均值）

    v6.19 更新：
    - 新增 price_percentile 字段（股价历史百分位）

    v6.11 更新：
    - 新增 roe、debt_ratio 字段

    v6.10 更新：
    - 新增 dividend_years 字段（连续分红年数）

    v6.9 更新：
    - 新增 pinyin_abbr 字段（股票名称拼音首字母缩写）

    v6.5 更新：
    - industry 字段归并到大类行业
    - 新增 market 字段（从代码推断市场类型）
    """
    if data_date is None:
        data_date = datetime.now().strftime('%Y-%m-%d')

    if df.empty:
        return pd.DataFrame(columns=[
            'code', 'name', 'industry', 'market', 'dividend_yield', 'annual_vol',
            'composite_score', 'rank', 'market_cap', 'payout_ratio', 'eps',
            'price', 'pe', 'pb', 'pinyin_abbr', 'dividend_years', 'roe', 'debt_ratio',
            'price_percentile', 'payout_3y_avg', 'data_date', 'updated_at',
            'profit_growth_3y', 'cashflow_profit_ratio', 'top1_shareholder_ratio',
            'strike_zone_score', 'strike_zone_rating', 'strike_zone',
            'ma250', 'price_vs_ma_pct', 'ma_slope', 'signal', 'signal_level', 'ma_score',
            'growth_factor', 'peg', 'roe_trend',  # v8.4新增
        ])

    # 行业归并
    industries = df['industry'].fillna('').apply(normalize_industry)

    # 市场类型推断
    markets = df['code'].apply(infer_market)

    # 拼音首字母缩写
    pinyin_abbrs = df['name'].apply(get_pinyin_abbr)

    # 确保数值字段是数值类型（v6.12修复，v8.0增强）
    numeric_cols = [
        'dividend_yield_ttm', 'annual_vol', 'market_cap', 'payout_ratio', 
        'basic_eps', 'price', 'pe', 'pb', 'roe', 'debt_ratio', 
        'price_percentile', 'payout_3y_avg', 'profit_growth_3y', 
        'cashflow_profit_ratio', 'top1_shareholder_ratio', 
        'strike_zone_score', 'ma250', 'ma20', 'ma60', 'current_price',
        'price_vs_ma_pct', 'ma_slope', 'signal_level', 'ma_score',
        'trend_strength', 'growth_factor', 'peg', 'roe_trend',  # v8.4新增
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    result = pd.DataFrame({
        'code': df['code'],
        'name': df['name'],
        'industry': industries,
        'market': markets,
        'dividend_yield': df['dividend_yield_ttm'].round(2),
        'annual_vol': df['annual_vol'].round(2),
        'composite_score': df['composite_score'],
        'rank': df['rank'],
        'market_cap': df['market_cap'].round(2),
        'payout_ratio': df['payout_ratio'].round(2),
        'eps': df['basic_eps'].round(2),
        'price': df['price'].round(2),
        'pe': df['pe'].round(2),
        'pb': df['pb'].round(2),
        'pinyin_abbr': pinyin_abbrs,
        'dividend_years': df['dividend_years'].fillna(0).astype(int),
        'roe': df['roe'].round(2),
        'debt_ratio': df['debt_ratio'].round(2),
        'price_percentile': df['price_percentile'].round(2),
        'payout_3y_avg': df['payout_3y_avg'].round(2) if 'payout_3y_avg' in df.columns else None,
        # v7.2新增
        'profit_growth_3y': df['profit_growth_3y'].round(4) if 'profit_growth_3y' in df.columns else None,
        'cashflow_profit_ratio': df['cashflow_profit_ratio'].round(2) if 'cashflow_profit_ratio' in df.columns else None,
        'top1_shareholder_ratio': df['top1_shareholder_ratio'].round(4) if 'top1_shareholder_ratio' in df.columns else None,
        'strike_zone_score': df['strike_zone_score'] if 'strike_zone_score' in df.columns else None,
        'strike_zone_rating': df['strike_zone_rating'] if 'strike_zone_rating' in df.columns else None,
        'strike_zone': df['strike_zone'] if 'strike_zone' in df.columns else None,
        # v7.2.1新增，v7.3升级
        'ma250': df['ma250'].round(2) if 'ma250' in df.columns else None,
        'ma20': df['ma20'].round(2) if 'ma20' in df.columns else None,  # v7.3新增
        'ma60': df['ma60'].round(2) if 'ma60' in df.columns else None,  # v7.3新增
        'current_price': df['current_price'].round(2) if 'current_price' in df.columns else None,  # v7.3新增
        'price_vs_ma_pct': df['price_vs_ma_pct'].round(2) if 'price_vs_ma_pct' in df.columns else None,
        'ma_slope': df['ma_slope'].round(4) if 'ma_slope' in df.columns else None,
        'trend': df['trend'] if 'trend' in df.columns else None,  # v7.3新增
        'trend_strength': df['trend_strength'] if 'trend_strength' in df.columns else None,  # v7.3新增
        'signal': df['signal'] if 'signal' in df.columns else None,
        'signal_level': df['signal_level'].fillna(0).astype(int) if 'signal_level' in df.columns else None,
        'signal_type': df['signal_type'] if 'signal_type' in df.columns else None,  # v7.3新增
        'action': df['action'] if 'action' in df.columns else None,  # v7.3新增
        'ma_score': df['ma_score'] if 'ma_score' in df.columns else None,
        # v8.4新增：成长因子
        'growth_factor': df['growth_factor'].round(2) if 'growth_factor' in df.columns else None,
        'peg': df['peg'].round(2) if 'peg' in df.columns else None,
        'roe_trend': df['roe_trend'].round(2) if 'roe_trend' in df.columns else None,
        'data_date': data_date,
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    })

    return result


# ============================================================
# v7.2新增：击球区评分
# ============================================================

def calculate_strike_zone_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算击球区评分
    
    v7.2.1更新：集成均线位置得分
    
    评分模型（60分制）:
    - 价格百分位得分（0-20分）
    - 估值得分（0-20分）
    - 均线位置得分（0-20分）⭐ v7.2.1新增
    
    击球区评级:
    - 50-60分 → ⭐⭐⭐⭐⭐ 强击球区
    - 40-50分 → ⭐⭐⭐⭐ 弱击球区
    - 30-40分 → ⭐⭐⭐ 观察区
    - 20-30分 → ⭐⭐ 观望区
    - 0-20分 → ⭐ 高估区
    """
    if df.empty:
        return df
    
    # 初始化得分
    price_percentile_scores = []
    valuation_scores = []
    ma_scores = []  # v7.2.1新增
    total_scores = []
    ratings = []
    zones = []
    
    for idx, row in df.iterrows():
        # 1. 价格百分位得分（0-20分）
        price_percentile = row.get('price_percentile')
        if pd.isna(price_percentile):
            price_score = 0
        elif price_percentile < 20:
            price_score = 20
        elif price_percentile < 30:
            price_score = 15
        elif price_percentile < 40:
            price_score = 10
        else:
            price_score = 0
        
        # 2. 估值得分（0-20分）
        pe = row.get('pe')
        if pd.isna(pe) or pe <= 0:
            valuation_score = 0
        elif pe < 8:
            valuation_score = 20
        elif pe < 10:
            valuation_score = 15
        elif pe < 15:
            valuation_score = 10
        else:
            valuation_score = 0
        
        # 3. 均线位置得分（0-20分）⭐ v7.2.1新增
        signal_level = row.get('signal_level')
        if pd.isna(signal_level):
            ma_score = 0
        elif signal_level == 5:  # 强烈买入
            ma_score = 20
        elif signal_level == 4:  # 买入
            ma_score = 15
        elif signal_level == 3:  # 持有
            ma_score = 10
        elif signal_level == 2:  # 观望
            ma_score = 5
        else:
            ma_score = 0
        
        # 总分
        total_score = price_score + valuation_score + ma_score
        
        # 评级
        if total_score >= 50:
            rating = '⭐⭐⭐⭐⭐'
            zone = '强击球区'
        elif total_score >= 40:
            rating = '⭐⭐⭐⭐'
            zone = '弱击球区'
        elif total_score >= 30:
            rating = '⭐⭐⭐'
            zone = '观察区'
        elif total_score >= 20:
            rating = '⭐⭐'
            zone = '观望区'
        else:
            rating = '⭐'
            zone = '高估区'
        
        price_percentile_scores.append(price_score)
        valuation_scores.append(valuation_score)
        ma_scores.append(ma_score)
        total_scores.append(total_score)
        ratings.append(rating)
        zones.append(zone)
    
    # 添加新字段
    df['price_percentile_score'] = price_percentile_scores
    df['valuation_score'] = valuation_scores
    df['ma_score'] = ma_scores  # v7.2.1新增
    df['strike_zone_score'] = total_scores
    df['strike_zone_rating'] = ratings
    df['strike_zone'] = zones
    
    return df
