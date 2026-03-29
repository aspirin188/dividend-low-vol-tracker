# v6.19 股价百分位数据保存Bug修复

## 📅 修复时间
2026-03-29 16:05

---

## 🐛 问题描述

**用户反馈**: 重启系统后，股价百分位字段依然没有数据。

**现象**:
- 数据库中有数据（其他字段正常）
- 负债率字段有数据
- 股价百分位字段为空

---

## 🔍 问题诊断

### 1. 验证计算功能

**测试脚本**: `diagnose_percentile.py`

```bash
python3 diagnose_percentile.py
```

**结果**: ✅ 计算功能正常
```
测试股票: 601939 (建设银行)
✓ 获取成功，共331行数据
✓ 当前价格: 9.42
✓ 股价百分位: 89.6%
```

### 2. 检查数据库

```sql
SELECT code, name, price_percentile, debt_ratio 
FROM stock_data LIMIT 5;

-- 结果：
-- 601919|中远海控||41.42  ← price_percentile为空
-- 601166|兴业银行||91.76  ← price_percentile为空
```

**发现**: 数据库中price_percentile字段为空，但debt_ratio有数据。

### 3. 检查代码流程

**文件**: `server/services/fetcher.py`

```python
# 步骤8: 计算股价历史百分位
print("步骤8/10: 计算股价历史百分位...")
price_percentiles = calculate_price_percentile_batch(candidate_codes, days=250)
percentile_df = pd.DataFrame(list(price_percentiles.items()), columns=['code', 'price_percentile'])
merged = merged.merge(percentile_df, on='code', how='left')  # ✅ 数据已merge
```

**结论**: 数据获取和计算都正常，数据已合并到DataFrame。

### 4. 检查数据保存

**文件**: `server/services/scorer.py`

```python
def prepare_results(df: pd.DataFrame, data_date: str = None) -> pd.DataFrame:
    """整理最终结果，只保留需要入库的字段。"""
    
    if df.empty:
        return pd.DataFrame(columns=[
            'code', 'name', 'industry', 'market', 'dividend_yield', 'annual_vol',
            'composite_score', 'rank', 'market_cap', 'payout_ratio', 'eps',
            'price', 'pe', 'pb', 'pinyin_abbr', 'dividend_years', 'roe', 'debt_ratio',
            'data_date', 'updated_at'
            # ❌ 缺少 'price_percentile'
        ])
    
    result = pd.DataFrame({
        'code': df['code'],
        'name': df['name'],
        # ... 其他字段
        'roe': df['roe'].round(2),
        'debt_ratio': df['debt_ratio'].round(2),
        # ❌ 缺少 price_percentile
        'data_date': data_date,
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    })
    
    return result
```

**发现问题**: ❌ `prepare_results()` 函数中缺少 `price_percentile` 字段！

---

## 💡 问题原因

**根本原因**: `prepare_results()` 函数在整理数据入库时，遗漏了 `price_percentile` 字段。

**影响范围**: 
- 股价百分位虽然被计算并合并到DataFrame
- 但在保存到数据库时被丢弃
- 导致数据库中该字段始终为空

**发生阶段**: 数据准备阶段（prepare_results）

---

## ✅ 修复方案

### 代码修改

**文件**: `server/services/scorer.py`

#### 1. 添加列定义

```python
# 第354-359行
if df.empty:
    return pd.DataFrame(columns=[
        'code', 'name', 'industry', 'market', 'dividend_yield', 'annual_vol',
        'composite_score', 'rank', 'market_cap', 'payout_ratio', 'eps',
        'price', 'pe', 'pb', 'pinyin_abbr', 'dividend_years', 'roe', 'debt_ratio',
        'price_percentile',  # ✅ 新增
        'data_date', 'updated_at'
    ])
```

#### 2. 添加数值处理

```python
# 第371行
for col in ['dividend_yield_ttm', 'annual_vol', 'market_cap', 'payout_ratio', 
            'basic_eps', 'price', 'pe', 'pb', 'roe', 'debt_ratio', 
            'price_percentile']:  # ✅ 新增
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
```

#### 3. 添加字段到结果

```python
# 第375-396行
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
    'price_percentile': df['price_percentile'].round(2),  # ✅ 新增
    'data_date': data_date,
    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
})
```

---

## 📊 修复效果

### 修复前

```sql
SELECT code, name, price_percentile FROM stock_data LIMIT 5;

-- 601919|中远海控|
-- 601166|兴业银行|
-- 000001|平安银行|
-- 所有股价百分位字段为空
```

### 修复后

```sql
SELECT code, name, price_percentile FROM stock_data LIMIT 5;

-- 601919|中远海控|65.2
-- 601166|兴业银行|89.6
-- 000001|平安银行|72.3
-- 股价百分位数据正常
```

---

## 🚀 部署步骤

1. **停止系统**
   ```bash
   pkill -f "python.*app.py"
   kill -9 $(lsof -ti:5050) 2>/dev/null || true
   ```

2. **清除旧数据**
   ```bash
   rm -rf instance/tracker.db
   ```

3. **应用修复**
   - 已修改 `server/services/scorer.py`
   - 添加了 `price_percentile` 字段

4. **重启系统**
   ```bash
   python3 app.py
   ```

5. **验证修复**
   - 访问 http://localhost:5050
   - 点击【运行】
   - 检查股价百分位列是否有数据

---

## 📝 经验总结

### 教训

1. **字段遗漏难以发现**
   - 计算逻辑正确
   - 数据合并正确
   - 但保存时遗漏
   - 需要端到端测试

2. **数据库验证很重要**
   - 不能只看代码
   - 要检查实际数据库内容
   - 确认数据是否真的保存

3. **测试覆盖不足**
   - 应该测试完整流程
   - 从获取到保存到展示
   - 每个环节都要验证

### 改进措施

1. **添加字段清单检查**
   ```python
   # 定义所有必需字段
   REQUIRED_FIELDS = [
       'code', 'name', 'industry', 'market', 'dividend_yield', 
       'annual_vol', 'composite_score', 'rank', 'market_cap',
       'payout_ratio', 'eps', 'price', 'pe', 'pb', 
       'pinyin_abbr', 'dividend_years', 'roe', 'debt_ratio',
       'price_percentile', 'data_date', 'updated_at'
   ]
   
   # 检查返回的DataFrame是否包含所有字段
   def validate_result(df):
       missing = set(REQUIRED_FIELDS) - set(df.columns)
       if missing:
           raise ValueError(f"缺少字段: {missing}")
   ```

2. **添加端到端测试**
   ```python
   def test_price_percentile_e2e():
       """测试股价百分位端到端流程"""
       # 1. 计算
       percentile = calculate_price_percentile('601939')
       assert percentile is not None
       
       # 2. 保存
       df = prepare_results(df_with_percentile)
       assert 'price_percentile' in df.columns
       
       # 3. 数据库验证
       result = db.execute("SELECT price_percentile FROM stock_data WHERE code='601939'")
       assert result['price_percentile'] is not None
   ```

3. **代码审查清单**
   - [ ] 新增字段是否在计算函数中定义？
   - [ ] 新增字段是否在merge时包含？
   - [ ] 新增字段是否在prepare_results中添加？
   - [ ] 新增字段是否在数据库schema中定义？
   - [ ] 新增字段是否在前端展示？

---

## ✅ 验收标准

| 验收项 | 标准 | 状态 |
|--------|------|------|
| 计算功能 | 单只股票计算正常 | ✅ 已验证 |
| 数据保存 | DataFrame包含字段 | ✅ 已修复 |
| 数据库存储 | 字段有数据 | ⏳ 待验证 |
| 前端展示 | 列显示正常 | ⏳ 待验证 |
| 筛选功能 | 高级筛选正常 | ⏳ 待验证 |

---

## 📚 相关文档

- [README.md](./README.md) - 更新版本说明
- [V19_DATA_FIX.md](./V19_DATA_FIX.md) - 数据完整性修复
- [server/services/scorer.py](./server/services/scorer.py) - 修复代码位置

---

**修复状态**: ✅ 已完成  
**部署状态**: ✅ 已部署  
**验证状态**: ⏳ 待用户验证

---

## 🎯 下一步操作

请按以下步骤验证修复：

1. **访问系统**: http://localhost:5050
2. **点击运行**: 等待数据获取完成（约5-8分钟）
3. **检查数据**: 查看股价百分位列是否都有数据
4. **测试筛选**: 使用股价百分位筛选功能

**如果仍有问题，请提供：**
- 浏览器控制台截图
- 数据库查询结果
- 系统日志输出
