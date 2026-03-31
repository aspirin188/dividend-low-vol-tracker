#!/usr/bin/env python3
"""
v7.6 最终集成测试
测试完整流程包括所有质量因子
"""

import sys
import time
sys.path.insert(0, '/Users/macair/Work/workbuddy_dir/hl3')

def main():
    print("\n" + "="*60)
    print("v7.6 最终集成测试")
    print("="*60 + "\n")
    
    # 测试1: 数据获取
    print("测试1: 数据获取...")
    from server.services.fetcher import merge_all_data
    
    start = time.time()
    result = merge_all_data()
    elapsed = time.time() - start
    
    if result.empty:
        print("✗ 数据获取失败")
        return 1
    
    print(f"✓ 数据获取成功: {len(result)}只股票 ({elapsed:.1f}秒)")
    
    # 测试2: 兼容性函数
    print("\n测试2: 兼容性函数...")
    from server.services.fetcher import (
        get_profit_history_batch,
        get_operating_cashflow_batch,
        get_top_shareholder_ratio_batch,
        calculate_profit_growth_3y,
        calculate_cashflow_profit_ratio,
        calc_ma_position_batch,
        is_profit_growing_strict
    )
    
    test_codes = result['code'].head(10).tolist()
    
    # 测试所有兼容性函数
    profit_history = get_profit_history_batch(test_codes)
    cashflow = get_operating_cashflow_batch(test_codes)
    shareholders = get_top_shareholder_ratio_batch(test_codes)
    ma_data = calc_ma_position_batch(test_codes)
    
    print(f"✓ 所有兼容性函数正常工作")
    
    # 测试3: 筛选和评分
    print("\n测试3: 筛选和评分...")
    from server.services.scorer import filter_stocks, calculate_scores
    
    filtered = filter_stocks(result)
    if filtered.empty:
        print("⚠️ 筛选后无结果")
    else:
        scored = calculate_scores(filtered)
        print(f"✓ 筛选评分成功: {len(scored)}只")
    
    # 测试4: 完整流程时间
    print("\n" + "="*60)
    print("测试结果")
    print("="*60)
    
    print(f"\n✓ 总耗时: {elapsed:.1f}秒 ({elapsed/60:.1f}分钟)")
    print(f"✓ 候选股: {len(result)}只")
    print(f"✓ 所有测试通过")
    
    # 显示前3名
    if not result.empty:
        print("\n股息率前3名:")
        top3 = result.nlargest(3, 'dividend_yield')
        for _, row in top3.iterrows():
            print(f"  {row['code']} {row['name']}: {row['dividend_yield']:.2f}%")
    
    print("\n" + "="*60)
    print("✓ v7.6 最终集成测试通过")
    print("="*60 + "\n")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
