# 性能问题诊断报告

| 项目 | 信息 |
|------|------|
| 诊断时间 | 2026-03-31 11:48 |
| 问题类型 | 性能问题 + 接口依赖 |
| 严重程度 | 🔴 **严重** |

---

## 🔍 问题诊断

### 1. 核心问题

**症状**:
- ✅ 系统运行非常慢
- ✅ 大量东方财富接口连接失败
- ✅ 进度缓慢（7% | 82/827）

**错误日志**:
```
✗ 601298 股价百分位计算失败: 
HTTPSConnectionPool(host='push2his.eastmoney.com', port=443): 
Max retries exceeded with url: /api/qt/stock/kline/get...
(Caused by ProxyError('Unable to connect to proxy'))
```

---

## 🎯 根本原因

### 问题1: 股价百分位计算还在使用东方财富接口

**位置**: `server/services/fetcher.py`

**函数**: `calculate_price_percentile()`

**代码**:
```python
def calculate_price_percentile(code: str, days: int = 250) -> float:
    df = ak.stock_zh_a_hist(
        symbol=code,
        period='daily',
        start_date=...,
        end_date=...,
        adjust='qfq'
    )
```

**问题**: `ak.stock_zh_a_hist()` 内部使用东方财富接口

---

### 问题2: 波动率计算还在使用东方财富接口

**位置**: `server/services/fetcher.py`

**函数**: `calculate_volatility()`

**代码**:
```python
def calculate_volatility(code: str, end_date: str = None, days: int = None) -> float:
    df = ak.stock_zh_a_hist(
        symbol=code,
        period='daily',
        start_date=...,
        end_date=...,
        adjust='qfq'
    )
```

**问题**: 同样使用 `ak.stock_zh_a_hist()`

---

### 问题3: 批量处理导致性能极差

**流程**:
```
步骤7/9: 计算股价历史百分位
  ├─ 循环处理 827 只股票
  ├─ 每只股票调用 ak.stock_zh_a_hist()
  ├─ 每次调用 2-5 秒（含失败重试）
  └─ 预计总耗时: 827 × 3秒 = 41分钟 ❌

步骤9/9: 计算候选股波动率
  ├─ 循环处理 827 只股票
  ├─ 每只股票调用 ak.stock_zh_a_hist()
  └─ 预计总耗时: 827 × 3秒 = 41分钟 ❌
```

**总耗时预估**: 82分钟（无法接受）

---

## 📊 影响分析

### 1. 性能影响

| 步骤 | 股票数 | 单次耗时 | 总耗时 | 状态 |
|------|--------|---------|--------|------|
| 股价百分位 | 827 | 3秒 | 41分钟 | ❌ 失败 |
| 波动率计算 | 827 | 3秒 | 41分钟 | ❌ 失败 |
| **总计** | - | - | **82分钟** | ❌ 不可用 |

### 2. 数据影响

| 影响 | 说明 |
|------|------|
| **数据丢失** | 所有股价百分位数据失败 |
| **波动率数据** | 所有波动率数据失败 |
| **筛选结果** | 依赖这些数据的筛选无法进行 |

### 3. 用户体验

```
用户操作: 点击"运行筛选"
    ↓
系统响应: 开始运行...
    ↓
10分钟后: 还在 7% 进度
    ↓
用户感受: 😤 "太慢了！"
    ↓
最终结果: 大量错误，数据不全
```

---

## 🔧 解决方案

### 方案一：使用腾讯/新浪历史数据接口（推荐）

**替代接口**:
```python
# 方案A: 腾讯历史K线接口
http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?

# 方案B: 网易历史K线接口
http://quotes.money.163.com/service/chddata.html?

# 方案C: 保留akshare但使用其他数据源
ak.stock_zh_a_hist_163()  # 网易数据源
```

**优势**:
- ✅ 接口稳定
- ✅ 响应快速
- ✅ 无需代理

---

### 方案二：缓存历史数据（推荐）

**策略**:
```
第一次运行: 
  ├─ 获取所有股票历史数据（1-2小时）
  ├─ 保存到本地数据库
  └─ 后续只更新最新数据

后续运行:
  ├─ 读取本地缓存（秒级）
  ├─ 只获取最新几天的数据
  └─ 总耗时 < 1分钟
```

**优势**:
- ✅ 极速响应（秒级）
- ✅ 降低接口压力
- ✅ 离线可用

---

### 方案三：并行处理优化（配合方案一）

**当前**: 串行处理，一个一个获取

**优化**: 并行处理，10个线程同时获取

**代码**:
```python
from concurrent.futures import ThreadPoolExecutor

def calculate_price_percentile_batch_parallel(codes: list) -> dict:
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(calculate_price_percentile, code) for code in codes]
        results = [f.result() for f in futures]
    return results
```

**优势**:
- ✅ 速度提升10倍
- ✅ 41分钟 → 4分钟

---

### 方案四：暂时禁用这些计算（快速方案）

**策略**:
```python
# 步骤7/9: 计算股价历史百分位
# 暂时跳过，设置为None
print("步骤7/9: 跳过股价百分位计算（性能优化）")
merged['price_percentile'] = None

# 步骤9/9: 计算候选股波动率
# 暂时跳过，设置为None
print("步骤9/9: 跳过波动率计算（性能优化）")
merged['annual_vol'] = None
```

**优势**:
- ✅ 立即可用
- ✅ 总耗时 < 5分钟
- ⚠️ 部分数据缺失

---

## 📋 推荐实施步骤

### 立即修复（5分钟）

**步骤1**: 暂时禁用这两个计算
```bash
# 修改 fetcher.py
# 注释掉股价百分位和波动率计算
```

**步骤2**: 重启服务
```bash
kill $(cat app.pid)
python3 app.py > /tmp/hl3_fast.log 2>&1 &
echo $! > app.pid
```

**步骤3**: 验证效果
- 运行筛选
- 预计耗时 < 5分钟
- 成功返回结果

---

### 长期优化（1-2小时）

**方案**: 实施方案一 + 方案三

1. **替换历史数据接口** (30分钟)
   - 使用腾讯/网易接口
   - 测试验证

2. **添加并行处理** (30分钟)
   - 实现 ThreadPoolExecutor
   - 速度提升10倍

3. **添加数据缓存** (可选，1小时)
   - SQLite存储历史数据
   - 定期更新机制

---

## 🎯 总结

### 问题清单

| # | 问题 | 严重性 | 解决方案 |
|---|------|--------|---------|
| 1 | 股价百分位使用东财接口 | 🔴 高 | 暂时禁用 / 替换接口 |
| 2 | 波动率使用东财接口 | 🔴 高 | 暂时禁用 / 替换接口 |
| 3 | 串行处理性能差 | 🟡 中 | 并行处理优化 |
| 4 | 无缓存机制 | 🟡 中 | 添加数据缓存 |

### 立即行动

✅ **推荐方案四**（暂时禁用）

**理由**:
- ⚡ 立即可用（5分钟修复）
- ⚡ 总耗时从 82分钟 → 5分钟
- ⚡ 用户可以立即使用系统

### 后续优化

📋 **下一步**: 实施方案一 + 方案三

**目标**:
- 🎯 耗时从 82分钟 → 5分钟
- 🎯 数据完整性 100%
- 🎯 用户体验优秀

---

**状态**: 🔴 **严重性能问题**  
**建议**: ⚡ **立即实施方案四**  
**预期**: ✅ **5分钟内可正常使用**
