#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8.4.1 简单集成测试
直接导入Flask应用并测试，避免subprocess的复杂性
"""

import sys
import os
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))


def test_app_direct():
    """直接测试Flask应用"""
    print("\n" + "="*80)
    print("V8.4.1 真正的完整集成测试")
    print("="*80 + "\n")
    
    print("--- 测试1: 初始化Flask应用 ---")
    try:
        from app import create_app
        print("✅ Flask应用初始化成功")
    except Exception as e:
        print(f"❌ Flask应用初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    app = create_app()
    
    # 测试配置服务
    print("\n--- 测试2: 配置服务 ---")
    try:
        from server.services.config_service import ConfigService
        
        with app.app_context():
            config = ConfigService.get_instance()
            
            # 测试配置读取（修复后的API）
            try:
                min_growth = float(config.get('MIN_PROFIT_GROWTH'))
                print(f"✅ MIN_PROFIT_GROWTH: {min_growth}")
            except (KeyError, ValueError):
                min_growth = 0.0
                print(f"✅ MIN_PROFIT_GROWTH 使用默认值: {min_growth}")
            
            try:
                enable_filter = config.get('ENABLE_PROFIT_GROWTH_FILTER') == 'True'
                print(f"✅ ENABLE_PROFIT_GROWTH_FILTER: {enable_filter}")
            except KeyError:
                enable_filter = False
                print(f"✅ ENABLE_PROFIT_GROWTH_FILTER 使用默认值: {enable_filter}")
            
            print("✅ 配置服务测试通过")
    except Exception as e:
        print(f"❌ 配置服务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 测试核心功能
    print("\n--- 测试3: 核心功能导入 ---")
    try:
        from server.services.scorer import calculate_scores, _calculate_growth_factor
        from server.services.fetcher import fetch_profit_growth_data, merge_all_data
        print("✅ 所有核心模块导入成功")
    except Exception as e:
        print(f"❌ 核心模块导入失败: {e}")
        return False
    
    # 测试成长因子计算
    print("\n--- 测试4: 成长因子计算 ---")
    try:
        gf1 = _calculate_growth_factor(12.0, 30.0, 2.0)
        gf2 = _calculate_growth_factor(8.0, 25.0, 1.0)
        gf3 = _calculate_growth_factor(None, 10.0, None)
        
        print(f"  高增长+高ROE趋势: {gf1}")
        print(f"  中增长+中ROE趋势: {gf2}")
        print(f"  无数据: {gf3}")
        
        if gf1 > 50 and gf2 > 40 and gf3 == 30:
            print("✅ 成长因子计算测试通过")
        else:
            print("❌ 成长因子计算测试失败")
            return False
    except Exception as e:
        print(f"❌ 成长因子计算失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 测试API端点（使用test client）
    print("\n--- 测试5: API端点（test client）---")
    try:
        client = app.test_client()
        
        # 测试配置API
        print("  测试GET /api/config...")
        response = client.get('/api/config')
        if response.status_code == 200:
            print("  ✅ 配置API测试通过")
        else:
            print(f"  ❌ 配置API失败，状态码: {response.status_code}")
            return False
        
        # 测试运行API（实际执行筛选流程）
        print("\n  测试POST /api/run（这可能需要1-2分钟）...")
        print("  注意: 此测试会调用真实API获取数据...")
        
        start = time.time()
        response = client.post('/api/run')
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = json.loads(response.data)
            
            if data.get('success'):
                count = data.get('result_count', 0)
                print(f"  ✅ 运行API测试通过，结果数: {count}, 耗时: {elapsed:.2f}秒")
            else:
                error = data.get('error', '未知错误')
                print(f"  ❌ 运行API返回失败: {error}")
                print(f"  错误详情:")
                print(f"    {error}")
                return False
        else:
            print(f"  ❌ 运行API失败，状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ API端点测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "="*80)
    print("🎉 所有测试通过！v8.4.1修复成功！")
    print("="*80 + "\n")
    
    return True


def main():
    """主函数"""
    try:
        success = test_app_direct()
        
        if success:
            return 0
        else:
            print("\n⚠️ 部分测试失败，请检查错误信息\n")
            return 1
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被中断\n")
        return 1
    except Exception as e:
        print("\n\n❌ 测试异常: {}".format(str(e)))
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
