#!/usr/bin/env python3
"""
检查数据库中的ROE数据
"""
import sqlite3
import os

# 数据库路径
db_path = os.path.expanduser('~/Work/workbuddy_dir/hl3/instance/tracker.db')

if not os.path.exists(db_path):
    print(f"数据库不存在: {db_path}")
    exit(1)

print(f"数据库路径: {db_path}")

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# 检查表结构
print("\n=== 表结构 ===")
cursor = conn.execute("PRAGMA table_info(stock_data)")
for row in cursor.fetchall():
    print(f"  {row['name']}: {row['type']}")

# 检查数据
print("\n=== 数据统计 ===")
cursor = conn.execute("SELECT COUNT(*) as count FROM stock_data")
total = cursor.fetchone()['count']
print(f"总记录数: {total}")

# 检查ROE字段
if total > 0:
    print("\n=== ROE 数据检查 ===")
    cursor = conn.execute("SELECT COUNT(*) as count FROM stock_data WHERE roe IS NOT NULL")
    roe_not_null = cursor.fetchone()['count']
    print(f"ROE非空: {roe_not_null}/{total}")
    
    cursor = conn.execute("SELECT COUNT(*) as count FROM stock_data WHERE roe >= 8.0")
    roe_ge_8 = cursor.fetchone()['count']
    print(f"ROE>=8%: {roe_ge_8}/{total}")
    
    # 查看前5条数据
    print("\n=== 前5条数据 ===")
    cursor = conn.execute("""
        SELECT code, name, dividend_yield, market_cap, composite_score, roe, debt_ratio
        FROM stock_data
        ORDER BY rank
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"  {row['code']} {row['name']}: 股息率={row['dividend_yield']}%, 市值={row['market_cap']}亿, 评分={row['composite_score']}, ROE={row['roe']}, 负债率={row['debt_ratio']}%")

conn.close()
