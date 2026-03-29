#!/usr/bin/env python3
"""
检查数据库中的ROE和支付率数据
"""
import sqlite3
import os

db_path = os.path.expanduser('~/Work/workbuddy_dir/hl3/instance/tracker.db')

if not os.path.exists(db_path):
    print("数据库不存在")
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# 统计数据
print("=" * 80)
print("数据库统计")
print("=" * 80)

cursor = conn.execute("SELECT COUNT(*) FROM stock_data")
total = cursor.fetchone()[0]
print(f"总记录数: {total}")

cursor = conn.execute("SELECT COUNT(*) FROM stock_data WHERE roe IS NOT NULL")
roe_count = cursor.fetchone()[0]
print(f"ROE非空: {roe_count}/{total}")

cursor = conn.execute("SELECT COUNT(*) FROM stock_data WHERE payout_ratio IS NOT NULL")
payout_count = cursor.fetchone()[0]
print(f"支付率非空: {payout_count}/{total}")

cursor = conn.execute("SELECT COUNT(*) FROM stock_data WHERE debt_ratio IS NOT NULL")
debt_count = cursor.fetchone()[0]
print(f"负债率非空: {debt_count}/{total}")

# 显示所有数据
print("\n" + "=" * 80)
print("完整数据列表")
print("=" * 80)

cursor = conn.execute("""
    SELECT rank, code, name, dividend_yield, roe, payout_ratio, debt_ratio
    FROM stock_data
    ORDER BY rank
""")

print(f"\n{'排名':<6s} {'代码':<8s} {'名称':<12s} {'股息率':<10s} {'ROE':<10s} {'支付率':<10s} {'负债率':<10s}")
print("-" * 80)

for row in cursor.fetchall():
    rank = str(row['rank']) if row['rank'] else 'N/A'
    code = row['code'] or ''
    name = row['name'] or ''

    div_yield = f"{row['dividend_yield']:.2f}%" if row['dividend_yield'] is not None else 'N/A'
    roe = f"{row['roe']:.2f}%" if row['roe'] is not None else 'N/A'
    payout = f"{row['payout_ratio']:.2f}%" if row['payout_ratio'] is not None else 'N/A'
    debt = f"{row['debt_ratio']:.2f}%" if row['debt_ratio'] is not None else 'N/A'

    print(f"{rank:<6s} {code:<8s} {name:<12s} {div_yield:<10s} {roe:<10s} {payout:<10s} {debt:<10s}")

conn.close()

print("\n" + "=" * 80)
print("总结")
print("=" * 80)
print(f"✅ ROE数据: {roe_count}/{total} 条有数据")
print(f"⚠️ 支付率数据: {payout_count}/{total} 条有数据")
print(f"⚠️ 负债率数据: {debt_count}/{total} 条有数据")
print("=" * 80)
