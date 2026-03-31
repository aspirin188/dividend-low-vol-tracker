#!/usr/bin/env python3
"""
v7.5 性能诊断和测试

彻底检查所有性能瓶颈和错误
"""

import sys
import time
sys.path.insert(0, '/Users/macair/Work/workbuddy_dir/hl3')

def test_eps_only():
    """测试1: 仅EPS数据获取"""
    print("\n" + "="*60)
    print("测试1: EPS数据获取性能")
    print("="*60)
    
    from server.services.fetcher import fetch_eps_batch
    
    start = time.time()
    eps_df = fetch_eps_batch()
    elapsed = time.time() - start
    
    print(f"✓ 耗时: {elapsed:.2f}秒")
    print(f"✓ 数量: {len(eps_df)}")
    return elapsed < 10  # 应该在10秒内完成


def test_quotes_only():
    """测试2: 仅行情获取"""
    print("\n" + "="*60)
    print("测试2: 新浪行情获取性能")
    print("="*60)
    
    from server.services.fetcher import fetch_eps_batch, _fetch_quotes_batch_sina
    
    # 先获取EPS
    eps_df = fetch_eps_batch()
    if eps_df.empty:
        print("✗ 无法获取EPS数据")
        return False
    
    # 测试500只股票
    test_codes = eps_df['code'].head(500).tolist()
    
    start = time.time()
    quotes = _fetch_quotes_batch_sina(test_codes, batch_size=100)
    elapsed = time.time() - start
    
    print(f"✓ 耗时: {elapsed:.2f}秒")
    print(f"✓ 数量: {len(quotes)}/500")
    print(f"✓ 平均速度: {len(quotes)/elapsed:.1f}只/秒")
    
    return elapsed < 10  # 应该在10秒内完成


def test_dividend_only():
    """测试3: 分红数据获取"""
    print("\n" + "="*60)
    print("测试3: 分红数据获取")
    print("="*60)
    
    from server.services.fetcher import fetch_dividend_from_akshare
    
    start = time.time()
    div_df = fetch_dividend_from_akshare('2024')
    elapsed = time.time() - start
    
    print(f"✓ 耗时: {elapsed:.2f}秒")
    print(f"✓ 数量: {len(div_df)}")
    
    return elapsed < 10  # 应该在10秒内完成


def test_full_flow():
    """测试4: 完整流程（简化版）"""
    print("\n" + "="*60)
    print("测试4: 完整流程性能")
    print("="*60)
    
    from server.services.fetcher import merge_all_data
    
    start = time.time()
    result = merge_all_data()
    elapsed = time.time() - start
    
    print(f"\n✓ 总耗时: {elapsed:.2f}秒 ({elapsed/60:.1f}分钟)")
    print(f"✓ 结果数量: {len(result)}")
    
    if not result.empty:
        print("\n前3名高股息股票:")
        top3 = result.nlargest(3, 'dividend_yield')
        for _, row in top3.iterrows():
            print(f"  {row['code']} {row['name']}: 股息率{row['dividend_yield']:.2f}%")
    
    return elapsed < 300  # 应该在5分钟内完成


def main():
    print("\n" + "="*60)
    print("v7.5 完整性能诊断测试")
    print("="*60)
    
    tests = [
        ("EPS获取", test_eps_only),
        ("行情获取", test_quotes_only),
        ("分红获取", test_dividend_only),
        ("完整流程", test_full_flow),
    ]
    
    results = {}
    total_start = time.time()
    
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n✗ 测试 '{name}' 失败: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False
    
    total_elapsed = time.time() - total_start
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    for name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{name}: {status}")
    
    print(f"\n总耗时: {total_elapsed:.1f}秒 ({total_elapsed/60:.1f}分钟)")
    
    passed = sum(results.values())
    total = len(results)
    
    print(f"\n通过率: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print("\n⚠️ 存在失败项，需要修复")
        return 1


if __name__ == '__main__':
    sys.exit(main())
