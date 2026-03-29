#!/usr/bin/env python3
"""测试股价百分位计算"""

import sys
sys.path.insert(0, '/Users/macair/Work/workbuddy_dir/hl3')

from server.services.fetcher import calculate_price_percentile

# 测试几只股票
test_codes = ['601939', '600036', '601318']

print("测试股价百分位计算...")
print("-" * 60)

for code in test_codes:
    print(f"\n测试 {code}...")
    try:
        percentile = calculate_price_percentile(code, days=250)
        if percentile is not None:
            print(f"  ✓ {code} 股价百分位: {percentile}%")
        else:
            print(f"  ✗ {code} 返回None")
    except Exception as e:
        print(f"  ✗ {code} 异常: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "-" * 60)
print("测试完成")
