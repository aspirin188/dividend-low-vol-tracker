"""
快速验证测试 - 只测试几只大盘股
"""
import sys
import warnings
warnings.filterwarnings('ignore')

from server.services.fetcher import fetch_eps_data, fetch_realtime_prices, fetch_dividend_data, fetch_market_cap_batch
from server.services.scorer import filter_stocks, calculate_scores
import pandas as pd

print("="*70)
print("快速验证测试 - 大盘股数据验证")
print("="*70)

# 1. 获取基础数据
print("\n[步骤1] 获取基础数据...")
eps_df = fetch_eps_data()
price_df = fetch_realtime_prices(eps_df['code'].tolist()[:100])  # 只测试前100只
div_df = fetch_dividend_data()

print(f"EPS数据: {len(eps_df)} 只")
print(f"股价数据: {len(price_df)} 只")
print(f"分红数据: {len(div_df)} 只")

# 2. 合并数据
print("\n[步骤2] 合并数据...")
merged = eps_df.merge(price_df, on='code', how='inner')
merged = merged.merge(div_df, on='code', how='left')

# 计算股息率
merged['div_yield'] = (merged['dividend'] / merged['price'] * 100).round(2)

# 筛选高股息
high_div = merged[merged['div_yield'] >= 3.0].copy()
print(f"高股息股票（≥3%）: {len(high_div)} 只")

if high_div.empty:
    print("\n无高股息股票，测试结束")
    sys.exit(0)

# 3. 获取市值数据
print("\n[步骤3] 获取市值数据（前20只高股息股票）...")
test_codes = high_div.head(20)['code'].tolist()
cap_data = fetch_market_cap_batch(test_codes)

print("\n市值数据验证:")
valid_count = 0
for code in test_codes[:10]:  # 只显示前10只
    cap = cap_data.get(code)
    row = high_div[high_div['code'] == code]
    name = row['name'].values[0] if not row.empty else '未知'
    div_yield = row['div_yield'].values[0] if not row.empty else 0
    
    if cap:
        print(f"  ✓ {code} {name}: 市值{cap:.0f}亿, 股息率{div_yield:.2f}%")
        valid_count += 1
    else:
        print(f"  ✗ {code} {name}: 市值获取失败")

print(f"\n有效市值数据: {valid_count}/10")

# 4. 检查大盘股
print("\n[步骤4] 检查知名大盘股...")
big_cap_codes = ['601318', '601398', '600036', '601288', '600519']

# 从完整数据中查找
eps_big = eps_df[eps_df['code'].isin(big_cap_codes)]
if not eps_big.empty:
    price_big = price_df[price_df['code'].isin(big_cap_codes)]
    div_big = div_df[div_df['code'].isin(big_cap_codes)]
    
    if not price_big.empty and not div_big.empty:
        merged_big = eps_big.merge(price_big, on='code').merge(div_big, on='code')
        merged_big['div_yield'] = (merged_big['dividend'] / merged_big['price'] * 100)
        
        cap_big = fetch_market_cap_batch(big_cap_codes)
        
        print("\n大盘股数据:")
        for code in big_cap_codes:
            row = merged_big[merged_big['code'] == code]
            cap = cap_big.get(code)
            
            if not row.empty and cap:
                name = row['name'].values[0]
                div = row['dividend'].values[0]
                price = row['price'].values[0]
                div_yield = row['div_yield'].values[0]
                print(f"  ✓ {code} {name}: 分红{div:.2f}元, 股价{price:.2f}元, 股息率{div_yield:.2f}%, 市值{cap:.0f}亿")
            else:
                print(f"  ✗ {code}: 数据缺失")

print("\n" + "="*70)
print("快速验证完成")
print("="*70)