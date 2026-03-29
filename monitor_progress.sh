#!/bin/bash
# 监控应用日志，实时显示进度

echo "开始监控应用日志..."
echo "等待用户点击'运行'按钮..."
echo ""

# 记录当前日志行数
INITIAL_LINES=$(wc -l < /tmp/hl3_app.log)

# 监控循环
while true; do
    # 检测是否有新的运行请求
    NEW_LINES=$(tail -n +$INITIAL_LINES /tmp/hl3_app.log 2>/dev/null)

    if echo "$NEW_LINES" | grep -q "POST /api/run"; then
        echo "========================================"
        echo "✓ 检测到运行请求！"
        echo "========================================"
        echo ""

        # 实时显示进度（持续120秒）
        for i in {1..120}; do
            # 获取最新的关键日志
            RECENT=$(tail -5 /tmp/hl3_app.log 2>/dev/null)

            # 提取并显示进度信息
            echo "$RECENT" | grep -E "步骤|ROE|EPS|筛选|评分|成功|失败" | while read line; do
                # 高亮显示关键信息
                if echo "$line" | grep -q "✓"; then
                    echo "✅ $line"
                elif echo "$line" | grep -q "✗"; then
                    echo "❌ $line"
                elif echo "$line" | grep -q "步骤"; then
                    echo ""
                    echo "📌 $line"
                else
                    echo "   $line"
                fi
            done

            # 检查是否完成
            if echo "$RECENT" | grep -q "success.*true\|success.*false"; then
                echo ""
                echo "========================================"
                echo "✓ 处理完成！"
                echo "========================================"
                echo ""

                # 显示最终结果
                echo "最终状态："
                tail -10 /tmp/hl3_app.log | grep -E "success|error|count" | head -3

                echo ""
                echo "========================================"
                echo "检查ROE数据"
                echo "========================================"

                # 检查数据库
                python3 - << 'PYTHON'
import sqlite3
import os

db_path = os.path.expanduser('~/Work/workbuddy_dir/hl3/instance/tracker.db')
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT COUNT(*) FROM stock_data WHERE roe IS NOT NULL")
    roe_count = cursor.fetchone()[0]
    cursor = conn.execute("SELECT COUNT(*) FROM stock_data")
    total_count = cursor.fetchone()[0]

    print(f"✓ 数据库中ROE数据: {roe_count}/{total_count} 只股票")

    if roe_count > 0:
        print("\n前5只股票ROE数据:")
        cursor = conn.execute("""
            SELECT code, name, dividend_yield, roe, debt_ratio
            FROM stock_data
            ORDER BY rank
            LIMIT 5
        """)
        for row in cursor.fetchall():
            print(f"  {row[0]} {row[1]}: 股息率={row[2]}%, ROE={row[3]}%, 负债率={row[4]}%")
        print("\n✅✅✅ ROE数据修复成功！✅✅✅")
    else:
        print("\n⚠️ ROE数据为空，请检查日志")

    conn.close()
else:
    print("✗ 数据库文件不存在")
PYTHON

                exit 0
            fi

            sleep 1
        done

        echo ""
        echo "⏱️ 处理时间较长，请继续等待..."
        exit 0
    fi

    sleep 1
done
