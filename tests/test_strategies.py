"""
策略测试脚本 - 验证每种策略的筛选效果

测试目标：
1. 验证每种策略都能筛选出股票
2. 对比不同策略的差异
3. 确保策略配置合理

运行方式：
python test_strategies.py
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server.services.config_service import ConfigService, PRESET_STRATEGIES
from server.services.fetcher import merge_all_data
from server.services.scorer import filter_stocks, calculate_scores, prepare_results
import pandas as pd
from datetime import datetime


def test_strategy(strategy_id: str, strategy_config: dict):
    """
    测试单个策略
    
    Args:
        strategy_id: 策略ID（如 'conservative'）
        strategy_config: 策略配置
    
    Returns:
        dict: 测试结果
    """
    print(f"\n{'='*60}")
    print(f"测试策略: {strategy_config['name']}")
    print(f"{'='*60}")
    
    # 1. 应用策略配置
    config = ConfigService.get_instance()
    
    # 应用策略参数
    for key, value in strategy_config['params'].items():
        try:
            config.set(key, value)
        except Exception as e:
            print(f"  ⚠️ 设置参数失败: {key}={value}, 错误: {e}")
    
    # 2. 打印策略参数
    print(f"\n策略参数:")
    for key, value in strategy_config['params'].items():
        print(f"  - {key}: {value}")
    
    # 3. 获取数据（使用缓存或重新获取）
    print(f"\n正在获取数据...")
    try:
        merged = merge_all_data()
        if merged.empty:
            return {
                'strategy_id': strategy_id,
                'strategy_name': strategy_config['name'],
                'success': False,
                'error': '无法获取数据',
                'count': 0,
                'stocks': []
            }
        
        raw_count = len(merged)
        print(f"  ✓ 获取到 {raw_count} 只股票")
        
        # 4. 筛选
        print(f"\n正在筛选...")
        filtered = filter_stocks(merged)
        filtered_count = len(filtered)
        print(f"  ✓ 筛选后剩余 {filtered_count} 只")
        
        if filtered.empty:
            return {
                'strategy_id': strategy_id,
                'strategy_name': strategy_config['name'],
                'success': True,
                'raw_count': raw_count,
                'count': 0,
                'stocks': [],
                'message': '没有符合条件的股票'
            }
        
        # 5. 评分
        print(f"\n正在评分...")
        scored = calculate_scores(filtered)
        
        # 6. 整理结果
        result = prepare_results(scored)
        
        # 7. 提取前10名股票
        top_10 = result.head(10)[['code', 'name', 'industry', 'dividend_yield', 
                                   'market_cap', 'roe', 'composite_score']].to_dict('records')
        
        print(f"\n前10名股票:")
        for i, stock in enumerate(top_10, 1):
            print(f"  {i}. {stock['name']} ({stock['code']}) - "
                  f"股息率:{stock['dividend_yield']:.2f}%, "
                  f"市值:{stock['market_cap']:.0f}亿, "
                  f"评分:{stock['composite_score']:.2f}")
        
        return {
            'strategy_id': strategy_id,
            'strategy_name': strategy_config['name'],
            'success': True,
            'raw_count': raw_count,
            'count': filtered_count,
            'stocks': top_10,
            'params': strategy_config['params']
        }
        
    except Exception as e:
        import traceback
        print(f"  ✗ 测试失败: {e}")
        traceback.print_exc()
        return {
            'strategy_id': strategy_id,
            'strategy_name': strategy_config['name'],
            'success': False,
            'error': str(e),
            'count': 0,
            'stocks': []
        }


def compare_strategies(results: list):
    """
    对比不同策略的结果
    
    Args:
        results: 所有策略的测试结果
    """
    print(f"\n{'='*60}")
    print(f"策略对比")
    print(f"{'='*60}")
    
    # 1. 数量对比
    print(f"\n筛选数量对比:")
    print(f"{'策略名称':<12} {'原始数据':<10} {'筛选后':<10} {'通过率':<10}")
    print(f"{'-'*50}")
    
    for r in results:
        if r['success']:
            raw = r.get('raw_count', 0)
            filtered = r['count']
            pass_rate = (filtered / raw * 100) if raw > 0 else 0
            print(f"{r['strategy_name']:<12} {raw:<10} {filtered:<10} {pass_rate:.1f}%")
        else:
            print(f"{r['strategy_name']:<12} {'失败':<10} {'-':<10} {'-':<10}")
    
    # 2. 股票差异
    print(f"\n股票差异分析:")
    
    # 收集所有股票代码
    all_stocks = {}
    for r in results:
        if r['success'] and r['stocks']:
            codes = [s['code'] for s in r['stocks']]
            all_stocks[r['strategy_name']] = set(codes)
    
    # 找出共同股票
    if len(all_stocks) >= 2:
        strategy_names = list(all_stocks.keys())
        
        # 共同股票
        common = all_stocks[strategy_names[0]]
        for name in strategy_names[1:]:
            common = common.intersection(all_stocks[name])
        
        print(f"\n所有策略都包含的股票（前10名）:")
        if common:
            print(f"  共 {len(common)} 只: {', '.join(sorted(common))}")
        else:
            print(f"  无（说明各策略差异明显）")
        
        # 特有股票
        print(f"\n各策略特有股票（前10名）:")
        for name, codes in all_stocks.items():
            unique = codes.copy()
            for other_name, other_codes in all_stocks.items():
                if other_name != name:
                    unique = unique - other_codes
            
            if unique:
                print(f"  {name}: {len(unique)} 只")
                print(f"    {', '.join(sorted(unique)[:5])}")
            else:
                print(f"  {name}: 无特有股票")


def main():
    """主测试流程"""
    print(f"\n{'='*60}")
    print(f"红利低波跟踪系统 - 策略测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    # 获取所有预设策略
    strategies = PRESET_STRATEGIES
    
    print(f"\n发现 {len(strategies)} 种策略:")
    for sid, s in strategies.items():
        print(f"  - {s['name']} ({sid})")
    
    # 测试每种策略
    results = []
    for strategy_id, strategy_config in strategies.items():
        result = test_strategy(strategy_id, strategy_config)
        results.append(result)
    
    # 对比结果
    compare_strategies(results)
    
    # 生成报告
    print(f"\n{'='*60}")
    print(f"测试报告")
    print(f"{'='*60}")
    
    # 成功率
    success_count = sum(1 for r in results if r['success'])
    print(f"\n成功率: {success_count}/{len(results)} ({success_count/len(results)*100:.0f}%)")
    
    # 有数据的策略
    valid_strategies = [r for r in results if r['success'] and r['count'] > 0]
    
    if valid_strategies:
        print(f"\n✓ 推荐使用:")
        for r in valid_strategies:
            print(f"  - {r['strategy_name']}: {r['count']} 只股票")
    else:
        print(f"\n✗ 警告: 所有策略都没有筛选出股票！")
        print(f"  可能原因:")
        print(f"  1. 数据获取失败")
        print(f"  2. 策略条件过于严格")
        print(f"  3. 市场环境特殊")
    
    # 无数据的策略
    invalid_strategies = [r for r in results if not r['success'] or r['count'] == 0]
    
    if invalid_strategies:
        print(f"\n⚠️ 需要调整:")
        for r in invalid_strategies:
            reason = r.get('error', r.get('message', '未知原因'))
            print(f"  - {r['strategy_name']}: {reason}")
            if r['success'] and r['count'] == 0:
                print(f"    建议：放宽筛选条件")
    
    print(f"\n{'='*60}")
    print(f"测试完成")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()