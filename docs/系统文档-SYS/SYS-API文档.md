# 红利低波跟踪系统 API文档

**版本**: v8.0  
**最后更新**: 2026-03-31

---

## 目录

- [概述](#概述)
- [基础信息](#基础信息)
- [配置API](#配置api)
- [筛选API](#筛选api)
- [数据API](#数据api)
- [错误处理](#错误处理)
- [版本历史](#版本历史)

---

## 概述

红利低波跟踪系统提供RESTful API接口,支持配置管理、股票筛选、数据查询等功能。

**基础URL**: `http://localhost:5050`

---

## 基础信息

### 请求格式

所有API请求使用JSON格式:

```bash
Content-Type: application/json
```

### 响应格式

成功响应:

```json
{
  "success": true,
  "data": {...}
}
```

失败响应:

```json
{
  "success": false,
  "error": "错误信息"
}
```

---

## 配置API

### 1. 获取预设策略列表

获取所有可用的预设策略。

**端点**: `GET /api/config/strategies`

**请求示例**:

```bash
curl -X GET http://localhost:5050/api/config/strategies
```

**响应示例**:

```json
{
  "current": "conservative",
  "strategies": {
    "conservative": {
      "name": "保守型",
      "description": "追求稳定收益,低风险",
      "params": {
        "MIN_DIVIDEND_YIELD": "4.0",
        "MAX_DEBT_RATIO": "60",
        "MIN_DIVIDEND_YEARS": "5",
        "MIN_ROE": "10.0",
        "MIN_MARKET_CAP": "800"
      }
    },
    "balanced": {
      "name": "均衡型",
      "description": "兼顾收益与风险的平衡策略",
      "params": {
        "MIN_DIVIDEND_YIELD": "3.0",
        "MAX_DEBT_RATIO": "70",
        "MIN_DIVIDEND_YEARS": "3",
        "MIN_ROE": "8.0",
        "MIN_MARKET_CAP": "500"
      }
    },
    "aggressive": {
      "name": "激进型",
      "description": "追求高收益,愿意承担较大波动",
      "params": {
        "MIN_DIVIDEND_YIELD": "2.0",
        "MAX_DEBT_RATIO": "80",
        "MIN_DIVIDEND_YEARS": "2",
        "MIN_ROE": "6.0",
        "MIN_MARKET_CAP": "300"
      }
    },
    "high_dividend": {
      "name": "高股息",
      "description": "专注于高股息收益率",
      "params": {
        "MIN_DIVIDEND_YIELD": "5.0",
        "MAX_DEBT_RATIO": "75",
        "MIN_DIVIDEND_YEARS": "3",
        "MIN_ROE": "8.0",
        "MIN_MARKET_CAP": "400"
      }
    },
    "value": {
      "name": "低估型",
      "description": "寻找低估值的优质股票",
      "params": {
        "MIN_DIVIDEND_YIELD": "3.5",
        "MAX_DEBT_RATIO": "70",
        "MIN_DIVIDEND_YEARS": "4",
        "MIN_ROE": "9.0",
        "MIN_MARKET_CAP": "600"
      }
    }
  }
}
```

**v8.0新增**: ✅

---

### 2. 应用预设策略

应用指定的预设策略,更新配置参数。

**端点**: `POST /api/config/strategies`

**请求参数**:

```json
{
  "strategy_id": "balanced",
  "reason": "追求平衡收益"
}
```

**请求示例**:

```bash
curl -X POST http://localhost:5050/api/config/strategies \
  -H "Content-Type: application/json" \
  -d '{"strategy_id":"balanced","reason":"追求平衡收益"}'
```

**响应示例**:

```json
{
  "success": true,
  "message": "已应用策略: 均衡型，更新了 8 个参数"
}
```

**错误响应**:

```json
{
  "success": false,
  "error": "策略不存在: invalid_strategy"
}
```

**v8.0新增**: ✅

---

### 3. 获取参数历史记录

获取配置参数的变更历史。

**端点**: `GET /api/config/history`

**请求示例**:

```bash
curl -X GET http://localhost:5050/api/config/history
```

**响应示例**:

```json
{
  "history": [
    {
      "id": 1,
      "timestamp": "2026-03-31 19:24:23",
      "strategy": "conservative",
      "reason": "测试应用保守策略",
      "params": {...}
    }
  ]
}
```

**v8.0新增**: ✅

---

### 4. 获取当前配置

获取所有配置参数。

**端点**: `GET /api/config`

**请求示例**:

```bash
curl -X GET http://localhost:5050/api/config
```

**响应示例**:

```json
{
  "config": {
    "MIN_DIVIDEND_YIELD": "4.0",
    "MAX_DEBT_RATIO": "60",
    "MIN_DIVIDEND_YEARS": "5",
    "MIN_ROE": "10.0",
    "MIN_MARKET_CAP": "800",
    "WEIGHT_DIVIDEND": "0.5",
    "WEIGHT_STABILITY": "0.3",
    "WEIGHT_VOL": "0.2"
  }
}
```

---

### 5. 批量更新配置

批量更新配置参数。

**端点**: `PUT /api/config/batch`

**请求参数**:

```json
{
  "MIN_DIVIDEND_YIELD": "3.5",
  "MAX_DEBT_RATIO": "65"
}
```

**请求示例**:

```bash
curl -X PUT http://localhost:5050/api/config/batch \
  -H "Content-Type: application/json" \
  -d '{"MIN_DIVIDEND_YIELD":"3.5","MAX_DEBT_RATIO":"65"}'
```

**响应示例**:

```json
{
  "success": true,
  "message": "配置已更新"
}
```

---

### 6. 恢复默认配置

恢复所有配置参数到默认值。

**端点**: `POST /api/config/reset`

**请求示例**:

```bash
curl -X POST http://localhost:5050/api/config/reset
```

**响应示例**:

```json
{
  "success": true,
  "message": "配置已恢复默认值"
}
```

---

## 筛选API

### 7. 执行筛选

执行股票筛选,更新数据库。

**端点**: `POST /api/run`

**请求参数**: 无 (使用当前配置)

**请求示例**:

```bash
curl -X POST http://localhost:5050/api/run
```

**响应示例**:

```json
{
  "success": true,
  "count": 50,
  "data_date": "2026-03-31"
}
```

**错误响应**:

```json
{
  "success": false,
  "error": "没有符合条件的股票，请稍后再试"
}
```

**说明**:
- 此操作是同步的,可能需要3-5分钟
- 建议设置较长的超时时间 (如600秒)
- 筛选结果会保存到数据库

---

## 数据API

### 8. 获取股票列表

获取筛选后的股票列表,支持搜索和筛选。

**端点**: `GET /api/stocks`

**查询参数**:

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `q` | string | 搜索关键词 (名称/代码/拼音) | `q=平安银行` |
| `industry` | string | 行业筛选 | `industry=银行` |
| `market_cap_range` | string | 市值范围 (large/medium/small) | `market_cap_range=large` |
| `div_yield_min` | float | 最低股息率 | `div_yield_min=4.0` |
| `market` | string | 市场 (sh/sz/gem/star) | `market=sh` |

**请求示例**:

```bash
# 获取所有股票
curl -X GET http://localhost:5050/api/stocks

# 搜索股票
curl -X GET "http://localhost:5050/api/stocks?q=平安银行"

# 筛选高股息股票
curl -X GET "http://localhost:5050/api/stocks?div_yield_min=5.0"
```

**响应示例**:

```json
{
  "stocks": [
    {
      "code": "000001",
      "name": "平安银行",
      "pinyin_abbr": "payh",
      "industry": "银行",
      "market": "深市",
      "dividend_yield": 5.6,
      "roe": 12.5,
      "debt_ratio": 45.2,
      "dividend_years": 5,
      "score": 85.3,
      "strike_zone_score": 78.5,
      "rank": 1
    }
  ],
  "total": 50,
  "updated_at": "2026-03-31 19:00:00"
}
```

---

### 9. 导出Excel

导出股票数据为Excel文件。

**端点**: `GET /api/export`

**请求示例**:

```bash
curl -X GET http://localhost:5050/api/export -o stocks.xlsx
```

**响应**: 下载Excel文件

---

## 错误处理

### 错误代码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

### 错误示例

**参数错误 (400)**:

```json
{
  "success": false,
  "error": "请指定 strategy_id"
}
```

**服务器错误 (500)**:

```json
{
  "success": false,
  "error": "Expected numeric dtype, got object instead."
}
```

---

## 版本历史

### v8.0 (2026-03-31)

**新增**:
- `GET /api/config/strategies` - 获取预设策略列表
- `POST /api/config/strategies` - 应用预设策略
- `GET /api/config/history` - 获取参数历史记录

**改进**:
- 优化API响应时间 (<1ms)
- 改进错误处理和日志记录

### v7.6 (2026-03-31)

**改进**:
- 极简稳定版本
- 性能提升350倍

### v6.20 (2026-03-29)

**新增**:
- `GET /api/config` - 获取配置
- `PUT /api/config/batch` - 批量更新配置
- `POST /api/config/reset` - 恢复默认配置

---

## 使用示例

### Python示例

```python
import requests

BASE_URL = "http://localhost:5050"

# 获取预设策略
response = requests.get(f"{BASE_URL}/api/config/strategies")
strategies = response.json()

# 应用策略
response = requests.post(
    f"{BASE_URL}/api/config/strategies",
    json={"strategy_id": "balanced", "reason": "测试"}
)

# 执行筛选
response = requests.post(f"{BASE_URL}/api/run")

# 获取股票列表
response = requests.get(f"{BASE_URL}/api/stocks")
stocks = response.json()

print(f"找到 {stocks['total']} 只股票")
```

### JavaScript示例

```javascript
const BASE_URL = "http://localhost:5050";

// 获取预设策略
fetch(`${BASE_URL}/api/config/strategies`)
  .then(res => res.json())
  .then(data => console.log(data));

// 应用策略
fetch(`${BASE_URL}/api/config/strategies`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    strategy_id: 'balanced',
    reason: '测试'
  })
})
  .then(res => res.json())
  .then(data => console.log(data));

// 获取股票列表
fetch(`${BASE_URL}/api/stocks`)
  .then(res => res.json())
  .then(data => {
    console.log(`找到 ${data.total} 只股票`);
  });
```

---

## 支持与反馈

如有问题或建议,请联系开发团队。

---

**最后更新**: 2026-03-31  
**文档版本**: v8.0
