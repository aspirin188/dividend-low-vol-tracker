"""
财务数据计算模块
v6.15: 改进ROE和负债率计算方式

核心改进：
1. ROE计算支持银行股（识别银行股专用字段）
2. 负债率计算支持多字段识别
3. 数据来源：akshare stock_financial_abstract_em
4. 错误处理和日志记录完善
"""

import akshare as ak
import pandas as pd
import numpy as np
from typing import Optional, Dict, List
import logging
import time

logger = logging.getLogger(__name__)


# ============================================================
# 银行股识别
# ============================================================

BANK_CODES = {
    # 国有大行
    '601939',  # 建设银行
    '601288',  # 农业银行
    '601988',  # 中国银行
    '601398',  # 工商银行
    '601328',  # 交通银行
    '601818',  # 光大银行
    # 股份制银行
    '600036',  # 招商银行
    '601166',  # 兴业银行
    '600016',  # 民生银行
    '600000',  # 浦发银行
    '601998',  # 中信银行
    '600015',  # 华夏银行
    '600919',  # 江苏银行
    '601169',  # 北京银行
    '601229',  # 上海银行
    '002142',  # 宁波银行
    '601838',  # 成都银行
    '601860',  # 紫金银行
    '601128',  # 常熟银行
    '601577',  # 长沙银行
    '601658',  # 邮储银行
    '601825',  # 农业银行
}

def is_bank_stock(code: str) -> bool:
    """判断是否为银行股"""
    return code in BANK_CODES


# ============================================================
# ROE计算（支持银行股）
# ============================================================

def calculate_roe(code: str, timeout: int = 10) -> Optional[Dict]:
    """
    计算ROE（支持银行股）
    
    公式: ROE = 净利润 / 股东权益 * 100%
    
    银行股特殊处理:
    - 字段名: "归属于母公司股东权益合计"
    - 而非普通股票的"股东权益合计"
    
    参数:
        code: 股票代码
        timeout: 超时时间
    
    返回:
        {
            'code': str,
            'roe': float,
            'net_profit': float,
            'equity': float,
            'source': str,
            'is_bank': bool,
            'field_used': str
        }
    """
    try:
        # 获取财务数据 - 使用新浪接口
        full_code = f"sh{code}" if code.startswith('6') else f"sz{code}"
        df = ak.stock_financial_report_sina(stock=full_code, symbol="资产负债表")
        
        if df is None or df.empty:
            logger.warning(f"无法获取财务数据 [{code}]")
            return None
        
        # 获取最新一期数据（第一行）
        latest = df.iloc[0]
        
        # 提取股东权益（区分银行股）
        equity = None
        field_used = None
        
        if is_bank_stock(code):
            # 银行股字段（银行业务特殊）
            bank_equity_fields = [
                '股东权益合计',
                '归属于母公司股东权益合计',
                '归属于母公司所有者权益合计',
                '所有者权益合计',
                '股东权益',
                '所有者权益'
            ]
            for field in bank_equity_fields:
                if field in latest.index and pd.notna(latest[field]):
                    equity = float(latest[field])
                    field_used = field
                    break
        else:
            # 普通股票字段
            for field in ['股东权益合计', '归属于母公司股东权益合计', '所有者权益合计']:
                if field in latest.index and pd.notna(latest[field]):
                    equity = float(latest[field])
                    field_used = field
                    break
        
        if equity is None or equity == 0:
            logger.warning(f"无法提取股东权益 [{code}]")
            return None
        
        # 获取利润表以提取净利润
        try:
            profit_df = ak.stock_financial_report_sina(stock=full_code, symbol="利润表")
            if profit_df is not None and not profit_df.empty:
                profit_latest = profit_df.iloc[0]
                
                # 提取净利润
                net_profit = None
                for field in ['净利润', '归属于母公司所有者的净利润', '归属于母公司股东的净利润']:
                    if field in profit_latest.index and pd.notna(profit_latest[field]):
                        net_profit = float(profit_latest[field])
                        break
                
                if net_profit and equity:
                    # 计算ROE
                    roe = (net_profit / equity) * 100
                    roe = round(roe, 2)
                    
                    return {
                        'code': code,
                        'roe': roe,
                        'net_profit': net_profit,
                        'equity': equity,
                        'source': 'calculation',
                        'is_bank': is_bank_stock(code),
                        'field_used': field_used
                    }
        except Exception as e:
            logger.warning(f"获取利润表失败 [{code}]: {e}")
        
        # 如果利润表获取失败，建议使用yjbb数据
        logger.warning(f"无法计算ROE，建议使用yjbb数据 [{code}]")
        return None
        
    except Exception as e:
        logger.error(f"计算ROE失败 [{code}]: {e}")
        return None


# ============================================================
# 负债率计算（改进版）
# ============================================================

def calculate_debt_ratio(code: str, timeout: int = 10) -> Optional[Dict]:
    """
    计算资产负债率
    
    公式: 负债率 = 总负债 / 总资产 * 100%
    
    参数:
        code: 股票代码
        timeout: 超时时间
    
    返回:
        {
            'code': str,
            'debt_ratio': float,
            'total_debt': float,
            'total_assets': float,
            'source': str,
            'field_used': dict
        }
    """
    try:
        # 获取财务数据 - 使用新浪接口
        full_code = f"sh{code}" if code.startswith('6') else f"sz{code}"
        df = ak.stock_financial_report_sina(stock=full_code, symbol="资产负债表")
        
        if df is None or df.empty:
            logger.warning(f"无法获取财务数据 [{code}]")
            return None
        
        # 获取最新一期数据
        latest = df.iloc[0]
        
        # 提取总负债
        total_debt = None
        debt_field = None
        for field in ['负债合计', '负债总额', '总负债', '负债']:
            if field in latest.index and pd.notna(latest[field]):
                total_debt = float(latest[field])
                debt_field = field
                break
        
        if total_debt is None:
            logger.warning(f"无法提取总负债 [{code}]")
            return None
        
        # 提取总资产
        total_assets = None
        asset_field = None
        for field in ['资产总计', '资产总额', '总资产', '资产']:
            if field in latest.index and pd.notna(latest[field]):
                total_assets = float(latest[field])
                asset_field = field
                break
        
        if total_assets is None or total_assets == 0:
            logger.warning(f"无法提取总资产 [{code}]")
            return None
        
        # 计算负债率
        debt_ratio = (total_debt / total_assets) * 100
        debt_ratio = round(debt_ratio, 2)
        
        return {
            'code': code,
            'debt_ratio': debt_ratio,
            'total_debt': total_debt,
            'total_assets': total_assets,
            'source': 'calculation',
            'field_used': {
                'debt': debt_field,
                'assets': asset_field
            }
        }
        
    except Exception as e:
        logger.error(f"计算负债率失败 [{code}]: {e}")
        return None


# ============================================================
# 批量计算
# ============================================================

def calculate_roe_batch(codes: List[str], 
                       delay: float = 0.5,
                       timeout: int = 10) -> Dict[str, Optional[Dict]]:
    """
    批量计算ROE
    
    参数:
        codes: 股票代码列表
        delay: 请求间隔（避免频率限制）
        timeout: 超时
    
    返回:
        {code: result_dict}
    """
    results = {}
    
    for code in codes:
        result = calculate_roe(code, timeout)
        results[code] = result
        
        # 延迟
        if delay > 0:
            time.sleep(delay)
    
    return results


def calculate_debt_ratio_batch(codes: List[str],
                              delay: float = 0.5,
                              timeout: int = 10) -> Dict[str, Optional[Dict]]:
    """
    批量计算负债率
    
    参数:
        codes: 股票代码列表
        delay: 请求间隔
        timeout: 超时
    
    返回:
        {code: result_dict}
    """
    results = {}
    
    for code in codes:
        result = calculate_debt_ratio(code, timeout)
        results[code] = result
        
        # 延迟
        if delay > 0:
            time.sleep(delay)
    
    return results


# ============================================================
# 数据验证
# ============================================================

def validate_roe_with_yjbb(code: str, 
                          roe_calculated: float,
                          tolerance: float = 0.05) -> Dict:
    """
    用akshare yjbb数据验证计算出的ROE
    
    参数:
        code: 股票代码
        roe_calculated: 计算出的ROE
        tolerance: 允许的相对差异
    
    返回:
        {
            'code': str,
            'roe_calculated': float,
            'roe_yjbb': float,
            'difference': float,
            'difference_pct': float,
            'is_consistent': bool,
            'confidence': str
        }
    """
    try:
        # 从yjbb获取ROE
        df = ak.stock_yjbb_em(date="20240930")
        row = df[df['股票代码'] == code]
        
        if row.empty:
            return {
                'code': code,
                'roe_calculated': roe_calculated,
                'roe_yjbb': None,
                'difference': None,
                'difference_pct': None,
                'is_consistent': None,
                'confidence': 'low',
                'message': 'yjbb无数据'
            }
        
        roe_yjbb = float(row['ROE'].values[0])
        
        # 计算差异
        difference = abs(roe_calculated - roe_yjbb)
        difference_pct = difference / roe_yjbb if roe_yjbb != 0 else 0
        
        # 判断一致性
        is_consistent = difference_pct <= tolerance
        
        if is_consistent:
            confidence = 'high'
            message = f'数据一致（差异{difference_pct*100:.2f}%）'
        else:
            confidence = 'medium'
            message = f'数据不一致（差异{difference_pct*100:.2f}%）'
        
        return {
            'code': code,
            'roe_calculated': roe_calculated,
            'roe_yjbb': roe_yjbb,
            'difference': round(difference, 2),
            'difference_pct': round(difference_pct * 100, 2),
            'is_consistent': is_consistent,
            'confidence': confidence,
            'message': message
        }
        
    except Exception as e:
        logger.error(f"验证ROE失败 [{code}]: {e}")
        return {
            'code': code,
            'roe_calculated': roe_calculated,
            'roe_yjbb': None,
            'difference': None,
            'difference_pct': None,
            'is_consistent': None,
            'confidence': 'low',
            'message': f'验证失败: {e}'
        }


# ============================================================
# 统计函数
# ============================================================

def get_calculation_stats(results: Dict[str, Optional[Dict]], field: str = 'roe') -> Dict:
    """
    统计计算结果
    
    参数:
        results: 计算结果字典
        field: 字段名 ('roe' 或 'debt_ratio')
    
    返回:
        {
            'total': int,
            'success': int,
            'success_rate': float,
            'bank_stocks': int,
            'bank_success': int,
            'bank_success_rate': float
        }
    """
    total = len(results)
    success = sum(1 for r in results.values() if r is not None and field in r)
    
    # 银行股统计
    bank_codes = [code for code in results.keys() if is_bank_stock(code)]
    bank_success = sum(1 for code in bank_codes if results.get(code) and field in results[code])
    
    return {
        'total': total,
        'success': success,
        'success_rate': round(success / total * 100, 2) if total > 0 else 0,
        'bank_stocks': len(bank_codes),
        'bank_success': bank_success,
        'bank_success_rate': round(bank_success / len(bank_codes) * 100, 2) if bank_codes else 0
    }
