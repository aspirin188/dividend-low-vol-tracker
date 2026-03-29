"""
两因子评分服务 — 红利低波跟踪系统

评分模型：
  综合评分 = 股息率归一化 × 60% + (1 - 波动率归一化) × 40%
  归一化方式：min-max，映射到 0-100 分

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
    
    # 排除 ST
    df = df[~df['name'].str.contains('ST', case=False, na=False)]

    # 确保关键字段为数值类型
    num_cols = ['dividend_yield_ttm', 'market_cap', 'annual_vol', 'basic_eps', 'dividend_years', 'roe', 'debt_ratio']
    df = df.copy()
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # 硬性条件筛选
    df = df[
        (df['dividend_yield_ttm'] >= MIN_DIVIDEND_YIELD) &
        (df['dividend_yield_ttm'] <= MAX_DIVIDEND_YIELD) &
        (df['market_cap'] >= MIN_MARKET_CAP) &
        (df['basic_eps'] > MIN_EPS) &
        (df['annual_vol'].notna()) &
        (df['dividend_yield_ttm'].notna()) &
        (df['market_cap'].notna()) &
        (df['basic_eps'].notna()) &
        (df['dividend_years'] >= MIN_DIVIDEND_YEARS) &
        (df['roe'].notna()) &
        (df['roe'] >= MIN_ROE)
    ].copy()

    # 股利支付率筛选（允许为空但不超过上限）
    df.loc[:, 'payout_ratio'] = pd.to_numeric(df['payout_ratio'], errors='coerce')
    df = df[
        (df['payout_ratio'].isna()) |
        (df['payout_ratio'] <= MAX_PAYOUT_RATIO)
    ].copy()

    # v6.12修改：资产负债率筛选暂时禁用
    # 原因：debt_ratio数据源问题，东方财富接口可能不支持该字段
    # TODO: 改用其他数据源获取负债率
    # 
    # # 先归并行业
    # industry_norms = df['industry'].fillna('').apply(normalize_industry)
    # 
    # def check_debt_ratio(idx):
    #     """检查资产负债率是否符合要求"""
    #     debt = df.loc[idx, 'debt_ratio']
    #     if pd.isna(debt):
    #         return False  # 数据缺失，过滤
    #     industry = industry_norms.loc[idx]
    #     if industry in FINANCE_INDUSTRIES:
    #         return debt <= MAX_DEBT_RATIO_FINANCE
    #     else:
    #         return debt <= MAX_DEBT_RATIO
    # 
    # df = df[df.index.map(check_debt_ratio)].copy()

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
    """
    if len(values) <= 1:
        return 0.5

    min_val = np.min(values)
    max_val = np.max(values)

    if min_val == max_val:
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
    三因子评分：股息率 X% + 波动率(取反) Y% + 分红稳定性 Z%。
    
    v7.0升级：稳定性评分增强（分红年数 + 支付率稳定性）
    v6.20改造：权重从配置服务读取
    v6.10升级：两因子 → 三因子
    - 股息率：min-max归一化
    - 波动率：min-max归一化后取反（越低越好）
    - 分红稳定性：直接映射（3年=60分, 4年=80分, 5年+=100分）
    """
    if df.empty:
        return df
    
    # v6.20: 从配置服务获取权重
    if config is None:
        config = ConfigService.get_instance()
    
    WEIGHT_DIVIDEND = config.get_float('WEIGHT_DIVIDEND')
    WEIGHT_VOL = config.get_float('WEIGHT_VOL')
    WEIGHT_STABILITY = config.get_float('WEIGHT_STABILITY')

    div_values = df['dividend_yield_ttm'].values
    vol_values = df['annual_vol'].values
    div_years_values = df['dividend_years'].values

    div_norms = []
    vol_norms = []
    stability_scores = []
    
    # v7.0新增：支付率稳定性评分
    from server.services.fetcher import calculate_payout_stability_score
    payout_stability_scores = []
    payout_3y_avgs = []

    for i in range(len(df)):
        # 股息率归一化
        d_norm = min_max_normalize(div_values, div_values[i])
        # 波动率归一化
        v_norm = min_max_normalize(vol_values, vol_values[i])
        
        # 分红稳定性评分（基础版：按年数）
        years = div_years_values[i]
        if years >= 5:
            years_score = 100.0
        elif years == 4:
            years_score = 80.0
        elif years == 3:
            years_score = 60.0
        else:
            years_score = 0.0
        
        # v7.0新增：支付率稳定性评分
        code = df.iloc[i]['code']
        payout_3y_avg, payout_stability = calculate_payout_stability_score(code)
        
        payout_3y_avgs.append(payout_3y_avg)
        payout_stability_scores.append(payout_stability)
        
        # v7.0: 稳定性总分 = 年数分 × 0.6 + 支付率稳定性分 × 0.4
        s_score = years_score * 0.6 + payout_stability * 0.4

        div_norms.append(d_norm)
        vol_norms.append(v_norm)
        stability_scores.append(s_score)

    df = df.copy()
    df['div_norm'] = div_norms
    df['vol_norm'] = vol_norms
    df['stability_score'] = stability_scores
    df['vol_score'] = [1.0 - v for v in vol_norms]  # 波动率越低越好
    
    # v7.0新增：保存支付率相关字段
    df['payout_3y_avg'] = payout_3y_avgs
    df['payout_stability_score'] = payout_stability_scores

    # 综合评分 0-100
    df['composite_score'] = (
        df['div_norm'] * WEIGHT_DIVIDEND +
        df['vol_score'] * WEIGHT_VOL +
        df['stability_score'] / 100.0 * WEIGHT_STABILITY
    ) * 100
    df['composite_score'] = df['composite_score'].round(2)

    # 按综合评分降序排名
    df = df.sort_values('composite_score', ascending=False).reset_index(drop=True)
    df['rank'] = range(1, len(df) + 1)

    return df


# ============================================================
# 结果处理
# ============================================================

def prepare_results(df: pd.DataFrame, data_date: str = None) -> pd.DataFrame:
    """
    整理最终结果，只保留需要入库的字段。

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
            'price_percentile', 'payout_3y_avg', 'data_date', 'updated_at'
        ])

    # 行业归并
    industries = df['industry'].fillna('').apply(normalize_industry)

    # 市场类型推断
    markets = df['code'].apply(infer_market)

    # 拼音首字母缩写
    pinyin_abbrs = df['name'].apply(get_pinyin_abbr)

    # 确保数值字段是数值类型（v6.12修复）
    for col in ['dividend_yield_ttm', 'annual_vol', 'market_cap', 'payout_ratio', 'basic_eps', 'price', 'pe', 'pb', 'roe', 'debt_ratio', 'price_percentile', 'payout_3y_avg']:
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
        'dividend_years': df['dividend_years'].astype(int),
        'roe': df['roe'].round(2),
        'debt_ratio': df['debt_ratio'].round(2),
        'price_percentile': df['price_percentile'].round(2),
        'payout_3y_avg': df['payout_3y_avg'].round(2) if 'payout_3y_avg' in df.columns else None,
        'data_date': data_date,
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    })

    return result
