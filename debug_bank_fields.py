"""调试银行股字段"""
import akshare as ak
import pandas as pd
import time

print("检查银行股和普通股票的财务字段差异")
print("=" * 80)

# 银行股
bank_code = '601939'
bank_full_code = f'sh{bank_code}'

# 普通股票
normal_code = '601318'
normal_full_code = f'sh{normal_code}'

for name, code, full_code in [('银行股-建设银行', bank_code, bank_full_code),
                              ('普通股-中国平安', normal_code, normal_full_code)]:
    print(f"\n{name} ({code}):")
    print("-" * 80)
    
    try:
        df = ak.stock_financial_report_sina(stock=full_code, symbol="资产负债表")
        print(f"总列数: {len(df.columns)}")
        
        # 查找权益相关字段
        print("\n权益相关字段:")
        latest = df.iloc[0]
        
        for col in df.columns:
            if '权益' in col or '股东' in col:
                value = latest[col] if pd.notna(latest[col]) else 'NaN'
                print(f"  - {col}: {value}")
        
        time.sleep(1)  # 避免频率限制
        
    except Exception as e:
        print(f"错误: {e}")
    
    time.sleep(2)

print("\n" + "=" * 80)
