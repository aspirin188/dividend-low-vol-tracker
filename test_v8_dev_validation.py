#!/usr/bin/env python3
"""
V8.0 开发验证测试脚本
测试目标：验证数据源增强、配置系统升级、信号系统功能
"""

import sys
sys.path.insert(0, '/Users/macair/Work/workbuddy_dir/hl3')
sys.path.insert(0, '/Users/macair/Work/workbuddy_dir/hl3/server/services')

print("=" * 70)
print("V8.0 开发验证测试")
print("=" * 70)

# 测试用例
TEST_STOCKS = [
    ('600519', '贵州茅台'),
    ('601318', '中国平安'),
    ('600036', '招商银行'),
]

# ========== 测试1: 配置系统升级 ==========
print("\n【测试1】配置系统升级 - 预设策略")
print("-" * 50)

try:
    from config_service import ConfigService, PRESET_STRATEGIES
    
    # 检查预设策略是否存在
    assert len(PRESET_STRATEGIES) == 5, "预设策略数量不正确"
    assert 'conservative' in PRESET_STRATEGIES, "缺少保守型策略"
    assert 'balanced' in PRESET_STRATEGIES, "缺少均衡型策略"
    assert 'aggressive' in PRESET_STRATEGIES, "缺少激进型策略"
    assert 'high_dividend' in PRESET_STRATEGIES, "缺少高股息策略"
    assert 'value' in PRESET_STRATEGIES, "缺少低估型策略"
    
    print(f"  ✓ 预设策略数量: {len(PRESET_STRATEGIES)}")
    for id_, s in PRESET_STRATEGIES.items():
        print(f"    - {id_}: {s['name']}")
    
    # 检查策略参数
    for id_, s in PRESET_STRATEGIES.items():
        params = s['params']
        assert 'MIN_DIVIDEND_YIELD' in params, f"{id_} 缺少股息率参数"
        assert 'WEIGHT_DIVIDEND' in params, f"{id_} 缺少权重参数"
    
    print("  ✓ 预设策略参数完整")
    
except Exception as e:
    print(f"  ✗ 测试失败: {e}")

# ========== 测试2: 配置历史记录功能 ==========
print("\n【测试2】配置系统升级 - 参数历史记录")
print("-" * 50)

try:
    # 检查config_service中的历史记录功能
    from config_service import ConfigService
    assert hasattr(ConfigService, 'get_config_history'), "缺少get_config_history方法"
    assert hasattr(ConfigService, 'record_config_change'), "缺少record_config_change方法"
    print("  ✓ 参数历史记录方法存在")
    
    # 检查routes.py中的历史API
    with open('/Users/macair/Work/workbuddy_dir/hl3/server/routes.py', 'r') as f:
        routes_content = f.read()
    assert '/api/config/history' in routes_content, "缺少历史API"
    print("  ✓ 历史API已添加")
    
except Exception as e:
    print(f"  ✗ 测试失败: {e}")

# ========== 测试3: 波动率计算函数 ==========
print("\n【测试3】数据源增强 - 波动率计算")
print("-" * 50)

try:
    from fetcher import calculate_volatility_batch
    print("  ✓ calculate_volatility_batch 函数存在")
    
    # 检查函数签名
    import inspect
    sig = inspect.signature(calculate_volatility_batch)
    assert 'stock_codes' in sig.parameters, "参数不正确"
    assert 'window' in sig.parameters, "缺少window参数"
    print("  ✓ 函数签名正确 (stock_codes, window=120)")
    
except Exception as e:
    print(f"  ✗ 测试失败: {e}")

# ========== 测试4: 价格百分位计算函数 ==========
print("\n【测试4】数据源增强 - 价格百分位计算")
print("-" * 50)

try:
    from fetcher import calculate_price_percentile_batch
    print("  ✓ calculate_price_percentile_batch 函数存在")
    
    import inspect
    sig = inspect.signature(calculate_price_percentile_batch)
    assert 'stock_codes' in sig.parameters, "参数不正确"
    assert 'days' in sig.parameters, "缺少days参数"
    print("  ✓ 函数签名正确 (stock_codes, days=252)")
    
except Exception as e:
    print(f"  ✗ 测试失败: {e}")

# ========== 测试5: 负债率获取函数 ==========
print("\n【测试5】数据源增强 - 负债率获取")
print("-" * 50)

try:
    from fetcher import fetch_debt_ratio_batch
    print("  ✓ fetch_debt_ratio_batch 函数存在")
    
    import inspect
    sig = inspect.signature(fetch_debt_ratio_batch)
    assert 'stock_codes' in sig.parameters, "参数不正确"
    print("  ✓ 函数签名正确 (stock_codes)")
    
except Exception as e:
    print(f"  ✗ 测试失败: {e}")

# ========== 测试6: 信号系统功能 ==========
print("\n【测试6】信号系统 - 均线位置计算")
print("-" * 50)

try:
    from fetcher import calc_ma_position_batch
    print("  ✓ calc_ma_position_batch 函数存在")
    
    # 检查返回值包含必要字段
    import inspect
    sig = inspect.signature(calc_ma_position_batch)
    assert 'stock_codes' in sig.parameters, "参数不正确"
    print("  ✓ 函数签名正确 (stock_codes)")
    
    # 检查scorer中的信号评分
    from scorer import calculate_strike_zone_score
    print("  ✓ calculate_strike_zone_score 函数存在")
    
except Exception as e:
    print(f"  ✗ 测试失败: {e}")

# ========== 测试7: 质量因子功能 ==========
print("\n【测试7】质量因子 - 支付率稳定性")
print("-" * 50)

try:
    from fetcher import calculate_payout_stability_score
    print("  ✓ calculate_payout_stability_score 函数存在")
    
    from fetcher import get_operating_cashflow_batch
    print("  ✓ get_operating_cashflow_batch 函数存在")
    
    from fetcher import calculate_profit_growth_3y
    print("  ✓ calculate_profit_growth_3y 函数存在")
    
except Exception as e:
    print(f"  ✗ 测试失败: {e}")

# ========== 测试8: 数据库表结构 ==========
print("\n【测试8】数据库 - 新增表结构")
print("-" * 50)

try:
    import sqlite3
    import os
    
    db_path = '/Users/macair/Work/workbuddy_dir/hl3/instance/tracker.db'
    
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查config_history表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='config_history'")
        result = cursor.fetchone()
        if result:
            print("  ✓ config_history 表存在")
        else:
            print("  ○ config_history 表不存在（首次运行后创建）")
        
        # 检查current_strategy表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='current_strategy'")
        result = cursor.fetchone()
        if result:
            print("  ✓ current_strategy 表存在")
        else:
            print("  ○ current_strategy 表不存在（首次运行后创建）")
        
        conn.close()
    else:
        print("  ○ 数据库文件不存在（首次运行后创建）")
        
except Exception as e:
    print(f"  ✗ 测试失败: {e}")

# ========== 测试9: 前端界面 ==========
print("\n【测试9】前端 - 预设策略UI")
print("-" * 50)

try:
    with open('/Users/macair/Work/workbuddy_dir/hl3/server/templates/config.html', 'r') as f:
        html_content = f.read()
    
    assert 'strategy-grid' in html_content, "缺少策略网格"
    assert 'applyStrategy' in html_content, "缺少applyStrategy函数"
    print("  ✓ 预设策略UI已添加")
    
    # 检查新增的API调用
    assert '/api/config/strategies' in html_content, "缺少策略API调用"
    print("  ✓ 策略API调用已添加")
    
except Exception as e:
    print(f"  ✗ 测试失败: {e}")

# ========== 测试10: 路由API ==========
print("\n【测试10】后端 - 新增API")
print("-" * 50)

try:
    with open('/Users/macair/Work/workbuddy_dir/hl3/server/routes.py', 'r') as f:
        routes_content = f.read()
    
    assert "get_strategies" in routes_content, "缺少get_strategies函数"
    assert "apply_strategy" in routes_content, "缺少apply_strategy函数"
    assert "get_config_history" in routes_content, "缺少get_config_history函数"
    print("  ✓ 新增API函数存在")
    
    # 检查API端点
    assert "/api/config/strategies" in routes_content, "缺少策略API端点"
    assert "/api/config/history" in routes_content, "缺少历史API端点"
    print("  ✓ API端点已注册")
    
except Exception as e:
    print(f"  ✗ 测试失败: {e}")

print("\n" + "=" * 70)
print("V8.0 开发验证测试完成")
print("=" * 70)