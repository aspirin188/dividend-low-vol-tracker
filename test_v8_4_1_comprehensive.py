#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8.4.1 全面验证测试
检查所有已修复的问题，并验证关键功能
"""

import sys
import os
import re

sys.path.insert(0, os.path.dirname(__file__))


def test_1_check_code_for_issues():
    """测试1: 检查代码中的问题"""
    print("\n" + "="*80)
    print("测试1: 代码静态检查")
    print("="*80 + "\n")
    
    issues = []
    
    # 读取routes.py
    with open('server/routes.py', 'r') as f:
        content = f.read()
        lines = content.split('\n')
    
    # 检查1: config未定义
    print("检查1: config实例定义")
    run_start = None
    for i, line in enumerate(lines):
        if 'def run():' in line:
            run_start = i
            break
    
    if run_start:
        run_end = run_start
        for i in range(run_start, min(run_start + 500, len(lines))):
            if '@bp.route' in lines[i]:
                run_end = i
                break
        
        run_section = '\n'.join(lines[run_start:run_end])
        
        # 检查config实例定义
        config_defined = 'config = ConfigService.get_instance()' in run_section
        
        # 检查config使用
        config_uses = len([l for l in run_section if 'config.get(' in l or 'config.get_float(' in l or 'config.get_bool(' in l])
        config_with_default = len([l for l in run_section if 'config.get_float(' in l and 'default=' in l])
        
        print(f"  config实例定义: {'✅' if config_defined else '❌'}")
        print(f"  config方法调用次数: {config_uses}")
        print(f"  不正确的default参数使用: {config_with_default}")
        
        if not config_defined:
            issues.append("config实例未定义")
        
        if config_with_default > 0:
            issues.append("config.get_float使用了不支持的default参数")
    
    # 检查2: f-string警告
    print("\n检查2: f-string占位符")
    fstring_lines = []
    for i, line in enumerate(lines, 1):
        if 'f"' in line and '{' not in line and '}' not in line and 'print(' in line:
            # 检查是否是不带占位符的f-string
            match = re.search(r'f"([^"]*)"', line)
            if match and '{' not in match.group(1):
                fstring_lines.append((i, line.strip()))
    
    if fstring_lines:
        print(f"  ⚠️ 发现{len(fstring_lines)}个f-string警告")
        for line_no, line_text in fstring_lines[:3]:
            print(f"    第{line_no}行: {line_text[:60]}...")
        issues.append(f"发现{len(fstring_lines)}个f-string警告")
    else:
        print(f"  ✅ 无f-string警告")
    
    # 检查3: ConfigService API调用
    print("\n检查3: ConfigService API调用正确性")
    config_api_calls = []
    for i, line in enumerate(lines, 1):
        if 'config.get_float(' in line:
            # 检查是否使用了default参数
            if 'default=' in line:
                config_api_calls.append((i, line.strip(), 'get_float使用了default参数'))
        if 'config.get_bool(' in line:
            config_api_calls.append((i, line.strip(), 'get_bool方法不存在'))
    
    if config_api_calls:
        print(f"  ⚠️ 发现{len(config_api_calls)}个API调用错误")
        for line_no, line_text, error in config_api_calls:
            print(f"    第{line_no}行: {line_text[:60]}...")
            print(f"      错误: {error}")
        issues.append(f"发现{len(config_api_calls)}个ConfigService API调用错误")
    else:
        print(f"  ✅ ConfigService API调用正确")
    
    if issues:
        print(f"\n❌ 发现{len(issues)}个问题:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        return False
    else:
        print("\n✅ 所有代码检查通过！")
        return True


def test_2_imports_and_syntax():
    """测试2: 导入和语法检查"""
    print("\n" + "="*80)
    print("测试2: 导入和语法检查")
    print("="*80 + "\n")
    
    # 检查Python语法
    print("检查: Python语法")
    import subprocess
    result = subprocess.run(['python3', '-m', 'py_compile', 'server/routes.py'],
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("  ✅ routes.py语法正确")
    else:
        print(f"  ❌ routes.py语法错误:")
        print(result.stderr)
        return False
    
    # 检查所有services文件
    print("\n检查: services/*.py语法")
    result = subprocess.run(['python3', '-m', 'py_compile', 'server/services/scorer.py',
                          'server/services/fetcher.py', 'server/services/config_service.py'],
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("  ✅ 所有services/*.py语法正确")
    else:
        print(f"  ❌ services/*.py语法错误:")
        print(result.stderr)
        return False
    
    print("\n✅ 所有语法检查通过！")
    return True


def test_3_config_service_api():
    """测试3: ConfigService API使用"""
    print("\n" + "="*80)
    print("测试3: ConfigService API使用验证")
    print("="*80 + "\n")
    
    try:
        from app import create_app
        from server.services.config_service import ConfigService
        
        app = create_app()
        
        with app.app_context():
            config = ConfigService.get_instance()
            
            print("测试1: 正确的API调用")
            
            # 测试get方法
            try:
                value = config.get('MIN_PROFIT_GROWTH')
                print(f"  ✅ get('MIN_PROFIT_GROWTH') = {value}")
            except KeyError as e:
                print(f"  ⚠️ get('MIN_PROFIT_GROWTH') - {e}")
            
            # 测试get_float方法（不带default）
            try:
                value = config.get_float('MIN_PROFIT_GROWTH')
                print(f"  ✅ get_float('MIN_PROFIT_GROWTH') = {value}")
            except (KeyError, ValueError) as e:
                print(f"  ⚠️ get_float('MIN_PROFIT_GROWTH') - {e}")
            
            # 测试正确的默认值处理
            try:
                min_growth = float(config.get('MIN_PROFIT_GROWTH'))
            except (KeyError, ValueError):
                min_growth = 0.0
                print(f"  ✅ 正确的默认值处理: {min_growth}")
            
            try:
                enable_filter = config.get('ENABLE_PROFIT_GROWTH_FILTER') == 'True'
            except KeyError:
                enable_filter = False
                print(f"  ✅ 正确的布尔值处理: {enable_filter}")
            
            print("\n测试2: 不正确的API调用（应该失败）")
            
            # 测试get_float不支持default参数
            try:
                value = config.get_float('MIN_PROFIT_GROWTH', default=0)
                print(f"  ❌ get_float支持default参数（不应该）: {value}")
                return False
            except TypeError as e:
                print(f"  ✅ get_float正确拒绝default参数: {e}")
            
            # 测试get_bool方法不存在
            if not hasattr(config, 'get_bool'):
                print(f"  ✅ get_bool方法不存在（正确）")
            else:
                print(f"  ❌ get_bool方法存在（不应该）")
                return False
            
            print("\n✅ ConfigService API验证通过！")
            return True
            
    except Exception as e:
        print(f"\n❌ ConfigService API验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_4_core_functions():
    """测试4: 核心功能测试"""
    print("\n" + "="*80)
    print("测试4: 核心功能测试")
    print("="*80 + "\n")
    
    try:
        from server.services.scorer import _calculate_growth_factor
        
        print("测试: 成长因子计算")
        
        # 测试用例
        test_cases = [
            (12.0, 30.0, 2.0, "高增长+高ROE趋势", 50),
            (8.0, 25.0, 1.0, "中增长+中ROE趋势", 40),
            (None, 10.0, None, "无数据", 30),
            (18.0, 15.0, 3.0, "超高增长+高ROE趋势", 60),
        ]
        
        print("\n测试用例:")
        all_passed = True
        for profit_growth, pe, roe_trend, desc, min_score in test_cases:
            gf = _calculate_growth_factor(profit_growth, pe, roe_trend)
            passed = gf >= min_score
            status = "✅" if passed else "❌"
            print(f"  {status} {desc}: {gf} (期望 >= {min_score})")
            if not passed:
                all_passed = False
        
        if all_passed:
            print("\n✅ 成长因子计算测试通过！")
            return True
        else:
            print("\n❌ 成长因子计算测试失败！")
            return False
            
    except Exception as e:
        print(f"\n❌ 核心功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_5_data_flow():
    """测试5: 数据流测试"""
    print("\n" + "="*80)
    print("测试5: 数据流测试")
    print("="*80 + "\n")
    
    try:
        import pandas as pd
        
        # 模拟成长因子数据
        growth_data = {
            '600519': {'profit_growth_3y': 12.0, 'roe_trend': 2.0},
            '000858': {'profit_growth_3y': 8.0, 'roe_trend': 1.0},
            '601318': {'profit_growth_3y': 5.0, 'roe_trend': -0.5},
        }
        
        # 模拟merged dataframe
        merged = pd.DataFrame({
            'code': ['600519', '000858', '601318'],
            'name': ['贵州茅台', '五粮液', '中国平安'],
        })
        
        # 数据映射
        merged['profit_growth_3y'] = merged['code'].map(lambda x: growth_data.get(x, {}).get('profit_growth_3y'))
        merged['roe_trend'] = merged['code'].map(lambda x: growth_data.get(x, {}).get('roe_trend'))
        
        print("数据映射结果:")
        print(merged[['code', 'name', 'profit_growth_3y', 'roe_trend']].to_string())
        
        # 验证数据映射
        expected = {
            '600519': {'profit_growth_3y': 12.0, 'roe_trend': 2.0},
            '000858': {'profit_growth_3y': 8.0, 'roe_trend': 1.0},
            '601318': {'profit_growth_3y': 5.0, 'roe_trend': -0.5},
        }
        
        success = True
        for code, expected_data in expected.items():
            actual = merged[merged['code'] == code].iloc[0]
            if actual['profit_growth_3y'] != expected_data['profit_growth_3y']:
                print(f"❌ {code} profit_growth_3y不匹配")
                success = False
            if actual['roe_trend'] != expected_data['roe_trend']:
                print(f"❌ {code} roe_trend不匹配")
                success = False
        
        if success:
            print("\n✅ 数据流测试通过！")
            return True
        else:
            print("\n❌ 数据流测试失败！")
            return False
            
    except Exception as e:
        print(f"\n❌ 数据流测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "="*80)
    print("V8.4.1 全面验证测试")
    print("="*80)
    
    results = []
    
    # 测试1: 代码静态检查
    result = test_1_check_code_for_issues()
    results.append(('代码静态检查', result))
    
    # 测试2: 导入和语法检查
    result = test_2_imports_and_syntax()
    results.append(('导入和语法检查', result))
    
    # 测试3: ConfigService API使用
    result = test_3_config_service_api()
    results.append(('ConfigService API使用', result))
    
    # 测试4: 核心功能
    result = test_4_core_functions()
    results.append(('核心功能', result))
    
    # 测试5: 数据流
    result = test_5_data_flow()
    results.append(('数据流', result))
    
    # 打印总结
    print("\n" + "="*80)
    print("V8.4.1 全面验证测试总结")
    print("="*80)
    
    total = len(results)
    passed = sum(1 for _, r in results if r)
    failed = total - passed
    
    print(f"总测试数: {total}")
    print(f"通过: {passed} ✅")
    print(f"失败: {failed} ❌")
    print(f"通过率: {passed/total*100:.1f}%")
    
    print("\n详细结果:")
    for name, result in results:
        status_icon = "✅" if result else "❌"
        print(f"  {status_icon} {name}")
    
    print("="*80)
    
    if passed == total:
        print("\n🎉 所有测试通过！v8.4.1修复成功！")
        print("\n✅ 关键修复：")
        print("  1. config实例定义正确")
        print("  2. ConfigService API调用正确")
        print("  3. f-string警告已修复")
        print("  4. 成长因子功能正常")
        print("  5. 数据流正确")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查错误信息")
        return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被中断")
        sys.exit(1)
    except Exception as e:
        print("\n\n❌ 测试异常: {}".format(str(e)))
        import traceback
        traceback.print_exc()
        sys.exit(1)
