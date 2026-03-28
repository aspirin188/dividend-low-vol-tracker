"""
路由 — 红利低波跟踪系统

4 个 API：
  GET  /          → 渲染首页
  POST /api/run   → 一键运行（同步，超时10分钟）
  GET  /api/stocks→ 获取标的列表（支持搜索和行业筛选）
  GET  /api/export→ 导出 Excel
"""

import os
import sqlite3
from io import BytesIO
from flask import (
    Blueprint, render_template, request, jsonify, send_file,
    current_app,
)
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, numbers
from openpyxl.utils import get_column_letter

from server.services.fetcher import merge_all_data
from server.services.scorer import filter_stocks, calculate_scores, prepare_results

bp = Blueprint('main', __name__)


# ============================================================
# 数据库辅助
# ============================================================

def get_db():
    """获取数据库连接。"""
    db_path = os.path.join(current_app.instance_path, 'tracker.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表。"""
    conn = get_db()
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
            data_date        TEXT,
            updated_at       TEXT
        )
    ''')

    # 兼容旧数据库：新增列
    for col, col_type in [('price', 'REAL'), ('pe', 'REAL'), ('pb', 'REAL'), ('market', 'TEXT'), ('pinyin_abbr', 'TEXT'), ('dividend_years', 'INTEGER'), ('roe', 'REAL'), ('debt_ratio', 'REAL')]:
        try:
            conn.execute(f'ALTER TABLE stock_data ADD COLUMN {col} {col_type}')
        except sqlite3.OperationalError:
            pass  # 列已存在

    conn.commit()
    conn.close()


# ============================================================
# GET / → 首页
# ============================================================

@bp.route('/')
def index():
    return render_template('index.html')


# ============================================================
# POST /api/run → 一键运行
# ============================================================

@bp.route('/api/run', methods=['POST'])
def run():
    """
    一键运行：获取数据 → 筛选 → 评分 → 保存。
    同步执行，前端超时设为 600s。
    """
    try:
        # 1. 合并所有数据
        merged = merge_all_data()

        if merged.empty:
            return jsonify({'success': False, 'error': '未获取到任何数据，请检查网络'})

        # 2. 硬性筛选
        filtered = filter_stocks(merged)
        print(f"筛选后: {len(filtered)} 只")

        if filtered.empty:
            return jsonify({'success': False, 'error': '没有符合条件的股票，请稍后再试'})

        # 3. 评分
        scored = calculate_scores(filtered)

        # 4. 整理并保存
        result = prepare_results(scored)
        conn = get_db()

        # 清空旧数据
        conn.execute('DELETE FROM stock_data')

        # 插入新数据
        result.to_sql('stock_data', conn, if_exists='append', index=False)
        conn.commit()
        conn.close()

        data_date = result['data_date'].iloc[0] if not result.empty else ''
        return jsonify({
            'success': True,
            'count': len(result),
            'data_date': data_date,
        })

    except Exception as e:
        print(f"运行失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


# ============================================================
# GET /api/stocks → 标的列表
# ============================================================

@bp.route('/api/stocks')
def stocks():
    """
    获取标的列表，支持搜索和多维筛选。

    Query 参数：
    - q: 搜索关键词（名称或代码）
    - industry: 行业筛选（大类行业）
    - market_cap_range: 市值区间（large≥1000亿 / medium 500-1000亿 / small 100-500亿）
    - div_yield_min: 股息率下限（4 / 6 / 8）
    - market: 市场类型（sh=沪市 / sz=深市 / gem=创业板 / star=科创板）
    """
    q = request.args.get('q', '').strip()
    industry = request.args.get('industry', '').strip()
    market_cap_range = request.args.get('market_cap_range', '').strip()
    div_yield_min = request.args.get('div_yield_min', '').strip()
    market = request.args.get('market', '').strip()

    conn = get_db()
    conn.row_factory = sqlite3.Row
    query = 'SELECT * FROM stock_data ORDER BY rank'
    params = []

    conditions = []
    if q:
        # v6.9: 支持简拼搜索，同时匹配名称、代码、拼音首字母
        conditions.append('(name LIKE ? OR code LIKE ? OR pinyin_abbr LIKE ?)')
        params.extend([f'%{q}%', f'%{q}%', f'%{q}%'])
    if industry:
        conditions.append('industry = ?')
        params.append(industry)
    if market_cap_range:
        cap_ranges = {
            'large': ('market_cap >= 1000', []),
            'medium': ('market_cap >= 500 AND market_cap < 1000', []),
            'small': ('market_cap >= 100 AND market_cap < 500', []),
        }
        if market_cap_range in cap_ranges:
            conditions.append(cap_ranges[market_cap_range][0])
            params.extend(cap_ranges[market_cap_range][1])
    if div_yield_min:
        try:
            min_yield = float(div_yield_min)
            conditions.append('dividend_yield >= ?')
            params.append(min_yield)
        except ValueError:
            pass
    if market:
        market_map = {
            'sh': '沪市',
            'sz': '深市',
            'gem': '创业板',
            'star': '科创板',
        }
        if market in market_map:
            conditions.append('market = ?')
            params.append(market_map[market])

    if conditions:
        query = 'SELECT * FROM stock_data WHERE ' + ' AND '.join(conditions) + ' ORDER BY rank'

    rows = conn.execute(query, params).fetchall()

    # 获取行业列表（用于筛选下拉）
    industries = [r['industry'] for r in conn.execute(
        'SELECT DISTINCT industry FROM stock_data WHERE industry IS NOT NULL AND industry != "" ORDER BY industry'
    ).fetchall()]

    # 获取元数据
    meta = conn.execute('SELECT data_date, updated_at FROM stock_data LIMIT 1').fetchone()

    conn.close()

    stock_list = [dict(r) for r in rows]

    return jsonify({
        'stocks': stock_list,
        'industries': industries,
        'total': len(stock_list),
        'data_date': dict(meta)['data_date'] if meta else None,
        'updated_at': dict(meta)['updated_at'] if meta else None,
    })


# ============================================================
# GET /api/export → 导出 Excel
# ============================================================

@bp.route('/api/export')
def export():
    """
    导出 Excel。

    文件名：红利低波_{data_date}_{count}只.xlsx
    列（17列）：排名 | 代码 | 名称 | 行业 | 市场 | 股价 | PE | PB | 股息率(%) | 总市值(亿) | 综合评分 | 波动率(%) | 股利支付率(%) | EPS | 分红年数 | ROE(%) | 负债率(%)
    """
    conn = get_db()
    conn.row_factory = sqlite3.Row
    rows = conn.execute('SELECT * FROM stock_data ORDER BY rank').fetchall()
    conn.close()

    if not rows:
        return jsonify({'error': '没有数据可导出，请先运行'}), 404

    stocks = [dict(r) for r in rows]
    data_date = stocks[0].get('data_date', 'unknown')
    count = len(stocks)

    # 创建 Excel
    wb = Workbook()
    ws = wb.active
    ws.title = '红利低波'

    # 表头（17列）- v6.11新增ROE、负债率
    headers = ['排名', '代码', '名称', '行业', '市场', '股价', 'PE', 'PB', '股息率(%)', '总市值(亿)', '综合评分', '波动率(%)', '股利支付率(%)', 'EPS', '分红年数', 'ROE(%)', '负债率(%)']
    header_font = Font(bold=True)
    header_alignment = Alignment(horizontal='center')

    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.alignment = header_alignment

    # 数据行
    for row_idx, s in enumerate(stocks, 2):
        ws.cell(row=row_idx, column=1, value=s.get('rank')).alignment = Alignment(horizontal='center')
        ws.cell(row=row_idx, column=2, value=s.get('code')).alignment = Alignment(horizontal='center')
        ws.cell(row=row_idx, column=3, value=s.get('name'))
        ws.cell(row=row_idx, column=4, value=s.get('industry') or '')
        ws.cell(row=row_idx, column=5, value=s.get('market') or '')
        ws.cell(row=row_idx, column=6, value=s.get('price')).number_format = '0.00'
        ws.cell(row=row_idx, column=7, value=s.get('pe')).number_format = '0.00'
        ws.cell(row=row_idx, column=8, value=s.get('pb')).number_format = '0.00'
        ws.cell(row=row_idx, column=9, value=s.get('dividend_yield')).number_format = '0.00'
        ws.cell(row=row_idx, column=10, value=s.get('market_cap')).number_format = '0.00'
        ws.cell(row=row_idx, column=11, value=s.get('composite_score')).number_format = '0.00'
        ws.cell(row=row_idx, column=12, value=s.get('annual_vol')).number_format = '0.00'
        ws.cell(row=row_idx, column=13, value=s.get('payout_ratio')).number_format = '0.00'
        ws.cell(row=row_idx, column=14, value=s.get('eps')).number_format = '0.00'
        ws.cell(row=row_idx, column=15, value=s.get('dividend_years')).alignment = Alignment(horizontal='center')
        ws.cell(row=row_idx, column=16, value=s.get('roe')).number_format = '0.00'
        ws.cell(row=row_idx, column=17, value=s.get('debt_ratio')).number_format = '0.00'

    # 冻结首行
    ws.freeze_panes = 'A2'

    # 自动列宽
    col_widths = [8, 12, 16, 12, 10, 10, 10, 10, 12, 12, 12, 12, 14, 10, 10, 10, 10]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # 输出到内存
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f'红利低波_{data_date}_{count}只.xlsx'
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename,
    )
