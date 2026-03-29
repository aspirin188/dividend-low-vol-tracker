"""
测试ROE数据获取的详细流程
"""
import pandas as pd
import akshare as ak
from server.services.fetcher import fetch_eps_batch, fetch_all_quotes

print("=" * 60)
print("测试1: 直接调用 akshare.stock_yjbb_em 获取ROE")
print("=" * 60)

try:
    df = ak.stock_yjbb_em(date='20241231')
    print(f"✓ 成功获取 {len(df)} 行数据")
    print(f"列名: {df.columns.tolist()}")
    
    # 检查是否有"净资产收益率"列
    if '净资产收益率' in df.columns:
        print("✓ 找到'净资产收益率'列")
        # 查看几个示例
        sample_codes = ['601939', '600036', '601318', '601288', '000651']
        for code in sample_codes:
            row = df[df['股票代码'] == code]
            if not row.empty:
                print(f"  {code} {row['股票简称'].values[0]}: ROE={row['净资产收益率'].values[0]}")
    else:
        print("✗ 未找到'净资产收益率'列")
        
except Exception as e:
    print(f"✗ 失败: {e}")

print("\n" + "=" * 60)
print("测试2: 调用 fetch_eps_batch() 函数")
print("=" * 60)

try:
    eps_df = fetch_eps_batch()
    print(f"✓ 成功获取 {len(eps_df)} 行数据")
    print(f"列名: {eps_df.columns.tolist()}")
    
    # 检查ROE数据
    if 'roe' in eps_df.columns:
        roe_not_null = eps_df[eps_df['roe'].notna()]
        print(f"✓ ROE非空: {len(roe_not_null)}/{len(eps_df)}")
        
        # 查看几个示例
        sample_codes = ['601939', '600036', '601318', '601288', '000651']
        for code in sample_codes:
            row = eps_df[eps_df['code'] == code]
            if not row.empty:
                print(f"  {code}: EPS={row['basic_eps'].values[0]}, ROE={row['roe'].values[0]}")
    else:
        print("✗ 未找到'roe'列")
        
except Exception as e:
    print(f"✗ 失败: {e}")

print("\n" + "=" * 60)
print("测试3: 检查 merge_all_data 流程中的ROE")
print("=" * 60)

try:
    # 获取行情
    quotes = fetch_all_quotes()
    print(f"✓ 获取行情 {len(quotes)} 只股票")
    
    # 获取EPS+ROE
    eps_df = fetch_eps_batch()
    print(f"✓ 获取EPS+ROE {len(eps_df)} 只股票")
    
    # 合并
    merged = quotes.merge(eps_df, on='code', how='left')
    print(f"✓ 合并后 {len(merged)} 行")
    
    # 检查ROE数据
    roe_not_null = merged[merged['roe'].notna()]
    print(f"✓ 合并后ROE非空: {len(roe_not_null)}/{len(merged)}")
    
    # 查看几个示例
    sample_codes = ['601939', '600036', '601318', '601288', '000651']
    for code in sample_codes:
        row = merged[merged['code'] == code]
        if not row.empty:
            name = row['name'].values[0]
            eps = row['basic_eps'].values[0]
            roe = row['roe'].values[0]
            print(f"  {code} {name}: EPS={eps}, ROE={roe}")
    
    # 初步筛选（市值>=500, EPS>0, 非ST）
    merged = merged[~merged['name'].str.contains('ST', case=False, na=False)]
    for col in ['market_cap', 'basic_eps']:
        merged[col] = pd.to_numeric(merged[col], errors='coerce')
    
    pre_filtered = merged[
        (merged['market_cap'] >= 500.0) &
        (merged['basic_eps'] > 0) &
        (merged['market_cap'].notna()) &
        (merged['basic_eps'].notna()) &
        (merged['price'].notna()) &
        (merged['price'] > 0)
    ].copy()
    
    print(f"\n初筛后: {len(pre_filtered)} 只候选股")
    
    # 检查初筛后的ROE
    roe_not_null = pre_filtered[pre_filtered['roe'].notna()]
    print(f"初筛后ROE非空: {len(roe_not_null)}/{len(pre_filtered)}")
    
    # ROE>=8%的股票
    roe_filtered = pre_filtered[pre_filtered['roe'] >= 8.0]
    print(f"ROE>=8%: {len(roe_filtered)} 只")
    
    if len(roe_filtered) > 0:
        print("\n前10只ROE>=8%的股票:")
        print(roe_filtered[['code', 'name', 'roe', 'market_cap']].head(10))
    else:
        print("\n✗ 没有股票ROE>=8%，这是问题所在！")
        
except Exception as e:
    print(f"✗ 失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
