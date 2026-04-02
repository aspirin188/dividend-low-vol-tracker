# 红利低波跟踪系统 v7.0 产品需求文档

| 项目 | 信息 |
|------|------|
| 产品名称 | 红利低波跟踪系统 |
| 版本 | v7.0 |
| 文档类型 | 产品需求文档（极简版） |
| 编制日期 | 2026-03-29 |
| 设计原则 | 第一性原理 + 极简主义 |

---

## 一、版本概览

### 1.1 版本定位

v7.0是一次**质量因子增强**升级，在不新增数据接口的前提下，通过强化现有三因子模型，提升筛选质量。

### 1.2 核心改进

| 改进项 | v6.20 | v7.0 | 价值 |
|--------|-------|------|------|
| 支付率维度 | 单年硬过滤 | **3年平均评分** | 验证分红可持续性 |
| 波动率窗口 | 固定120日 | **可配置(120/252)** | 灵活适应不同策略 |
| 分红稳定性 | 单维度(年数) | **双维度(年数+支付率)** | 更全面的评估 |
| 数据接口 | - | **零新增** | 零成本升级 |

### 1.3 升级路径

```
v6.20 (三因子模型)
    ↓
v7.0 (质量因子增强)
    ├─ 支付率稳定性维度 ✅
    ├─ 波动率窗口配置化 ✅
    ├─ 历史分红数据函数 ✅
    └─ 股息率异常检测 ✅
```

---

## 二、需求详情

### 2.1 支付率稳定性维度

#### 2.1.1 需求背景

**问题**：
- 单年支付率可能被操纵（如临时提高分红率）
- 支付率>100%表示分红超过盈利，不可持续
- 无法验证"真金白银"的分红质量

**案例**：
```
某公司:
- 2022年: 支付率 150%（分红超盈利）
- 2023年: 支付率 80%（正常）
- 2024年: 支付率 120%（再次超盈利）

v6.20: 单年120% → 通过筛选（<150%）
v7.0: 3年平均116.7% → 低分警告
```

#### 2.1.2 解决方案

**数据获取**：
- 复用现有 `fetch_dividend_from_akshare()` 获取分红数据
- 复用现有 `stock_yjbb_em` 获取EPS数据
- 计算：`支付率 = 每股分红 / EPS × 100`

**评分逻辑**：
```python
def calculate_payout_stability_score(code: str) -> tuple:
    """
    计算支付率稳定性评分
    
    返回: (支付率3年均值, 稳定性评分)
    """
    # 获取近3年支付率
    payouts = []
    for year in [2024, 2023, 2022]:
        payout = get_payout_for_year(code, year)
        if payout:
            payouts.append(payout)
    
    if not payouts:
        return (None, 0)
    
    payout_3y_avg = sum(payouts) / len(payouts)
    
    # 评分分级
    if payout_3y_avg <= 80:
        score = 100  # 理想区间
    elif payout_3y_avg <= 100:
        score = 80   # 合理区间
    elif payout_3y_avg <= 150:
        score = 50   # 警告区间
    else:
        score = 0    # 危险区间
    
    return (payout_3y_avg, score)
```

#### 2.1.3 集成方式

**稳定性评分公式调整**：
```
v6.20:
stability_score = 分红年数分

v7.0:
stability_score = 分红年数分 × 0.6 + 支付率稳定性分 × 0.4
```

### 2.2 波动率窗口配置化

#### 2.2.1 需求背景

**问题**：
- 120日约6个月，部分用户认为窗口偏短
- 252日约1年，更稳定但响应慢
- 不同投资风格需要不同参数

#### 2.2.2 解决方案

**新增配置参数**：
```python
# config_service.py
VOL_WINDOW = 120  # 默认120日，可选252日
```

**配置界面**：
```
┌─────────────────────────────────────────────────────────────────┐
│  🛡️ 风控参数 (B类)                                               │
│                                                                 │
│  波动率窗口      [ 120 ] 日    范围: 120-252, 建议: 120或252    │
│  └ 计算波动率的交易日窗口。120日≈6个月, 252日≈1年               │
└─────────────────────────────────────────────────────────────────┘
```

**计算逻辑**：
```python
def calculate_volatility(code: str, days: int = None) -> float:
    """
    计算年化波动率
    
    Args:
        code: 股票代码
        days: 窗口天数，默认从配置读取
    
    Returns:
        年化波动率（百分比）
    """
    if days is None:
        days = config_service.get('VOL_WINDOW', 120)
    
    # 获取历史数据
    df = akshare.stock_zh_a_hist(symbol=code, period='daily', 
                                   adjust='qfq')
    
    # 取最近N天
    df = df.tail(days)
    
    # 计算对数收益率
    df['log_return'] = np.log(df['收盘'] / df['收盘'].shift(1))
    
    # 年化波动率
    vol = df['log_return'].std() * np.sqrt(242) * 100
    
    return vol
```

### 2.3 历史分红数据函数

#### 2.3.1 需求背景

需要获取历史分红数据用于：
- 计算3年平均股息率
- 计算3年平均支付率
- 验证分红稳定性

#### 2.3.2 解决方案

**新增函数**：

```python
# fetcher.py

def get_dividend_history(code: str, years: int = 3) -> list:
    """
    获取近N年每年每股分红
    
    Args:
        code: 股票代码
        years: 年数，默认3年
    
    Returns:
        [{year: 2024, div_per_share: 0.5, ex_date: '2024-06-01'}, ...]
    """
    # 复用现有分红数据获取逻辑
    df = fetch_dividend_from_akshare(code)
    
    if df is None or df.empty:
        return []
    
    # 按年份分组，计算每年每股分红
    result = []
    for year in range(2024, 2024 - years, -1):
        year_data = df[df['除权除息日'].str.startswith(str(year))]
        if not year_data.empty:
            # 计算每股分红（现金）
            cash_div = year_data[year_data['分红金额(元/10股)'].notna()]['分红金额(元/10股)'].sum()
            div_per_share = cash_div / 10  # 转换为每股
            
            ex_date = year_data['除权除息日'].iloc[0]
            
            result.append({
                'year': year,
                'div_per_share': div_per_share,
                'ex_date': ex_date
            })
    
    return result


def get_payout_history(code: str, years: int = 3) -> list:
    """
    获取近N年每年支付率
    
    Args:
        code: 股票代码
        years: 年数，默认3年
    
    Returns:
        [{year: 2024, payout: 65.5, div_per_share: 0.5, eps: 0.77}, ...]
    """
    # 获取历史分红
    div_history = get_dividend_history(code, years)
    
    if not div_history:
        return []
    
    # 获取EPS数据（从业绩报表）
    eps_data = get_eps_history(code, years)
    
    result = []
    for div_item in div_history:
        year = div_item['year']
        div_per_share = div_item['div_per_share']
        
        # 查找对应年份的EPS
        eps_item = next((e for e in eps_data if e['year'] == year), None)
        
        if eps_item and eps_item['eps'] > 0:
            payout = (div_per_share / eps_item['eps']) * 100
        else:
            payout = None
        
        result.append({
            'year': year,
            'payout': payout,
            'div_per_share': div_per_share,
            'eps': eps_item['eps'] if eps_item else None
        })
    
    return result
```

### 2.4 股息率异常检测

#### 2.4.1 需求背景

**问题**：
- TTM股息率可能被一次性特别分红拉高
- 即使使用3年平均，仍可能偏高

**案例**：
```
某公司:
- 2022年: 股息率 5%
- 2023年: 股息率 5%
- 2024年: 股息率 50%（含特别分红）
- TTM: 50% ← 极端异常
- 3年平均: 20% ← 仍然偏高
```

#### 2.4.2 解决方案

**异常检测逻辑**：
```python
def detect_dividend_anomaly(code: str, div_ttm: float, div_3y_avg: float) -> dict:
    """
    检测股息率异常
    
    Returns:
        {
            'is_anomaly': True/False,
            'anomaly_type': '特别分红' / '高波动' / '正常',
            'suggestion': '降权' / '过滤' / '通过'
        }
    """
    if div_3y_avg is None or div_3y_avg == 0:
        return {'is_anomaly': False, 'anomaly_type': '数据不足', 'suggestion': '通过'}
    
    ratio = div_ttm / div_3y_avg
    
    if ratio > 3.0:
        return {
            'is_anomaly': True,
            'anomaly_type': '特别分红',
            'suggestion': '降权',
            'ratio': ratio
        }
    elif ratio > 2.0:
        return {
            'is_anomaly': True,
            'anomaly_type': '高波动',
            'suggestion': '关注',
            'ratio': ratio
        }
    else:
        return {
            'is_anomaly': False,
            'anomaly_type': '正常',
            'suggestion': '通过',
            'ratio': ratio
        }
```

**评分调整**：
```python
# 在scorer.py中
anomaly_result = detect_dividend_anomaly(code, div_ttm, div_3y_avg)

if anomaly_result['suggestion'] == '降权':
    div_score = div_score * 0.5  # 股息率评分减半
```

---

## 三、数据模型变更

### 3.1 数据库Schema

**无需变更**，复用现有字段：
- `div_yield`: 股息率
- `payout_ratio`: 支付率
- `dividend_years`: 分红年数
- `volatility`: 波动率

### 3.2 新增计算字段

| 字段 | 计算方式 | 用途 |
|------|---------|------|
| `payout_3y_avg` | 3年支付率平均 | 稳定性评分 |
| `div_anomaly` | 异常检测结果 | 风险提示 |

---

## 四、评分模型升级

### 4.1 权重调整

| 因子 | v6.20 | v7.0 | 说明 |
|------|-------|------|------|
| 股息率 | 50% | **50%** | 保持不变 |
| 波动率 | 30% | **25%** | 降低5% |
| 分红稳定性 | 20% | **25%** | 提升5% |

### 4.2 稳定性评分升级

```
v6.20:
stability_score = f(分红年数)

v7.0:
stability_score = f(分红年数) × 0.6 + f(支付率稳定性) × 0.4

其中:
f(支付率稳定性) = {
    100分: 30% ≤ payout_3y_avg ≤ 80%
    80分:  80% < payout_3y_avg ≤ 100%
    50分:  100% < payout_3y_avg ≤ 150%
    0分:   payout_3y_avg > 150%
}
```

### 4.3 综合评分公式

```python
composite_score = (
    div_score × 0.50 +           # 股息率评分
    vol_score × 0.25 +           # 波动率评分
    stability_score × 0.25       # 稳定性评分（增强版）
) × 100
```

---

## 五、配置系统升级

### 5.1 新增配置项

| 参数名 | 类型 | 默认值 | 范围 | 分类 |
|--------|------|--------|------|------|
| `VOL_WINDOW` | int | 120 | 120-252 | B类风控参数 |

### 5.2 配置界面更新

在风控参数区域新增：
```
波动率窗口      [ 120 ] 日
范围: 120-252
说明: 计算波动率的交易日窗口。120日≈6个月, 252日≈1年
```

---

## 六、技术实现清单

### 6.1 文件变更

| 文件 | 变更类型 | 变更内容 |
|------|---------|---------|
| `server/services/fetcher.py` | 修改 | 新增 `get_dividend_history()`, `get_payout_history()` |
| `server/services/scorer.py` | 修改 | 稳定性评分增强，波动率配置化 |
| `server/services/config_service.py` | 修改 | 新增 `VOL_WINDOW` 配置项 |
| `server/templates/config.html` | 修改 | 新增波动率窗口输入框 |
| `server/templates/index.html` | 修改 | 显示支付率3年均值和异常提示 |

### 6.2 实施步骤

| 步骤 | 内容 | 工时 |
|------|------|------|
| 1 | 新增 `get_dividend_history()` | 2h |
| 2 | 新增 `get_payout_history()` | 1.5h |
| 3 | 修改稳定性评分逻辑 | 2h |
| 4 | 波动率窗口配置化 | 1h |
| 5 | 股息率异常检测 | 1.5h |
| 6 | 配置界面调整 | 1h |
| 7 | 前端显示优化 | 1h |
| 8 | 整体测试（3轮） | 3h |

**总工时：约13小时**

---

## 七、测试计划

### 7.1 单元测试

- [ ] `get_dividend_history()` 函数测试
- [ ] `get_payout_history()` 函数测试
- [ ] 稳定性评分计算测试
- [ ] 异常检测逻辑测试

### 7.2 集成测试

- [ ] 端到端数据流测试
- [ ] 配置生效测试
- [ ] 界面显示测试

### 7.3 回归测试

- [ ] 原有功能不受影响
- [ ] 数据完整性验证
- [ ] 性能测试（响应时间）

---

## 八、风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 历史数据不足3年 | 中 | 低 | 使用已有年份数据 |
| 计算性能下降 | 低 | 中 | 并发优化 |
| 配置参数误用 | 低 | 中 | 参数范围校验 |

---

## 九、发布计划

### 9.1 发布版本

- **v7.0**: 质量因子增强版

### 9.2 发布日期

- 2026-03-29

### 9.3 升级方式

- 向后兼容，无破坏性变更
- 配置自动迁移（VOL_WINDOW默认120）

---

## 十、后续规划

```
v7.0 (当前)
    ↓
v7.1 → 自由现金流收益率（可选）
        - 新增FCF数据接口
        - 进一步验证分红质量
        - 预计工时: +8h

v7.2 → 回测体系
        - 历史表现验证
        - 策略优化
```

---

**文档状态**: 已完成  
**编制日期**: 2026-03-29  
**版本**: v7.0
