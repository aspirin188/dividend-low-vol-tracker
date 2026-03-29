#!/usr/bin/env python3
"""完整调试ROE数据流"""
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("步骤1: 测试fetch_eps_batch()")
print("=" * 60)
from server.services.fetcher import fetch_eps_batch
eps_df = fetch_eps_batch()
print(f"列名: {eps_df.columns.tolist()}")
print(f"ROE非空: {eps_df['roe'].notna().sum()}/{len(eps_df)}")

if eps_df['roe'].notna().sum() > 0:
    print("✅ fetch_eps_batch()返回ROE数据")
    print("\\n示例:")
    print(eps_df[eps_df['roe'].notna()][['code', 'basic_eps', 'roe']].head(3).to_string(index=False))
else:
    print("❌ fetch_eps_batch()没有返回ROE数据")

print("\\n" + "=" * 60)
print("步骤2: 测试完整merge流程")
print("=" * 60)
from server.services.fetcher import fetch_all_quotes
quotes = fetch_all_quotes()
merged = quotes.merge(eps_df, on='code', how='left')

print(f"merge后列名: {merged.columns.tolist()}")
if 'roe' in merged.columns:
    print(f"ROE非空: {merged['roe'].notna().sum()}/{len(merged)}")
    print("✅ merge后ROE列存在")
else:
    print("❌ merge后ROE列不存在")

print("\\n" + "=" * 60)
print("步骤3: 检查后续merge操作")
print("=" * 60)
from server.services.fetcher import fetch_dividend_for_candidates

# 模拟候选股
test_codes = ['601919', '600036', '000001']
div_df = fetch_dividend_for_candidates(test_codes)
print(f"div_df列名: {div_df.columns.tolist()}")
print(f"div_df数据:\\n{div_df.to_string(index=False)}")

# 再次merge
merged_test = merged[merged['code'].isin(test_codes)].copy()
merged_test = merged_test.merge(div_df, on='code', how='left')

print(f"\\n再次merge后列名: {merged_test.columns.tolist()}")
if 'roe' in merged_test.columns:
    print(f"ROE非空: {merged_test['roe'].notna().sum()}/{len(merged_test)}")
    print("✅ 再次merge后ROE列仍然存在")
    print("\\n数据示例:")
    print(merged_test[['code', 'name', 'basic_eps', 'roe']].to_string(index=False))
else:
    print("❌ 再次merge后ROE列消失")
