#!/usr/bin/env python3
"""
测试 akshare stock_yjbb_em 接口的 ROE 数据
直接打印，不依赖复杂的逻辑
"""
import sys
import pandas as pd

print("开始测试 akshare stock_yjbb_em 接口...", flush=True)
print("这可能需要几秒钟...", flush=True)

try:
    import akshare as ak
    print("✓ akshare 导入成功", flush=True)
    
    print("\n正在调用 ak.stock_yjbb_em(date='20241231')...", flush=True)
    df = ak.stock_yjbb_em(date='20241231')
    print(f"✓ 成功获取 {len(df)} 行数据", flush=True)
    
    print(f"\n列名: {df.columns.tolist()}", flush=True)
    
    # 检查ROE列
    if '净资产收益率' in df.columns:
        print("\n✅ 找到'净资产收益率'列", flush=True)
        
        # 检查A股
        df_a = df[df['股票代码'].str.startswith(('0', '3', '6'))].copy()
        print(f"A股数量: {len(df_a)}", flush=True)
        
        # ROE统计
        roe_series = pd.to_numeric(df_a['净资产收益率'], errors='coerce')
        roe_notna = roe_series.notna().sum()
        print(f"ROE非空: {roe_notna}/{len(df_a)}", flush=True)
        
        # 示例股票
        test_codes = ['601939', '600036', '601318', '000651', '601288']
        print(f"\n测试股票ROE数据:", flush=True)
        for code in test_codes:
            row = df_a[df_a['股票代码'] == code]
            if not row.empty:
                name = row['股票简称'].values[0]
                roe = row['净资产收益率'].values[0]
                print(f"  {code} {name}: ROE={roe}", flush=True)
        
        # ROE>=8%的数量
        roe_ge_8 = (roe_series >= 8.0).sum()
        print(f"\nROE>=8%的A股数量: {roe_ge_8}", flush=True)
        
    else:
        print("\n❌ 未找到'净资产收益率'列", flush=True)
        print(f"可用列: {df.columns.tolist()}", flush=True)
        
except Exception as e:
    print(f"\n❌ 错误: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✓ 测试完成", flush=True)
