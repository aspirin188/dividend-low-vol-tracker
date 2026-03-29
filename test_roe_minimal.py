#!/usr/bin/env python3
"""
最小化测试 - 检查 akshare ROE 数据
使用更简单的方法，避免网络超时
"""
import sys
import signal

# 设置超时
def timeout_handler(signum, frame):
    print("\n❌ 超时! akshare调用可能卡住了", flush=True)
    sys.exit(1)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(60)  # 60秒超时

try:
    print("导入模块...", flush=True)
    import akshare as ak
    import pandas as pd
    print("✓ 导入成功", flush=True)
    
    print("\n尝试获取业绩报表...", flush=True)
    # 使用 try-except 捕获所有异常
    df = None
    for date_str in ['20241231', '20231231']:
        try:
            print(f"  尝试日期: {date_str}", flush=True)
            df = ak.stock_yjbb_em(date=date_str)
            if df is not None and not df.empty:
                print(f"  ✓ 成功获取 {len(df)} 行", flush=True)
                break
        except Exception as e:
            print(f"  ✗ 失败: {e}", flush=True)
            continue
    
    if df is None or df.empty:
        print("\n❌ 无法获取数据", flush=True)
        sys.exit(1)
    
    print(f"\n列名: {df.columns.tolist()}", flush=True)
    
    # 检查ROE
    if '净资产收益率' in df.columns:
        print("\n✅ 找到'净资产收益率'列", flush=True)
        
        # 测试几只股票
        test_codes = ['601939', '600036']
        for code in test_codes:
            row = df[df['股票代码'] == code]
            if not row.empty:
                print(f"  {code}: ROE={row['净资产收益率'].values[0]}", flush=True)
    else:
        print("\n❌ 未找到'净资产收益率'列", flush=True)
        
    signal.alarm(0)  # 取消超时
    print("\n✓ 测试完成", flush=True)
    
except Exception as e:
    print(f"\n❌ 错误: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)
