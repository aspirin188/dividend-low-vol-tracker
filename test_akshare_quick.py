#!/usr/bin/env python3
"""快速测试akshare ROE接口"""
import akshare as ak

print("尝试获取2024年报数据...")
try:
    df = ak.stock_yjbb_em(date='20241231')
    print(f"成功! 获取 {len(df)} 条")
    print(f"列名: {df.columns.tolist()[:10]}")  # 只看前10列
    
    # 检查是否有ROE
    if '净资产收益率' in df.columns:
        print("\\n✅ 找到'净资产收益率'字段")
        # 检查招商银行
        cmb = df[df['股票代码'] == '600036']
        if not cmb.empty:
            print(f"招商银行ROE: {cmb['净资产收益率'].values[0]}")
    else:
        print("\\n❌ 没有'净资产收益率'字段")
        
except Exception as e:
    print(f"失败: {e}")
    
    # 尝试2023年
    print("\\n尝试2023年报...")
    try:
        df = ak.stock_yjbb_em(date='20231231')
        print(f"成功! 获取 {len(df)} 条")
        print(f"列名: {df.columns.tolist()[:10]}")
    except Exception as e2:
        print(f"也失败: {e2}")
