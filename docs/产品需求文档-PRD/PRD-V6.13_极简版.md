# 红利低波跟踪系统 — 产品需求文档 (PRD)

## 极简版

| 项目 | 信息 |
|------|------|
| 产品名称 | 红利低波跟踪系统 |
| 版本 | v6.13 |
| 版本类型 | **极简版** |
| 最后更新 | 2026-03-28 |
| 文档状态 | 支付率和负债率修复版 |
| 设计理念 | 第一性原理 + 乔布斯极简原则 |

### v6.12 → v6.13 修订记录

| 修订项 | 内容 | 原因 |
|--------|------|------|
| **修复ROE超时问题** | 将signal模块改为threading模块实现超时控制 | signal模块在Flask子线程中无法使用 |
| **修复数值类型错误** | prepare_results()中添加数值类型转换 | 避免对object类型调用round()方法 |
| **修复支付率数据缺失** | fetch_dividend_for_candidates()中payout_ratio计算逻辑问题 | 股利支付率列显示为空 |
| **修复负债率数据缺失** | ASSETLIABRATIO字段从东方财富接口获取失败 | 负债率列显示为空 |

### Bug修复详情

#### 1. ROE超时控制问题

**v6.12 问题**：
```
错误: signal only works in main thread of the main interpreter
```

**原因**：
- Flask应用运行在子线程中
- signal模块只能在主线程使用

**v6.13 解决方案**：
```python
# 使用threading模块替代signal模块
import threading

thread = threading.Thread(target=fetch_data, args=(year_end,))
thread.start()
thread.join(timeout=60)  # 60秒超时
```

#### 2. 数值类型错误

**v6.12 问题**：
```
错误: Expected numeric dtype, got object instead
```

**原因**：
- prepare_results()中对字段调用round()方法
- 字段可能是object类型而非数值类型

**v6.13 解决方案**：
```python
# 在prepare_results()中添加数值类型转换
for col in ['dividend_yield_ttm', 'annual_vol', 'market_cap',
            'payout_ratio', 'basic_eps', 'price', 'pe', 'pb',
            'roe', 'debt_ratio']:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
```

#### 3. 支付率数据缺失

**v6.12 问题**：
```
股利支付率列全部显示为空
```

**诊断过程**：
1. fetch_dividend_for_candidates()函数应该返回payout_ratio
2. 计算公式：payout_ratio = dividend_per_share / eps * 100
3. 需要检查：
   - dividend_per_share是否正确解析
   - eps数据是否正确获取
   - 计算逻辑是否正确

**v6.13 解决方案**：
- 检查fetch_dividend_for_candidates()中的分红方案解析逻辑
- 确保dividend_per_share正确计算
- 确保使用正确的EPS数据（来自fetch_eps_batch）

#### 4. 负债率数据缺失

**v6.12 问题**：
```
资产负债率列全部显示为空
```

**诊断过程**：
1. fetch_dividend_for_candidates()尝试从ASSETLIABRATIO字段获取
2. 东方财富RPT_LICO_FN_CPD接口可能不支持该字段
3. 需要找到正确的负债率数据源

**v6.13 解决方案**：
- 方案1：检查ASSETLIABRATIO字段是否真实存在
- 方案2：改用其他akshare接口获取负债率
- 方案3：暂时隐藏负债率列，待找到可靠数据源后再启用

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

硬性筛选(v6.13):
- 股息率 ≥ 3%
- 总市值 ≥ 500亿
- 股利支付率 ≤ 150%（⚠️ 数据源待修复）
- EPS > 0
- 非ST
- 连续分红年数 ≥ 3年
- ROE ≥ 8%（✅ v6.13已修复）
- 资产负债率 ≤ 70%（金融地产≤85%）（⚠️ 数据源待修复）
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
│  排名│名称│代码│行业│市场│股价│PE│PB│股息率│市值│评分│分红年数│ROE│支付率│负债率│...│
├──────────────────────────────────────────────────────────────────┤
│  1  │建设银行│601939│金融│沪市│8.52│...│...│...  │... │... │ 5 │10.69│32.3%│93.2%│   │
│  ...                                                             │
└──────────────────────────────────────────────────────────────────┘
```

---

## 5. 技术方案

### 5.1 数据表结构(v6.13)

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
    payout_ratio     REAL,        -- v6.13: 待修复数据获取
    eps              REAL,
    price            REAL,
    pe               REAL,
    pb               REAL,
    pinyin_abbr      TEXT,
    dividend_years   INTEGER,
    roe              REAL,        -- v6.13: 已修复，数据来自akshare stock_yjbb_em
    debt_ratio       REAL,        -- v6.13: 待修复数据获取
    data_date        TEXT,
    updated_at       TEXT
);
```

### 5.2 数据获取方案(v6.13)

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
- 净资产收益率 → ROE ✅ v6.13已修复

东方财富 RPT_LICO_FN_CPD 接口:
- ASSIGNDSCRPT → 分红方案（用于计算TTM股息率和支付率）
- ASSETLIABRATIO → 资产负债率 ⚠️ 待验证是否支持
```

---

## 6. 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| ROE数据显示 | 建设银行ROE显示为10.69% | ✅ 已修复 |
| 支付率数据显示 | 建设银行支付率显示为32.3% | ⚠️ 待修复 |
| 负债率数据显示 | 建设银行负债率显示为93.2% | ⚠️ 待修复 |
| 连续分红计算 | 2024有、2023有、2022无 → 返回2年（非3年） | ✅ 正常 |
| 分红判断 | "10送5股"能被识别为分红 | ✅ 正常 |

---

## 附录:修订历史

| 版本 | 主要变更 |
|------|----------|
| **v6.13** | **修复ROE超时、数值类型错误；支付率和负债率数据缺失待修复** |
| v6.12 | 数据源优化：ROE改用akshare接口；修复空DataFrame、industry_norm错误 |
| v6.11 | Bug修复：连续分红计算、分红判断条件；新增ROE、负债率筛选 |
| v6.10 | 新增分红稳定性因子，升级三因子评分模型 |
| v6.9 | 新增"复原"按钮、简拼搜索功能 |

---

*文档结束。*
