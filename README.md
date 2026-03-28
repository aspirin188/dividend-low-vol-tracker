# 红利低波跟踪系统 (Dividend Low-Volatility Tracker)

基于两因子模型的高股息股票筛选系统

## 📊 项目简介

红利低波跟踪系统是一个自动化股票筛选工具，通过**股息率+低波动率**两因子模型，帮助投资者发现高质量的高股息投资标的。

### 核心功能

- ✅ **一键运行**: 自动获取数据、筛选、评分
- ✅ **多维筛选**: 支持行业、市值、股息率、市场类型筛选
- ✅ **实时更新**: 数据源来自东方财富，实时准确
- ✅ **Excel导出**: 一键导出筛选结果
- ✅ **综合评分**: 两因子模型自动评分排名

### 两因子模型

```
综合评分 = 股息率归一化 × 60% + (1 - 波动率归一化) × 40%
```

**硬性筛选条件:**
- 股息率 ≥ 4%
- 总市值 ≥ 100亿
- 股利支付率 ≤ 150%
- EPS > 0
- 非ST股票

## 🚀 快速开始

### 环境要求

- Python 3.8+
- pip

### 安装依赖

```bash
git clone https://github.com/aspirin188/dividend-low-vol-tracker.git
cd dividend-low-vol-tracker
pip install -r requirements.txt
```

### 运行系统

```bash
python app.py
```

访问: http://localhost:5050

## 📖 使用说明

1. 点击**【运行】**按钮，系统自动获取数据并筛选
2. 使用搜索框和筛选器过滤结果
3. 点击**【导出】**按钮下载Excel文件

## 🔧 技术栈

- **后端**: Python + Flask
- **前端**: 原生HTML/CSS/JavaScript
- **数据库**: SQLite
- **数据源**: 东方财富API + akshare

## 📝 版本历史

### v6.6 (2026-03-28) - 当前版本
- **重大修复**: 股息率计算bug修复
- 废弃东方财富f115字段，改为自计算TTM股息率
- 招商银行案例: 从错误6.62%修复为正确5.11%

### v6.5
- 行业归并: 50+细分行业→16个大类
- 新增市场筛选器

### v6.2-v6.4
- 增加股价/PE/PB显示
- 市值/股息率筛选器
- 表头排序功能
- 搜索bug修复

详见 `PRD_红利低波跟踪系统_v6.6_极简版.md`

## 📊 数据说明

### 股息率计算口径

- **TTM (Trailing Twelve Months)**: 过去12个月已实施的分红总额 ÷ 当前股价
- 数据源: 东方财富数据中心RPT_LICO_FN_CPD接口
- 计算方式: 自计算，不依赖第三方字段

### 波动率计算

- 窗口期: 120个交易日
- 计算方式: 对数收益率年化 (√242)

## 📁 项目结构

```
dividend-low-vol-tracker/
├── app.py                  # Flask入口
├── requirements.txt        # 依赖清单
├── server/
│   ├── routes.py          # API路由
│   ├── services/
│   │   ├── fetcher.py     # 数据获取(v6.6修复股息率计算)
│   │   └── scorer.py      # 评分模型
│   └── templates/
│       └── index.html     # 前端页面
├── tests/                  # 测试用例
└── PRD_*.md               # 产品需求文档
```

## ⚠️ 免责声明

本系统仅供学习和研究使用，不构成任何投资建议。股市有风险，投资需谨慎。

## 📄 许可证

MIT License

## 👤 作者

aspirin188

## 🙏 致谢

- 数据来源: [东方财富](https://www.eastmoney.com/)
- 数据接口: [akshare](https://github.com/akfamily/akshare)
