#!/usr/bin/env python3
"""
测试新的数据源接口
v6.14: 测试stock_fhps_em和stock_financial_analysis_indicator接口
"""
import sys
import time

print("=" * 60)
print("测试新数据源接口 (v6.14)")
print("=" * 60)

# 测试1: 获取分红数据 (stock_fhps_em)
print("\n【测试1】获取分红数据 - akshare stock_fhps_em")
print("-" * 60)

try:
    import akshare as ak
    
    print("正在获取2024年分红数据...", end=' ', flush=True)
    start = time.time()
    
    # 获取分红配送数据
    df = ak.stock_fhps_em(date="20241231")
    
    elapsed = time.time() - start
    print(f"✓ 成功 (耗时: {elapsed:.2f}秒)")
    
    if df is not None and not df.empty:
        print(f"  总记录数: {len(df)}")
        print(f"  列名: {list(df.columns)}")
        
        # 筛选A股
        a_stock = df[df['股票代码'].str.startswith(('0', '3', '6'))]
        print(f"  A股数量: {len(a_stock)}")
        
        # 显示前5条
        print("\n  示例数据:")
        for idx, row in a_stock.head(5).iterrows():
            print(f"    {row['股票代码']} {row['股票简称']}: 每股股利={row.get('每股股利(元)', 'N/A')}")
        
        # 统计每股股利数据
        if '每股股利(元)' in df.columns:
            valid_dividend = df['每股股利(元)'].notna().sum()
            print(f"\n  有每股股利数据的股票: {valid_dividend}/{len(df)}")
    else:
        print("  ✗ 未获取到数据")
        
except Exception as e:
    print(f"✗ 失败: {e}")
    import traceback
    traceback.print_exc()

# 测试2: 获取财务指标 (stock_financial_analysis_indicator)
print("\n【测试2】获取财务指标 - akshare stock_financial_analysis_indicator")
print("-" * 60)

test_codes = ['601939', '600036', '601318']  # 建设银行、招商银行、中国平安

try:
    import akshare as ak
    
    for code in test_codes:
        print(f"\n获取 {code} 财务指标...", end=' ', flush=True)
        start = time.time()
        
        try:
            df = ak.stock_financial_analysis_indicator(symbol=code)
            
            elapsed = time.time() - start
            print(f"✓ 成功 (耗时: {elapsed:.2f}秒)")
            
            if df is not None and not df.empty:
                print(f"  总记录数: {len(df)}")
                print(f"  列名: {list(df.columns)[:10]}...")  # 显示前10列
                
                # 查找负债率列
                debt_cols = [col for col in df.columns if '负债' in col or '资产负债' in col]
                if debt_cols:
                    print(f"  找到负债率相关列: {debt_cols}")
                    
                    # 显示最新数据
                    latest = df.iloc[0] if len(df) > 0 else None
                    if latest is not None:
                        for col in debt_cols:
                            print(f"    {col}: {latest[col]}")
                else:
                    print("  ⚠️ 未找到负债率相关列")
                    
        except Exception as e:
            print(f"✗ 失败: {e}")
            
        time.sleep(0.5)  # 避免请求过快
        
except Exception as e:
    print(f"✗ 整体失败: {e}")
    import traceback
    traceback.print_exc()

# 测试3: 获取资产负债表数据
print("\n【测试3】获取资产负债表 - akshare stock_balance_sheet_by_report_em")
print("-" * 60)

try:
    import akshare as ak
    
    for code in test_codes[:1]:  # 只测试一个
        print(f"\n获取 {code} 资产负债表...", end=' ', flush=True)
        start = time.time()
        
        try:
            df = ak.stock_balance_sheet_by_report_em(symbol=code)
            
            elapsed = time.time() - start
            print(f"✓ 成功 (耗时: {elapsed:.2f}秒)")
            
            if df is not None and not df.empty:
                print(f"  总记录数: {len(df)}")
                print(f"  列名: {list(df.columns)[:10]}...")
                
                # 查找负债相关列
                debt_cols = [col for col in df.columns if '负债' in col]
                if debt_cols:
                    print(f"  找到负债相关列: {debt_cols[:5]}")
                    
        except Exception as e:
            print(f"✗ 失败: {e}")
            
        time.sleep(0.5)
        
except Exception as e:
    print(f"✗ 整体失败: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
