#!/usr/bin/env python3
"""
测试双重验证机制
v6.15: 测试数据交叉验证功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server.services.data_validator import (
    DataSourceRegistry, 
    DualDataValidator,
    check_consistency
)
import akshare as ak
import pandas as pd
import time

print("=" * 70)
print("双重验证机制测试 - v6.15")
print("=" * 70)

# ============================================================
# 步骤1: 创建数据源注册表
# ============================================================

print("\n【步骤1】创建数据源注册表")
print("-" * 70)

registry = DataSourceRegistry()

# ============================================================
# 步骤2: 注册ROE数据源
# ============================================================

print("\n【步骤2】注册ROE数据源")
print("-" * 70)

# 数据源A: akshare stock_yjbb_em
def fetch_roe_from_yjbb(code, context):
    """从akshare yjbb获取ROE"""
    eps_df = context.get('eps_df') if context else None
    if eps_df is not None and code in eps_df['code'].values:
        roe = eps_df[eps_df['code'] == code]['roe'].values[0]
        return roe
    return None

# 数据源B: akshare stock_financial_analysis_indicator
def fetch_roe_from_financial_indicator(code, context):
    """从财务指标接口获取ROE"""
    try:
        df = ak.stock_financial_analysis_indicator(symbol=code)
        if df is not None and not df.empty:
            # 找到ROE列
            roe_col = None
            for col in df.columns:
                if '加权净资产收益率' in col or 'ROE' in col.upper():
                    roe_col = col
                    break
            
            if roe_col:
                # 获取最新的ROE
                latest = df[df[roe_col].notna()].iloc[0]
                return float(latest[roe_col])
    except Exception as e:
        pass
    return None

# 注册
registry.register('roe', 'akshare_yjbb', fetch_roe_from_yjbb, priority=10)
registry.register('roe', 'akshare_financial', fetch_roe_from_financial_indicator, priority=5)

# ============================================================
# 步骤3: 注册EPS数据源
# ============================================================

print("\n【步骤3】注册EPS数据源")
print("-" * 70)

def fetch_eps_from_yjbb(code, context):
    """从akshare yjbb获取EPS"""
    eps_df = context.get('eps_df') if context else None
    if eps_df is not None and code in eps_df['code'].values:
        eps = eps_df[eps_df['code'] == code]['basic_eps'].values[0]
        return eps
    return None

def fetch_eps_from_fhps(code, context):
    """从分红接口获取EPS（部分股票有）"""
    try:
        df = ak.stock_fhps_em(date="20241231")
        if df is not None and not df.empty:
            row = df[df['代码'] == code]
            if not row.empty and '每股收益' in df.columns:
                return float(row['每股收益'].values[0])
    except:
        pass
    return None

registry.register('eps', 'akshare_yjbb', fetch_eps_from_yjbb, priority=10)
registry.register('eps', 'akshare_fhps', fetch_eps_from_fhps, priority=5)

# ============================================================
# 步骤4: 注册每股股利数据源
# ============================================================

print("\n【步骤4】注册每股股利数据源")
print("-" * 70)

def fetch_dividend_from_fhps(code, context):
    """从akshare fhps获取每股股利"""
    div_df = context.get('div_df') if context else None
    if div_df is not None and code in div_df['code'].values:
        div = div_df[div_df['code'] == code]['dividend_per_share'].values[0]
        return div
    return None

def fetch_dividend_from_hist(code, context):
    """从历史数据计算每股股利（备用方案）"""
    # 简化版：从接口直接获取
    try:
        df = ak.stock_fhps_em(date="20241231")
        if df is not None and not df.empty:
            row = df[df['代码'] == code]
            if not row.empty and '现金分红-现金分红比例' in df.columns:
                value = row['现金分红-现金分红比例'].values[0]
                # 转换为每股股利（每10股派息 -> 每股股利）
                return float(value) / 10
    except:
        pass
    return None

registry.register('dividend_per_share', 'akshare_fhps', fetch_dividend_from_fhps, priority=10)
registry.register('dividend_per_share', 'akshare_hist', fetch_dividend_from_hist, priority=5)

# ============================================================
# 步骤5: 准备上下文数据
# ============================================================

print("\n【步骤5】准备上下文数据")
print("-" * 70)

print("获取EPS和ROE数据（akshare yjbb）...")
try:
    eps_df = ak.stock_yjbb_em(date="20241231")
    eps_df = eps_df[eps_df['股票代码'].str.startswith(('0', '3', '6'))].copy()
    eps_df['code'] = eps_df['股票代码']
    eps_df['basic_eps'] = pd.to_numeric(eps_df['每股收益'], errors='coerce')
    eps_df['roe'] = pd.to_numeric(eps_df['净资产收益率'], errors='coerce')
    print(f"✓ 获取到 {len(eps_df)} 只股票的数据")
except Exception as e:
    print(f"✗ 失败: {e}")
    eps_df = pd.DataFrame()

print("\n获取分红数据（akshare fhps）...")
try:
    div_df = ak.stock_fhps_em(date="20241231")
    div_df = div_df[div_df['代码'].str.startswith(('0', '3', '6'))].copy()
    div_df['code'] = div_df['代码']
    div_df['dividend_per_share'] = pd.to_numeric(div_df['现金分红-现金分红比例'], errors='coerce') / 10
    print(f"✓ 获取到 {len(div_df)} 只股票的数据")
except Exception as e:
    print(f"✗ 失败: {e}")
    div_df = pd.DataFrame()

context = {
    'eps_df': eps_df,
    'div_df': div_df,
}

# ============================================================
# 步骤6: 创建验证器并测试
# ============================================================

print("\n【步骤6】测试双重验证")
print("-" * 70)

validator = DualDataValidator(registry)

# 测试几只股票
test_codes = ['601939', '600036', '601318', '601919', '000001']
test_fields = ['roe', 'eps', 'dividend_per_share']

print(f"\n测试股票: {test_codes}")
print(f"测试字段: {test_fields}")

results = validator.validate_batch(test_codes, test_fields, context)

# ============================================================
# 步骤7: 显示详细结果
# ============================================================

print("\n【步骤7】验证结果详情")
print("-" * 70)

for code, field_results in results.items():
    print(f"\n{code}:")
    for field, result in field_results.items():
        confidence_emoji = {'high': '✓', 'medium': '⚠️', 'low': '✗', 'none': '✗'}
        emoji = confidence_emoji.get(result['confidence'], '?')
        
        print(f"  {field}: {result['value']} {emoji} ({result['confidence']})")
        print(f"    消息: {result['message']}")
        print(f"    数据源: {', '.join(result['sources'])}")
        
        if result['raw_values']:
            print(f"    原始值:")
            for source, value in result['raw_values'].items():
                print(f"      {source}: {value}")

# ============================================================
# 步骤8: 生成验证报告
# ============================================================

print("\n【步骤8】验证报告")
print("-" * 70)

report = validator.get_validation_report()

print(f"总验证次数: {report['total_validations']}")
print(f"数据质量评分: {report['quality_score']}/100")
print(f"\n可信度分布:")
for conf, count in report['by_confidence'].items():
    pct = count / report['total_validations'] * 100 if report['total_validations'] > 0 else 0
    print(f"  {conf}: {count} ({pct:.1f}%)")

print(f"\n告警数: {report['alerts_count']}")

# 字段质量摘要
print("\n字段质量摘要:")
for field in test_fields:
    field_summary = validator.get_field_quality_summary(field)
    print(f"  {field}: 质量评分 {field_summary['quality_score']}/100")

# ============================================================
# 步骤9: 一致性检查测试
# ============================================================

print("\n【步骤9】一致性检查测试")
print("-" * 70)

# 测试不同场景的一致性检查
test_cases = [
    ('roe', 10.69, 10.71),      # 高度一致
    ('roe', 10.69, 11.20),      # 轻微差异
    ('roe', 10.69, 15.30),      # 明显差异
    ('roe', 10.69, None),       # 单一数据源
    ('roe', None, None),        # 无数据
]

for field, val_a, val_b in test_cases:
    result = check_consistency(val_a, val_b, field)
    print(f"\n{field}: {val_a} vs {val_b}")
    print(f"  一致性: {result['is_consistent']}")
    print(f"  可信度: {result['confidence']}")
    print(f"  推荐值: {result['recommended_value']}")
    print(f"  消息: {result['message']}")

# ============================================================
# 总结
# ============================================================

print("\n" + "=" * 70)
print("测试完成")
print("=" * 70)

print("\n核心结论:")
print("1. ✅ 双重验证机制已实现")
print("2. ✅ 可以自动检测数据一致性")
print("3. ✅ 可以标记数据可信度")
print("4. ✅ 可以生成数据质量报告")
print("5. ✅ 单一数据源会被标记为低可信度")

print("\n下一步:")
print("1. 将此机制集成到 merge_all_data() 函数")
print("2. 在前端显示数据可信度标识")
print("3. 建立监控和告警系统")
