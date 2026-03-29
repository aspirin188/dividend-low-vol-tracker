#!/bin/bash
# 简单测试脚本

echo "=========================================="
echo "1. 发送运行请求"
echo "=========================================="

# 发送请求（后台运行）
nohup curl -X POST http://127.0.0.1:5050/api/run > /tmp/result.json 2>&1 &
PID=$!
echo "请求已发送 (PID: $PID)"

echo ""
echo "=========================================="
echo "2. 等待处理完成（每10秒检查一次）"
echo "=========================================="

for i in {1..30}; do
    sleep 10
    echo "已等待 $((i*10)) 秒..."

    # 检查是否完成
    if ! ps -p $PID > /dev/null 2>&1; then
        echo ""
        echo "✓ 处理完成!"
        echo ""
        echo "=========================================="
        echo "3. 查看结果"
        echo "=========================================="
        cat /tmp/result.json
        echo ""
        exit 0
    fi

    # 显示当前进度
    echo "  当前进度："
    tail -3 /tmp/hl3_app.log | grep -E "步骤|ROE|EPS|筛选" | sed 's/^/    /'
    echo ""
done

echo "✗ 超时！"
kill $PID 2>/dev/null
exit 1
