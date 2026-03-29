#!/usr/bin/env python3
"""
详细测试运行流程 - 捕获所有异常
"""
import sys
import traceback

print("=" * 60)
print("开始详细测试...")
print("=" * 60)

try:
    print("\n[1] 导入模块...")
    from server.services.fetcher import merge_all_data
    from server.services.scorer import filter_stocks, calculate_scores, prepare_results
    print("✓ 模块导入成功")
    
    print("\n[2] 获取数据...")
    merged = merge_all_data()
    print(f"✓ 获取到 {len(merged)} 条数据")
    
    if merged.empty:
        print("✗ 未获取到任何数据")
        sys.exit(1)
    
    print("\n[3] 筛选数据...")
    print(f"筛选前字段: {list(merged.columns)}")
    filtered = filter_stocks(merged)
    print(f"✓ 筛选后 {len(filtered)} 条")
    
    if filtered.empty:
        print("✗ 没有符合条件的股票")
        sys.exit(1)
    
    print("\n[4] 计算评分...")
    scored = calculate_scores(filtered)
    print(f"✓ 评分完成，共 {len(scored)} 条")
    
    print("\n[5] 整理结果...")
    result = prepare_results(scored)
    print(f"✓ 结果整理完成")
    print(f"\n前3条数据:")
    print(result[['code', 'name', 'dividend_yield', 'composite_score', 'roe', 'debt_ratio']].head(3))
    
    print("\n" + "=" * 60)
    print("✓ 测试全部通过！")
    print("=" * 60)
    
except Exception as e:
    print("\n" + "=" * 60)
    print(f"✗ 发生错误: {e}")
    print("=" * 60)
    traceback.print_exc()
    sys.exit(1)
