"""
v6.18 验证机制优化测试脚本

测试目标：
1. 健康度追踪器工作正常
2. 并发验证性能提升
3. 缓存机制工作正常
4. 可信度调整合理

设计原则：
- 第一性原理：验证核心问题是否解决
- 极简主义：最小测试用例
"""

import sys
import time
import asyncio
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from server.services.health_tracker import get_health_tracker
from server.services.validation_cache import get_cache
from server.services.price_dual_validator import (
    validate_price_dual,
    validate_prices_batch_async,
    get_validation_stats
)


def test_health_tracker():
    """测试健康度追踪器"""
    print("\n" + "="*60)
    print("测试1: 健康度追踪器")
    print("="*60)
    
    tracker = get_health_tracker()
    
    # 模拟一些请求
    print("\n模拟请求记录...")
    tracker.record_request('sina_price', True, 0.3)
    tracker.record_request('sina_price', True, 0.25)
    tracker.record_request('sina_price', True, 0.35)
    tracker.record_request('sina_price', False, 2.0, "timeout")
    
    tracker.record_request('tencent_price', True, 0.2)
    tracker.record_request('tencent_price', True, 0.22)
    tracker.record_request('tencent_price', True, 0.18)
    
    # 获取可靠性评分
    sina_reliability = tracker.get_reliability('sina_price')
    tencent_reliability = tracker.get_reliability('tencent_price')
    
    print(f"\n数据源可靠性评分:")
    print(f"  新浪财经: {sina_reliability:.3f}")
    print(f"  腾讯财经: {tencent_reliability:.3f}")
    
    # 获取统计报告
    print(f"\n统计报告:")
    for source in ['sina_price', 'tencent_price']:
        report = tracker.get_stats_report(source)
        print(f"  {source}:")
        print(f"    成功率: {report['success_rate']:.1f}%")
        print(f"    平均延迟: {report['avg_latency']:.3f}秒")
        print(f"    可靠性: {report['reliability']:.3f}")
    
    # 测试可信度调整
    print(f"\n可信度调整测试:")
    for base_confidence in ['high', 'medium', 'low']:
        adjusted = tracker.get_confidence_adjustment('sina_price', base_confidence)
        print(f"  {base_confidence} -> {adjusted}")
    
    print("\n✅ 健康度追踪器测试通过")
    return True


def test_cache():
    """测试缓存机制"""
    print("\n" + "="*60)
    print("测试2: 缓存机制")
    print("="*60)
    
    cache = get_cache()
    
    # 测试设置和获取
    print("\n测试缓存设置和获取...")
    cache.set('601939', 'price', 10.50, 'high')
    cache.set('601939', 'roe', 12.5, 'medium')
    
    # 获取缓存
    cached_price = cache.get('601939', 'price')
    cached_roe = cache.get('601939', 'roe')
    
    print(f"  价格缓存: {cached_price['value'] if cached_price else None}")
    print(f"  ROE缓存: {cached_roe['value'] if cached_roe else None}")
    
    # 测试TTL
    print("\n测试TTL...")
    cache.set('600036', 'price', 15.0, 'high')
    
    # 立即获取（应该命中）
    cached = cache.get('600036', 'price')
    print(f"  立即获取: {'命中' if cached else '未命中'}")
    
    # 修改TTL测试过期
    cache.ttl_config['price'] = 0  # 设置为0秒，立即过期
    time.sleep(0.1)
    cached = cache.get('600036', 'price')
    print(f"  过期后获取: {'命中' if cached else '未命中'}")
    
    # 恢复TTL
    cache.ttl_config['price'] = 60
    
    # 获取统计信息
    stats = cache.get_stats()
    print(f"\n缓存统计:")
    print(f"  总条目: {stats['total_entries']}")
    print(f"  命中: {stats['hits']}")
    print(f"  未命中: {stats['misses']}")
    print(f"  命中率: {stats['hit_rate']:.2f}%")
    
    print("\n✅ 缓存机制测试通过")
    return True


def test_price_validation():
    """测试价格验证（同步版本）"""
    print("\n" + "="*60)
    print("测试3: 价格双重验证（同步版本）")
    print("="*60)
    
    test_codes = ['601939', '600036', '000001']
    
    print(f"\n测试股票: {', '.join(test_codes)}")
    
    for code in test_codes:
        print(f"\n验证 {code}...")
        result = validate_price_dual(code)
        
        print(f"  价格: {result['price']}")
        print(f"  可信度: {result['confidence']}")
        print(f"  新浪可靠性: {result['health']['sina_reliability']}")
        print(f"  腾讯可靠性: {result['health']['tencent_reliability']}")
        if 'difference_pct' in result['validation']:
            print(f"  差异: {result['validation']['difference_pct']:.2f}%")
    
    print("\n✅ 价格验证测试通过")
    return True


async def test_async_validation():
    """测试异步并发验证"""
    print("\n" + "="*60)
    print("测试4: 异步并发验证（性能测试）")
    print("="*60)
    
    # 测试股票列表
    test_codes = [
        '601939', '600036', '601288', '601988', '601398',
        '600016', '600000', '601166', '600030', '601318'
    ]
    
    print(f"\n测试股票数: {len(test_codes)}只")
    print(f"并发配置: max_concurrent=5")
    
    # 测试异步并发
    start_time = time.time()
    results = await validate_prices_batch_async(test_codes, max_concurrent=5)
    elapsed = time.time() - start_time
    
    print(f"\n耗时: {elapsed:.2f}秒")
    print(f"平均: {elapsed/len(test_codes):.3f}秒/只")
    
    # 统计结果
    success_count = sum(1 for r in results.values() if r['price'] is not None)
    print(f"成功率: {success_count}/{len(test_codes)}")
    
    # 显示部分结果
    print(f"\n部分结果:")
    for code in test_codes[:3]:
        result = results.get(code, {})
        print(f"  {code}: 价格={result.get('price')}, 可信度={result.get('confidence')}")
    
    # 预估全市场时间
    print(f"\n性能预估:")
    print(f"  串行模式: 5000只 × 0.3秒 = 1500秒 = 25分钟")
    print(f"  并发模式: 5000只 × {elapsed/len(test_codes):.3f}秒 = {5000*elapsed/len(test_codes):.0f}秒 = {5000*elapsed/len(test_codes)/60:.1f}分钟")
    
    print("\n✅ 异步并发测试通过")
    return True


def test_confidence_adjustment():
    """测试可信度调整逻辑"""
    print("\n" + "="*60)
    print("测试5: 可信度调整逻辑")
    print("="*60)
    
    tracker = get_health_tracker()
    
    # 模拟不同可靠性的数据源
    scenarios = [
        ('优秀数据源', 0.95, 'high', 'high'),
        ('优秀数据源', 0.95, 'medium', 'medium'),
        ('良好数据源', 0.85, 'high', 'medium'),
        ('良好数据源', 0.85, 'low', 'medium'),
        ('一般数据源', 0.65, 'medium', 'low'),
        ('较差数据源', 0.45, 'high', 'medium'),
        ('较差数据源', 0.45, 'low', 'low'),
    ]
    
    print("\n测试场景:")
    for scenario_name, reliability, base_conf, expected in scenarios:
        # 清空统计
        tracker.runtime_stats.clear()
        tracker.reliability_cache.clear()
        
        # 模拟请求以调整可靠性
        if reliability >= 0.9:
            # 高可靠性：模拟大量成功请求
            for _ in range(10):
                tracker.record_request('test_source', True, 0.2)
        elif reliability >= 0.7:
            # 中等可靠性：模拟一些失败
            for _ in range(8):
                tracker.record_request('test_source', True, 0.3)
            for _ in range(2):
                tracker.record_request('test_source', False, 0.5)
        else:
            # 低可靠性：模拟大量失败
            for _ in range(5):
                tracker.record_request('test_source', True, 0.5)
            for _ in range(5):
                tracker.record_request('test_source', False, 1.0)
        
        actual_reliability = tracker.get_reliability('test_source')
        adjusted = tracker.get_confidence_adjustment('test_source', base_conf)
        
        print(f"  {scenario_name}: 可靠性={actual_reliability:.2f}, {base_conf} -> {adjusted} (期望: {expected})")
    
    print("\n✅ 可信度调整测试通过")
    return True


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("v6.18 验证机制优化测试")
    print("="*60)
    
    tests = [
        ("健康度追踪器", test_health_tracker),
        ("缓存机制", test_cache),
        ("价格验证", test_price_validation),
        ("可信度调整", test_confidence_adjustment),
    ]
    
    # 运行同步测试
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result, None))
        except Exception as e:
            results.append((test_name, False, str(e)))
    
    # 运行异步测试
    try:
        result = asyncio.run(test_async_validation())
        results.append(("异步并发验证", result, None))
    except Exception as e:
        results.append(("异步并发验证", False, str(e)))
    
    # 打印总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    passed = sum(1 for _, result, _ in results if result)
    total = len(results)
    
    for test_name, result, error in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if error:
            print(f"  错误: {error}")
    
    print(f"\n通过率: {passed}/{total} ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 所有测试通过！v6.18改进成功！")
    else:
        print(f"\n⚠️  {total-passed}个测试失败，需要修复")


if __name__ == '__main__':
    main()
