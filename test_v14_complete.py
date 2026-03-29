#!/usr/bin/env python3
"""
完整测试 v6.14 - 支付率数据修复
测试新的分红数据源（akshare stock_fhps_em）
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server.services.fetcher import fetch_dividend_from_akshare, fetch_eps_batch, merge_all_data
import pandas as pd

print("=" * 60)
print("完整测试 v6.14 - 支付率数据修复")
print("=" * 60)

# 测试1: 分红数据获取
print("\n【测试1】分红数据获取 - fetch_dividend_from_akshare()")
print("-" * 60)

try:
    div_df = fetch_dividend_from_akshare('2024')
    
    if not div_df.empty:
        print(f"✓ 成功获取 {len(div_df)} 只股票的分红数据")
        print(f"  有每股股利数据: {div_df['dividend_per_share'].notna().sum()}/{len(div_df)}")
        
        # 显示示例
        print("\n示例数据（有每股股利的前5条）:")
        sample = div_df[div_df['dividend_per_share'].notna()].head(5)
        for _, row in sample.iterrows():
            print(f"  {row['code']}: 每股股利={row['dividend_per_share']:.4f}元")
    else:
        print("✗ 未获取到分红数据")
        
except Exception as e:
    print(f"✗ 失败: {e}")
    import traceback
    traceback.print_exc()

# 测试2: 完整流程测试
print("\n【测试2】完整流程测试 - merge_all_data()")
print("-" * 60)
print("注意：完整流程需要几分钟，正在运行...")

try:
    import time
    start = time.time()
    
    result = merge_all_data()
    
    elapsed = time.time() - start
    print(f"\n✓ 完整流程完成，耗时: {elapsed:.2f}秒")
    
    if not result.empty:
        print(f"\n结果统计:")
        print(f"  总记录数: {len(result)}")
        print(f"  ROE数据: {result['roe'].notna().sum()}/{len(result)}")
        print(f"  支付率数据: {result['payout_ratio'].notna().sum()}/{len(result)}")
        print(f"  负债率数据: {result['debt_ratio'].notna().sum()}/{len(result)}")
        
        # 显示前10条数据
        print("\n前10条记录:")
        cols = ['code', 'name', 'dividend_yield_ttm', 'roe', 'payout_ratio', 'debt_ratio']
        display_cols = [col for col in cols if col in result.columns]
        
        for i, row in result.head(10).iterrows():
            info = f"  {row['code']} {row['name']}: 股息率={row['dividend_yield_ttm']:.2f}%, "
            info += f"ROE={row.get('roe', 'N/A')}, "
            info += f"支付率={row.get('payout_ratio', 'N/A')}, "
            info += f"负债率={row.get('debt_ratio', 'N/A')}"
            print(info)
    else:
        print("✗ 未获取到结果数据")
        
except Exception as e:
    print(f"✗ 失败: {e}")
    import traceback
    traceback.print_exc()

# 测试3: 检查数据库
print("\n【测试3】检查数据库数据")
print("-" * 60)

try:
    import sqlite3
    
    db_path = '/Users/macair/Work/workbuddy_dir/hl3/data/high_dividend.db'
    conn = sqlite3.connect(db_path)
    
    df = pd.read_sql_query("""
        SELECT code, name, dividend_yield_ttm, roe, payout_ratio, debt_ratio
        FROM results
        ORDER BY rank
        LIMIT 10
    """, conn)
    
    conn.close()
    
    if not df.empty:
        print(f"✓ 数据库中有 {len(df)} 条记录（前10条）")
        
        # 统计数据完整性
        roe_count = df['roe'].notna().sum()
        payout_count = df['payout_ratio'].notna().sum()
        debt_count = df['debt_ratio'].notna().sum()
        
        print(f"\n数据完整性（前10条）:")
        print(f"  ROE: {roe_count}/10")
        print(f"  支付率: {payout_count}/10")
        print(f"  负债率: {debt_count}/10")
        
        print("\n数据示例:")
        for _, row in df.iterrows():
            print(f"  {row['code']} {row['name']}: ROE={row['roe']}, 支付率={row['payout_ratio']}, 负债率={row['debt_ratio']}")
    else:
        print("⚠️ 数据库中暂无数据")
        
except Exception as e:
    print(f"✗ 失败: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
