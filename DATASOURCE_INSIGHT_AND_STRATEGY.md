# 数据接口测试Insight与应对策略

## 📊 数据接口测试总结

### 一、东方财富接口测试Insight

#### 1. 接口能力边界

**测试结果**：

| 字段 | 接口 | 支持情况 | 错误信息 |
|------|------|---------|---------|
| ROE（净资产收益率） | RPT_LICO_FN_CPD | ❌ 不支持 | `"WEIGHTEDAVERAGEORE返回字段不存在"` |
| 资产负债率 | RPT_LICO_FN_CPD | ❌ 不支持 | `"ASSETLIABRATIO返回字段不存在"` |
| 每股收益 | RPT_LICO_FN_CPD | ✅ 支持 | BASIC_EPS |
| 分红方案 | RPT_LICO_FN_CPD | ⚠️ 返回空数据 | 无数据 |

**Insight 1：接口字段有明确的能力边界**
```python
# 错误请求示例
params = {
    'reportName': 'RPT_LICO_FN_CPD',
    'columns': 'SECURITY_CODE,WEIGHTEDAVERAGEORE',  # ❌ 不支持
}

# 接口明确返回错误
response = {
    "success": false,
    "message": "WEIGHTEDAVERAGEORE返回字段不存在"
}
```

**启示**：
- 不能假设接口支持所有字段
- 需要先查询接口支持的字段列表
- 接口会明确告知不支持，这是好的设计

---

#### 2. 数据返回的不确定性

**测试结果**：
```
测试日期: 2026-03-28
接口: RPT_LICO_FN_CPD（分红数据）
结果: 返回空数据

原因可能：
1. 接口已变更
2. 访问限制（频率/权限）
3. 数据源切换
4. 时间特定性（非分红季）
```

**Insight 2：接口可用性可能随时变化**
```python
# 某天可能正常工作
df = fetch_from_eastmoney()  # 返回数据

# 另一天可能突然失败
df = fetch_from_eastmoney()  # 返回空或错误
```

**启示**：
- 需要实时监控接口可用性
- 需要有备选方案
- 需要记录接口状态变化

---

#### 3. 数据准确性问题

**测试对比**：
```
东方财富 BASIC_EPS: 有时不准确
akshare 每股收益: 相对准确

例子：某股票
- 东方财富 BASIC_EPS: 0.5（不准确）
- akshare 每股收益: 1.2（准确）
```

**Insight 3：不同数据源的数据可能有差异**
- 同一个指标，不同数据源的值可能不同
- 需要交叉验证数据准确性
- 建立数据可信度评估

---

### 二、akshare接口测试Insight

#### 1. 数据完整性高

**测试结果**：

| 接口 | 数据量 | 完整性 | 示例 |
|------|--------|--------|------|
| stock_yjbb_em | 5202只 | ROE: 5170/5202 (99.4%) | 业绩报表 |
| stock_fhps_em | 3464只 | 分红: 3444/3464 (99.4%) | 分红配送 |
| stock_a_lg_indicator | 5000+只 | 股息率: 100% | 股息率 |

**Insight 4：akshare数据完整性通常>95%**
- 数据质量高，可以作为主要数据源
- 少量缺失数据可以接受
- 需要处理None值

---

#### 2. 字段命名不统一

**测试结果**：
```python
# stock_fhps_em 接口
df.columns = ['代码', '名称', '现金分红-现金分红比例', ...]
# 注意：是'代码'，不是'股票代码'

# stock_yjbb_em 接口
df.columns = ['股票代码', '股票简称', '每股收益', ...]
# 注意：是'股票代码'，不是'代码'
```

**Insight 5：不同接口的字段命名不统一**
- 需要先打印columns确认字段名
- 不能假设字段名
- 需要建立字段映射表

**解决方案**：
```python
# 建立字段映射表
FIELD_MAPPING = {
    'stock_fhps_em': {
        'code': '代码',
        'name': '名称',
        'dividend_per_share': '现金分红-现金分红比例',
    },
    'stock_yjbb_em': {
        'code': '股票代码',
        'name': '股票简称',
        'eps': '每股收益',
        'roe': '净资产收益率',
    }
}

def get_field(interface, field_key):
    """获取接口的实际字段名"""
    return FIELD_MAPPING.get(interface, {}).get(field_key, field_key)
```

---

#### 3. 数据需要计算转换

**测试结果**：
```python
# stock_fhps_em 返回的是"每10股派息金额"
df['现金分红-现金分红比例'] = 3.62  # 表示每10股派3.62元

# 需要转换为"每股股利"
dividend_per_share = 3.62 / 10 = 0.362  # 每股0.362元
```

**Insight 6：接口数据不一定直接可用**
- 需要理解数据含义
- 需要适当的转换计算
- 需要验证计算逻辑

---

#### 4. 部分接口数据较旧

**测试结果**：
```python
# stock_financial_analysis_indicator 接口
# 返回的数据：
{
    '日期': '1999-12-31',  # 20多年前的数据
    '资产负债率(%)': 98.16
}
```

**Insight 7：接口有数据，但数据可能过时**
- 需要检查数据的时效性
- 需要筛选最新数据
- 某些接口可能不再维护

---

### 三、接口性能Insight

#### 1. 响应时间差异

**测试结果**：

| 接口 | 响应时间 | 数据量 | 备注 |
|------|---------|--------|------|
| akshare stock_yjbb_em | 4-5秒 | 5202条 | 有进度条 |
| akshare stock_fhps_em | 2秒 | 3464条 | 有进度条 |
| 东方财富 RPT_LICO_FN_CPD | 1-2秒 | 变化 | 无进度条 |

**Insight 8：接口性能差异明显**
- 大数据量接口响应较慢
- 需要添加超时控制
- 需要考虑用户体验

---

#### 2. 并发限制

**测试观察**：
```python
# 快速连续请求可能导致失败
for code in codes:
    data = fetch_data(code)  # 可能触发限流
    
# 解决方案：添加延迟
import time
for code in codes:
    data = fetch_data(code)
    time.sleep(0.3)  # 延迟300ms
```

**Insight 9：接口有访问频率限制**
- 需要控制请求频率
- 需要添加重试机制
- 批量接口优于单只查询

---

### 四、数据一致性Insight

#### 1. 跨接口数据对齐

**测试发现**：
```python
# 股票代码在不同接口中格式可能不同
# 接口A: '601939'
# 接口B: '601939.SH'
# 接口C: 'sh601939'
```

**Insight 10：需要统一数据键值**
- 建立标准化的代码格式
- 在合并数据前先统一格式
- 例如统一使用6位数字代码

---

## 🛠️ 应对策略框架

### 策略1：多数据源架构

#### 设计原则

**单一数据源 vs 多数据源**：

```
❌ 单一数据源（脆弱）
应用 → 接口A
      └─ 接口A失败 → 整个应用失败

✅ 多数据源（健壮）
应用 → 数据源管理器
      ├─ 接口A（优先）
      ├─ 接口B（备选）
      ├─ 接口C（兜底）
      └─ 优雅降级
```

#### 实现框架

```python
class DataSourceManager:
    """数据源管理器"""
    
    def __init__(self):
        self.sources = {}  # 注册的数据源
        self.health_status = {}  # 健康状态
        self.fallback_chain = []  # 回退链
        
    def register_source(self, name, fetch_func, priority=1, 
                       health_check=None, metadata=None):
        """注册数据源"""
        self.sources[name] = {
            'fetch': fetch_func,
            'priority': priority,
            'health_check': health_check,
            'metadata': metadata or {},
            'stats': {
                'success_count': 0,
                'fail_count': 0,
                'last_success': None,
                'last_fail': None,
            }
        }
        
        # 更新回退链（按优先级排序）
        self.fallback_chain = sorted(
            self.sources.keys(),
            key=lambda x: self.sources[x]['priority'],
            reverse=True
        )
    
    def fetch(self, data_type, params=None, fallback=True):
        """获取数据（支持自动回退）"""
        errors = []
        
        for source_name in self.fallback_chain:
            source = self.sources[source_name]
            
            # 健康检查
            if source['health_check']:
                if not source['health_check']():
                    print(f"⚠️ {source_name} 健康检查失败，跳过")
                    continue
            
            try:
                # 尝试获取数据
                data = source['fetch'](data_type, params)
                
                # 验证数据
                if self._validate_data(data, data_type):
                    # 更新成功统计
                    source['stats']['success_count'] += 1
                    source['stats']['last_success'] = datetime.now()
                    
                    print(f"✓ 从 {source_name} 获取数据成功")
                    return {
                        'data': data,
                        'source': source_name,
                        'quality': self._assess_quality(data),
                    }
                else:
                    errors.append(f"{source_name}: 数据验证失败")
                    
            except Exception as e:
                # 记录失败
                source['stats']['fail_count'] += 1
                source['stats']['last_fail'] = datetime.now()
                errors.append(f"{source_name}: {str(e)}")
                
                print(f"✗ {source_name} 失败: {e}")
        
        # 所有数据源都失败
        if fallback and self._can_graceful_degrade(data_type):
            return self._graceful_degradation(data_type, errors)
        
        raise DataSourceError(f"所有数据源失败: {'; '.join(errors)}")
    
    def _validate_data(self, data, data_type):
        """验证数据质量"""
        if data is None or data.empty:
            return False
        
        # 检查必需字段
        required_fields = DATA_VALIDATION_RULES.get(data_type, {}).get('required_fields', [])
        for field in required_fields:
            if field not in data.columns:
                return False
        
        # 检查数据量
        min_records = DATA_VALIDATION_RULES.get(data_type, {}).get('min_records', 0)
        if len(data) < min_records:
            return False
        
        # 检查数据完整性
        quality_threshold = DATA_VALIDATION_RULES.get(data_type, {}).get('quality_threshold', 0.8)
        for key_field in DATA_VALIDATION_RULES.get(data_type, {}).get('key_fields', []):
            completeness = data[key_field].notna().sum() / len(data)
            if completeness < quality_threshold:
                return False
        
        return True
    
    def _assess_quality(self, data):
        """评估数据质量"""
        return {
            'completeness': data.notna().sum().sum() / (len(data) * len(data.columns)),
            'record_count': len(data),
            'timestamp': datetime.now().isoformat(),
        }
    
    def _can_graceful_degrade(self, data_type):
        """是否可以优雅降级"""
        return data_type in DEGRADATION_STRATEGIES
    
    def _graceful_degradation(self, data_type, errors):
        """优雅降级"""
        strategy = DEGRADATION_STRATEGIES.get(data_type, {})
        
        return {
            'data': strategy.get('fallback_value', None),
            'source': 'graceful_degradation',
            'quality': {'completeness': 0},
            'errors': errors,
            'message': strategy.get('message', '数据暂时不可用'),
        }
```

#### 使用示例

```python
# 初始化数据源管理器
manager = DataSourceManager()

# 注册数据源（按优先级）
manager.register_source(
    name='akshare_yjbb',
    fetch_func=fetch_from_akshare_yjbb,
    priority=10,  # 最高优先级
    health_check=lambda: check_akshare_health(),
    metadata={
        'type': 'primary',
        'fields': ['code', 'eps', 'roe'],
    }
)

manager.register_source(
    name='eastmoney_cpd',
    fetch_func=fetch_from_eastmoney_cpd,
    priority=5,  # 次优先级
    health_check=lambda: check_eastmoney_health(),
    metadata={
        'type': 'backup',
        'fields': ['code', 'eps'],  # 注意：不支持ROE
    }
)

manager.register_source(
    name='local_cache',
    fetch_func=fetch_from_cache,
    priority=1,  # 最低优先级（兜底）
    metadata={
        'type': 'fallback',
        'fields': ['code', 'eps', 'roe'],
    }
)

# 获取数据
try:
    result = manager.fetch('roe_data', params={'year': 2024})
    print(f"数据来源: {result['source']}")
    print(f"数据质量: {result['quality']}")
except DataSourceError as e:
    print(f"获取失败: {e}")
```

---

### 策略2：接口能力探测

#### 设计原则

**不要假设接口能力，而是主动探测**

#### 实现框架

```python
class InterfaceCapabilityDetector:
    """接口能力探测器"""
    
    def __init__(self):
        self.capabilities = {}  # 已探测的能力
        self.last_check = {}  # 上次检查时间
        
    def detect_capabilities(self, interface_name, test_code='601939'):
        """探测接口支持的字段和能力"""
        print(f"正在探测接口 {interface_name} 的能力...")
        
        # 常见字段列表
        common_fields = [
            'SECURITY_CODE', 'SECURITY_NAME_ABBR', 
            'BASIC_EPS', 'WEIGHTEDAVERAGEORE',  # ROE
            'ASSETLIABRATIO',  # 资产负债率
            'ASSIGNDSCRPT',  # 分红方案
        ]
        
        # 逐个测试字段
        supported_fields = []
        unsupported_fields = []
        
        for field in common_fields:
            try:
                # 尝试获取该字段
                data = self._test_field(interface_name, field, test_code)
                if data is not None:
                    supported_fields.append(field)
                    print(f"  ✓ {field}: 支持")
                else:
                    unsupported_fields.append(field)
            except Exception as e:
                unsupported_fields.append(field)
                print(f"  ✗ {field}: 不支持 ({e})")
        
        # 记录结果
        self.capabilities[interface_name] = {
            'supported_fields': supported_fields,
            'unsupported_fields': unsupported_fields,
            'checked_at': datetime.now(),
        }
        
        return self.capabilities[interface_name]
    
    def _test_field(self, interface_name, field, test_code):
        """测试单个字段"""
        # 根据接口类型调用不同的测试方法
        if interface_name == 'eastmoney_cpd':
            return self._test_eastmoney_field(field, test_code)
        elif interface_name == 'akshare':
            return self._test_akshare_field(field, test_code)
        else:
            return None
    
    def get_supported_fields(self, interface_name):
        """获取接口支持的字段列表"""
        if interface_name not in self.capabilities:
            self.detect_capabilities(interface_name)
        
        return self.capabilities[interface_name]['supported_fields']
    
    def is_field_supported(self, interface_name, field):
        """检查字段是否支持"""
        supported = self.get_supported_fields(interface_name)
        return field in supported
    
    def refresh_capabilities(self, interface_name=None):
        """刷新能力探测（定期执行）"""
        if interface_name:
            self.detect_capabilities(interface_name)
        else:
            for name in self.capabilities.keys():
                self.detect_capabilities(name)
```

#### 使用示例

```python
# 初始化探测器
detector = InterfaceCapabilityDetector()

# 探测接口能力
capabilities = detector.detect_capabilities('eastmoney_cpd')

# 使用探测结果
if detector.is_field_supported('eastmoney_cpd', 'WEIGHTEDAVERAGEORE'):
    # 可以获取ROE
    roe = fetch_roe_from_eastmoney()
else:
    # 使用其他数据源
    roe = fetch_roe_from_akshare()

# 定期刷新（如每天）
schedule.every().day.at("00:00").do(
    detector.refresh_capabilities
)
```

---

### 策略3：优雅降级设计

#### 设计原则

**当数据不可用时，如何优雅地处理？**

#### 降级策略表

```python
DEGRADATION_STRATEGIES = {
    'roe': {
        'strategy': 'use_zero',
        'fallback_value': None,
        'message': 'ROE数据暂不可用，显示为空',
        'impact': '低',
        'user_action': '无需操作，等待数据恢复',
    },
    'payout_ratio': {
        'strategy': 'use_zero',
        'fallback_value': None,
        'message': '支付率数据暂不可用，显示为空',
        'impact': '低',
        'user_action': '无需操作，等待数据恢复',
    },
    'debt_ratio': {
        'strategy': 'use_zero',
        'fallback_value': None,
        'message': '负债率数据暂不可用，显示为空',
        'impact': '低',
        'user_action': '无需操作，等待数据恢复',
    },
    'dividend_yield': {
        'strategy': 'calculate_from_price',
        'fallback_func': calculate_dividend_yield_from_price,
        'message': '股息率数据不可用，使用价格计算',
        'impact': '中',
        'user_action': '检查计算结果的准确性',
    },
    'price': {
        'strategy': 'fail_fast',
        'message': '价格数据不可用，无法继续',
        'impact': '高',
        'user_action': '联系管理员',
    },
}
```

#### 实现框架

```python
class GracefulDegradation:
    """优雅降级管理"""
    
    def __init__(self):
        self.degradation_log = []
        
    def handle_missing_data(self, data_type, context=None):
        """处理缺失数据"""
        strategy = DEGRADATION_STRATEGIES.get(data_type, {
            'strategy': 'fail_fast',
            'message': f'{data_type}数据不可用',
        })
        
        # 记录降级事件
        self.degradation_log.append({
            'data_type': data_type,
            'strategy': strategy['strategy'],
            'timestamp': datetime.now(),
            'context': context,
        })
        
        # 根据策略处理
        if strategy['strategy'] == 'use_zero':
            # 返回空值，继续执行
            print(f"⚠️ {strategy['message']}")
            return {
                'value': strategy.get('fallback_value'),
                'status': 'degraded',
                'message': strategy['message'],
            }
        
        elif strategy['strategy'] == 'calculate_from_price':
            # 使用备选计算方法
            print(f"⚠️ {strategy['message']}")
            fallback_value = strategy['fallback_func'](context)
            return {
                'value': fallback_value,
                'status': 'calculated',
                'message': strategy['message'],
            }
        
        elif strategy['strategy'] == 'fail_fast':
            # 快速失败
            raise CriticalDataError(strategy['message'])
        
        else:
            # 未知策略
            raise ValueError(f"未知的降级策略: {strategy['strategy']}")
    
    def get_degradation_report(self):
        """获取降级报告"""
        return {
            'total_degradations': len(self.degradation_log),
            'by_type': self._group_by_type(),
            'recent_events': self.degradation_log[-10:],
        }
    
    def _group_by_type(self):
        """按类型分组"""
        from collections import Counter
        types = [log['data_type'] for log in self.degradation_log]
        return dict(Counter(types))
```

#### 使用示例

```python
degradation = GracefulDegradation()

# 处理ROE缺失
try:
    roe_data = fetch_roe()
except DataSourceError:
    roe_data = degradation.handle_missing_data('roe')
    # roe_data = {'value': None, 'status': 'degraded', 'message': '...'}

# 处理价格缺失（快速失败）
try:
    price_data = fetch_price()
except DataSourceError:
    # 会抛出CriticalDataError
    price_data = degradation.handle_missing_data('price')

# 查看降级报告
report = degradation.get_degradation_report()
print(f"总降级次数: {report['total_degradations']}")
```

---

### 策略4：替代方案矩阵

#### 当接口不支持某个字段时，如何寻找替代？

**替代方案矩阵**：

| 缺失字段 | 方案1（推荐） | 方案2（备选） | 方案3（计算） | 方案4（人工） |
|---------|-------------|-------------|-------------|-------------|
| **ROE** | akshare.stock_yjbb_em | 东方财富其他接口 | 计算: 净利润/净资产 | 用户输入 |
| **资产负债率** | akshare.stock_financial_analysis_indicator | akshare资产负债表接口 | 计算: 负债/资产 | 用户输入 |
| **支付率** | akshare.stock_fhps_em | 东方财富分红接口 | 计算: 每股股利/EPS | 用户输入 |
| **股息率** | akshare.stock_a_lg_indicator | 计算: 年股利/股价 | 历史数据推算 | 用户输入 |
| **市值** | akshare.stock_zh_a_spot_em | 计算: 股价×总股本 | 实时计算 | - |
| **波动率** | akshare.stock_zh_a_hist | 历史数据计算 | 使用近似值 | - |

#### 实现框架

```python
class FieldAlternativeResolver:
    """字段替代方案解析器"""
    
    def __init__(self):
        self.alternatives = self._build_alternative_matrix()
        self.attempt_log = []
        
    def _build_alternative_matrix(self):
        """构建替代方案矩阵"""
        return {
            'roe': [
                {
                    'source': 'akshare.stock_yjbb_em',
                    'priority': 1,
                    'field': '净资产收益率',
                    'pros': ['数据完整', '更新及时'],
                    'cons': ['响应较慢'],
                },
                {
                    'source': 'eastmoney.other_interface',
                    'priority': 2,
                    'field': 'ROE',
                    'pros': ['响应快'],
                    'cons': ['需要找到正确接口'],
                },
                {
                    'source': 'calculate',
                    'priority': 3,
                    'formula': '净利润 / 净资产',
                    'requires': ['net_profit', 'net_assets'],
                    'pros': ['理论准确'],
                    'cons': ['需要多个原始数据'],
                },
            ],
            'debt_ratio': [
                {
                    'source': 'akshare.stock_financial_analysis_indicator',
                    'priority': 1,
                    'field': '资产负债率(%)',
                    'pros': ['直接可用'],
                    'cons': ['数据可能较旧'],
                },
                {
                    'source': 'akshare.stock_balance_sheet_by_report_em',
                    'priority': 2,
                    'field': '负债合计 / 资产总计',
                    'pros': ['数据新鲜'],
                    'cons': ['需要计算'],
                },
                {
                    'source': 'calculate',
                    'priority': 3,
                    'formula': '总负债 / 总资产',
                    'requires': ['total_liabilities', 'total_assets'],
                    'pros': ['理论准确'],
                    'cons': ['需要原始财务数据'],
                },
            ],
            'payout_ratio': [
                {
                    'source': 'akshare.stock_fhps_em',
                    'priority': 1,
                    'calculation': '每股股利 / 每股收益 * 100',
                    'requires': ['dividend_per_share', 'eps'],
                    'pros': ['数据准确'],
                    'cons': ['需要EPS数据'],
                },
            ],
        }
    
    def resolve(self, field_name, context=None):
        """解析字段的替代方案"""
        alternatives = self.alternatives.get(field_name, [])
        
        if not alternatives:
            raise NoAlternativeError(f"字段 {field_name} 没有可用的替代方案")
        
        # 按优先级尝试
        for alt in alternatives:
            print(f"尝试方案 {alt['priority']}: {alt['source']}")
            
            try:
                data = self._try_alternative(alt, context)
                
                # 记录成功
                self.attempt_log.append({
                    'field': field_name,
                    'alternative': alt['source'],
                    'status': 'success',
                    'timestamp': datetime.now(),
                })
                
                return {
                    'data': data,
                    'source': alt['source'],
                    'method': alt.get('calculation', 'direct'),
                }
                
            except Exception as e:
                print(f"  ✗ 失败: {e}")
                self.attempt_log.append({
                    'field': field_name,
                    'alternative': alt['source'],
                    'status': 'failed',
                    'error': str(e),
                    'timestamp': datetime.now(),
                })
                continue
        
        # 所有方案都失败
        raise AllAlternativesFailedError(
            f"字段 {field_name} 的所有替代方案都失败"
        )
    
    def _try_alternative(self, alternative, context):
        """尝试具体的替代方案"""
        source = alternative['source']
        
        if source.startswith('akshare.'):
            # akshare接口
            interface = source.split('.')[1]
            return self._fetch_from_akshare(interface, alternative, context)
        
        elif source.startswith('eastmoney.'):
            # 东方财富接口
            interface = source.split('.')[1]
            return self._fetch_from_eastmoney(interface, alternative, context)
        
        elif source == 'calculate':
            # 计算方案
            return self._calculate_field(alternative, context)
        
        else:
            raise ValueError(f"未知的方案类型: {source}")
```

#### 使用示例

```python
resolver = FieldAlternativeResolver()

# 解析ROE字段
try:
    result = resolver.resolve('roe', context={'year': 2024})
    print(f"数据来源: {result['source']}")
    roe_data = result['data']
except AllAlternativesFailedError as e:
    print(f"所有方案都失败: {e}")
    # 使用降级策略
    roe_data = None

# 解析资产负债率
try:
    result = resolver.resolve('debt_ratio', context={'codes': ['601939']})
    debt_data = result['data']
except AllAlternativesFailedError as e:
    print(f"所有方案都失败: {e}")
    debt_data = None
```

---

### 策略5：主动监控和告警

#### 设计原则

**不要等用户发现问题，主动监控数据质量**

#### 监控指标

```python
class DataSourceMonitor:
    """数据源监控器"""
    
    def __init__(self):
        self.metrics = {}
        self.alerts = []
        self.thresholds = {
            'completeness': 0.8,  # 数据完整性阈值
            'success_rate': 0.9,  # 成功率阈值
            'response_time': 10,  # 响应时间阈值（秒）
        }
    
    def check_data_quality(self, source_name, data):
        """检查数据质量"""
        metrics = {
            'timestamp': datetime.now(),
            'record_count': len(data),
            'field_count': len(data.columns),
            'completeness': {},
        }
        
        # 检查每个字段的完整性
        for col in data.columns:
            completeness = data[col].notna().sum() / len(data)
            metrics['completeness'][col] = completeness
            
            # 告警检查
            if completeness < self.thresholds['completeness']:
                self._create_alert(
                    level='warning',
                    source=source_name,
                    field=col,
                    message=f"数据完整性不足: {completeness:.1%}",
                    value=completeness,
                )
        
        self.metrics[source_name] = metrics
        return metrics
    
    def check_interface_health(self, source_name, fetch_func):
        """检查接口健康状态"""
        import time
        
        start = time.time()
        try:
            data = fetch_func()
            elapsed = time.time() - start
            
            health = {
                'status': 'healthy',
                'response_time': elapsed,
                'has_data': data is not None and not data.empty,
            }
            
            # 响应时间告警
            if elapsed > self.thresholds['response_time']:
                self._create_alert(
                    level='warning',
                    source=source_name,
                    message=f"响应时间过长: {elapsed:.2f}秒",
                    value=elapsed,
                )
            
        except Exception as e:
            health = {
                'status': 'unhealthy',
                'error': str(e),
            }
            
            self._create_alert(
                level='critical',
                source=source_name,
                message=f"接口异常: {e}",
            )
        
        return health
    
    def _create_alert(self, level, source, message, field=None, value=None):
        """创建告警"""
        alert = {
            'level': level,  # critical, warning, info
            'source': source,
            'field': field,
            'message': message,
            'value': value,
            'timestamp': datetime.now(),
        }
        
        self.alerts.append(alert)
        
        # 打印告警
        level_emoji = {'critical': '🔴', 'warning': '⚠️', 'info': 'ℹ️'}
        print(f"{level_emoji.get(level, '⚠️')} [{level.upper()}] {source}: {message}")
    
    def get_health_report(self):
        """获取健康报告"""
        return {
            'total_alerts': len(self.alerts),
            'alerts_by_level': self._group_alerts_by_level(),
            'recent_alerts': self.alerts[-10:],
            'metrics': self.metrics,
        }
    
    def _group_alerts_by_level(self):
        """按级别分组告警"""
        from collections import Counter
        levels = [alert['level'] for alert in self.alerts]
        return dict(Counter(levels))
```

#### 使用示例

```python
monitor = DataSourceMonitor()

# 检查数据质量
data = fetch_roe_from_akshare()
metrics = monitor.check_data_quality('akshare_yjbb', data)

# 检查接口健康
health = monitor.check_interface_health(
    'akshare_yjbb',
    fetch_func=lambda: ak.stock_yjbb_em(date='20241231')
)

# 获取健康报告
report = monitor.get_health_report()
print(f"总告警数: {report['total_alerts']}")
print(f"告警分布: {report['alerts_by_level']}")
```

---

## 📋 实战决策流程图

### 当发现接口不支持某个字段时

```
步骤1: 确认问题
├─ 字段名是否正确？
├─ 接口是否真的不支持？
└─ 是否是临时性问题？

步骤2: 寻找替代方案
├─ 查看替代方案矩阵
├─ 尝试优先级最高的方案
├─ 依次尝试备选方案
└─ 记录尝试结果

步骤3: 评估影响
├─ 数据完整性要求？
├─ 对用户的影响？
└─ 对系统的影响？

步骤4: 选择策略
├─ 如果影响低 → 优雅降级
├─ 如果影响中 → 使用替代方案
├─ 如果影响高 → 快速失败
└─ 如果可计算 → 计算得出

步骤5: 实施和监控
├─ 实施选定策略
├─ 添加监控告警
├─ 记录日志
└─ 通知相关人员

步骤6: 持续改进
├─ 寻找更好的数据源
├─ 优化算法
├─ 更新文档
└─ 分享经验
```

---

## 🎯 具体场景处理指南

### 场景1：发现新接口不支持某个字段

**处理流程**：

```python
# 1. 探测能力
detector = InterfaceCapabilityDetector()
capabilities = detector.detect_capabilities('new_interface')

# 2. 查找替代方案
resolver = FieldAlternativeResolver()
try:
    result = resolver.resolve('missing_field', context=context)
    data = result['data']
    source = result['source']
except AllAlternativesFailedError:
    # 3. 优雅降级
    degradation = GracefulDegradation()
    result = degradation.handle_missing_data('missing_field')

# 4. 记录和监控
monitor = DataSourceMonitor()
monitor.check_data_quality('new_interface', data)
```

---

### 场景2：接口突然返回空数据

**处理流程**：

```python
# 1. 使用多数据源架构
manager = DataSourceManager()

# 注册多个数据源
manager.register_source('primary', fetch_primary, priority=10)
manager.register_source('backup', fetch_backup, priority=5)
manager.register_source('cache', fetch_cache, priority=1)

# 2. 自动回退
try:
    result = manager.fetch('data_type', fallback=True)
    print(f"数据来源: {result['source']}")
except DataSourceError as e:
    print(f"所有数据源失败: {e}")
    
    # 3. 优雅降级
    degradation = GracefulDegradation()
    result = degradation.handle_missing_data('data_type')
```

---

### 场景3：数据质量下降

**处理流程**：

```python
# 1. 监控数据质量
monitor = DataSourceMonitor()
data = fetch_data()
metrics = monitor.check_data_quality('source_name', data)

# 2. 检查告警
report = monitor.get_health_report()
if report['total_alerts'] > 0:
    print("发现数据质量问题:")
    for alert in report['recent_alerts']:
        print(f"  {alert['level']}: {alert['message']}")
    
    # 3. 切换数据源
    print("切换到备选数据源...")
    data = fetch_from_backup()
    
    # 4. 更新优先级
    manager.update_priority('backup', priority=10)
    manager.update_priority('primary', priority=5)
```

---

## 💡 总结：数据接口管理的最佳实践

### 1. **假设接口会失败**
- 永远不要假设接口100%可用
- 设计时考虑失败场景
- 准备好应对措施

### 2. **多数据源是必须的**
- 至少准备2-3个数据源
- 按优先级排列
- 实现自动回退

### 3. **验证先于使用**
- 使用前验证数据质量
- 检查字段存在性
- 检查数据完整性

### 4. **监控不能少**
- 实时监控数据质量
- 设置告警阈值
- 定期生成报告

### 5. **优雅降级**
- 即使数据缺失，系统也要可用
- 明确告知用户数据状态
- 不影响其他功能

### 6. **记录和分享**
- 记录所有问题
- 记录解决方案
- 更新知识库

---

**核心认知**：

> 数据接口是外部依赖，我们无法控制它的行为。
> 我们能做的是：**预见问题、准备方案、快速响应、持续优化**。

**最终建议**：

建立一套完整的数据接口管理体系，包括：
- 能力探测机制
- 多数据源架构
- 替代方案矩阵
- 优雅降级策略
- 监控告警系统

**这样，无论遇到什么问题，都能从容应对。** 🎯
