#!/usr/bin/env python3
"""诊断股价百分位计算问题"""

import akshare as ak
from datetime import datetime, timedelta

print("=" * 60)
print("股价百分位计算诊断")
print("=" * 60)

code = '601939'  # 建设银行
days = 250

print(f"\n测试股票: {code}")
print(f"历史天数: {days}")
print("-" * 60)

try:
    print("\n步骤1: 调用akshare获取历史数据...")
    start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y%m%d')
    end_date = datetime.now().strftime('%Y%m%d')
    
    print(f"  开始日期: {start_date}")
    print(f"  结束日期: {end_date}")
    print(f"  复权方式: 前复权(qfq)")
    
    df = ak.stock_zh_a_hist(
        symbol=code,
        period='daily',
        start_date=start_date,
        end_date=end_date,
        adjust='qfq'
    )
    
    print(f"\n步骤2: 检查返回数据...")
    if df is None:
        print("  ✗ 返回None")
    elif len(df) == 0:
        print("  ✗ 返回空DataFrame")
    else:
        print(f"  ✓ 获取成功，共{len(df)}行数据")
        print(f"  列名: {df.columns.tolist()}")
        
        print(f"\n步骤3: 取最近{days}天数据...")
        df_tail = df.tail(days)
        print(f"  ✓ 取得{len(df_tail)}行数据")
        
        print(f"\n步骤4: 获取当前价格...")
        if '收盘' in df_tail.columns:
            current_price = float(df_tail['收盘'].iloc[-1])
            print(f"  ✓ 当前价格: {current_price}")
            
            print(f"\n步骤5: 计算百分位...")
            historical_prices = df_tail['收盘'].values
            lower_count = sum(historical_prices < current_price)
            percentile = (lower_count / len(historical_prices)) * 100
            print(f"  ✓ 股价百分位: {round(percentile, 2)}%")
            print(f"  当前价格高于历史{round(percentile, 2)}%的时间")
        else:
            print(f"  ✗ 没有找到'收盘'列")
            print(f"  可用列: {df_tail.columns.tolist()}")
    
except Exception as e:
    print(f"\n✗ 发生异常: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)
