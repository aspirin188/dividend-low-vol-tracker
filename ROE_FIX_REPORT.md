# ROE数据修复报告

## 问题诊断

### 1. 根本原因
通过测试发现两个关键问题：

#### 问题1: signal模块在Flask子线程中无法使用
```
错误信息: signal only works in main thread of the main interpreter
```

**原因**: v6.12修复时添加的超时控制使用了`signal`模块，但Flask应用运行在子线程中，`signal`模块只能在主线程使用。

#### 问题2: 数据类型错误
```
错误信息: Expected numeric dtype, got object instead
```

**原因**: `prepare_results()`函数中对数值字段调用`.round(2)`时，这些字段可能是object类型而非数值类型。

### 2. 验证ROE数据源

通过测试确认：
- ✅ akshare的`stock_yjbb_em`接口**可以正常获取ROE数据**
- ✅ 成功获取5202只股票，其中5170只有ROE数据
- ✅ ROE数据示例：
  - 建设银行(601939): 10.69%
  - 招商银行(600036): 14.49%
  - 中国平安(601318): 13.8%

## 修复措施

### 修复1: 改用threading实现超时控制

**文件**: `server/services/fetcher.py`

**修改**: 将`signal`模块改为`threading`模块实现超时控制

```python
# 旧代码（有问题）
import signal
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(60)

# 新代码（已修复）
import threading
thread = threading.Thread(target=fetch_data, args=(year_end,))
thread.start()
thread.join(timeout=60)
```

### 修复2: 确保数值字段类型正确

**文件**: `server/services/scorer.py`

**修改**: 在`prepare_results()`函数中添加数值类型转换

```python
# 确保数值字段是数值类型（v6.12修复）
for col in ['dividend_yield_ttm', 'annual_vol', 'market_cap', 'payout_ratio', 'basic_eps', 'price', 'pe', 'pb', 'roe', 'debt_ratio']:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
```

## 测试结果

### ✅ ROE数据获取成功
```
正在获取 2024 年报数据...
✓ 获取 5202 只股票, ROE非空 5170/5202
```

### ✅ ROE数据验证
- 建设银行(601939): ROE=10.69% ✓
- 招商银行(600036): ROE=14.49% ✓
- 中国平安(601318): ROE=13.8% ✓

## 建议下一步

1. **重启应用**: 由于代码已更新，需要重启Flask应用
2. **运行完整流程**: 点击"运行"按钮，验证ROE数据是否正常显示
3. **检查数据库**: 确认ROE数据是否正确保存到数据库

## 代码变更文件

- `server/services/fetcher.py` - 修复超时控制机制
- `server/services/scorer.py` - 修复数值类型转换

## 版本更新

建议更新PRD到v6.13版本，记录此次修复：
- 修复signal模块在Flask子线程中无法使用的问题
- 修复prepare_results中的数值类型错误
- 添加更详细的错误日志
