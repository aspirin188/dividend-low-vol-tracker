#!/usr/bin/env python3
"""
本地测试 - 完整流程
"""
import sys
import os

# 设置环境
os.environ['FLASK_APP'] = 'app'
os.environ['FLASK_ENV'] = 'development'

sys.path.insert(0, '.')

print("=" * 60, flush=True)
print("完整流程本地测试", flush=True)
print("=" * 60, flush=True)

try:
    from server.services.fetcher import merge_all_data
    from server.services.scorer import filter_stocks, calculate_scores, prepare_results
    
    print("\n[1] 获取数据...", flush=True)
    merged = merge_all_data()
    
    if merged.empty:
        print("✗ 未获取到数据", flush=True)
        sys.exit(1)
    
    print(f"✓ 获取 {len(merged)} 条数据", flush=True)
    print(f"ROE非空: {merged['roe'].notna().sum()}/{len(merged)}", flush=True)
    
    print("\n[2] 筛选数据...", flush=True)
    filtered = filter_stocks(merged)
    print(f"✓ 筛选后 {len(filtered)} 条", flush=True)
    
    if filtered.empty:
        print("✗ 没有符合条件的股票", flush=True)
        # 检查原因
        print("\n检查筛选条件:", flush=True)
        print(f"  股息率>=3%: {(merged['dividend_yield_ttm'] >= 3.0).sum()}", flush=True)
        print(f"  市值>=500亿: {(merged['market_cap'] >= 500.0).sum()}", flush=True)
        print(f"  EPS>0: {(merged['basic_eps'] > 0).sum()}", flush=True)
        print(f"  ROE>=8%: {(merged['roe'] >= 8.0).sum()}", flush=True)
        print(f"  ROE非空: {merged['roe'].notna().sum()}", flush=True)
        sys.exit(1)
    
    print("\n[3] 计算评分...", flush=True)
    scored = calculate_scores(filtered)
    print(f"✓ 评分完成", flush=True)
    
    print("\n[4] 整理结果...", flush=True)
    result = prepare_results(scored)
    print(f"✓ 整理完成", flush=True)
    
    # 检查ROE数据
    print("\n[5] 检查ROE数据...", flush=True)
    roe_not_null = result['roe'].notna().sum()
    print(f"ROE非空: {roe_not_null}/{len(result)}", flush=True)
    
    if roe_not_null > 0:
        print("\n前5条数据:", flush=True)
        print(result[['code', 'name', 'dividend_yield', 'roe', 'debt_ratio']].head(), flush=True)
        
        print("\n" + "=" * 60, flush=True)
        print("✓✓✓ 测试成功! ROE数据正常 ✓✓✓", flush=True)
        print("=" * 60, flush=True)
    else:
        print("\n✗ ROE数据全部为空", flush=True)
        sys.exit(1)
        
except Exception as e:
    print(f"\n✗ 测试失败: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)
