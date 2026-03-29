"""测试akshare财务数据接口"""
import akshare as ak
import pandas as pd

print("=" * 60)
print("查找akshare财务接口")
print("=" * 60)

# 查找相关接口
funcs = [f for f in dir(ak) if 'financial' in f.lower()]
print(f"\n包含'financial'的接口 ({len(funcs)}个):")
for f in sorted(funcs)[:20]:
    print(f"  - {f}")

print("\n" + "=" * 60)
print("测试具体接口")
print("=" * 60)

# 测试接口
test_code = '601939'  # 建设银行

# 1. stock_financial_report_sina
print("\n1. stock_financial_report_sina:")
try:
    df = ak.stock_financial_report_sina(stock=f"sh{test_code}", symbol="资产负债表")
    print(f"   ✓ 成功！列: {list(df.columns)[:10]}")
    print(f"   行数: {len(df)}")
    if not df.empty:
        print(f"   第一行数据:")
        print(df.head(1).to_string())
except Exception as e:
    print(f"   ✗ 失败: {e}")

# 2. stock_financial_analysis_indicator
print("\n2. stock_financial_analysis_indicator:")
try:
    df = ak.stock_financial_analysis_indicator(symbol=test_code)
    print(f"   ✓ 成功！列: {list(df.columns)[:10]}")
    print(f"   行数: {len(df)}")
    if not df.empty:
        print(f"   第一行数据:")
        print(df.head(1).to_string())
except Exception as e:
    print(f"   ✗ 失败: {e}")

# 3. stock_yjbb_em (已知可用)
print("\n3. stock_yjbb_em (参考):")
try:
    df = ak.stock_yjbb_em(date="20240930")
    row = df[df['股票代码'] == test_code]
    if not row.empty:
        print(f"   ✓ 成功！ROE={row['ROE'].values[0]}, EPS={row['每股收益'].values[0]}")
except Exception as e:
    print(f"   ✗ 失败: {e}")

print("\n" + "=" * 60)
