#!/usr/bin/env python3
"""
完整本地测试 - 捕获所有错误
"""
import sys
import os
import traceback

os.environ['FLASK_APP'] = 'app'
os.environ['FLASK_ENV'] = 'development'
sys.path.insert(0, '.')

print("=" * 80)
print("完整本地测试 - 查找所有错误")
print("=" * 80)

try:
    print("\n[步骤1] 导入模块...")
    from server.services.fetcher import merge_all_data
    from server.services.scorer import filter_stocks, calculate_scores, prepare_results
    print("✓ 导入成功")

    print("\n[步骤2] 运行 merge_all_data()...")
    merged = merge_all_data()

    if merged.empty:
        print("✗ merge_all_data() 返回空数据")
        sys.exit(1)

    print(f"✓ 获取到 {len(merged)} 条数据")
    print(f"列名: {list(merged.columns)}")

    # 检查关键字段
    print("\n[步骤3] 检查关键字段...")
    for col in ['roe', 'payout_ratio', 'debt_ratio', 'dividend_per_share', 'basic_eps']:
        if col in merged.columns:
            dtype = merged[col].dtype
            not_null = merged[col].notna().sum()
            print(f"  {col}: dtype={dtype}, 非空={not_null}/{len(merged)}")
        else:
            print(f"  {col}: ❌ 列不存在")

    print("\n[步骤4] 运行 filter_stocks()...")
    filtered = filter_stocks(merged)
    print(f"✓ 筛选后 {len(filtered)} 条")

    if filtered.empty:
        print("✗ 筛选后无数据")
        sys.exit(1)

    print("\n[步骤5] 运行 calculate_scores()...")
    scored = calculate_scores(filtered)
    print(f"✓ 评分完成")

    print("\n[步骤6] 运行 prepare_results()...")
    result = prepare_results(scored)
    print(f"✓ 整理完成")

    print("\n[步骤7] 检查最终结果...")
    print(f"总行数: {len(result)}")
    for col in ['roe', 'payout_ratio', 'debt_ratio']:
        if col in result.columns:
            not_null = result[col].notna().sum()
            print(f"  {col}: 非空={not_null}/{len(result)}")
        else:
            print(f"  {col}: ❌ 列不存在")

    print("\n前3行数据:")
    print(result[['code', 'name', 'dividend_yield', 'roe', 'payout_ratio', 'debt_ratio']].head(3))

    print("\n" + "=" * 80)
    print("✅✅✅ 测试成功！所有步骤完成！")
    print("=" * 80)

except Exception as e:
    print("\n" + "=" * 80)
    print(f"❌ 错误: {e}")
    print("=" * 80)
    traceback.print_exc()
    sys.exit(1)
