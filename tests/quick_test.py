#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速验证测试"""

import json
import time
import sqlite3

def test_database():
    """测试数据库"""
    print("\n=== 数据库测试 ===")
    db_path = "instance/tracker.db"
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 查看表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("数据表数量:", len(tables))
        for table in tables:
            print("  -", table[0])
        
        # 查看配置表
        if len([t for t in tables if 'config' in t[0].lower()]) > 0:
            cursor.execute("SELECT * FROM config LIMIT 5")
            configs = cursor.fetchall()
            print("配置记录数:", len(configs))
        
        # 查看预设策略
        try:
            cursor.execute("SELECT * FROM preset_strategies")
            strategies = cursor.fetchall()
            print("预设策略数:", len(strategies))
        except:
            print("预设策略表不存在")
        
        conn.close()
        print("✅ 数据库测试通过")
        return True
    except Exception as e:
        print("❌ 数据库测试失败:", str(e))
        return False

def test_api_connectivity():
    """测试API连接"""
    print("\n=== API连接测试 ===")
    try:
        import requests
        response = requests.get("http://localhost:5050/", timeout=5)
        if response.status_code == 200:
            print("✅ 服务器连接成功")
            return True
        else:
            print("❌ 服务器返回错误:", response.status_code)
            return False
    except Exception as e:
        print("❌ API连接失败:", str(e))
        return False

def test_akshare():
    """测试akshare"""
    print("\n=== Akshare测试 ===")
    try:
        import akshare as ak
        
        # 测试获取股票列表
        print("正在获取股票列表...")
        stocks = ak.stock_zh_a_spot_em()
        print("✅ 获取成功,股票数:", len(stocks))
        
        # 测试获取单只股票数据
        print("\n正在获取平安银行(000001)历史数据...")
        history = ak.stock_zh_a_hist(symbol="000001", period="daily", adjust="")
        print("✅ 获取成功,K线数:", len(history))
        print("最新日期:", history.iloc[-1]['日期'])
        print("最新收盘价:", history.iloc[-1]['收盘'])
        
        return True
    except Exception as e:
        print("❌ Akshare测试失败:", str(e))
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*60)
    print("V8.0 快速验证测试")
    print("开始时间:", time.strftime('%Y-%m-%d %H:%M:%S'))
    print("="*60)
    
    results = []
    
    # 测试1: 数据库
    results.append(("数据库", test_database()))
    
    # 测试2: API
    results.append(("API连接", test_api_connectivity()))
    
    # 测试3: Akshare
    results.append(("Akshare", test_akshare()))
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"\n通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    print("="*60)

if __name__ == "__main__":
    main()
