#!/usr/bin/env python3
"""
改进版的 ROE 数据获取函数
添加超时控制、错误处理和备用方案
"""
import signal
import sys
import pandas as pd
import akshare as ak

def timeout_handler(signum, frame):
    raise TimeoutError("操作超时")

def fetch_roe_with_timeout(timeout_seconds=30):
    """
    带超时控制的 ROE 数据获取
    """
    print(f"尝试获取ROE数据（超时{timeout_seconds}秒）...", flush=True)
    
    # 设置超时
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    
    try:
        # 尝试最近3个年报日期
        for year_end in ['20241231', '20231231', '20221231']:
            try:
                print(f"  尝试日期: {year_end}", flush=True)
                df = ak.stock_yjbb_em(date=year_end)
                
                if df is None or df.empty:
                    print(f"    未获取到数据", flush=True)
                    continue
                
                # 检查列名
                print(f"    列名: {df.columns.tolist()[:5]}...", flush=True)
                
                if '净资产收益率' not in df.columns:
                    print(f"    ✗ 未找到'净资产收益率'列", flush=True)
                    continue
                
                # 只保留主板 A 股
                df = df[df['股票代码'].str.startswith(('0', '3', '6'))].copy()
                
                if df.empty:
                    continue
                
                # 提取数据
                result = pd.DataFrame({
                    'code': df['股票代码'].values,
                    'basic_eps': pd.to_numeric(df['每股收益'], errors='coerce').values,
                    'roe': pd.to_numeric(df['净资产收益率'], errors='coerce').values,
                    'report_year': int(year_end[:4]),
                })
                
                # 取消超时
                signal.alarm(0)
                
                print(f"  ✓ 成功获取 {len(result)} 只股票的ROE数据", flush=True)
                
                # 显示示例
                roe_not_null = result['roe'].notna().sum()
                print(f"  ROE非空: {roe_not_null}/{len(result)}", flush=True)
                
                # 显示几只股票
                sample_codes = ['601939', '600036', '601318']
                for code in sample_codes:
                    row = result[result['code'] == code]
                    if not row.empty:
                        print(f"    {code}: ROE={row['roe'].values[0]}", flush=True)
                
                return result
                
            except TimeoutError:
                print(f"    ✗ 超时!", flush=True)
                signal.alarm(0)
                continue
            except Exception as e:
                print(f"    ✗ 错误: {e}", flush=True)
                continue
        
        # 所有日期都失败了
        signal.alarm(0)
        print("  ✗ 所有日期都失败了", flush=True)
        return pd.DataFrame(columns=['code', 'basic_eps', 'roe', 'report_year'])
        
    except Exception as e:
        signal.alarm(0)
        print(f"✗ 严重错误: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return pd.DataFrame(columns=['code', 'basic_eps', 'roe', 'report_year'])

# 测试
if __name__ == "__main__":
    print("=" * 60, flush=True)
    print("测试改进版ROE获取函数", flush=True)
    print("=" * 60, flush=True)
    
    result = fetch_roe_with_timeout(timeout_seconds=60)
    
    if not result.empty:
        print(f"\n✓ 测试成功，获取到 {len(result)} 条数据", flush=True)
    else:
        print(f"\n✗ 测试失败，未获取到数据", flush=True)
        print("\n可能的原因:", flush=True)
        print("  1. 网络连接问题", flush=True)
        print("  2. akshare接口暂时不可用", flush=True)
        print("  3. 接口返回格式改变", flush=True)
