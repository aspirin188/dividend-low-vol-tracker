"""
V8.1完整筛选测试 - 验证市值和分红数据修复
"""
import sys
import warnings
warnings.filterwarnings('ignore')

from server.services.fetcher import merge_all_data
from server.services.scorer import filter_stocks, calculate_scores

print("="*70)
print("红利低波跟踪系统 V8.1 - 完整筛选测试")
print("="*70)

# 1. 获取数据
print("\n[步骤1] 获取数据...")
df = merge_all_data()

if df.empty:
    print("\n✗ 数据获取失败")
    sys.exit(1)

print(f"\n原始数据: {len(df)} 只股票")

# 显示数据质量统计
print("\n数据质量统计:")
print(f"  - 有效市值数据: {df['market_cap'].notna().sum()} 只")
print(f"  - 有效分红数据: {df['dividend'].notna().sum()} 只")
print(f"  - 有效股息率: {df['div_yield'].notna().sum()} 只")

# 2. 筛选
print("\n[步骤2] 筛选股票...")
filtered = filter_stocks(df)

print(f"筛选后: {len(filtered)} 只股票")

if filtered.empty:
    print("\n✗ 无符合条件的股票")
    sys.exit(1)

# 3. 评分
print("\n[步骤3] 计算评分...")
scored = calculate_scores(filtered)

if scored.empty:
    print("\n✗ 评分计算失败")
    sys.exit(1)

# 4. 显示结果
print("\n" + "="*70)
print("筛选结果（前20名）")
print("="*70)

# 显示关键指标
cols = ['rank', 'code', 'name', 'dividend_yield', 'annual_vol', 
        'composite_score', 'market_cap', 'roe', 'debt_ratio']

result = scored[cols].head(20)

print("\n" + result.to_string(index=False))

# 统计市值分布
print("\n" + "="*70)
print("市值分布分析")
print("="*70)

# 市值区间统计
cap_ranges = [
    (0, 300, '小盘股（<300亿）'),
    (300, 500, '中盘股（300-500亿）'),
    (500, 1000, '大盘股（500-1000亿）'),
    (1000, float('inf'), '超大盘股（>1000亿）')
]

print("\n市值区间分布:")
for min_cap, max_cap, label in cap_ranges:
    count = len(scored[(scored['market_cap'] >= min_cap) & (scored['market_cap'] < max_cap)])
    print(f"  {label}: {count} 只")

print("\n市值统计:")
print(f"  最小市值: {scored['market_cap'].min():.2f} 亿元")
print(f"  最大市值: {scored['market_cap'].max():.2f} 亿元")
print(f"  平均市值: {scored['market_cap'].mean():.2f} 亿元")
print(f"  中位数市值: {scored['market_cap'].median():.2f} 亿元")

# 检查是否有知名大盘股
print("\n知名大盘股检查:")
big_cap_stocks = ['601318', '601398', '600036', '601288', '600519']
for code in big_cap_stocks:
    row = scored[scored['code'] == code]
    if not row.empty:
        name = row['name'].values[0]
        div_yield = row['dividend_yield'].values[0]
        market_cap = row['market_cap'].values[0]
        print(f"  ✓ {code} {name}: 股息率{div_yield:.2f}%, 市值{market_cap:.0f}亿")
    else:
        print(f"  ✗ {code}: 未入选")

print("\n" + "="*70)
print("测试完成")
print("="*70)