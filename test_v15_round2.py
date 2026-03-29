"""
v6.15 第二轮完整功能测试

测试内容：
1. 价格双重验证（扩大测试范围）
2. ROE计算（更多银行股测试）
3. 负债率计算（扩大测试范围）
4. 完整流程测试（多只股票）
5. 性能测试

测试目标：
- 价格验证成功率 >= 95%
- ROE计算成功率 >= 80%（银行股 >= 70%）
- 负债率计算成功率 >= 90%
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
    # 银行股（更多）
    'banks': ['601939', '600036', '601998', '601288', '601166', '600016', '600000', '601169'],
    # 普通股票（更多）
    'normal': ['601318', '600519', '601857', '600028', '601088', '600036', '000001', '600887'],
}

print("=" * 80)
print("v6.15 第二轮完整功能测试")
print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)
print()


# ============================================================
# 测试1: 价格双重验证（扩大范围）
# ============================================================

print("【测试1】价格双重验证（扩大范围）")
print("-" * 80)

test_prices = TEST_CODES['banks'][:5] + TEST_CODES['normal'][:5]  # 测试10只
print(f"测试股票数量: {len(test_prices)}")
print()

price_results = validate_prices_batch(test_prices, tolerance=0.01, timeout=5, delay=0.2)

print("测试结果:")
for code, result in price_results.items():
    if result['price']:
        print(f"  {code}: 价格={result['price']}元, 可信度={result['confidence']}", end='')
        if result['validation'].get('difference_pct') is not None:
            print(f", 差异={result['validation']['difference_pct']}%")
        else:
            print()
    else:
        print(f"  {code}: ✗ 获取失败")

print()
price_stats = get_validation_stats(price_results)
print("统计结果:")
print(f"  总数: {price_stats['total']}")
print(f"  成功: {price_stats['success']} ({price_stats['success_rate']}%)")
print(f"  高可信度: {price_stats['high_confidence']} ({price_stats['high_confidence_rate']}%)")
print(f"  中可信度: {price_stats['medium_confidence']}")
print(f"  低可信度: {price_stats['low_confidence']}")
print(f"  平均差异: {price_stats['avg_difference']}%")
print()


# ============================================================
# 测试2: ROE计算（更多银行股）
# ============================================================

print("【测试2】ROE计算（更多银行股）")
print("-" * 80)

print("银行股测试:")
bank_results = calculate_roe_batch(TEST_CODES['banks'][:6], delay=0.5, timeout=10)
for code, result in bank_results.items():
    if result:
        print(f"  {code}: ✓ ROE={result['roe']}%, 银行股={result['is_bank']}, 字段={result['field_used']}")
    else:
        print(f"  {code}: ✗ 计算失败")

print()
print("普通股票测试:")
normal_results = calculate_roe_batch(TEST_CODES['normal'][:6], delay=0.5, timeout=10)
for code, result in normal_results.items():
    if result:
        print(f"  {code}: ✓ ROE={result['roe']}%, 银行股={result['is_bank']}, 字段={result['field_used']}")
    else:
        print(f"  {code}: ✗ 计算失败")

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
# 测试3: 负债率计算（扩大范围）
# ============================================================

print("【测试3】负债率计算（扩大范围）")
print("-" * 80)

test_debt_codes = TEST_CODES['banks'][:4] + TEST_CODES['normal'][:4]
debt_results = calculate_debt_ratio_batch(test_debt_codes, delay=0.5, timeout=10)

print("测试结果:")
for code, result in debt_results.items():
    if result:
        stock_type = "银行股" if is_bank_stock(code) else "普通股"
        print(f"  {code} ({stock_type}): ✓ 负债率={result['debt_ratio']}%")
    else:
        print(f"  {code}: ✗ 计算失败")

print()

debt_stats = get_calculation_stats(debt_results, 'debt_ratio')
print("负债率计算统计:")
print(f"  总数: {debt_stats['total']}")
print(f"  成功: {debt_stats['success']} ({debt_stats['success_rate']}%)")
print()


# ============================================================
# 测试4: 完整流程测试（多只股票）
# ============================================================

print("【测试4】完整流程测试（多只股票）")
print("-" * 80)

# 测试3只股票的完整流程
test_stocks = [
    ('601939', '建设银行', '银行股'),
    ('601318', '中国平安', '保险股'),
    ('600519', '贵州茅台', '消费股'),
]

complete_test_results = []

for code, name, stock_type in test_stocks:
    print(f"\n测试 {name} ({code}) - {stock_type}:")
    
    test_result = {
        'code': code,
        'name': name,
        'type': stock_type,
        'price': None,
        'roe': None,
        'debt_ratio': None,
        'status': 'pending'
    }
    
    # 4.1 价格验证
    print("  4.1 价格双重验证...", end=' ')
    price_result = validate_price_dual(code, tolerance=0.01, timeout=5)
    if price_result['price']:
        test_result['price'] = price_result['price']
        print(f"✓ {price_result['price']}元 ({price_result['confidence']})")
    else:
        print("✗ 失败")
    
    # 4.2 ROE计算
    print("  4.2 ROE计算...", end=' ')
    roe_result = calculate_roe(code, timeout=10)
    if roe_result:
        test_result['roe'] = roe_result['roe']
        print(f"✓ {roe_result['roe']}%")
    else:
        print("✗ 失败")
    
    # 4.3 负债率计算
    print("  4.3 负债率计算...", end=' ')
    debt_result = calculate_debt_ratio(code, timeout=10)
    if debt_result:
        test_result['debt_ratio'] = debt_result['debt_ratio']
        print(f"✓ {debt_result['debt_ratio']}%")
    else:
        print("✗ 失败")
    
    # 判断是否成功
    if test_result['price'] and (test_result['roe'] or test_result['debt_ratio']):
        test_result['status'] = 'success'
    else:
        test_result['status'] = 'partial'
    
    complete_test_results.append(test_result)
    
    time.sleep(0.5)  # 避免频率限制

print()
print("完整流程测试总结:")
success_count = sum(1 for r in complete_test_results if r['status'] == 'success')
print(f"  成功: {success_count}/{len(complete_test_results)}")
for result in complete_test_results:
    status_icon = '✓' if result['status'] == 'success' else '⚠️'
    print(f"  {status_icon} {result['name']}: 价格={result['price']}, ROE={result['roe']}, 负债率={result['debt_ratio']}")

print()


# ============================================================
# 测试5: 性能测试
# ============================================================

print("【测试5】性能测试")
print("-" * 80)

# 5.1 价格验证性能
print("5.1 价格验证性能:")
test_codes_perf = TEST_CODES['banks'][:5]
start_time = time.time()
perf_price_results = validate_prices_batch(test_codes_perf, tolerance=0.01, timeout=5, delay=0.1)
end_time = time.time()
print(f"  测试股票数: {len(test_codes_perf)}")
print(f"  总耗时: {end_time - start_time:.2f}秒")
print(f"  平均每只: {(end_time - start_time) / len(test_codes_perf):.2f}秒")

print()

# 5.2 ROE计算性能
print("5.2 ROE计算性能:")
test_codes_perf = TEST_CODES['normal'][:3]
start_time = time.time()
perf_roe_results = calculate_roe_batch(test_codes_perf, delay=0.3, timeout=10)
end_time = time.time()
print(f"  测试股票数: {len(test_codes_perf)}")
print(f"  总耗时: {end_time - start_time:.2f}秒")
print(f"  平均每只: {(end_time - start_time) / len(test_codes_perf):.2f}秒")

print()


# ============================================================
# 测试总结
# ============================================================

print("=" * 80)
print("第二轮测试总结")
print("=" * 80)
print()

print("1. 价格双重验证:")
print(f"   ✓ 成功率: {price_stats['success_rate']}%")
print(f"   ✓ 高可信度率: {price_stats['high_confidence_rate']}%")
print(f"   {'✅' if price_stats['success_rate'] >= 95 else '⚠️'} 达标" if price_stats['success_rate'] >= 95 else f"   {'⚠️'} 未达标（目标>=95%）")
print()

print("2. ROE计算:")
print(f"   ✓ 总体成功率: {roe_stats['success_rate']}%")
print(f"   ✓ 银行股成功率: {roe_stats['bank_success_rate']}%")
print(f"   {'✅' if roe_stats['success_rate'] >= 80 else '⚠️'} 达标" if roe_stats['success_rate'] >= 80 else f"   {'⚠️'} 未达标（目标>=80%）")
print()

print("3. 负债率计算:")
print(f"   ✓ 成功率: {debt_stats['success_rate']}%")
print(f"   {'✅' if debt_stats['success_rate'] >= 90 else '⚠️'} 达标" if debt_stats['success_rate'] >= 90 else f"   {'⚠️'} 未达标（目标>=90%）")
print()

# 检查是否所有功能都通过
all_passed = (
    price_stats['success_rate'] >= 95 and
    roe_stats['success_rate'] >= 80 and
    debt_stats['success_rate'] >= 90
)

if all_passed:
    print("=" * 80)
    print("✅✅✅ 所有测试达标！v6.15开发完成，可以通知用户。")
    print("=" * 80)
else:
    print("=" * 80)
    print("⚠️ 部分测试未达标，需要继续优化。")
    print("=" * 80)

print()
print(f"测试完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)
