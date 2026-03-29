#!/usr/bin/env python3
"""最小化测试 - 只检查ROE数据获取和筛选"""
import sys
sys.path.insert(0, '.')

print("测试开始...", flush=True)

# 测试1: 检查ROE数据获取
print("\n[测试1] ROE数据获取", flush=True)
from server.services.fetcher import fetch_eps_batch
eps_df = fetch_eps_batch()

if eps_df.empty:
    print("✗ 未获取到数据", flush=True)
    sys.exit(1)

print(f"✓ 获取 {len(eps_df)} 只股票", flush=True)
print(f"ROE非空: {eps_df['roe'].notna().sum()}/{len(eps_df)}", flush=True)

# 显示几只股票
for code in ['601939', '600036', '601318']:
    row = eps_df[eps_df['code'] == code]
    if not row.empty:
        print(f"  {code}: ROE={row['roe'].values[0]}", flush=True)

print("\n✓ 测试成功!", flush=True)
