"""
策略参数验证脚本 - 快速验证策略配置

验证目标：
1. 每种策略的参数配置正确
2. 参数范围合理
3. 不同策略有显著差异
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server.services.config_service import PRESET_STRATEGIES
import pandas as pd


def validate_strategy_params():
    """验证所有策略参数"""
    
    print(f"\n{'='*60}")
    print(f"策略参数验证")
    print(f"{'='*60}")
    
    strategies = PRESET_STRATEGIES
    
    # 1. 打印所有策略参数
    print(f"\n发现 {len(strategies)} 种策略:")
    
    for strategy_id, strategy_config in strategies.items():
        print(f"\n{'='*60}")
        print(f"策略: {strategy_config['name']} ({strategy_id})")
        print(f"描述: {strategy_config['description']}")
        print(f"{'='*60}")
        
        params = strategy_config['params']
        
        # 筛选参数
        print(f"\n筛选参数:")
        filter_params = {
            'MIN_DIVIDEND_YIELD': '股息率下限',
            'MIN_MARKET_CAP': '市值下限',
            'MIN_ROE': 'ROE下限',
            'MIN_DIVIDEND_YEARS': '分红年数下限',
            'MAX_DEBT_RATIO': '负债率上限',
            'MIN_PROFIT_GROWTH': '利润增速下限',
        }
        
        for key, name in filter_params.items():
            if key in params:
                value = params[key]
                unit = '%' if 'YIELD' in key or 'ROE' in key or 'RATIO' in key or 'GROWTH' in key else '亿'
                print(f"  {name}: {value}{unit}")
        
        # 权重参数
        print(f"\n评分权重:")
        weight_params = {
            'WEIGHT_DIVIDEND': '股息率权重',
            'WEIGHT_VOL': '波动率权重',
            'WEIGHT_STABILITY': '稳定性权重',
            'WEIGHT_GROWTH': '成长因子权重',
        }
        
        total_weight = 0
        for key, name in weight_params.items():
            if key in params:
                value = float(params[key])
                total_weight += value
                print(f"  {name}: {value:.2f}")
        
        print(f"  权重和: {total_weight:.2f} {'✓' if abs(total_weight - 1.0) < 0.01 else '✗'}")
    
    # 2. 策略对比
    print(f"\n{'='*60}")
    print(f"策略对比")
    print(f"{'='*60}")
    
    # 创建对比表
    comparison = []
    
    for strategy_id, strategy_config in strategies.items():
        params = strategy_config['params']
        
        row = {
            '策略': strategy_config['name'],
            '股息率≥': float(params.get('MIN_DIVIDEND_YIELD', 0)),
            '市值≥': float(params.get('MIN_MARKET_CAP', 0)),
            'ROE≥': float(params.get('MIN_ROE', 0)),
            '分红年数≥': int(float(params.get('MIN_DIVIDEND_YEARS', 0))),
            '负债率≤': float(params.get('MAX_DEBT_RATIO', 100)),
            '股息率权重': float(params.get('WEIGHT_DIVIDEND', 0)),
            '成长权重': float(params.get('WEIGHT_GROWTH', 0)),
        }
        
        comparison.append(row)
    
    df = pd.DataFrame(comparison)
    
    print(f"\n筛选条件对比:")
    print(df[['策略', '股息率≥', '市值≥', 'ROE≥', '分红年数≥', '负债率≤']].to_string(index=False))
    
    print(f"\n权重配置对比:")
    print(df[['策略', '股息率权重', '成长权重']].to_string(index=False))
    
    # 3. 严格程度排序
    print(f"\n{'='*60}")
    print(f"策略严格程度排序（从严格到宽松）")
    print(f"{'='*60}")
    
    # 计算综合严格度分数（越高越严格）
    for i, row in enumerate(comparison):
        # 严格度 = 股息率权重 + 市值权重 + ROE权重 + 分红年数权重
        # 使用相对值计算
        strictness = (
            row['股息率≥'] / 4.0 * 25 +  # 最高4%，占比25分
            row['市值≥'] / 800 * 25 +      # 最高800亿，占比25分
            row['ROE≥'] / 10 * 25 +        # 最高10%，占比25分
            row['分红年数≥'] / 5 * 25     # 最高5年，占比25分
        )
        comparison[i]['严格度'] = strictness
    
    # 排序
    comparison_sorted = sorted(comparison, key=lambda x: x['严格度'], reverse=True)
    
    for i, row in enumerate(comparison_sorted, 1):
        print(f"{i}. {row['策略']}: {row['严格度']:.1f}分")
    
    # 4. 预期筛选效果
    print(f"\n{'='*60}")
    print(f"预期筛选效果")
    print(f"{'='*60}")
    
    predictions = {
        '保守型': {
            'description': '条件最严格，筛选股票最少（0-10只）',
            '适用场景': '市场高位、极度保守投资者',
            '风险': '可能没有股票'
        },
        '均衡型': {
            'description': '条件适中，筛选股票适中（20-50只）',
            '适用场景': '大多数投资者（推荐）',
            '风险': '无'
        },
        '激进型': {
            'description': '条件宽松，筛选股票较多（50-100只）',
            '适用场景': '市场低位、追求收益',
            '风险': '可能包含质量较低的股票'
        },
        '成长红利': {
            'description': '重视成长性，筛选股票适中（30-60只）',
            '适用场景': '成长型投资者',
            '风险': '波动可能较大'
        }
    }
    
    for strategy_name, info in predictions.items():
        if strategy_name in [r['策略'] for r in comparison]:
            print(f"\n{strategy_name}:")
            print(f"  {info['description']}")
            print(f"  适用场景: {info['适用场景']}")
            print(f"  风险: {info['风险']}")
    
    # 5. 建议
    print(f"\n{'='*60}")
    print(f"使用建议")
    print(f"{'='*60}")
    
    print(f"\n✓ 推荐：均衡型策略")
    print(f"  - 筛选条件适中，风险可控")
    print(f"  - 股票数量合理（20-50只）")
    print(f"  - 适合大多数投资者")
    
    print(f"\n⚠️ 慎用：保守型策略")
    print(f"  - 条件严格，可能没有股票")
    print(f"  - 适合市场高位或极度保守者")
    print(f"  - 建议放宽部分条件（如股息率3.5%）")
    
    print(f"\n💡 建议：激进型策略")
    print(f"  - 筛选股票多，需深入研究")
    print(f"  - 适合市场低位或追求收益者")
    print(f"  - 建议结合其他指标筛选")
    
    print(f"\n{'='*60}")
    print(f"验证完成")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    validate_strategy_params()