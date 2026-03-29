"""
v6.15 第一轮完整功能测试

测试内容：
1. 价格双重验证（新浪+腾讯）
2. ROE计算（支持银行股）
3. 负债率计算
4. 完整流程测试

测试股票：
- 普通股票：中国平安(601318)、贵州茅台(600519)
- 银行股：建设银行(601939)、招商银行(600036)、中信银行(601998)
"""

import sys
import time
import json
from datetime import datetime

# 添加项目路径
sys.path.insert(0, '/Users/macair/Work/workbuddy_dir/hl3')

from server.services.price_dual_validator import (
    validate_price_dual,
    validate_prices_batch,
    get_validation_stats
)
from server.services.financial_calculator import (
    calculate_roe,
    calculate_debt_ratio,
    calculate_roe_batch,
    calculate_debt_ratio_batch,
    validate_roe_with_yjbb,
    get_calculation_stats,
    is_bank_stock
)


# ============================================================
# 测试配置
# ============================================================

TEST_CODES = {
    # 银行股
    'banks': ['601939', '600036', '601998', '601288', '601166'],
    # 普通股票
    'normal': ['601318', '600519', '601857', '600028', '601088'],
}

ALL_TEST_CODES = TEST_CODES['banks'] + TEST_CODES['normal']

print("=" * 80)
print("v6.15 第一轮完整功能测试")
print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)
print()


# ============================================================
# 测试1: 价格双重验证
# ============================================================

print("【测试1】价格双重验证（新浪+腾讯）")
print("-" * 80)

test_prices = ALL_TEST_CODES[:5]  # 先测试5只
print(f"测试股票: {test_prices}")
print()

price_results = {}
for code in test_prices:
    print(f"  测试 {code}...", end=' ')
    result = validate_price_dual(code, tolerance=0.01, timeout=5)
    price_results[code] = result
    
    if result['price']:
        print(f"✓ 价格={result['price']}元, 可信度={result['confidence']}", end='')
        if result['validation'].get('difference_pct') is not None:
            print(f", 差异={result['validation']['difference_pct']}%")
        else:
            print()
    else:
        print("✗ 获取失败")

print()
price_stats = get_validation_stats(price_results)
print("统计结果:")
print(f"  总数: {price_stats['total']}")
print(f"  成功: {price_stats['success']} ({price_stats['success_rate']}%)")
print(f"  高可信度: {price_stats['high_confidence']} ({price_stats['high_confidence_rate']}%)")
print(f"  平均差异: {price_stats['avg_difference']}%")
print()

# 详细验证结果
print("详细验证结果:")
for code, result in price_results.items():
    if result['validation']:
        print(f"  {code}: {result['validation']['message']}")
print()


# ============================================================
# 测试2: ROE计算（银行股支持）
# ============================================================

print("【测试2】ROE计算（支持银行股）")
print("-" * 80)

print("银行股测试:")
bank_results = {}
for code in TEST_CODES['banks'][:3]:  # 测试3只银行股
    print(f"  测试 {code}...", end=' ')
    result = calculate_roe(code, timeout=10)
    bank_results[code] = result
    
    if result:
        print(f"✓ ROE={result['roe']}%, 银行股={result['is_bank']}, 字段={result['field_used']}")
    else:
        print("✗ 计算失败")

print()
print("普通股票测试:")
normal_results = {}
for code in TEST_CODES['normal'][:3]:  # 测试3只普通股票
    print(f"  测试 {code}...", end=' ')
    result = calculate_roe(code, timeout=10)
    normal_results[code] = result
    
    if result:
        print(f"✓ ROE={result['roe']}%, 银行股={result['is_bank']}, 字段={result['field_used']}")
    else:
        print("✗ 计算失败")

print()

# 合并结果
all_roe_results = {**bank_results, **normal_results}
roe_stats = get_calculation_stats(all_roe_results, 'roe')

print("ROE计算统计:")
print(f"  总数: {roe_stats['total']}")
print(f"  成功: {roe_stats['success']} ({roe_stats['success_rate']}%)")
print(f"  银行股: {roe_stats['bank_stocks']}只")
print(f"  银行股成功: {roe_stats['bank_success']}只 ({roe_stats['bank_success_rate']}%)")
print()


# ============================================================
# 测试3: 负债率计算
# ============================================================

print("【测试3】负债率计算")
print("-" * 80)

debt_results = {}
for code in ALL_TEST_CODES[:5]:  # 测试5只
    print(f"  测试 {code}...", end=' ')
    result = calculate_debt_ratio(code, timeout=10)
    debt_results[code] = result
    
    if result:
        print(f"✓ 负债率={result['debt_ratio']}%, 字段={result['field_used']}")
    else:
        print("✗ 计算失败")

print()

debt_stats = get_calculation_stats(debt_results, 'debt_ratio')
print("负债率计算统计:")
print(f"  总数: {debt_stats['total']}")
print(f"  成功: {debt_stats['success']} ({debt_stats['success_rate']}%)")
print()


# ============================================================
# 测试4: ROE双重验证
# ============================================================

print("【测试4】ROE双重验证（计算值 vs yjbb数据）")
print("-" * 80)

roe_validation_results = {}
for code, roe_result in list(all_roe_results.items())[:5]:
    if roe_result and 'roe' in roe_result:
        print(f"  验证 {code}...", end=' ')
        validation = validate_roe_with_yjbb(code, roe_result['roe'], tolerance=0.05)
        roe_validation_results[code] = validation
        
        print(f"✓ 计算ROE={validation['roe_calculated']}%, yjbb ROE={validation['roe_yjbb']}%", end='')
        if validation['difference_pct'] is not None:
            print(f", 差异={validation['difference_pct']}%, {validation['confidence']}")
        else:
            print()

print()


# ============================================================
# 测试5: 完整流程测试
# ============================================================

print("【测试5】完整流程测试")
print("-" * 80)

# 选择一只股票完整测试
test_code = '601939'  # 建设银行
print(f"完整测试股票: {test_code}")
print()

# 5.1 价格验证
print("  5.1 价格双重验证...")
price_result = validate_price_dual(test_code, tolerance=0.01, timeout=5)
if price_result['price']:
    print(f"      ✓ 价格: {price_result['price']}元 ({price_result['confidence']})")
else:
    print("      ✗ 价格获取失败")

# 5.2 ROE计算
print("  5.2 ROE计算...")
roe_result = calculate_roe(test_code, timeout=10)
if roe_result:
    print(f"      ✓ ROE: {roe_result['roe']}% (银行股={roe_result['is_bank']})")
    
    # 5.3 ROE验证
    print("  5.3 ROE双重验证...")
    roe_validation = validate_roe_with_yjbb(test_code, roe_result['roe'], tolerance=0.05)
    if roe_validation['roe_yjbb']:
        print(f"      ✓ yjbb ROE: {roe_validation['roe_yjbb']}%")
        print(f"      ✓ 差异: {roe_validation['difference_pct']}% ({roe_validation['confidence']})")
    else:
        print("      ⚠ yjbb数据不可用")
else:
    print("      ✗ ROE计算失败")

# 5.4 负债率计算
print("  5.4 负债率计算...")
debt_result = calculate_debt_ratio(test_code, timeout=10)
if debt_result:
    print(f"      ✓ 负债率: {debt_result['debt_ratio']}%")
else:
    print("      ✗ 负债率计算失败")

print()


# ============================================================
# 测试总结
# ============================================================

print("=" * 80)
print("第一轮测试总结")
print("=" * 80)
print()

print("1. 价格双重验证:")
print(f"   ✓ 成功率: {price_stats['success_rate']}%")
print(f"   ✓ 高可信度率: {price_stats['high_confidence_rate']}%")
print()

print("2. ROE计算:")
print(f"   ✓ 总体成功率: {roe_stats['success_rate']}%")
print(f"   ✓ 银行股成功率: {roe_stats['bank_success_rate']}%")
print()

print("3. 负债率计算:")
print(f"   ✓ 成功率: {debt_stats['success_rate']}%")
print()

# 检查是否所有功能都通过
all_passed = (
    price_stats['success_rate'] >= 80 and
    roe_stats['success_rate'] >= 80 and
    roe_stats['bank_success_rate'] >= 80 and
    debt_stats['success_rate'] >= 60
)

if all_passed:
    print("✅ 所有测试通过！可以进行第二轮测试。")
else:
    print("⚠️ 部分测试未达标，需要检查问题。")

print()
print(f"测试完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)
