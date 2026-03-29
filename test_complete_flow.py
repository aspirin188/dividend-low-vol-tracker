#!/usr/bin/env python3
"""
完整测试流程 - 包括数据库保存
"""
import sys
import os
import sqlite3
import traceback

os.environ['FLASK_APP'] = 'app'
os.environ['FLASK_ENV'] = 'development'
sys.path.insert(0, '.')

print("=" * 80)
print("完整测试流程 - 从数据获取到数据库保存")
print("=" * 80)

try:
    # 导入模块
    print("\n[步骤1] 导入模块...", flush=True)
    from server.services.fetcher import merge_all_data
    from server.services.scorer import filter_stocks, calculate_scores, prepare_results
    print("✓ 导入成功", flush=True)

    # 获取数据
    print("\n[步骤2] 获取并合并数据...", flush=True)
    merged = merge_all_data()

    if merged.empty:
        print("✗ merge_all_data() 返回空数据", flush=True)
        sys.exit(1)

    print(f"✓ 获取到 {len(merged)} 条原始数据", flush=True)

    # 检查关键字段
    print("\n[步骤3] 检查关键字段...", flush=True)
    key_fields = ['roe', 'payout_ratio', 'debt_ratio', 'dividend_per_share', 'basic_eps']
    for field in key_fields:
        if field in merged.columns:
            dtype = merged[field].dtype
            not_null = merged[field].notna().sum()
            print(f"  {field:20s}: dtype={dtype:10s}, 非空={not_null:4d}/{len(merged)}", flush=True)
        else:
            print(f"  {field:20s}: ❌ 列不存在", flush=True)

    # 筛选
    print("\n[步骤4] 筛选数据...", flush=True)
    filtered = filter_stocks(merged)
    print(f"✓ 筛选后 {len(filtered)} 条", flush=True)

    if filtered.empty:
        print("✗ 筛选后无数据，检查筛选条件...", flush=True)
        print(f"  股息率>=3%: {(merged['dividend_yield_ttm'] >= 3.0).sum()}", flush=True)
        print(f"  市值>=500亿: {(merged['market_cap'] >= 500.0).sum()}", flush=True)
        print(f"  EPS>0: {(merged['basic_eps'] > 0).sum()}", flush=True)
        print(f"  ROE>=8%: {(merged['roe'] >= 8.0).sum()}", flush=True)
        print(f"  ROE非空: {merged['roe'].notna().sum()}", flush=True)
        sys.exit(1)

    # 评分
    print("\n[步骤5] 计算评分...", flush=True)
    scored = calculate_scores(filtered)
    print(f"✓ 评分完成", flush=True)

    # 整理结果
    print("\n[步骤6] 整理结果...", flush=True)
    result = prepare_results(scored)
    print(f"✓ 整理完成，共 {len(result)} 条", flush=True)

    # 检查最终结果
    print("\n[步骤7] 检查最终结果字段...", flush=True)
    for field in ['roe', 'payout_ratio', 'debt_ratio']:
        if field in result.columns:
            not_null = result[field].notna().sum()
            print(f"  {field:15s}: 非空={not_null:4d}/{len(result)}", flush=True)
        else:
            print(f"  {field:15s}: ❌ 列不存在", flush=True)

    # 显示前5条数据
    print("\n[步骤8] 前5条数据预览...", flush=True)
    print(result[['code', 'name', 'dividend_yield', 'roe', 'payout_ratio', 'debt_ratio']].head(), flush=True)

    # 保存到数据库
    print("\n[步骤9] 保存到数据库...", flush=True)
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'tracker.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)

    # 创建表（如果不存在）
    conn.execute('''
        CREATE TABLE IF NOT EXISTS stock_data (
            code             TEXT PRIMARY KEY,
            name             TEXT,
            industry         TEXT,
            market           TEXT,
            dividend_yield   REAL,
            annual_vol       REAL,
            composite_score  REAL,
            rank             INTEGER,
            market_cap       REAL,
            payout_ratio     REAL,
            eps              REAL,
            price            REAL,
            pe               REAL,
            pb               REAL,
            pinyin_abbr      TEXT,
            dividend_years   INTEGER,
            roe              REAL,
            debt_ratio       REAL,
            data_date        TEXT,
            updated_at       TEXT
        )
    ''')

    # 清空旧数据
    conn.execute('DELETE FROM stock_data')

    # 插入新数据
    result.to_sql('stock_data', conn, if_exists='append', index=False)
    conn.commit()
    print(f"✓ 已保存 {len(result)} 条数据到数据库", flush=True)

    conn.close()

    # 验证数据库
    print("\n[步骤10] 验证数据库...", flush=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # 总数
    cursor = conn.execute("SELECT COUNT(*) FROM stock_data")
    total = cursor.fetchone()[0]
    print(f"  总记录数: {total}", flush=True)

    # ROE统计
    cursor = conn.execute("SELECT COUNT(*) FROM stock_data WHERE roe IS NOT NULL")
    roe_count = cursor.fetchone()[0]
    print(f"  ROE非空: {roe_count}/{total}", flush=True)

    # 支付率统计
    cursor = conn.execute("SELECT COUNT(*) FROM stock_data WHERE payout_ratio IS NOT NULL")
    payout_count = cursor.fetchone()[0]
    print(f"  支付率非空: {payout_count}/{total}", flush=True)

    # 负债率统计
    cursor = conn.execute("SELECT COUNT(*) FROM stock_data WHERE debt_ratio IS NOT NULL")
    debt_count = cursor.fetchone()[0]
    print(f"  负债率非空: {debt_count}/{total}", flush=True)

    # 显示前5条
    print("\n[步骤11] 数据库中前5条数据...", flush=True)
    cursor = conn.execute("""
        SELECT code, name, dividend_yield, roe, payout_ratio, debt_ratio
        FROM stock_data
        ORDER BY rank
        LIMIT 5
    """)

    print(f"{'代码':<8s} {'名称':<10s} {'股息率':<8s} {'ROE':<8s} {'支付率':<8s} {'负债率':<8s}", flush=True)
    print("-" * 60, flush=True)
    for row in cursor.fetchall():
        code = row['code'] or ''
        name = row['name'] or ''
        div_yield = f"{row['dividend_yield']:.2f}%" if row['dividend_yield'] is not None else 'N/A'
        roe = f"{row['roe']:.2f}%" if row['roe'] is not None else 'N/A'
        payout = f"{row['payout_ratio']:.2f}%" if row['payout_ratio'] is not None else 'N/A'
        debt = f"{row['debt_ratio']:.2f}%" if row['debt_ratio'] is not None else 'N/A'

        print(f"{code:<8s} {name:<10s} {div_yield:<8s} {roe:<8s} {payout:<8s} {debt:<8s}", flush=True)

    conn.close()

    print("\n" + "=" * 80)
    print("✅✅✅ 完整测试成功！所有步骤完成！")
    print("=" * 80)
    print("\n总结:")
    print(f"  - 获取数据: {len(merged)} 条")
    print(f"  - 筛选后: {len(filtered)} 条")
    print(f"  - 最终入库: {len(result)} 条")
    print(f"  - ROE数据: {roe_count}/{total} 条有数据")
    print(f"  - 支付率数据: {payout_count}/{total} 条有数据")
    print(f"  - 负债率数据: {debt_count}/{total} 条有数据 (数据源不可用)")
    print("=" * 80)

except Exception as e:
    print("\n" + "=" * 80)
    print(f"❌ 错误: {e}")
    print("=" * 80)
    traceback.print_exc()
    sys.exit(1)
