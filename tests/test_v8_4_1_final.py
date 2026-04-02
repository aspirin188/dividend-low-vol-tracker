#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8.4.1 最终验证测试
快速验证所有修复是否正确
"""

import sys
import os
import subprocess

sys.path.insert(0, os.path.dirname(__file__))


def test_final():
    """最终测试"""
    print("\n" + "="*80)
    print("V8.4.1 最终验证测试")
    print("="*80 + "\n")
    
    tests_passed = 0
    tests_failed = 0
    
    # 测试1: Python语法检查
    print("测试1: Python语法检查")
    result = subprocess.run(['python3', '-m', 'py_compile', 'server/routes.py'],
                          capture_output=True, text=True)
    if result.returncode == 0:
        print("  ✅ routes.py语法正确")
        tests_passed += 1
    else:
        print("  ❌ routes.py语法错误")
        tests_failed += 1
    
    # 测试2: pyflakes静态分析
    print("\n测试2: pyflakes静态分析")
    result = subprocess.run(['python3', '-m', 'pyflakes', 'server/routes.py'],
                          capture_output=True, text=True)
    
    # 过滤掉已知的警告（未使用的导入等）
    errors = [line for line in result.stdout.split('\n') 
              if 'f-string' in line or 'default' in line or 'get_bool' in line]
    
    if not errors:
        print("  ✅ 无f-string或API调用错误")
        tests_passed += 1
    else:
        print(f"  ❌ 发现{len(errors)}个错误:")
        for error in errors:
            print(f"    {error}")
        tests_failed += 1
    
    # 测试3: 成长因子计算
    print("\n测试3: 成长因子计算")
    try:
        from server.services.scorer import _calculate_growth_factor
        
        gf = _calculate_growth_factor(10.0, 20.0, 1.0)
        if gf > 40:
            print(f"  ✅ 成长因子计算正常: {gf}")
            tests_passed += 1
        else:
            print(f"  ❌ 成长因子计算异常: {gf}")
            tests_failed += 1
    except Exception as e:
        print(f"  ❌ 成长因子计算失败: {e}")
        tests_failed += 1
    
    # 测试4: ConfigService API验证
    print("\n测试4: ConfigService API验证")
    try:
        from flask import Flask
        from server.routes import bp
        
        app = Flask(__name__, instance_relative_config=True)
        app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
        app.register_blueprint(bp)
        
        with app.app_context():
            from server.routes import init_db
            from server.services.config_service import ConfigService
            
            init_db()
            config = ConfigService.get_instance()
            
            # 测试正确的API调用
            try:
                value = float(config.get('MIN_PROFIT_GROWTH'))
                print(f"  ✅ get('MIN_PROFIT_GROWTH') = {value}")
            except (KeyError, ValueError) as e:
                print(f"  ❌ get('MIN_PROFIT_GROWTH') 失败: {e}")
                tests_failed += 1
            
            # 测试不正确的API调用（应该失败）
            try:
                value = config.get_float('MIN_PROFIT_GROWTH', default=0)
                print(f"  ❌ get_float支持default参数（不应该）: {value}")
                tests_failed += 1
            except TypeError:
                print(f"  ✅ get_float正确拒绝default参数")
            
            # 检查get_bool方法是否存在
            if hasattr(config, 'get_bool'):
                print(f"  ❌ get_bool方法存在（不应该）")
                tests_failed += 1
            else:
                print(f"  ✅ get_bool方法不存在（正确）")
            
            tests_passed += 1
    except Exception as e:
        print(f"  ❌ ConfigService API验证失败: {e}")
        import traceback
        traceback.print_exc()
        tests_failed += 1
    
    # 打印总结
    print("\n" + "="*80)
    print("V8.4.1 最终验证测试总结")
    print("="*80)
    print(f"总测试数: {tests_passed + tests_failed}")
    print(f"通过: {tests_passed} ✅")
    print(f"失败: {tests_failed} ❌")
    
    if tests_passed + tests_failed > 0:
        print(f"通过率: {tests_passed/(tests_passed+tests_failed)*100:.1f}%")
    
    print("="*80)
    
    if tests_failed == 0:
        print("\n🎉 所有测试通过！v8.4.1修复成功！")
        return 0
    else:
        print("\n⚠️ 部分测试失败")
        return 1


if __name__ == '__main__':
    try:
        sys.exit(test_final())
    except Exception as e:
        print(f"\n\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
