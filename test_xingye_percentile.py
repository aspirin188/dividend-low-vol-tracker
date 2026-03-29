"""
测试兴业银行(601166)股价百分位计算
"""
import akshare as ak
import numpy as np
from datetime import datetime, timedelta

code = '601166'
days = 250

print(f"=== 测试兴业银行({code})股价百分位 ===\n")

# 获取历史数据
print("1. 获取历史价格数据...")
df = ak.stock_zh_a_hist(
    symbol=code,
    period='daily',
    start_date=(datetime.now() - timedelta(days=days*2)).strftime('%Y%m%d'),
    end_date=datetime.now().strftime('%Y%m%d'),
    adjust='qfq'  # 前复权
)

print(f"   获取到 {len(df)} 天数据")

# 只取最近250天
df_tail = df.tail(days)
print(f"   取最近 {len(df_tail)} 天数据\n")

# 当前价格
current_price = float(df_tail['收盘'].iloc[-1])
print(f"2. 当前股价: {current_price} 元\n")

# 历史价格统计
historical_prices = df_tail['收盘'].values
print(f"3. 历史价格统计:")
print(f"   最高价: {np.max(historical_prices):.2f} 元")
print(f"   最低价: {np.min(historical_prices):.2f} 元")
print(f"   平均价: {np.mean(historical_prices):.2f} 元")
print(f"   中位数: {np.median(historical_prices):.2f} 元")
print(f"   标准差: {np.std(historical_prices):.2f} 元\n")

# 计算百分位
lower_count = sum(historical_prices < current_price)
percentile = (lower_count / len(historical_prices)) * 100

print(f"4. 百分位计算:")
print(f"   当前价格 {current_price} 元")
print(f"   低于当前价格的天数: {lower_count}")
print(f"   总天数: {len(historical_prices)}")
print(f"   百分位: {percentile:.2f}%\n")

# 价格分布
print(f"5. 价格分布 (当前 {current_price:.2f} 元):")
bins = np.percentile(historical_prices, [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
for i in range(len(bins)-1):
    count = sum((historical_prices >= bins[i]) & (historical_prices < bins[i+1]))
    print(f"   {bins[i]:6.2f} - {bins[i+1]:6.2f} 元: {count:3d} 天")

# 显示当前价格在分布中的位置
print(f"\n6. 当前价格位置判断:")
if current_price < np.percentile(historical_prices, 10):
    print(f"   当前股价处于历史最低10%区间")
elif current_price < np.percentile(historical_prices, 20):
    print(f"   当前股价处于历史10%-20%区间")
elif current_price < np.percentile(historical_prices, 30):
    print(f"   当前股价处于历史20%-30%区间")
else:
    # 找到具体区间
    for i in range(10, 100, 10):
        if current_price < np.percentile(historical_prices, i):
            print(f"   当前股价处于历史{i-10}%-{i}%区间")
            break
    else:
        print(f"   当前股价处于历史90%-100%区间")

# 显示最近价格趋势
print(f"\n7. 最近10个交易日收盘价:")
recent = df_tail.tail(10)[['日期', '收盘']]
for idx, row in recent.iterrows():
    print(f"   {row['日期']}: {row['收盘']:.2f} 元")

print(f"\n结论: 股价百分位 {percentile:.2f}% 表示当前价格高于过去{days}天中 {percentile:.1f}% 的交易日价格")
