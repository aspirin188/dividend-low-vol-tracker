# 红利低波跟踪系统 — 产品需求文档 (PRD)

## 极简版

| 项目 | 信息 |
|------|------|
| 产品名称 | 红利低波跟踪系统 |
| 版本 | v6.12 |
| 版本类型 | **极简版** |
| 最后更新 | 2026-03-28 |
| 文档状态 | 数据源优化版 |
| 设计理念 | 第一性原理 + 乔布斯极简原则 |

### v6.11 → v6.12 修订记录

| 修订项 | 内容 | 原因 |
|--------|------|------|
| **ROE数据源变更** | 从akshare的stock_yjbb_em接口获取ROE（净资产收益率字段） | 东方财富RPT_LICO_FN_CPD接口不支持WEIGHTEDAVERAGEORE字段 |
| **修复ROE数据覆盖Bug** | 从fetch_dividend_for_candidates()移除ROE字段返回 | 避免覆盖fetch_eps_batch()获取的ROE数据 |
| **暂时禁用负债率筛选** | 注释掉debt_ratio筛选条件 | 负债率数据源待解决 |
| **修复空DataFrame错误** | fetch_dividend_for_candidates返回空DataFrame时显式指定列名 | 避免merge时缺少code列 |
| **修复industry_norm错误** | 改用临时变量而非添加列到DataFrame | 避免删除不存在的列 |

### Bug修复详情

#### 1. ROE数据源问题

**v6.11 问题**：
```
东方财富 RPT_LICO_FN_CPD 接口查询 WEIGHTEDAVERAGEORE 字段报错：
"返回字段不存在"
```

**原因**：
- 东方财富该接口不支持ROE字段
- 接口文档可能过时或字段已改名

**v6.12 解决方案**：
```python
# 改用 akshare 的 stock_yjbb_em 接口
# 该接口包含"净资产收益率"字段

def fetch_eps_batch() -> pd.DataFrame:
    """
    用 akshare stock_yjbb_em 一次性获取全 A 股最新年报 EPS 和 ROE。
    返回 DataFrame：code, basic_eps, roe, report_year
    """
    for year_end in ['20241231', '20231231', '20221231']:
        try:
            df = ak.stock_yjbb_em(date=year_end)
            df = df[df['股票代码'].str.startswith(('0', '3', '6'))].copy()
            result = pd.DataFrame({
                'code': df['股票代码'].values,
                'basic_eps': pd.to_numeric(df['每股收益'], errors='coerce').values,
                'roe': pd.to_numeric(df['净资产收益率'], errors='coerce').values,
                'report_year': int(year_end[:4]),
            })
            return result
        except Exception as e:
            continue
    return pd.DataFrame(columns=['code', 'basic_eps', 'roe', 'report_year'])
```

**数据源对比**：
| 字段 | 原接口 | 新接口 |
|------|--------|--------|
| EPS | 东方财富 RPT_LICO_FN_CPD (BASIC_EPS) | akshare stock_yjbb_em (每股收益) |
| ROE | ❌ 不支持 | akshare stock_yjbb_em (净资产收益率) |

#### 2. 空DataFrame错误

**v6.11 问题**：
```python
# fetch_dividend_for_candidates 返回空 DataFrame
return pd.DataFrame()  # 没有列名

# merge 时报错：'code' 列不存在
df.merge(dividend_df, on='code', how='left')
```

**v6.12 修复**：
```python
# 显式指定列名
return pd.DataFrame(columns=['code', 'dividend_per_share', 'payout_ratio', 'debt_ratio'])
```

#### 3. industry_norm删除错误

**v6.11 问题**：
```python
df['industry_norm'] = df['industry'].fillna('').apply(normalize_industry)
# ...
df.drop(columns=['industry_norm'])  # KeyError: "['industry_norm'] not found in axis"
```

**v6.12 修复**：
```python
# 改用临时变量
industry_norms = df['industry'].fillna('').apply(normalize_industry)
# 直接使用，不添加到DataFrame
```

### 待修复问题

#### 资产负债率数据缺失

**现象**：运行后负债率列全部显示为空

**可能原因**：
1. fetch_dividend_for_candidates 函数返回空数据
2. 东方财富接口的ASSETLIABRATIO字段可能同样不存在
3. 需要改用其他数据源

**下一步**：
- 调查负债率数据获取逻辑
- 如东方财富接口不支持，改用akshare其他接口

---

## 1. 产品哲学

```
问:用户真正想要的是什么?
答:找到值得研究的高股息好公司

设计理念:第一性原理 + 乔布斯极简原则
```

---

## 2. 核心功能

```
功能1:一键运行(获取数据)
功能2:查看标的列表(搜索、筛选、排序)
功能3:导出 Excel
```

---

## 3. 三因子评分模型（v6.10）

```
综合评分 = 股息率归一化 × 0.5 + (1 - 波动率归一化) × 0.3 + 分红稳定性归一化 × 0.2

数据口径:
- 股息率:TTM(近12个月,自计算)
- 波动率:120日对数收益率,年化 √242
- 分红稳定性:过去5年连续分红年数

硬性筛选(v6.12):
- 股息率 ≥ 3%
- 总市值 ≥ 500亿
- 股利支付率 ≤ 150%
- EPS > 0
- 非ST
- 连续分红年数 ≥ 3年（v6.11修复计算逻辑）
- ROE ≥ 8%（v6.12数据源变更：使用akshare）
- 资产负债率 ≤ 70%（金融地产≤85%）（v6.12待修复）
```

---

## 4. 单页面设计

```
┌──────────────────────────────────────────────────────────────────┐
│  🏠 红利低波跟踪系统                [复原] [运行] [导出]        │
├──────────────────────────────────────────────────────────────────┤
│  共 XX 只标的  |  数据日期:2026-03-28                           │
│  三因子评分模型：综合评分 = 股息率×50% + 波动率×30% + 稳定性×20%│
│                                                                 │
│  [搜索框] [行业] [市值] [股息率] [市场]                         │
│                                                                 │
├──────────────────────────────────────────────────────────────────┤
│  排名│名称│代码│行业│市场│股价│PE│PB│股息率│市值│评分│分红年数│ROE│负债率│...│
├──────────────────────────────────────────────────────────────────┤
│  1  │建设银行│601939│金融│沪市│8.52│...│...│...  │... │... │ 5 │12.5│92%│   │
│  ...                                                             │
└──────────────────────────────────────────────────────────────────┘
```

---

## 5. 技术方案

### 5.1 数据表结构(v6.12)

```sql
CREATE TABLE stock_data (
    code             TEXT PRIMARY KEY,
    name             TEXT,
    industry         TEXT,
    market           TEXT,
    dividend_yield   REAL,
    annual_vol       REAL,
    composite_score  REAL,
    rank             INTEGER,
    market_cap       REAL,
    payout_ratio     REAL,
    eps              REAL,
    price            REAL,
    pe               REAL,
    pb               REAL,
    pinyin_abbr      TEXT,
    dividend_years   INTEGER,
    roe              REAL,        -- v6.12: 数据源变更为akshare stock_yjbb_em
    debt_ratio       REAL,        -- v6.12: 待修复数据获取
    data_date        TEXT,
    updated_at       TEXT
);
```

### 5.2 数据获取方案(v6.12)

```python
# 实时行情
东方财富 push2 接口:
- f2: 股价
- f9: PE
- f23: PB
- f20: 总市值
- f100: 行业

# 财务数据
akshare stock_yjbb_em 接口:
- 每股收益 → EPS
- 净资产收益率 → ROE ✅ v6.12新增

东方财富 RPT_LICO_FN_CPD 接口:
- ASSIGNDSCRPT → 分红方案（用于计算TTM股息率）
- ASSETLIABRATIO → 资产负债率 ⚠️ 待验证是否支持
```

### 5.3 筛选条件配置

```python
# server/services/scorer.py

MIN_DIVIDEND_YIELD = 3.0      # 股息率 ≥ 3%
MIN_MARKET_CAP = 500.0        # 总市值 ≥ 500亿
MAX_PAYOUT_RATIO = 150.0      # 股利支付率 ≤ 150%
MIN_EPS = 0.0                 # EPS > 0
MIN_DIVIDEND_YEARS = 3        # 连续分红年数 ≥ 3年
MIN_ROE = 8.0                 # ROE ≥ 8%（v6.12数据源变更）
MAX_DEBT_RATIO = 70.0         # 资产负债率 ≤ 70%（待修复）
MAX_DEBT_RATIO_FINANCE = 85.0 # 金融地产资产负债率 ≤ 85%（待修复）
```

---

## 6. 验收标准

| 验收项 | 标准 |
|--------|------|
| 连续分红计算 | 2024有、2023有、2022无 → 返回2年（非3年） |
| 分红判断 | "10送5股"能被识别为分红 |
| ROE筛选 | 只保留ROE ≥ 8%的股票，数据来自akshare |
| 负债率筛选 | 一般行业 ≤ 70%，金融地产 ≤ 85%（待修复） |
| 数据完整性 | ROE、负债率数据缺失时跳过该股票 |

---

## 附录:修订历史

| 版本 | 主要变更 |
|------|----------|
| **v6.12** | **数据源优化：ROE改用akshare接口；修复空DataFrame、industry_norm错误** |
| v6.11 | Bug修复：连续分红计算、分红判断条件；新增ROE、负债率筛选 |
| v6.10 | 新增分红稳定性因子，升级三因子评分模型 |
| v6.9 | 新增"复原"按钮、简拼搜索功能 |
| v6.8 | 筛选条件调整:股息率下限3%,市值下限500亿 |
| v6.7 | 字段显示次序调整:股息率、市值前置,综合评分前置 |
| v6.6 | 股息率计算bug修复:废弃f115字段,改为自计算TTM股息率 |

---

*文档结束。*
