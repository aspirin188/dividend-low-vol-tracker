#!/usr/bin/env python3
"""
v7.6 第二轮完整测试

验证系统稳定性和性能
"""

import sys
import time
sys.path.insert(0, '/Users/macair/Work/workbuddy_dir/hl3')

def main():
    print("\n" + "="*60)
    print("v7.6 第二轮完整测试")
    print("="*60 + "\n")
    
    from server.services.fetcher import merge_all_data
    
    # 运行测试
    start = time.time()
    result = merge_all_data()
    elapsed = time.time() - start
    
    # 验证结果
    print("\n" + "="*60)
    print("测试结果")
    print("="*60)
    
    print(f"\n✓ 耗时: {elapsed:.1f}秒 ({elapsed/60:.1f}分钟)")
    print(f"✓ 结果数量: {len(result)} 只候选股")
    
    if result.empty:
        print("\n✗ 测试失败：结果为空")
        return 1
    
    # 验证数据完整性
    print("\n数据完整性检查:")
    required_fields = ['code', 'name', 'price', 'eps', 'roe', 'div_yield']
    missing = [f for f in required_fields if f not in result.columns]
    
    if missing:
        print(f"  ✗ 缺少字段: {missing}")
        return 1
    else:
        print("  ✓ 所有必需字段存在")
    
    # 统计信息
    print("\n数据统计:")
    print(f"  - 平均股息率: {result['div_yield'].mean():.2f}%")
    print(f"  - 平均ROE: {result['roe'].mean():.2f}%")
    print(f"  - 平均EPS: {result['eps'].mean():.2f}")
    
    # 显示前5名
    print("\n股息率前5名:")
    top5 = result.nlargest(5, 'div_yield')
    for i, (_, row) in enumerate(top5.iterrows(), 1):
        print(f"  {i}. {row['code']} {row['name']}: {row['div_yield']:.2f}% (ROE {row['roe']:.2f}%)")
    
    # 性能验证
    if elapsed < 120:  # 2分钟内
        print("\n✓ 性能达标 (< 2分钟)")
        status = "优秀"
    elif elapsed < 180:  # 3分钟内
        print("\n✓ 性能良好 (< 3分钟)")
        status = "良好"
    else:
        print("\n⚠️ 性能需优化 (> 3分钟)")
        status = "一般"
    
    print("\n" + "="*60)
    print(f"✓ 第二轮测试完成 - 性能: {status}")
    print("="*60 + "\n")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
