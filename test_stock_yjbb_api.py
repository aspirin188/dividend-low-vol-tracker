#!/usr/bin/env python3
"""
测试 akshare 其他获取ROE的接口
"""
import sys

print("检查 akshare 中可用的 ROE 数据接口...\n", flush=True)

try:
    import akshare as ak
    
    # 列出所有包含 'stock' 和 'roe' 或 '财务' 的函数
    print("查找相关函数...", flush=True)
    
    all_functions = [name for name in dir(ak) if not name.startswith('_')]
    
    # 可能包含财务数据的函数
    finance_funcs = [f for f in all_functions if any(kw in f.lower() for kw in ['fin', '财务', 'report', '业绩', 'roe', 'ratio'])]
    
    print(f"\n找到 {len(finance_funcs)} 个可能相关的函数:", flush=True)
    for f in finance_funcs[:20]:  # 只显示前20个
        print(f"  - {f}", flush=True)
    
    # 检查特定的接口
    print("\n检查特定接口:", flush=True)
    
    # 1. stock_financial_abstract - 财务摘要
    if hasattr(ak, 'stock_financial_abstract'):
        print("  ✓ stock_financial_abstract 存在", flush=True)
    
    # 2. stock_financial_report_sina - 新浪财务报表
    if hasattr(ak, 'stock_financial_report_sina'):
        print("  ✓ stock_financial_report_sina 存在", flush=True)
    
    # 3. stock_zyjs_ths - 同花顺财务摘要
    if hasattr(ak, 'stock_zyjs_ths'):
        print("  ✓ stock_zyjs_ths 存在", flush=True)
    
    # 4. stock_financial_analysis_indicator - 财务分析指标
    if hasattr(ak, 'stock_financial_analysis_indicator'):
        print("  ✓ stock_financial_analysis_indicator 存在", flush=True)
    
    # 测试 stock_financial_analysis_indicator
    print("\n尝试测试 stock_financial_analysis_indicator...", flush=True)
    try:
        # 这个接口可能返回ROE数据
        print("  调用: ak.stock_financial_analysis_indicator(symbol='000001')", flush=True)
        df = ak.stock_financial_analysis_indicator(symbol='000001')
        if df is not None and not df.empty:
            print(f"  ✓ 成功获取 {len(df)} 行数据", flush=True)
            print(f"  列名: {df.columns.tolist()[:10]}...", flush=True)
            if '净资产收益率' in df.columns or 'roe' in df.columns.str.lower():
                print("  ✓ 找到ROE相关字段!", flush=True)
        else:
            print("  ✗ 未获取到数据", flush=True)
    except Exception as e:
        print(f"  ✗ 错误: {e}", flush=True)
    
except Exception as e:
    print(f"\n❌ 错误: {e}", flush=True)
    import traceback
    traceback.print_exc()
