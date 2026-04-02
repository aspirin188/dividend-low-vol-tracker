# 红利低波跟踪系统 — 产品需求文档 (PRD)

## 极简版

| 项目 | 信息 |
|------|------|
| 产品名称 | 红利低波跟踪系统 |
| 版本 | v6.20 |
| 版本类型 | **极简版** |
| 最后更新 | 2026-03-29 |
| 文档状态 | 功能完善版 |
| 设计理念 | 第一性原理 + 乔布斯极简原则 |

### v6.19 → v6.20 修订记录

| 修订项 | 内容 | 原因 |
|--------|------|------|
| **参数化配置系统** | 将硬编码的筛选参数改为可配置 | 用户需要动态调整股票池规模和策略 |
| **配置管理页面** | 独立的配置管理界面 | 提供友好的参数调整体验 |
| **配置自动生效** | 修改配置后自动重新运行 | 无需手动操作，即刻看到效果 |
| **参数分类分级** | A类筛选/B类风控/C类权重 | 结构清晰，便于理解 |

---

## v6.20 参数化配置系统

### 一、需求背景

#### 1.1 痛点分析

当前系统存在以下问题：

| 问题 | 影响 |
|------|------|
| 参数硬编码在代码中 | 修改参数需要改代码、重启服务 |
| 股票池规模固定（约30只） | 无法根据市场情况灵活调整 |
| 筛选策略不可变 | 无法探索不同投资风格 |
| 缺乏参数说明 | 新用户不了解参数含义 |

#### 1.2 目标

- **参数可视化**：所有筛选参数一目了然
- **配置灵活化**：用户可自由调整参数
- **效果即时化**：修改配置后立即看到结果
- **默认安全化**：提供合理的默认值，防止异常

---

### 二、配置参数设计

#### 2.1 A类：核心筛选参数（高频调整）

| 参数键 | 参数名 | 默认值 | 范围 | 单位 | 说明 |
|--------|--------|--------|------|------|------|
| `MIN_DIVIDEND_YIELD` | 股息率下限 | 3.0 | 1.0-10.0 | % | 筛选高股息股票的最低门槛。默认3%符合红利低波策略的基本要求。建议值：激进型2.0%，稳健型3.0%，保守型4.0% |
| `MIN_MARKET_CAP` | 市值下限 | 500 | 100-2000 | 亿元 | 筛选大盘股，确保流动性。默认500亿排除中小市值股票。建议值：大盘型800，均衡型500，宽泛型300 |
| `MIN_ROE` | ROE下限 | 8.0 | 0-30.0 | % | 筛选盈利能力强的公司。默认8%过滤掉盈利能力差的公司。建议值：优选型10%，均衡型8%，宽泛型6% |
| `MIN_DIVIDEND_YEARS` | 分红年数下限 | 3 | 1-10 | 年 | 筛选分红稳定公司。默认3年确保公司有持续分红意愿。建议值：严格型5年，均衡型3年，宽泛型2年 |

**预估影响**：
- 全部使用默认值：股票池约30只
- 调整为激进参数（股息率2%/市值300/ROE6%/年数2）：股票池约80-100只
- 调整为保守参数（股息率4%/市值800/ROE10%/年数5）：股票池约15-20只

#### 2.2 B类：风控参数（中频调整）

| 参数键 | 参数名 | 默认值 | 范围 | 单位 | 说明 |
|--------|--------|--------|------|------|------|
| `MAX_PAYOUT_RATIO` | 股利支付率上限 | 150 | 50-300 | % | 防止分红不可持续。默认150%过滤掉过度分红的公司。过高可能透支未来分红能力 |
| `MAX_DIVIDEND_YIELD` | 股息率上限 | 30.0 | 10-50 | % | 过滤异常数据。默认30%排除数据异常或即将退市的股票。超过此值通常是陷阱 |
| `MAX_DEBT_RATIO` | 资产负债率上限 | 70 | 30-100 | % | 控制财务风险（非金融地产）。默认70%过滤高负债公司。建议值：保守型60%，均衡型70%，宽泛型80% |
| `MAX_DEBT_RATIO_FINANCE` | 资产负债率上限(金融) | 85 | 50-100 | % | 金融地产行业特殊处理。默认85%适应银行业高负债特点 |

#### 2.3 C类：评分权重参数（低频调整）

| 参数键 | 参数名 | 默认值 | 范围 | 单位 | 说明 |
|--------|--------|--------|------|------|------|
| `WEIGHT_DIVIDEND` | 股息率权重 | 0.5 | 0-1.0 | - | 股息率因子在评分中的权重。默认0.5强调分红收益。提高权重更重视股息率 |
| `WEIGHT_VOL` | 波动率权重 | 0.3 | 0-1.0 | - | 波动率因子在评分中的权重。默认0.3强调低波动。提高权重更重视稳定性 |
| `WEIGHT_STABILITY` | 分红稳定性权重 | 0.2 | 0-1.0 | - | 分红稳定性因子在评分中的权重。默认0.2作为辅助因子。提高权重更重视持续分红能力 |

**约束条件**：三个权重之和必须等于1.0

**权重调整建议**：
- 收益优先型：股息率0.6 + 波动率0.2 + 稳定性0.2
- 稳健型：股息率0.4 + 波动率0.4 + 稳定性0.2
- 均衡型：股息率0.5 + 波动率0.3 + 稳定性0.2（默认）

---

### 三、数据库设计

#### 3.1 系统配置表

```sql
CREATE TABLE system_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key VARCHAR(50) UNIQUE NOT NULL,    -- 参数键名
    config_value VARCHAR(100) NOT NULL,         -- 参数值
    config_type VARCHAR(20) NOT NULL,           -- 参数类型：float/int
    category VARCHAR(20) NOT NULL,              -- 分类：A筛选/B风控/C权重
    description TEXT NOT NULL,                  -- 参数说明
    default_value VARCHAR(100) NOT NULL,        -- 默认值
    min_value VARCHAR(50),                      -- 最小值
    max_value VARCHAR(50),                      -- 最大值
    unit VARCHAR(20),                           -- 单位：%、亿元、年等
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3.2 初始数据

```sql
-- A类：核心筛选参数
INSERT INTO system_config (config_key, config_value, config_type, category, description, default_value, min_value, max_value, unit) VALUES
('MIN_DIVIDEND_YIELD', '3.0', 'float', 'A筛选', '筛选高股息股票的最低门槛。默认3%符合红利低波策略的基本要求。建议值：激进型2.0%，稳健型3.0%，保守型4.0%', '3.0', '1.0', '10.0', '%'),
('MIN_MARKET_CAP', '500', 'float', 'A筛选', '筛选大盘股，确保流动性。默认500亿排除中小市值股票。建议值：大盘型800，均衡型500，宽泛型300', '500', '100', '2000', '亿元'),
('MIN_ROE', '8.0', 'float', 'A筛选', '筛选盈利能力强的公司。默认8%过滤掉盈利能力差的公司。建议值：优选型10%，均衡型8%，宽泛型6%', '8.0', '0', '30.0', '%'),
('MIN_DIVIDEND_YEARS', '3', 'int', 'A筛选', '筛选分红稳定公司。默认3年确保公司有持续分红意愿。建议值：严格型5年，均衡型3年，宽泛型2年', '3', '1', '10', '年');

-- B类：风控参数
INSERT INTO system_config (config_key, config_value, config_type, category, description, default_value, min_value, max_value, unit) VALUES
('MAX_PAYOUT_RATIO', '150', 'float', 'B风控', '防止分红不可持续。默认150%过滤掉过度分红的公司。过高可能透支未来分红能力', '150', '50', '300', '%'),
('MAX_DIVIDEND_YIELD', '30.0', 'float', 'B风控', '过滤异常数据。默认30%排除数据异常或即将退市的股票。超过此值通常是陷阱', '30.0', '10', '50', '%'),
('MAX_DEBT_RATIO', '70', 'float', 'B风控', '控制财务风险（非金融地产）。默认70%过滤高负债公司。建议值：保守型60%，均衡型70%，宽泛型80%', '70', '30', '100', '%'),
('MAX_DEBT_RATIO_FINANCE', '85', 'float', 'B风控', '金融地产行业特殊处理。默认85%适应银行业高负债特点', '85', '50', '100', '%');

-- C类：评分权重参数
INSERT INTO system_config (config_key, config_value, config_type, category, description, default_value, min_value, max_value, unit) VALUES
('WEIGHT_DIVIDEND', '0.5', 'float', 'C权重', '股息率因子在评分中的权重。默认0.5强调分红收益。提高权重更重视股息率', '0.5', '0', '1.0', '-'),
('WEIGHT_VOL', '0.3', 'float', 'C权重', '波动率因子在评分中的权重。默认0.3强调低波动。提高权重更重视稳定性', '0.3', '0', '1.0', '-'),
('WEIGHT_STABILITY', '0.2', 'float', 'C权重', '分红稳定性因子在评分中的权重。默认0.2作为辅助因子。提高权重更重视持续分红能力', '0.2', '0', '1.0', '-');
```

---

### 四、后端API设计

#### 4.1 获取所有配置

```python
GET /api/config

Response:
{
    "success": true,
    "data": {
        "A筛选": [
            {
                "config_key": "MIN_DIVIDEND_YIELD",
                "config_value": "3.0",
                "config_type": "float",
                "description": "筛选高股息股票的最低门槛...",
                "default_value": "3.0",
                "min_value": "1.0",
                "max_value": "10.0",
                "unit": "%"
            },
            ...
        ],
        "B风控": [...],
        "C权重": [...]
    }
}
```

#### 4.2 更新单个配置

```python
PUT /api/config/<config_key>
Body: {"value": "2.5"}

Response:
{
    "success": true,
    "message": "配置已更新",
    "trigger_rerun": true  # 提示前端需要重新运行
}
```

#### 4.3 批量更新配置

```python
PUT /api/config/batch
Body: {
    "configs": {
        "MIN_DIVIDEND_YIELD": "2.5",
        "MIN_MARKET_CAP": "300",
        "MIN_ROE": "6.0"
    }
}

Response:
{
    "success": true,
    "updated_count": 3,
    "message": "配置已更新，正在重新运行..."
}
```

#### 4.4 恢复默认值

```python
POST /api/config/reset
Body: {"category": "A筛选"}  # 或 {"all": true}

Response:
{
    "success": true,
    "message": "已恢复默认值",
    "reset_count": 4
}
```

#### 4.5 预览效果（不保存）

```python
POST /api/config/preview
Body: {
    "MIN_DIVIDEND_YIELD": "2.5",
    "MIN_MARKET_CAP": "300"
}

Response:
{
    "success": true,
    "current_pool_size": 30,
    "preview_pool_size": 85,
    "change": "+55只",
    "message": "预计股票池将从30只增加到85只"
}
```

---

### 五、前端界面设计

#### 5.1 配置页面布局

```
┌─────────────────────────────────────────────────────────────────┐
│  ⚙️ 系统配置                           [预览效果] [恢复默认]     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📊 筛选参数 (A类)                                               │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  股息率下限     [  3.0  ] %     范围: 1.0-10.0%           │ │
│  │  └ 筛选高股息股票的最低门槛。默认3%符合红利低波策略要求。   │ │
│  │                                                             │ │
│  │  市值下限       [ 500  ] 亿元  范围: 100-2000亿元          │ │
│  │  └ 筛选大盘股，确保流动性。默认500亿排除中小市值股票。      │ │
│  │                                                             │ │
│  │  ROE下限        [  8.0  ] %     范围: 0-30.0%             │ │
│  │  └ 筛选盈利能力强的公司。默认8%过滤掉盈利能力差的公司。     │ │
│  │                                                             │ │
│  │  分红年数下限   [  3   ] 年    范围: 1-10年               │ │
│  │  └ 筛选分红稳定公司。默认3年确保公司有持续分红意愿。        │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  🛡️ 风控参数 (B类)                                               │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  股利支付率上限     [ 150 ] %    范围: 50-300%            │ │
│  │  └ 防止分红不可持续。默认150%过滤过度分红的公司。           │ │
│  │                                                             │ │
│  │  股息率上限         [ 30.0 ] %   范围: 10-50%             │ │
│  │  └ 过滤异常数据。超过此值通常是陷阱。                       │ │
│  │                                                             │ │
│  │  负债率上限         [  70 ] %    范围: 30-100%            │ │
│  │  └ 控制财务风险（非金融地产）。默认70%过滤高负债公司。      │ │
│  │                                                             │ │
│  │  负债率上限(金融)   [  85 ] %    范围: 50-100%            │ │
│  │  └ 金融地产行业特殊处理。适应银行业高负债特点。             │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ⚖️ 评分权重 (C类)                        [权重和: 1.0 ✓]       │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  股息率权重     [ 0.5 ]      范围: 0-1.0                  │ │
│  │  └ 股息率因子在评分中的权重。默认0.5强调分红收益。          │ │
│  │                                                             │ │
│  │  波动率权重     [ 0.3 ]      范围: 0-1.0                  │ │
│  │  └ 波动率因子在评分中的权重。默认0.3强调低波动。            │ │
│  │                                                             │ │
│  │  稳定性权重     [ 0.2 ]      范围: 0-1.0                  │ │
│  │  └ 分红稳定性因子在评分中的权重。默认0.2作为辅助因子。      │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  💡 提示：修改配置后将自动重新运行，更新股票池                   │
│                                                                 │
│                          [保存配置]                             │
└─────────────────────────────────────────────────────────────────┘
```

#### 5.2 配置说明样式

- **参数名**：加粗显示，简洁明了
- **输入框**：数字输入，带范围限制
- **单位**：右侧灰色显示（%、亿元、年等）
- **说明文字**：浅色字体，缩进显示，详细解释参数用途和默认值含义
- **建议值**：在说明中给出激进型/均衡型/保守型的建议值

#### 5.3 交互逻辑

1. **实时验证**：
   - 输入值超出范围时显示警告
   - 权重和不等于1.0时显示错误提示

2. **预览功能**：
   - 点击"预览效果"按钮
   - 显示预计股票池变化（增加/减少多少只）
   - 不保存配置，只做模拟计算

3. **保存并运行**：
   - 点击"保存配置"按钮
   - 后端保存配置到数据库
   - 自动触发重新运行
   - 前端跳转到主页并刷新数据

4. **恢复默认**：
   - 点击"恢复默认"按钮
   - 弹出确认对话框
   - 确认后恢复所有配置为默认值
   - 自动触发重新运行

---

### 六、代码改造方案

#### 6.1 新增配置服务模块

```python
# server/services/config_service.py

class ConfigService:
    """配置管理服务"""
    
    _instance = None
    
    def __init__(self, db_path):
        self.db_path = db_path
        self._cache = {}  # 内存缓存
        self._load_cache()
    
    @classmethod
    def get_instance(cls):
        """单例模式"""
        if cls._instance is None:
            from flask import current_app
            db_path = os.path.join(current_app.instance_path, 'tracker.db')
            cls._instance = cls(db_path)
        return cls._instance
    
    def _load_cache(self):
        """启动时加载所有配置到内存"""
        
    def get(self, key: str) -> str:
        """获取配置值"""
        
    def get_float(self, key: str) -> float:
        """获取浮点型配置值"""
        
    def get_int(self, key: str) -> int:
        """获取整型配置值"""
        
    def get_all(self) -> dict:
        """获取所有配置，按分类组织"""
        
    def update(self, key: str, value: str) -> tuple:
        """更新配置值，返回(成功, 消息)"""
        
    def batch_update(self, configs: dict) -> tuple:
        """批量更新配置"""
        
    def reset_to_default(self, category: str = None) -> int:
        """恢复默认值，返回重置数量"""
        
    def validate(self, key: str, value: str) -> tuple:
        """校验参数值是否合法"""
```

#### 6.2 改造 scorer.py

```python
# 当前：硬编码常量
MIN_DIVIDEND_YIELD = 3.0
MIN_MARKET_CAP = 500.0

# 改造后：从配置服务读取
from server.services.config_service import ConfigService

def filter_stocks(df: pd.DataFrame, config: ConfigService = None) -> pd.DataFrame:
    """硬性筛选：使用配置参数"""
    if config is None:
        config = ConfigService.get_instance()
    
    # 从配置服务获取参数
    MIN_DIVIDEND_YIELD = config.get_float('MIN_DIVIDEND_YIELD')
    MIN_MARKET_CAP = config.get_float('MIN_MARKET_CAP')
    MIN_ROE = config.get_float('MIN_ROE')
    MIN_DIVIDEND_YEARS = config.get_int('MIN_DIVIDEND_YEARS')
    MAX_PAYOUT_RATIO = config.get_float('MAX_PAYOUT_RATIO')
    MAX_DIVIDEND_YIELD = config.get_float('MAX_DIVIDEND_YIELD')
    # ...
    
    # 筛选逻辑保持不变
```

```python
# 当前：硬编码权重
WEIGHT_DIVIDEND = 0.5
WEIGHT_VOL = 0.3
WEIGHT_STABILITY = 0.2

# 改造后：从配置服务读取
def calculate_scores(df: pd.DataFrame, config: ConfigService = None) -> pd.DataFrame:
    """三因子评分：使用配置权重"""
    if config is None:
        config = ConfigService.get_instance()
    
    WEIGHT_DIVIDEND = config.get_float('WEIGHT_DIVIDEND')
    WEIGHT_VOL = config.get_float('WEIGHT_VOL')
    WEIGHT_STABILITY = config.get_float('WEIGHT_STABILITY')
    
    # 评分逻辑保持不变
```

#### 6.3 新增配置页面路由

```python
# server/routes.py

# 配置页面
@bp.route('/config')
def config_page():
    """配置管理页面"""
    return render_template('config.html')

# 获取所有配置
@bp.route('/api/config', methods=['GET'])
def get_config():
    """获取所有配置"""

# 更新配置
@bp.route('/api/config/<config_key>', methods=['PUT'])
def update_config(config_key):
    """更新单个配置"""

# 批量更新配置
@bp.route('/api/config/batch', methods=['PUT'])
def batch_update_config():
    """批量更新配置"""

# 恢复默认值
@bp.route('/api/config/reset', methods=['POST'])
def reset_config():
    """恢复默认值"""
```

---

### 七、实施计划

#### Phase 1: 数据库与配置服务（1小时）

1. 创建 `system_config` 表
2. 插入初始配置数据
3. 实现 `ConfigService` 服务类
4. 实现内存缓存机制

#### Phase 2: 后端API（1小时）

1. 实现配置查询接口
2. 实现配置更新接口
3. 实现批量更新接口
4. 实现恢复默认接口
5. 实现预览功能（可选）

#### Phase 3: 改造筛选逻辑（0.5小时）

1. 改造 `filter_stocks()` 使用配置
2. 改造 `calculate_scores()` 使用配置
3. 测试筛选功能

#### Phase 4: 前端界面（1.5小时）

1. 创建配置页面模板
2. 实现配置表单交互
3. 实现保存并自动运行
4. 实现恢复默认功能
5. 添加导航入口

---

### 八、测试计划

#### 8.1 功能测试

| 测试项 | 预期结果 | 状态 |
|--------|----------|------|
| 查看配置页面 | 显示所有配置项，分类清晰 | - |
| 修改单个参数 | 保存成功，提示重新运行 | - |
| 批量修改参数 | 全部保存成功，自动运行 | - |
| 输入超出范围 | 显示错误提示，阻止保存 | - |
| 权重和不等于1.0 | 显示错误提示，阻止保存 | - |
| 恢复默认值 | 所有配置恢复默认，自动运行 | - |
| 运行结果正确 | 使用新参数筛选，股票池变化符合预期 | - |

#### 8.2 边界测试

| 测试项 | 预期结果 |
|--------|----------|
| 股息率下限设为1.0% | 股票池显著增加 |
| 股息率下限设为10.0% | 股票池极少或为空 |
| 市值下限设为100亿 | 股票池增加 |
| 市值下限设为2000亿 | 股票池极少 |
| 权重设为极端值（1.0, 0, 0） | 评分按单因子排序 |

---

### 九、版本历史

| 版本 | 日期 | 主要更新 |
|------|------|---------|
| v6.20 | 2026-03-29 | 参数化配置系统、配置管理页面、配置自动生效 |
| v6.19 | 2026-03-29 | 前端健康度展示、高级筛选功能 |
| v6.18 | 2026-03-29 | 接口可靠性分级、并发优化 |
| v6.17 | 2026-03-29 | UI自适应布局优化 |
| v6.16 | 2026-03-28 | 价格双重验证、ROE计算改进 |

---

## 设计原则回顾

### 第一性原理
- 用户真正需要什么？→ 灵活调整投资策略
- 如何实现？→ 参数化配置 + 即时生效

### 极简主义
- 只暴露核心参数，避免过度复杂
- 配置页面清晰分类，一目了然
- 每个参数配详细说明，降低理解成本

### 快速迭代
- 小步快跑，先实现核心功能
- 后续可扩展：预览功能、配置历史等

---

**文档状态**: ✅ 已完成
**最后更新**: 2026-03-29 17:10
