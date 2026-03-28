"""快速测试数据流（不含波动率）"""
import warnings; warnings.filterwarnings('ignore')
import sys, time
import pandas as pd
from server.services.fetcher import fetch_all_quotes, fetch_eps_batch, fetch_dividend_for_candidates

t0 = time.time()
print("=== 数据流测试 ===")

print("[1] 行情...", flush=True)
q = fetch_all_quotes()
print(f"  {len(q)}只 {time.time()-t0:.1f}s")

print("[2] EPS...", flush=True)
e = fetch_eps_batch()
print(f"  {len(e)}只 {time.time()-t0:.1f}s")

m = q.merge(e, on='code', how='left')
m = m[~m['name'].str.contains('ST', case=False, na=False)]
for c in ['dividend_yield_ttm','market_cap','basic_eps']:
    m[c] = pd.to_numeric(m[c], errors='coerce')

p = m[
    (m['dividend_yield_ttm']>=4.0) & (m['market_cap']>=100) & (m['basic_eps']>0) &
    m['dividend_yield_ttm'].notna() & m['market_cap'].notna() & m['basic_eps'].notna()
].copy()
codes = p['code'].tolist()
print(f"[3] 初筛: {len(codes)}只 {time.time()-t0:.1f}s")

print("[4] 分红...", flush=True)
d = fetch_dividend_for_candidates(codes)
f = p.merge(d, on='code', how='left')

print(f"[OK] {len(f)}只, 总{time.time()-t0:.1f}s")
print("\n前10:")
print(f[['code','name','dividend_yield_ttm','market_cap','basic_eps','payout_ratio']].head(10).to_string())
