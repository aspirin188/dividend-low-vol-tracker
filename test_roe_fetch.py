#!/usr/bin/env python3
"""测试ROE数据获取"""
import sys
sys.path.insert(0, '.')

import akshare as ak

print("测试 akshare stock_yjbb_em 接口...")

try:
    df = ak.stock_yjbb_em(date='20241231')
    print(f"成功获取 {len(df)} 条数据")
    print(f"列名: {df.columns.tolist()}")
    
    # 检查ROE字段
    if '净资产收益率' in df.columns:
        print("\\n✅ '净资产收益率' 字段存在")
        # 只保留A股
        df_a = df[df['股票代码'].str.startswith(('0', '3', '6'))].copy()
        print(f"A股数量: {len(df_a)}")
        
        # 检查ROE数据
        roe_notna = df_a['净资产收益率'].notna().sum()
        print(f"ROE非空数量: {roe_notna}")
        
        # 示例数据
        print("\\n示例数据（前10个有ROE的）:")
        sample = df_a[df_a['净资产收益率'].notna()][['股票代码', '股票简称', '每股收益', '净资产收益率']].head(10)
        print(sample.to_string(index=False))
    else:
        print("\\n❌ '净资产收益率' 字段不存在")
        print("可用字段:", df.columns.tolist())
        
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
