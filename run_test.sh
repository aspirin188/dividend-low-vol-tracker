#!/bin/bash
# 运行测试并实时显示日志

echo "=========================================="
echo "开始运行测试..."
echo "=========================================="
echo ""

# 启动curl请求（后台运行）
curl -X POST http://127.0.0.1:5050/api/run > /tmp/curl_result.json 2>&1 &
CURL_PID=$!

echo "测试已启动，PID: $CURL_PID"
echo "正在处理中，请稍候..."
echo ""
echo "进度日志："
echo "----------------------------------------"

# 实时显示日志（最多等待300秒）
for i in {1..300}; do
    # 显示最新的日志
    tail -1 /tmp/hl3_app.log 2>/dev/null | grep -E "(步骤|ROE|EPS|筛选|评分|成功|失败|错误)" --color=always
    
    # 检查curl是否完成
    if ! ps -p $CURL_PID > /dev/null 2>&1; then
        echo ""
        echo "----------------------------------------"
        echo "✓ 测试完成!"
        echo "----------------------------------------"
        echo ""
        
        # 显示结果
        cat /tmp/curl_result.json | python3 -m json.tool 2>/dev/null || cat /tmp/curl_result.json
        echo ""
        
        # 如果成功，检查数据库中的ROE数据
        if grep -q '"success": true' /tmp/curl_result.json; then
            echo "检查数据库中的ROE数据..."
            python3 - << 'PYTHON_SCRIPT'
import sqlite3
import os

db_path = os.path.expanduser('~/Work/workbuddy_dir/hl3/instance/tracker.db')
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT COUNT(*) FROM stock_data WHERE roe IS NOT NULL")
    roe_count = cursor.fetchone()[0]
    cursor = conn.execute("SELECT COUNT(*) FROM stock_data")
    total_count = cursor.fetchone()[0]
    
    print(f"✓ ROE数据: {roe_count}/{total_count} 只股票")
    
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
    
    conn.close()
else:
    print("✗ 数据库不存在")
PYTHON_SCRIPT
        fi
        
        exit 0
    fi
    
    sleep 1
done

echo ""
echo "✗ 超时！测试运行超过5分钟"
kill $CURL_PID 2>/dev/null
exit 1
