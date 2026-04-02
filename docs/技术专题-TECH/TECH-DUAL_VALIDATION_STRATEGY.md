# 数据双重验证机制设计文档

## 核心原则

**"不能依赖单一数据源，必须通过交叉验证确认数据可靠性"**

### 设计理念

```
传统方案（不可靠）：
数据源A → 使用数据
        └─ 数据源A错误 → 整个系统错误

双重验证方案（可靠）：
数据源A → 比较 → 一致性检查 → 使用数据
数据源B → 比较 → 一致性检查 → 使用数据
        └─ 不一致 → 告警/降级/人工介入
```

---

## 一、数据验证策略

### 1.1 验证级别

**Level 1: 完全一致（高可信度）**
```
数据源A: 10.69%
数据源B: 10.71%
差异: 0.02% < 阈值(5%)
结论: ✅ 数据可信，使用平均值: 10.70%
```

**Level 2: 轻微差异（中可信度）**
```
数据源A: 10.69%
数据源B: 11.20%
差异: 0.51% ≈ 阈值(5%)
结论: ⚠️ 数据可用但有偏差，使用平均值并标记
```

**Level 3: 明显差异（低可信度）**
```
数据源A: 10.69%
数据源B: 15.30%
差异: 4.61% > 阈值(5%)
结论: ❌ 数据冲突，需要进一步验证
行动: 
  - 标记异常
  - 使用历史数据或权威数据源
  - 触发人工审核
```

**Level 4: 单一数据源（最低可信度）**
```
数据源A: 10.69%
数据源B: 无数据
结论: ⚠️ 只有一个数据源，数据可信度低
行动:
  - 使用数据源A，但标记为"未验证"
  - 触发告警
  - 尝试获取第三数据源
```

**Level 5: 全部失败（不可信）**
```
数据源A: 无数据
数据源B: 无数据
结论: ❌ 数据完全不可用
行动:
  - 标记为缺失
  - 触发严重告警
  - 优雅降级
```

---

### 1.2 验证规则

#### 1.2.1 数值型数据验证

```python
VALIDATION_RULES = {
    'roe': {
        'type': 'percentage',
        'range': [-50, 100],  # 合理范围
        'tolerance': 0.05,    # 5%的差异容忍度
        'absolute_tolerance': 0.5,  # 绝对值容忍度（百分点）
        'description': '净资产收益率',
    },
    'payout_ratio': {
        'type': 'percentage',
        'range': [0, 200],    # 合理范围
        'tolerance': 0.10,    # 10%的差异容忍度
        'absolute_tolerance': 5.0,  # 绝对值容忍度
        'description': '股利支付率',
    },
    'debt_ratio': {
        'type': 'percentage',
        'range': [0, 100],    # 合理范围
        'tolerance': 0.05,    # 5%的差异容忍度
        'absolute_tolerance': 3.0,  # 绝对值容忍度
        'description': '资产负债率',
    },
    'eps': {
        'type': 'currency',
        'range': [-10, 100],  # 合理范围（元）
        'tolerance': 0.10,    # 10%的差异容忍度
        'absolute_tolerance': 0.5,  # 绝对值容忍度（元）
        'description': '每股收益',
    },
    'dividend_yield': {
        'type': 'percentage',
        'range': [0, 20],     # 合理范围
        'tolerance': 0.10,    # 10%的差异容忍度
        'absolute_tolerance': 0.5,  # 绝对值容忍度
        'description': '股息率',
    },
}
```

#### 1.2.2 一致性检查算法

```python
def check_consistency(value_a, value_b, field_name):
    """
    检查两个数据源的一致性
    
    返回：
    {
        'is_consistent': bool,
        'confidence': 'high' | 'medium' | 'low',
        'difference': float,
        'difference_pct': float,
        'recommended_value': float,
        'message': str,
    }
    """
    rule = VALIDATION_RULES[field_name]
    
    # 两个数据源都有值
    if value_a is not None and value_b is not None:
        # 计算差异
        difference = abs(value_a - value_b)
        avg_value = (value_a + value_b) / 2
        difference_pct = difference / avg_value if avg_value != 0 else 0
        
        # 判断一致性级别
        if difference_pct <= rule['tolerance'] and difference <= rule['absolute_tolerance']:
            # 完全一致
            return {
                'is_consistent': True,
                'confidence': 'high',
                'difference': difference,
                'difference_pct': difference_pct,
                'recommended_value': round(avg_value, 2),
                'message': f"数据一致（差异{difference_pct:.2%}）",
            }
        elif difference_pct <= rule['tolerance'] * 2:
            # 轻微差异
            return {
                'is_consistent': True,
                'confidence': 'medium',
                'difference': difference,
                'difference_pct': difference_pct,
                'recommended_value': round(avg_value, 2),
                'message': f"数据轻微差异（差异{difference_pct:.2%}）",
            }
        else:
            # 明显差异
            return {
                'is_consistent': False,
                'confidence': 'low',
                'difference': difference,
                'difference_pct': difference_pct,
                'recommended_value': None,  # 需要进一步验证
                'message': f"数据明显差异（差异{difference_pct:.2%}）",
            }
    
    # 只有一个数据源有值
    elif value_a is not None:
        return {
            'is_consistent': None,  # 无法验证
            'confidence': 'low',
            'difference': None,
            'difference_pct': None,
            'recommended_value': value_a,
            'message': "只有一个数据源，未验证",
        }
    elif value_b is not None:
        return {
            'is_consistent': None,
            'confidence': 'low',
            'difference': None,
            'difference_pct': None,
            'recommended_value': value_b,
            'message': "只有一个数据源，未验证",
        }
    
    # 两个数据源都没有值
    else:
        return {
            'is_consistent': None,
            'confidence': 'none',
            'difference': None,
            'difference_pct': None,
            'recommended_value': None,
            'message': "两个数据源都无数据",
        }
```

---

## 二、数据源注册方案

### 2.1 可用数据源矩阵

| 字段 | 数据源A（主） | 数据源B（副） | 数据源C（备选） |
|------|-------------|-------------|--------------|
| **ROE** | akshare.stock_yjbb_em | 东方财富财务指标 | 计算方法 |
| **EPS** | akshare.stock_yjbb_em | 东方财富RPT_LICO_FN_CPD | Tushare |
| **支付率** | akshare.stock_fhps_em | 计算：每股股利/EPS | 东方财富分红 |
| **负债率** | akshare.stock_financial_analysis_indicator | akshare资产负债表 | 计算：负债/资产 |
| **股息率** | akshare.stock_a_lg_indicator | 计算：年股利/股价 | 聚宽 |
| **市值** | akshare.stock_zh_a_spot_em | 计算：股价×股本 | 东方财富 |
| **股价** | akshare.stock_zh_a_spot_em | Tushare | 东方财富 |
| **波动率** | akshare历史数据计算 | Tushare | 估算方法 |

### 2.2 数据源实现

```python
# data_sources.py

class DataSourceRegistry:
    """数据源注册表"""
    
    def __init__(self):
        self.sources = {}
        
    def register(self, field_name, source_name, fetch_func, priority=1):
        """注册数据源"""
        if field_name not in self.sources:
            self.sources[field_name] = []
        
        self.sources[field_name].append({
            'name': source_name,
            'fetch': fetch_func,
            'priority': priority,
            'stats': {
                'success_count': 0,
                'fail_count': 0,
                'avg_response_time': 0,
            }
        })
        
        # 按优先级排序
        self.sources[field_name].sort(key=lambda x: x['priority'], reverse=True)

# 注册数据源
registry = DataSourceRegistry()

# ROE数据源
registry.register('roe', 'akshare_yjbb', 
                  fetch_func=fetch_roe_from_akshare_yjbb, 
                  priority=10)
registry.register('roe', 'eastmoney_financial', 
                  fetch_func=fetch_roe_from_eastmoney, 
                  priority=5)

# EPS数据源
registry.register('eps', 'akshare_yjbb', 
                  fetch_func=fetch_eps_from_akshare_yjbb, 
                  priority=10)
registry.register('eps', 'eastmoney_cpd', 
                  fetch_func=fetch_eps_from_eastmoney_cpd, 
                  priority=5)

# 支付率数据源
registry.register('payout_ratio', 'akshare_fhps', 
                  fetch_func=fetch_payout_from_akshare_fhps, 
                  priority=10)
registry.register('payout_ratio', 'calculate', 
                  fetch_func=calculate_payout_ratio, 
                  priority=5)

# 负债率数据源
registry.register('debt_ratio', 'akshare_financial_indicator', 
                  fetch_func=fetch_debt_from_akshare_indicator, 
                  priority=10)
registry.register('debt_ratio', 'akshare_balance_sheet', 
                  fetch_func=fetch_debt_from_balance_sheet, 
                  priority=5)
```

---

## 三、双重验证框架

### 3.1 核心验证类

```python
class DualDataValidator:
    """双重数据验证器"""
    
    def __init__(self, registry):
        self.registry = registry
        self.validation_log = []
        self.alerts = []
        
    def validate_field(self, field_name, code, context=None):
        """
        验证单个字段的数据
        
        步骤：
        1. 从两个数据源获取数据
        2. 检查一致性
        3. 返回验证结果和推荐值
        """
        print(f"\n验证字段 {field_name} ({code})...")
        
        # 获取该字段的所有数据源
        sources = self.registry.sources.get(field_name, [])
        
        if len(sources) < 2:
            print(f"  ⚠️ 只有 {len(sources)} 个数据源，无法进行双重验证")
            # 只有一个数据源，获取数据但标记为未验证
            if len(sources) == 1:
                value = self._fetch_from_source(sources[0], code, context)
                return self._create_result(
                    field_name=field_name,
                    value=value,
                    confidence='low',
                    message='单一数据源，未验证',
                    sources=[sources[0]['name']]
                )
            else:
                return self._create_result(
                    field_name=field_name,
                    value=None,
                    confidence='none',
                    message='无可用数据源',
                    sources=[]
                )
        
        # 从两个数据源获取数据
        source_a = sources[0]  # 主数据源
        source_b = sources[1]  # 副数据源
        
        value_a = self._fetch_from_source(source_a, code, context)
        value_b = self._fetch_from_source(source_b, code, context)
        
        # 一致性检查
        consistency = check_consistency(value_a, value_b, field_name)
        
        # 记录验证日志
        log_entry = {
            'timestamp': datetime.now(),
            'field': field_name,
            'code': code,
            'source_a': source_a['name'],
            'value_a': value_a,
            'source_b': source_b['name'],
            'value_b': value_b,
            'consistency': consistency,
        }
        self.validation_log.append(log_entry)
        
        # 创建告警（如果需要）
        if consistency['confidence'] == 'low':
            self._create_alert(field_name, code, consistency)
        
        # 返回结果
        return self._create_result(
            field_name=field_name,
            value=consistency['recommended_value'],
            confidence=consistency['confidence'],
            message=consistency['message'],
            sources=[source_a['name'], source_b['name']],
            raw_values={
                source_a['name']: value_a,
                source_b['name']: value_b,
            },
            consistency=consistency,
        )
    
    def _fetch_from_source(self, source, code, context):
        """从数据源获取数据"""
        import time
        start = time.time()
        
        try:
            value = source['fetch'](code, context)
            elapsed = time.time() - start
            
            # 更新统计
            source['stats']['success_count'] += 1
            source['stats']['avg_response_time'] = (
                source['stats']['avg_response_time'] * 0.9 + elapsed * 0.1
            )
            
            print(f"  ✓ {source['name']}: {value} (耗时{elapsed:.2f}s)")
            return value
            
        except Exception as e:
            source['stats']['fail_count'] += 1
            print(f"  ✗ {source['name']}: 失败 - {e}")
            return None
    
    def _create_result(self, field_name, value, confidence, message, 
                      sources, raw_values=None, consistency=None):
        """创建验证结果"""
        return {
            'field': field_name,
            'value': value,
            'confidence': confidence,
            'message': message,
            'sources': sources,
            'raw_values': raw_values,
            'consistency': consistency,
            'timestamp': datetime.now().isoformat(),
        }
    
    def _create_alert(self, field_name, code, consistency):
        """创建告警"""
        alert = {
            'level': 'warning',
            'field': field_name,
            'code': code,
            'message': consistency['message'],
            'difference': consistency['difference'],
            'difference_pct': consistency['difference_pct'],
            'timestamp': datetime.now(),
        }
        self.alerts.append(alert)
        print(f"  ⚠️ 告警: {alert['message']}")
    
    def validate_all_fields(self, code, fields, context=None):
        """验证所有字段"""
        results = {}
        
        for field in fields:
            results[field] = self.validate_field(field, code, context)
        
        return results
    
    def get_validation_report(self):
        """获取验证报告"""
        # 按可信度分组
        by_confidence = {'high': 0, 'medium': 0, 'low': 0, 'none': 0}
        for log in self.validation_log:
            confidence = log['consistency']['confidence']
            by_confidence[confidence] = by_confidence.get(confidence, 0) + 1
        
        return {
            'total_validations': len(self.validation_log),
            'by_confidence': by_confidence,
            'alerts_count': len(self.alerts),
            'recent_alerts': self.alerts[-10:],
            'validation_log': self.validation_log[-20:],
        }
```

### 3.2 批量验证

```python
class BatchDualValidator:
    """批量双重验证器"""
    
    def __init__(self, dual_validator):
        self.validator = dual_validator
        
    def validate_batch(self, codes, fields, context=None):
        """批量验证多只股票的多个字段"""
        all_results = {}
        
        total = len(codes) * len(fields)
        current = 0
        
        for code in codes:
            all_results[code] = {}
            
            for field in fields:
                current += 1
                print(f"\n[{current}/{total}] 验证 {code} - {field}")
                
                result = self.validator.validate_field(field, code, context)
                all_results[code][field] = result
                
                # 延迟，避免请求过快
                import time
                time.sleep(0.3)
        
        return all_results
    
    def generate_quality_report(self, results):
        """生成数据质量报告"""
        report = {
            'total_stocks': len(results),
            'total_fields': 0,
            'by_confidence': {'high': 0, 'medium': 0, 'low': 0, 'none': 0},
            'by_field': {},
            'problematic_data': [],
        }
        
        for code, fields in results.items():
            for field_name, result in fields.items():
                report['total_fields'] += 1
                
                # 按可信度统计
                confidence = result['confidence']
                report['by_confidence'][confidence] += 1
                
                # 按字段统计
                if field_name not in report['by_field']:
                    report['by_field'][field_name] = {
                        'high': 0, 'medium': 0, 'low': 0, 'none': 0
                    }
                report['by_field'][field_name][confidence] += 1
                
                # 记录问题数据
                if confidence in ['low', 'none']:
                    report['problematic_data'].append({
                        'code': code,
                        'field': field_name,
                        'message': result['message'],
                    })
        
        return report
```

---

## 四、实际应用示例

### 4.1 在当前项目中应用

```python
# 创建数据源注册表
registry = DataSourceRegistry()

# 注册ROE数据源
def fetch_roe_from_akshare_yjbb(code, context):
    """从akshare yjbb获取ROE"""
    df = context.get('eps_df')  # 已获取的EPS数据
    if df is not None and code in df['code'].values:
        return df[df['code'] == code]['roe'].values[0]
    return None

def fetch_roe_from_eastmoney_financial(code, context):
    """从东方财富财务指标获取ROE"""
    import akshare as ak
    try:
        df = ak.stock_financial_analysis_indicator(symbol=code)
        if df is not None and not df.empty:
            # 获取最新的ROE
            latest = df[df['加权净资产收益率(%)'].notna()].iloc[0]
            return latest['加权净资产收益率(%)']
    except:
        pass
    return None

# 注册
registry.register('roe', 'akshare_yjbb', fetch_roe_from_akshare_yjbb, priority=10)
registry.register('roe', 'eastmoney_financial', fetch_roe_from_eastmoney_financial, priority=5)

# 注册EPS数据源
def fetch_eps_from_akshare_yjbb(code, context):
    """从akshare yjbb获取EPS"""
    df = context.get('eps_df')
    if df is not None and code in df['code'].values:
        return df[df['code'] == code]['basic_eps'].values[0]
    return None

def fetch_eps_from_eastmoney_cpd(code, context):
    """从东方财富CPD获取EPS"""
    # 实现获取逻辑
    pass

registry.register('eps', 'akshare_yjbb', fetch_eps_from_akshare_yjbb, priority=10)
registry.register('eps', 'eastmoney_cpd', fetch_eps_from_eastmoney_cpd, priority=5)

# 创建验证器
validator = DualDataValidator(registry)

# 验证单只股票
result = validator.validate_field('roe', '601939', context={'eps_df': eps_df})

print(f"字段: {result['field']}")
print(f"推荐值: {result['value']}")
print(f"可信度: {result['confidence']}")
print(f"消息: {result['message']}")
print(f"数据源: {result['sources']}")
print(f"原始值: {result['raw_values']}")
```

### 4.2 集成到数据流程中

```python
def merge_all_data_with_validation():
    """带双重验证的数据合并流程"""
    
    print("步骤1/9: 获取全A股实时行情...")
    # ... 获取行情数据
    
    print("步骤2/9: 获取EPS和ROE数据（从数据源A）...")
    eps_df_a = fetch_eps_batch_from_akshare()  # 数据源A
    
    print("步骤3/9: 获取EPS和ROE数据（从数据源B）...")
    eps_df_b = fetch_eps_batch_from_eastmoney()  # 数据源B
    
    print("步骤4/9: 数据交叉验证...")
    validator = DualDataValidator(registry)
    
    # 对每只股票进行验证
    validated_data = []
    for code in candidate_codes:
        result = validator.validate_field('roe', code, 
                                         context={'eps_df_a': eps_df_a, 
                                                 'eps_df_b': eps_df_b})
        
        if result['confidence'] in ['high', 'medium']:
            # 使用验证通过的数据
            validated_data.append({
                'code': code,
                'roe': result['value'],
                'roe_confidence': result['confidence'],
                'roe_sources': result['sources'],
            })
        else:
            # 低可信度或数据冲突
            print(f"  ⚠️ {code} ROE数据可信度低: {result['message']}")
            validated_data.append({
                'code': code,
                'roe': result['value'],
                'roe_confidence': result['confidence'],
                'roe_sources': result['sources'],
            })
    
    print("步骤5/9: 生成验证报告...")
    report = validator.get_validation_report()
    print(f"  总验证次数: {report['total_validations']}")
    print(f"  高可信度: {report['by_confidence']['high']}")
    print(f"  中可信度: {report['by_confidence']['medium']}")
    print(f"  低可信度: {report['by_confidence']['low']}")
    print(f"  无数据: {report['by_confidence']['none']}")
    
    # 继续后续步骤...
    
    return validated_data
```

---

## 五、用户界面展示

### 5.1 数据质量标识

在前端展示数据时，添加质量标识：

```
代码: 601939
名称: 建设银行
ROE: 10.69% ✓ (高可信度)
     └─ 数据源: akshare yjbb, 东方财富财务
     └─ 差异: 0.02%

支付率: 15.73% ⚠️ (中可信度)
       └─ 数据源: akshare fhps, 计算方法
       └─ 差异: 1.2%

负债率: N/A ⚠️ (低可信度)
       └─ 消息: 单一数据源，未验证
```

### 5.2 数据质量评分

为每只股票生成综合质量评分：

```python
def calculate_data_quality_score(validation_results):
    """计算数据质量评分"""
    total_fields = len(validation_results)
    
    if total_fields == 0:
        return 0
    
    # 权重
    weights = {
        'high': 1.0,
        'medium': 0.7,
        'low': 0.3,
        'none': 0.0,
    }
    
    # 计算加权分数
    score = 0
    for field, result in validation_results.items():
        confidence = result['confidence']
        score += weights[confidence]
    
    # 归一化到0-100
    final_score = (score / total_fields) * 100
    
    return round(final_score, 1)

# 示例
quality_score = calculate_data_quality_score(results)
print(f"数据质量评分: {quality_score}/100")

if quality_score >= 80:
    print("✓ 数据质量优秀")
elif quality_score >= 60:
    print("⚠️ 数据质量良好")
else:
    print("✗ 数据质量较差")
```

---

## 六、监控和告警

### 6.1 实时监控面板

```
┌─────────────────────────────────────┐
│     数据质量监控面板                │
├─────────────────────────────────────┤
│ 总验证次数: 5202                    │
│ 高可信度: 4980 (95.7%) ████████████ │
│ 中可信度: 180 (3.5%)   █            │
│ 低可信度: 40 (0.8%)    ▌            │
│ 无数据:   2 (0.0%)                  │
├─────────────────────────────────────┤
│ 数据源健康状态:                     │
│ akshare yjbb:    ✓ 正常 (99.8%)     │
│ eastmoney cpd:   ✓ 正常 (98.2%)     │
│ akshare fhps:    ✓ 正常 (99.4%)     │
├─────────────────────────────────────┤
│ 最近告警:                           │
│ ⚠️ 600036 ROE数据差异 6.2%          │
│ ⚠️ 601318 支付率单一数据源          │
└─────────────────────────────────────┘
```

### 6.2 告警规则

```python
ALERT_RULES = [
    {
        'name': '数据冲突',
        'condition': lambda r: r['consistency']['is_consistent'] == False,
        'level': 'warning',
        'message': '数据源之间差异过大',
        'action': '标记并触发人工审核',
    },
    {
        'name': '单一数据源',
        'condition': lambda r: len(r['sources']) == 1,
        'level': 'info',
        'message': '只有一个数据源，未验证',
        'action': '记录并尝试获取第二数据源',
    },
    {
        'name': '数据缺失',
        'condition': lambda r: r['value'] is None,
        'level': 'warning',
        'message': '数据缺失',
        'action': '优雅降级',
    },
    {
        'name': '数据质量下降',
        'condition': lambda r: r['confidence'] == 'low',
        'level': 'info',
        'message': '数据可信度低',
        'action': '标记并监控',
    },
]
```

---

## 七、实施路线图

### Phase 1: 基础验证框架（1周）

- [x] 设计验证规则
- [ ] 实现DualDataValidator类
- [ ] 注册至少2个数据源
- [ ] 基础一致性检查

### Phase 2: 集成到现有流程（1周）

- [ ] 修改merge_all_data函数
- [ ] 添加数据质量标记
- [ ] 生成验证报告
- [ ] 前端展示质量标识

### Phase 3: 监控和优化（持续）

- [ ] 建立监控面板
- [ ] 设置告警规则
- [ ] 定期审查数据质量
- [ ] 优化验证算法

---

## 八、成本效益分析

### 成本

1. **开发成本**
   - 双重验证框架：3天
   - 数据源集成：2天
   - 监控系统：2天
   - 总计：约1周

2. **运行成本**
   - 双倍API调用
   - 额外计算资源
   - 存储验证日志

### 收益

1. **数据可靠性提升**
   - 从60%提升到95%+
   - 减少错误数据导致的决策失误

2. **用户体验改善**
   - 数据质量透明
   - 问题及时发现

3. **维护成本降低**
   - 自动发现问题
   - 减少用户投诉

### 结论

**投入产出比：高**

- 一次性投入约1周开发时间
- 长期收益显著
- 数据质量是核心价值，值得投入

---

## 九、最佳实践总结

1. ✅ **至少两个数据源**
   - 主数据源 + 副数据源
   - 互为备份

2. ✅ **交叉验证**
   - 比对数据一致性
   - 计算差异度和可信度

3. ✅ **质量透明**
   - 向用户展示数据质量
   - 低质量数据明确标记

4. ✅ **监控告警**
   - 实时监控数据质量
   - 及时发现问题

5. ✅ **优雅降级**
   - 数据冲突时有备选方案
   - 系统保持可用

---

**核心原则：**

> **"数据质量是生命线，必须通过双重验证确保可靠性"**
