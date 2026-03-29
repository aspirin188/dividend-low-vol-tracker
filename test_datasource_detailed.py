#!/usr/bin/env python3
"""
详细测试数据源接口 - v6.14
"""
import akshare as ak
import pandas as pd

print("=" * 60)
print("详细测试数据源接口")
print("=" * 60)

# 测试1: 分红数据 - 获取每股股利
print("\n【测试1】分红数据详细分析")
print("-" * 60)

try:
    df = ak.stock_fhps_em(date="20241231")
    print(f"✓ 获取到 {len(df)} 条记录")
    print(f"列名: {list(df.columns)}")
    
    # 筛选A股
    a_stock = df[df['代码'].str.startswith(('0', '3', '6'))].copy()
    print(f"A股数量: {len(a_stock)}")
    
    # 计算每股股利（现金分红比例 / 10）
    # 假设: "现金分红-现金分红比例" 是每10股派息金额
    if '现金分红-现金分红比例' in a_stock.columns:
        a_stock['每股股利'] = pd.to_numeric(a_stock['现金分红-现金分红比例'], errors='coerce') / 10
        valid = a_stock['每股股利'].notna().sum()
        print(f"有每股股利数据的股票: {valid}/{len(a_stock)}")
        
        # 显示示例
        print("\n示例数据（前10条）:")
        sample = a_stock[a_stock['每股股利'].notna()].head(10)
        for _, row in sample.iterrows():
            print(f"  {row['代码']} {row['名称']}: 每股股利={row['每股股利']:.4f}元")
    
except Exception as e:
    print(f"✗ 失败: {e}")
    import traceback
    traceback.print_exc()

# 测试2: 财务指标 - 获取负债率
print("\n【测试2】财务指标详细分析")
print("-" * 60)

test_codes = ['601939', '600036', '601318', '000001', '000895']

for code in test_codes:
    print(f"\n{code}:")
    try:
        df = ak.stock_financial_analysis_indicator(symbol=code)
        
        if df is not None and not df.empty:
            # 查找资产负债率列
            if '资产负债率(%)' in df.columns:
                # 获取最近几期的数据
                df['资产负债率(%)'] = pd.to_numeric(df['资产负债率(%)'], errors='coerce')
                
                # 显示前5期数据
                recent = df[df['资产负债率(%)'].notna()].head(5)
                if not recent.empty:
                    print(f"  ✓ 找到负债率数据")
                    for _, row in recent.iterrows():
                        print(f"    {row['日期']}: 资产负债率={row['资产负债率(%)']:.2f}%")
                else:
                    print(f"  ✗ 无有效负债率数据")
            else:
                print(f"  ✗ 未找到'资产负债率(%)'列")
                
    except Exception as e:
        print(f"  ✗ 失败: {e}")
    
    import time
    time.sleep(0.3)

# 测试3: 综合计算支付率
print("\n【测试3】支付率计算验证")
print("-" * 60)

try:
    # 获取分红数据
    div_df = ak.stock_fhps_em(date="20241231")
    div_df = div_df[div_df['代码'].str.startswith(('0', '3', '6'))].copy()
    div_df['每股股利'] = pd.to_numeric(div_df['现金分红-现金分红比例'], errors='coerce') / 10
    
    # 获取EPS数据
    eps_df = ak.stock_yjbb_em(date="20241231")
    eps_df = eps_df[eps_df['股票代码'].str.startswith(('0', '3', '6'))].copy()
    eps_df['每股收益'] = pd.to_numeric(eps_df['每股收益'], errors='coerce')
    
    # 合并数据
    merged = div_df.merge(eps_df, left_on='代码', right_on='股票代码', how='inner')
    
    # 计算支付率
    merged['支付率'] = None
    mask = (merged['每股股利'].notna()) & (merged['每股收益'] > 0)
    merged.loc[mask, '支付率'] = (merged.loc[mask, '每股股利'] / merged.loc[mask, '每股收益'] * 100).round(2)
    
    valid_payout = merged['支付率'].notna().sum()
    print(f"✓ 成功计算 {valid_payout}/{len(merged)} 只股票的支付率")
    
    # 显示示例
    print("\n示例数据（前10条）:")
    sample = merged[merged['支付率'].notna()].head(10)
    for _, row in sample.iterrows():
        print(f"  {row['代码']} {row['名称']}: 每股股利={row['每股股利']:.4f}, EPS={row['每股收益']:.2f}, 支付率={row['支付率']:.2f}%")
    
except Exception as e:
    print(f"✗ 失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
