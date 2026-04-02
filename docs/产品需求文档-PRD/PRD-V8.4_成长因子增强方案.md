# V8.4 成长因子增强方案

> 日期：2026-04-01
> 状态：已实施（V8.4.1 增强中）

## 一、问题诊断

当前系统的**三因子评分模型**本质上是纯防御型：

| 因子 | 当前逻辑 | 偏向 |
|------|----------|------|
| 股息率（50%） | 越高越好 | **过去**的回报 |
| 波动率（30%） | 越低越好 | **回避**风险 |
| 稳定性（20%） | 分红年数越长越好 | **过去**的惯性 |

**核心缺陷**：没有衡量"未来成长能力"的因子，选出来的全是银行、电力、高速公路、煤炭——典型的利率敏感型防御资产。

---

## 一、问题诊断（续）

**V8.4 问题**：成长因子仅作为排序加分项，不影响筛选结果。

| 问题 | 说明 |
|------|------|
| 负增长股票仍可能入选 | 只要股息高、波动低，负增长也能进入候选池 |
| 成长因子影响有限 | 只影响排序，不影响选股 |
| 筛选目标未达成 | "分红持续增长的优质公司"需要硬性筛选 |

### V8.4.1 增强方案

**新增筛选条件**：最低利润增长筛选

```
候选股票池 → A类筛选 → [利润增长筛选] → B类风控 → 四因子评分
```

**核心改进**：
- 过滤掉负增长股票（profit_growth_3y < MIN_PROFIT_GROWTH）
- 无数据股票默认放行（避免过度过滤）
- 与权重评分形成双重保障

## 二、解决方案

### 2.1 新增第四因子：成长因子

引入三个成长子指标，整合为"成长因子"：

| 子指标 | 数据来源 | 计算逻辑 | 权重 |
|--------|---------|---------|------|
| 净利润增长率 | akshare stock_yjbb_em | 近3年净利润CAGR | 40% |
| PEG | 计算 = PE / 净利润增速 | PEG < 1 为低估 | 30% |
| ROE趋势 | akshare stock_yjbb_em | 最新ROE vs 前年ROE变化 | 30% |

### 2.2 四因子评分模型

```
综合评分 = 股息率 × W1 + 波动率(反向) × W2 + 分红稳定性 × W3 + 成长因子 × W4
```

默认权重（均衡型）：
- W1（股息率）= 0.35
- W2（波动率）= 0.25
- W3（稳定性）= 0.15
- W4（成长）= 0.25

### 2.3 新增预设策略：成长红利型

```python
'growth_dividend': {
    'name': '成长红利',
    'description': '兼顾分红收益与成长性，捕捉"分红持续增长的优质公司"',
    'params': {
        'MIN_DIVIDEND_YIELD': '2.5',    # 降低股息门槛
        'MIN_MARKET_CAP': '300',        # 扩大范围
        'MIN_ROE': '10.0',              # 高盈利
        'MIN_DIVIDEND_YEARS': '3',      # 稳定分红
        'MAX_DEBT_RATIO': '70',
        'WEIGHT_DIVIDEND': '0.3',       # 降低分红权重
        'WEIGHT_VOL': '0.2',            # 降低波动权重
        'WEIGHT_STABILITY': '0.15',
        'WEIGHT_GROWTH': '0.35',        # 提高成长权重 ⭐
    }
}
```

## 三、技术设计

### 3.1 新增函数

```python
# fetcher.py
def fetch_profit_growth_data(stock_codes):
    """
    批量获取净利润增长数据
    - 查询近3年 stock_yjbb_em 数据
    - 计算净利润CAGR
    - 计算ROE趋势（最新ROE - 3年前ROE）
    - 计算 PEG = PE / 利润增速
    Returns: {code: {profit_growth_3y, roe_trend, peg}}
    """
```

### 3.2 评分模型修改

```python
# scorer.py - calculate_scores()
def calculate_scores(df, config=None):
    # ... 原有三因子计算 ...
    
    # 新增：成长因子计算
    WEIGHT_GROWTH = config.get_float('WEIGHT_GROWTH')
    
    for i in range(len(df)):
        # 成长子指标1：净利润增长率 (0-100)
        growth_score = normalize_growth(profit_growth_3y)
        
        # 成长子指标2：PEG (0-100)
        peg_score = normalize_peg(peg)
        
        # 成长子指标3：ROE趋势 (0-100)
        roe_trend_score = normalize_roe_trend(roe_trend)
        
        # 成长因子总分 = 子指标加权
        growth_factor = growth_score * 0.4 + peg_score * 0.3 + roe_trend_score * 0.3
    
    # 四因子综合评分
    df['composite_score'] = (
        df['div_norm'] * WEIGHT_DIVIDEND +
        df['vol_score'] * WEIGHT_VOL +
        df['stability_score'] / 100.0 * WEIGHT_STABILITY +
        df['growth_factor'] * WEIGHT_GROWTH
    ) * 100
```

### 3.3 成长因子评分算法

```python
def normalize_growth(profit_growth_3y):
    """
    净利润增长率评分 (0-100)
    - >= 15% → 100分（高成长）
    - >= 10% → 80分
    - >= 5%  → 60分
    - >= 0%  → 40分
    - < 0%   → 0分
    """

def normalize_peg(peg):
    """
    PEG评分 (0-100)
    - <= 0.5 → 100分（严重低估）
    - <= 0.8 → 80分（低估）
    - <= 1.0 → 60分（合理）
    - <= 1.5 → 30分（偏高）
    - > 1.5 或 None → 0分
    """

def normalize_roe_trend(roe_trend):
    """
    ROE趋势评分 (0-100)
    - roe_trend > 2% → 100分（显著提升）
    - roe_trend > 0% → 70分（稳步提升）
    - roe_trend > -2% → 30分（基本持平）
    - roe_trend <= -2% → 0分（下滑）
    """
```

## 四、配置参数变更

### 4.1 新增参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| WEIGHT_GROWTH | float | 0.25 | 成长因子权重 |
| ENABLE_GROWTH_FACTOR | bool | true | 是否启用成长因子 |
| **MIN_PROFIT_GROWTH** ⭐ | float | **0** | 最低3年净利润CAGR（%），过滤负增长 |
| **ENABLE_PROFIT_GROWTH_FILTER** ⭐ | bool | **True** | 是否启用利润增长筛选 |

### 4.2 权重体系变更

**旧权重（三因子）**：股息率50% + 波动率30% + 稳定性20% = 100%

**新权重（四因子）**：股息率35% + 波动率25% + 稳定性15% + 成长25% = 100%

### 4.3 预设策略调整

所有已有策略需更新权重，增加 WEIGHT_GROWTH 和 MIN_PROFIT_GROWTH 参数：

| 策略 | WEIGHT_GROWTH | MIN_PROFIT_GROWTH |
|------|---------------|-------------------|
| 保守型 | 0.05 | 5 |
| 均衡型 | 0.25 | 3 |
| 激进型 | 0.30 | 0 |
| 高股息 | 0.05 | 0 |
| 低估型 | 0.25 | 3 |
| **成长红利** ⭐ | **0.35** | **5** |

## 五、数据库变更

```sql
ALTER TABLE stock_data ADD COLUMN profit_growth_3y REAL;   -- 近3年净利润CAGR (%)
ALTER TABLE stock_data ADD COLUMN peg REAL;                 -- PEG比率
ALTER TABLE stock_data ADD COLUMN roe_trend REAL;           -- ROE趋势变化 (%)
ALTER TABLE stock_data ADD COLUMN growth_factor REAL;       -- 成长因子综合得分 (0-100)
```

## 六、界面变更

### 6.1 主页 (index.html)

- 评分模型说明更新为"四因子评分模型"
- 表格新增列：`PEG`、`利润增速(%)`、`成长得分`
- 版本号更新为 v8.4

### 6.2 配置页 (config.html)

- C类权重新增 `WEIGHT_GROWTH` 参数
- 权重和校验改为四因子之和 = 1.0
- 预设策略新增"成长红利"

## 七、验收标准

1. 成长因子数据获取成功率 > 80%
2. PEG 计算正确（PE / 利润增速）
3. 四因子权重和 = 1.0
4. "成长红利"策略可选且权重合理
5. 表格新增列正确显示
6. 所有已有测试通过

---

## 八、V8.4.1 成长因子筛选增强

### 8.1 筛选流程变更

```
V8.4 流程：
候选股票池 → A类筛选 → B类风控 → 四因子评分

V8.4.1 流程：⭐
候选股票池 → A类筛选 → [利润增长筛选] → B类风控 → 四因子评分
                                    ↑
                        profit_growth_3y >= MIN_PROFIT_GROWTH
```

### 8.2 筛选逻辑

```python
# routes.py - 筛选流程中增加
def apply_growth_filter(df, config):
    """
    应用利润增长筛选
    - profit_growth_3y >= MIN_PROFIT_GROWTH
    - 无数据(None)的股票默认放行
    """
    if not config.get_bool('ENABLE_PROFIT_GROWTH_FILTER'):
        return df
    
    min_growth = config.get_float('MIN_PROFIT_GROWTH', default=0)
    
    # 筛选：负增长过滤掉，正增长和无数据放行
    mask = (df['profit_growth_3y'].isna()) | (df['profit_growth_3y'] >= min_growth)
    filtered = df[mask].copy()
    
    return filtered
```

### 8.3 数据处理规则

| profit_growth_3y | 处理方式 | 原因 |
|------------------|----------|------|
| >= MIN_PROFIT_GROWTH | 放行 | 满足增长要求 |
| < MIN_PROFIT_GROWTH (且 >= 0) | 放行 | 正增长 |
| < 0 | **过滤** ⭐ | 负增长 |
| None (无数据) | 放行 | 避免过度过滤 |

### 8.4 预期效果

| 场景 | V8.4 | V8.4.1 |
|------|------|--------|
| 负增长高股息银行股 | 可能入选 | **过滤** |
| 稳定增长消费股 | 入选 | 入选 |
| 无增长数据股票 | 入选 | 入选（默认放行） |

### 8.5 验收标准

1. 负增长股票被正确过滤
2. 无数据股票默认放行
3. 各预设策略的 MIN_PROFIT_GROWTH 生效
4. 筛选流程无错误
5. 界面可配置最低增速阈值
