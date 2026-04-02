#!/usr/bin/env python3
"""V8.2 快速验证测试（仅验证关键修复点）"""
import os, sys, warnings
warnings.filterwarnings('ignore')

# 清除代理
for key in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY',
            'all_proxy', 'ALL_PROXY', 'no_proxy', 'NO_PROXY']:
    os.environ.pop(key, None)

# 全局 monkey-patch requests 禁用代理
import requests as _req
_orig_get = _req.Session.get
_orig_post = _req.Session.post
_req.Session.get = lambda self, url, **kw: _orig_get(self, url, **{**kw, 'proxies': {'http': None, 'https': None}})
_req.Session.post = lambda self, url, **kw: _orig_post(self, url, **{**kw, 'proxies': {'http': None, 'https': None}})

sys.path.insert(0, '/Users/macair/Work/workbuddy_dir/hl3')

passed = 0
failed = 0

def test(name, ok, detail=''):
    global passed, failed
    status = '✓' if ok else '✗'
    print(f'  {status} {name} {detail}')
    if ok: passed += 1
    else: failed += 1

# ============================================================
print('\n=== 1. fetch_dividend_data 增强字段 ===')
from server.services.fetcher import fetch_dividend_data
div_df = fetch_dividend_data()
test('获取分红数据', not div_df.empty, f'→ {len(div_df)} 只')
if not div_df.empty:
    test('包含 total_shares', 'total_shares' in div_df.columns)
    test('包含 bps', 'bps' in div_df.columns)
    test('包含 div_per_share', 'div_per_share' in div_df.columns)
    valid_s = div_df['total_shares'].notna().sum()
    valid_b = div_df['bps'].notna().sum()
    test('总股本有效', valid_s > 100, f'→ {valid_s} 只')
    test('每股净资产有效', valid_b > 100, f'→ {valid_b} 只')

# ============================================================
print('\n=== 2. merge_all_data PE/PB/市值 ===')
from server.services.fetcher import merge_all_data
print('开始 merge_all_data（3-5 分钟）...')
result = merge_all_data()
test('有候选股', not result.empty, f'→ {len(result)} 只')

if not result.empty:
    # PE
    pe_v = result['pe'].notna().sum()
    pe_m = result['pe'].dropna().mean()
    test('PE有效', pe_v > len(result)*0.5, f'→ {pe_v}/{len(result)} 只，均值={pe_m:.1f}')
    test('PE合理', 3 <= pe_m <= 50, f'→ {pe_m:.1f}')
    
    # PB
    pb_v = result['pb'].notna().sum()
    pb_m = result['pb'].dropna().mean()
    test('PB有效', pb_v > len(result)*0.3, f'→ {pb_v}/{len(result)} 只，均值={pb_m:.1f}')
    
    # 市值
    cap_m = result['market_cap'].dropna().mean()
    test('市值合理', 100 <= cap_m <= 50000, f'→ 均值={cap_m:.0f}亿')
    
    # 已知股票
    for code, name, exp_cap in [('601398','工行',20000),('600036','招行',9000)]:
        row = result[result['code']==code]
        if not row.empty:
            actual = row['market_cap'].values[0]
            err = abs(actual-exp_cap)/exp_cap*100
            test(f'{name}市值误差<30%', err<30, f'→ {actual:.0f}亿(预期≈{exp_cap})')

    # dividend_per_share
    if 'dividend_per_share' in result.columns:
        dps = result['dividend_per_share'].dropna()
        test('每股股利合理', 0.1 <= dps.mean() <= 3, f'→ {dps.mean():.2f}元')

    # payout_ratio
    pr = result['payout_ratio'].dropna()
    test('支付率合理', 10 <= pr.mean() <= 100, f'→ {pr.mean():.1f}%')

# ============================================================
print('\n=== 3. 分红年数 ===')
from server.services.fetcher import get_dividend_years_batch
dy = get_dividend_years_batch(['601398','600036','600519','000651'], years=4)
vals = list(dy.values())
test('不全相同', len(set(vals))>1, f'→ {vals}')

# ============================================================
print('\n=== 4. 支付率稳定性 ===')
from server.services.fetcher import calculate_payout_stability_score
scores = {}
for c in ['601398','600036','000651']:
    a, s = calculate_payout_stability_score(c)
    scores[c] = s
    print(f'  {c}: 稳定性={s}')
sv = [v for v in scores.values() if v is not None]
test('稳定性有区分', len(set(sv))>1, f'→ {sv}')

# ============================================================
print('\n=== 5. 桩函数已删除 ===')
import server.services.fetcher as fm
has_stale = hasattr(fm, 'calculate_ma_position_batch') and \
    callable(getattr(fm, 'calculate_ma_position_batch', None))
test('无桩函数', not has_stale)

# ============================================================
print(f'\n{"="*60}')
print(f'结果: {passed} 通过, {failed} 失败')
if failed > 0:
    sys.exit(1)
