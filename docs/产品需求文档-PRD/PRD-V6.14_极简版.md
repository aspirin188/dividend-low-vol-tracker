# 红利低波跟踪系统 — 产品需求文档 (PRD)

## 极简版

| 项目 | 信息 |
|------|------|
| 产品名称 | 红利低波跟踪系统 |
| 版本 | v6.14 |
| 版本类型 | **极简版** |
| 最后更新 | 2026-03-28 |
| 文档状态 | 数据源修复版 |
| 设计理念 | 第一性原理 + 乔布斯极简原则 |

### v6.13 → v6.14 修订记录

| 修订项 | 内容 | 原因 |
|--------|------|------|
| **修复支付率数据源** | 改用akshare的stock_fhps_em接口获取每股股利数据 | 东方财富RPT_LICO_FN_CPD接口返回空数据 |
| **修复负债率数据源** | 改用akshare的stock_financial_analysis_indicator接口获取负债率 | 东方财富接口不支持ASSETLIABRATIO字段 |
| **优化数据获取流程** | 添加数据源回退机制，优先使用akshare接口 | 提高数据获取成功率 |

### Bug修复详情

#### 1. 支付率数据源问题

**v6.13 问题**：
```
分红数据获取: 0/40 只股票
支付率数据: 0/30 条有数据 (0%)
```

**原因**：
- 东方财富 `RPT_LICO_FN_CPD` 接口返回空数据
- 接口可能已变更或限制访问

**v6.14 解决方案**：
```python
# 使用akshare的stock_fhps_em接口获取分红数据
import akshare as ak

# 获取分红数据
df = ak.stock_fhps_em(date="20241231")
# 计算支付率
payout_ratio = dividend_per_share / basic_eps * 100
```

**数据来源**：
- 每股股利：akshare `stock_fhps_em` 接口（分红配送数据）
- 每股收益：已从 `stock_yjbb_em` 接口获取
- 支付率 = 每股股利 / 每股收益 * 100

#### 2. 负债率数据源问题

**v6.13 问题**：
```
错误: ASSETLIABRATIO返回字段不存在
负债率数据: 0/30 条有数据 (0%)
```

**原因**：
- 东方财富 `RPT_LICO_FN_CPD` 接口不支持 `ASSETLIABRATIO` 字段
- 需要寻找其他财务数据接口

**v6.14 解决方案**：
```python
# 使用akshare的财务分析指标接口获取负债率
import akshare as ak

# 获取财务指标
df = ak.stock_financial_analysis_indicator(symbol="601939")
# 提取资产负债率
debt_ratio = df['资产负债率(%)'].values
```

**数据来源**：
- akshare `stock_financial_analysis_indicator` 接口
- 或 `stock_balance_sheet_by_report_em` 接口（资产负债表）

### 数据源架构

#### 当前数据源列表

| 数据项 | 数据源接口 | 状态 | 备注 |
|--------|-----------|------|------|
| 股息率(TTM) | akshare stock_a_lg_indicator | ✅ 正常 | 股息率数据 |
| 市值 | akshare stock_zh_a_spot_em | ✅ 正常 | 实时行情数据 |
| EPS/ROE | akshare stock_yjbb_em | ✅ 正常 | 业绩报表数据 |
| 每股股利 | akshare stock_fhps_em | 🆕 新增 | 分红配送数据 |
| 负债率 | akshare stock_financial_analysis_indicator | 🆕 新增 | 财务分析指标 |

#### 数据获取流程

```
步骤1: 获取股票列表
  └─ akshare stock_zh_a_spot_em (市值、价格、PE、PB)

步骤2: 获取EPS和ROE
  └─ akshare stock_yjbb_em (每股收益、净资产收益率)

步骤3: 获取股息率
  └─ akshare stock_a_lg_indicator (股息率TTM)

步骤4: 筛选候选股
  └─ 按市值、股息率、波动率筛选

步骤5: 获取分红数据 🆕
  └─ akshare stock_fhps_em (每股股利)
  └─ 计算支付率 = 每股股利 / 每股收益 * 100

步骤6: 获取财务指标 🆕
  └─ akshare stock_financial_analysis_indicator (负债率)

步骤7: 综合评分排序
  └─ 股息率40% + 波动率40% + EPS 20%

步骤8: 保存结果
  └─ SQLite数据库
```

### 测试计划

#### 单元测试

1. **支付率数据获取测试**
   - 测试 `stock_fhps_em` 接口是否可用
   - 验证每股股利数据格式
   - 计算支付率逻辑验证

2. **负债率数据获取测试**
   - 测试 `stock_financial_analysis_indicator` 接口是否可用
   - 验证负债率数据格式
   - 数据有效性检查

#### 集成测试

1. **完整流程测试**
   - 运行完整数据获取流程
   - 验证所有数据字段完整性
   - 检查数据库保存结果

2. **数据质量测试**
   - ROE数据完整性：目标 >95%
   - 支付率数据完整性：目标 >80%
   - 负债率数据完整性：目标 >80%

#### 验收标准

- ✅ ROE数据：30/30 条有数据（已达成）
- 🎯 支付率数据：>24/30 条有数据（目标80%）
- 🎯 负债率数据：>24/30 条有数据（目标80%）

### 风险与缓解

#### 风险1：akshare接口不稳定

**缓解措施**：
- 添加超时控制（60秒）
- 添加重试机制（最多3次）
- 记录错误日志

#### 风险2：数据源字段变更

**缓解措施**：
- 使用字段名映射表
- 添加字段存在性检查
- 灵活的数据解析逻辑

#### 风险3：接口访问限制

**缓解措施**：
- 添加请求间隔控制
- 使用缓存机制
- 准备备选数据源

### 下一步计划

1. **立即执行**：
   - 实现 `stock_fhps_em` 接口获取分红数据
   - 实现 `stock_financial_analysis_indicator` 接口获取负债率
   - 更新 `fetcher.py` 中的数据获取逻辑

2. **后续优化**：
   - 添加数据质量监控
   - 实现增量更新机制
   - 优化数据获取性能

3. **长期规划**：
   - 接入更多数据源
   - 实现数据源自动切换
   - 建立数据质量评分体系
