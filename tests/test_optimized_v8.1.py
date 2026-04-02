"""
V8.1优化版快速测试
"""
import sys
import time
import warnings
warnings.filterwarnings('ignore')

from app import create_app
from server.services.fetcher import merge_all_data
from server.services.scorer import filter_stocks, calculate_scores

print("="*70)
print("红利低波跟踪系统 V8.1优化版 - 快速测试")
print("="*70)

# 创建Flask应用
app = create_app()

# 计时开始
start_time = time.time()

# 1. 获取数据
print("\n[步骤1] 获取数据...")
df = merge_all_data()

if df.empty:
    print("\n✗ 数据获取失败")
    sys.exit(1)

# 数据质量报告
print("\n数据质量报告:")
print(f"  原始数据: {len(df)} 只股票")
print(f"  有效股息率: {df['div_yield'].notna().sum()} 只")
print(f"  有效ROE: {df['roe'].notna().sum()} 只")
print(f"  有效负债率: {df['debt_ratio'].notna().sum()} 只")
print(f"  市值估算: 使用股价×100亿（替代方案）")

# 2. 筛选（需要Flask应用上下文）
print("\n[步骤2] 筛选股票...")
with app.app_context():
    filtered = filter_stocks(df)

print(f"筛选后: {len(filtered)} 只股票")

if filtered.empty:
    print("\n✗ 无符合条件的股票")
    print("\n可能原因:")
    print("  1. 股息率筛选过严（当前≥3%）")
    print("  2. ROE筛选过严（当前≥8%）")
    print("  3. 其他硬性条件未满足")
    sys.exit(0)

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

cols = ['rank', 'code', 'name', 'dividend_yield', 'composite_score', 
        'market_cap', 'roe', 'debt_ratio']

result = scored[cols].head(20)

print("\n" + result.to_string(index=False))

# 性能统计
elapsed = time.time() - start_time
minutes = int(elapsed // 60)
seconds = int(elapsed % 60)

print("\n" + "="*70)
print(f"✓ 完成！共 {len(scored)} 只候选股")
print(f"✓ 耗时: {minutes}分{seconds}秒")
print("="*70)

# 检查知名大盘股
print("\n知名大盘股检查:")
big_cap_codes = ['601318', '601398', '600036', '601288', '600519']
for code in big_cap_codes:
    row = scored[scored['code'] == code]
    if not row.empty:
        name = row['name'].values[0]
        div_yield = row['dividend_yield'].values[0]
        print(f"  ✓ {code} {name}: 股息率{div_yield:.2f}%")
    else:
        print(f"  ✗ {code}: 未入选")

print("\n提示: 市值数据使用估算值（股价×100亿）")
print("      请查看股价、行业等信息判断是否为大盘股")
print("\n" + "="*70)