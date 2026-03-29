"""
价格双重验证模块
v6.18: 集成健康度追踪器 + 异步并发优化

核心功能：
1. 从新浪和腾讯两个数据源获取实时价格
2. 交叉验证数据一致性
3. 根据数据源可靠性动态调整可信度
4. 异步并发请求，提升性能

设计原则：
- 第一性原理：解决"单源模式可信度评估不科学"和"验证耗时长"的核心问题
- 极简主义：最小可行方案，聚焦核心问题
"""

import requests
import time
import asyncio
import aiohttp
from typing import Dict, Optional, Tuple, List
import logging
from datetime import datetime

# 导入健康度追踪器
from .health_tracker import get_health_tracker

logger = logging.getLogger(__name__)


# ============================================================
# 新浪财经接口
# ============================================================

def fetch_price_from_sina(code: str, timeout: int = 5) -> Optional[Dict]:
    """
    从新浪财经获取实时价格（集成健康度追踪）
    
    参数:
        code: 股票代码（如 '601939'）
        timeout: 超时时间（秒）
    
    返回:
        {
            'code': str,
            'name': str,
            'price': float,
            'open': float,
            'high': float,
            'low': float,
            'volume': int,
            'amount': float,
            'source': 'sina'
        }
    """
    health_tracker = get_health_tracker()
    start_time = time.time()
    
    try:
        # 确定市场前缀
        if code.startswith('6'):
            full_code = f"sh{code}"
        else:
            full_code = f"sz{code}"
        
        url = f"http://hq.sinajs.cn/list={full_code}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'http://finance.sina.com.cn'
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.encoding = 'gbk'
        
        # 解析数据
        text = response.text
        if '="' not in text:
            health_tracker.record_request('sina_price', False, time.time() - start_time, '数据格式错误')
            return None
        
        data_str = text.split('"')[1]
        if not data_str:
            health_tracker.record_request('sina_price', False, time.time() - start_time, '数据为空')
            return None
        
        parts = data_str.split(',')
        
        if len(parts) < 31:
            health_tracker.record_request('sina_price', False, time.time() - start_time, '数据字段不足')
            return None
        
        # 提取关键字段
        result = {
            'code': code,
            'name': parts[0],
            'price': float(parts[3]) if parts[3] else None,
            'open': float(parts[1]) if parts[1] else None,
            'high': float(parts[4]) if parts[4] else None,
            'low': float(parts[5]) if parts[5] else None,
            'volume': int(parts[8]) if parts[8] else None,
            'amount': float(parts[9]) if parts[9] else None,
            'source': 'sina'
        }
        
        # 记录成功
        health_tracker.record_request('sina_price', True, time.time() - start_time)
        
        return result
        
    except Exception as e:
        latency = time.time() - start_time
        health_tracker.record_request('sina_price', False, latency, str(e))
        logger.warning(f"新浪财经获取失败 [{code}]: {e}")
        return None


# ============================================================
# 腾讯财经接口
# ============================================================

def fetch_price_from_tencent(code: str, timeout: int = 5) -> Optional[Dict]:
    """
    从腾讯财经获取实时价格（集成健康度追踪）
    
    参数:
        code: 股票代码（如 '601939'）
        timeout: 超时时间（秒）
    
    返回:
        {
            'code': str,
            'name': str,
            'price': float,
            'open': float,
            'high': float,
            'low': float,
            'volume': int,
            'amount': float,
            'source': 'tencent'
        }
    """
    health_tracker = get_health_tracker()
    start_time = time.time()
    
    try:
        # 确定市场前缀
        if code.startswith('6'):
            full_code = f"sh{code}"
        else:
            full_code = f"sz{code}"
        
        url = f"http://qt.gtimg.cn/q={full_code}"
        response = requests.get(url, timeout=timeout)
        response.encoding = 'gbk'
        
        # 解析数据
        text = response.text
        if '~' not in text:
            health_tracker.record_request('tencent_price', False, time.time() - start_time, '数据格式错误')
            return None
        
        parts = text.split('~')
        
        if len(parts) < 40:
            health_tracker.record_request('tencent_price', False, time.time() - start_time, '数据字段不足')
            return None
        
        # 提取关键字段
        result = {
            'code': code,
            'name': parts[1],
            'price': float(parts[3]) if parts[3] else None,
            'open': float(parts[5]) if parts[5] else None,
            'high': float(parts[33]) if len(parts) > 33 and parts[33] else None,
            'low': float(parts[34]) if len(parts) > 34 and parts[34] else None,
            'volume': int(parts[6]) if parts[6] else None,
            'amount': float(parts[37]) if len(parts) > 37 and parts[37] else None,
            'source': 'tencent'
        }
        
        # 记录成功
        health_tracker.record_request('tencent_price', True, time.time() - start_time)
        
        return result
        
    except Exception as e:
        latency = time.time() - start_time
        health_tracker.record_request('tencent_price', False, latency, str(e))
        logger.warning(f"腾讯财经获取失败 [{code}]: {e}")
        return None


# ============================================================
# 双重验证函数
# ============================================================

def validate_price_dual(code: str, 
                       tolerance: float = 0.01,
                       timeout: int = 5) -> Dict:
    """
    价格双重验证（集成健康度调整）
    
    流程:
    1. 从新浪获取价格
    2. 从腾讯获取价格
    3. 比对一致性
    4. 根据数据源可靠性调整可信度
    5. 返回结果和可信度
    
    参数:
        code: 股票代码
        tolerance: 允许的差异比例（默认1%）
        timeout: 超时时间
    
    返回:
        {
            'code': str,
            'price': float,
            'name': str,
            'confidence': 'high'|'medium'|'low'|'none',
            'sources': {
                'sina': {...},
                'tencent': {...}
            },
            'validation': {
                'is_consistent': bool,
                'difference': float,
                'difference_pct': float,
                'message': str
            },
            'health': {
                'sina_reliability': float,
                'tencent_reliability': float,
            }
        }
    """
    health_tracker = get_health_tracker()
    
    result = {
        'code': code,
        'price': None,
        'name': None,
        'confidence': 'none',
        'sources': {},
        'validation': {},
        'health': {}
    }
    
    # 1. 从两个数据源获取
    sina_data = fetch_price_from_sina(code, timeout)
    tencent_data = fetch_price_from_tencent(code, timeout)
    
    result['sources'] = {
        'sina': sina_data,
        'tencent': tencent_data
    }
    
    # 获取数据源可靠性
    sina_reliability = health_tracker.get_reliability('sina_price')
    tencent_reliability = health_tracker.get_reliability('tencent_price')
    
    result['health'] = {
        'sina_reliability': round(sina_reliability, 3),
        'tencent_reliability': round(tencent_reliability, 3),
    }
    
    # 2. 判断数据可用性
    if sina_data is None and tencent_data is None:
        result['validation'] = {
            'is_consistent': False,
            'difference': None,
            'difference_pct': None,
            'message': '两个数据源都失败'
        }
        result['confidence'] = 'none'
        return result
    
    # 3. 只有一个数据源 - 根据可靠性调整可信度
    if sina_data is None or tencent_data is None:
        available_data = sina_data if sina_data else tencent_data
        source_name = 'sina' if sina_data else 'tencent'
        source_reliability = sina_reliability if sina_data else tencent_reliability
        
        result['price'] = available_data['price']
        result['name'] = available_data['name']
        result['validation'] = {
            'is_consistent': None,
            'difference': None,
            'difference_pct': None,
            'message': f'仅{source_name}数据源可用'
        }
        
        # 根据可靠性调整可信度
        if source_reliability >= 0.9:
            result['confidence'] = 'medium'  # 高可靠性 → 中可信度
        elif source_reliability >= 0.7:
            result['confidence'] = 'low'     # 中等可靠性 → 低可信度
        else:
            result['confidence'] = 'low'     # 低可靠性 → 低可信度
        
        return result
    
    # 4. 两个数据源都有数据
    price_sina = sina_data['price']
    price_tencent = tencent_data['price']
    
    # 检查价格是否有效
    if price_sina is None or price_tencent is None:
        available = price_sina if price_sina else price_tencent
        result['price'] = available
        result['name'] = sina_data['name'] if sina_data['name'] else tencent_data['name']
        result['validation'] = {
            'is_consistent': None,
            'difference': None,
            'difference_pct': None,
            'message': '部分价格数据缺失'
        }
        result['confidence'] = 'low'
        return result
    
    # 5. 计算差异
    difference = abs(price_sina - price_tencent)
    difference_pct = difference / price_sina if price_sina > 0 else 0
    
    # 6. 判断一致性
    is_consistent = difference_pct <= tolerance
    
    # 7. 选择推荐值
    if is_consistent:
        # 一致，取平均值
        recommended_price = round((price_sina + price_tencent) / 2, 2)
        base_confidence = 'high'
        message = f'数据一致（差异{difference_pct*100:.2f}%）'
    else:
        # 不一致，使用高可靠性数据源
        if sina_reliability > tencent_reliability:
            recommended_price = price_sina
            message = f'数据不一致（差异{difference_pct*100:.2f}%），使用新浪数据（可靠性{sina_reliability:.2f}）'
        else:
            recommended_price = price_tencent
            message = f'数据不一致（差异{difference_pct*100:.2f}%），使用腾讯数据（可靠性{tencent_reliability:.2f}）'
        base_confidence = 'medium'
    
    # 8. 根据健康度调整可信度
    confidence = health_tracker.get_confidence_adjustment(
        'sina_price' if recommended_price == price_sina else 'tencent_price',
        base_confidence
    )
    
    result['price'] = recommended_price
    result['name'] = sina_data['name']
    result['validation'] = {
        'is_consistent': is_consistent,
        'difference': round(difference, 2),
        'difference_pct': round(difference_pct * 100, 2),
        'message': message
    }
    result['confidence'] = confidence
    
    return result


# ============================================================
# 批量验证函数
# ============================================================

def validate_prices_batch(codes: list, 
                         tolerance: float = 0.01,
                         timeout: int = 5,
                         delay: float = 0.1) -> Dict[str, Dict]:
    """
    批量价格验证（串行版本，保持兼容）
    
    参数:
        codes: 股票代码列表
        tolerance: 允许差异
        timeout: 超时
        delay: 请求间隔（避免频率限制）
    
    返回:
        {code: validation_result}
    """
    results = {}
    
    for code in codes:
        result = validate_price_dual(code, tolerance, timeout)
        results[code] = result
        
        # 延迟，避免频率限制
        if delay > 0:
            time.sleep(delay)
    
    return results


# ============================================================
# 异步并发验证函数（v6.18新增）
# ============================================================

async def fetch_price_from_sina_async(code: str, session: aiohttp.ClientSession, 
                                      timeout: int = 5) -> Optional[Dict]:
    """从新浪财经异步获取实时价格"""
    health_tracker = get_health_tracker()
    start_time = time.time()
    
    try:
        # 确定市场前缀
        if code.startswith('6'):
            full_code = f"sh{code}"
        else:
            full_code = f"sz{code}"
        
        url = f"http://hq.sinajs.cn/list={full_code}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'http://finance.sina.com.cn'
        }
        
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
            text = await response.text()
            
            # 解析数据
            if '="' not in text:
                health_tracker.record_request('sina_price', False, time.time() - start_time, '数据格式错误')
                return None
            
            data_str = text.split('"')[1]
            if not data_str:
                health_tracker.record_request('sina_price', False, time.time() - start_time, '数据为空')
                return None
            
            parts = data_str.split(',')
            
            if len(parts) < 31:
                health_tracker.record_request('sina_price', False, time.time() - start_time, '数据字段不足')
                return None
            
            result = {
                'code': code,
                'name': parts[0],
                'price': float(parts[3]) if parts[3] else None,
                'source': 'sina'
            }
            
            health_tracker.record_request('sina_price', True, time.time() - start_time)
            return result
            
    except Exception as e:
        latency = time.time() - start_time
        health_tracker.record_request('sina_price', False, latency, str(e))
        logger.warning(f"新浪财经异步获取失败 [{code}]: {e}")
        return None


async def fetch_price_from_tencent_async(code: str, session: aiohttp.ClientSession,
                                         timeout: int = 5) -> Optional[Dict]:
    """从腾讯财经异步获取实时价格"""
    health_tracker = get_health_tracker()
    start_time = time.time()
    
    try:
        # 确定市场前缀
        if code.startswith('6'):
            full_code = f"sh{code}"
        else:
            full_code = f"sz{code}"
        
        url = f"http://qt.gtimg.cn/q={full_code}"
        
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
            text = await response.text()
            
            if '~' not in text:
                health_tracker.record_request('tencent_price', False, time.time() - start_time, '数据格式错误')
                return None
            
            parts = text.split('~')
            
            if len(parts) < 40:
                health_tracker.record_request('tencent_price', False, time.time() - start_time, '数据字段不足')
                return None
            
            result = {
                'code': code,
                'name': parts[1],
                'price': float(parts[3]) if parts[3] else None,
                'source': 'tencent'
            }
            
            health_tracker.record_request('tencent_price', True, time.time() - start_time)
            return result
            
    except Exception as e:
        latency = time.time() - start_time
        health_tracker.record_request('tencent_price', False, latency, str(e))
        logger.warning(f"腾讯财经异步获取失败 [{code}]: {e}")
        return None


async def validate_price_dual_async(code: str, session: aiohttp.ClientSession,
                                   tolerance: float = 0.01, timeout: int = 5) -> Dict:
    """异步双重验证"""
    health_tracker = get_health_tracker()
    
    result = {
        'code': code,
        'price': None,
        'name': None,
        'confidence': 'none',
        'sources': {},
        'validation': {},
        'health': {}
    }
    
    # 并发请求两个数据源
    tasks = [
        fetch_price_from_sina_async(code, session, timeout),
        fetch_price_from_tencent_async(code, session, timeout),
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    sina_data = results[0] if not isinstance(results[0], Exception) else None
    tencent_data = results[1] if not isinstance(results[1], Exception) else None
    
    result['sources'] = {
        'sina': sina_data,
        'tencent': tencent_data
    }
    
    # 获取可靠性
    sina_reliability = health_tracker.get_reliability('sina_price')
    tencent_reliability = health_tracker.get_reliability('tencent_price')
    
    result['health'] = {
        'sina_reliability': round(sina_reliability, 3),
        'tencent_reliability': round(tencent_reliability, 3),
    }
    
    # 验证逻辑（与同步版本相同）
    if sina_data is None and tencent_data is None:
        result['validation'] = {'message': '两个数据源都失败'}
        result['confidence'] = 'none'
        return result
    
    if sina_data is None or tencent_data is None:
        available_data = sina_data if sina_data else tencent_data
        source_reliability = sina_reliability if sina_data else tencent_reliability
        
        result['price'] = available_data['price']
        result['name'] = available_data['name']
        
        if source_reliability >= 0.9:
            result['confidence'] = 'medium'
        else:
            result['confidence'] = 'low'
        
        return result
    
    # 两个数据源都有数据
    price_sina = sina_data['price']
    price_tencent = tencent_data['price']
    
    if price_sina is None or price_tencent is None:
        result['price'] = price_sina if price_sina else price_tencent
        result['name'] = sina_data['name'] if sina_data else tencent_data['name']
        result['confidence'] = 'low'
        return result
    
    # 计算差异
    difference = abs(price_sina - price_tencent)
    difference_pct = difference / price_sina if price_sina > 0 else 0
    
    is_consistent = difference_pct <= tolerance
    
    if is_consistent:
        recommended_price = round((price_sina + price_tencent) / 2, 2)
        base_confidence = 'high'
    else:
        recommended_price = price_sina if sina_reliability > tencent_reliability else price_tencent
        base_confidence = 'medium'
    
    # 调整可信度
    confidence = health_tracker.get_confidence_adjustment(
        'sina_price' if recommended_price == price_sina else 'tencent_price',
        base_confidence
    )
    
    result['price'] = recommended_price
    result['name'] = sina_data['name']
    result['confidence'] = confidence
    result['validation'] = {
        'is_consistent': is_consistent,
        'difference_pct': round(difference_pct * 100, 2),
    }
    
    return result


async def validate_prices_batch_async(codes: list, 
                                     tolerance: float = 0.01,
                                     timeout: int = 5,
                                     max_concurrent: int = 20) -> Dict[str, Dict]:
    """
    批量异步价格验证（并发优化）
    
    参数:
        codes: 股票代码列表
        tolerance: 允许差异
        timeout: 超时
        max_concurrent: 最大并发数（默认20）
    
    返回:
        {code: validation_result}
    
    性能提升:
        - 串行: 5000只 × 0.3s = 25分钟
        - 并发: 5000只 / 20并发 × 0.2s ≈ 50秒（提速30倍）
    """
    # 控制并发数
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def validate_with_limit(code, session):
        async with semaphore:
            # 短暂延迟避免频率限制
            await asyncio.sleep(0.01)
            result = await validate_price_dual_async(code, session, tolerance, timeout)
            return code, result
    
    async with aiohttp.ClientSession() as session:
        tasks = [validate_with_limit(code, session) for code in codes]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 组装结果
    results = {}
    for item in results_list:
        if isinstance(item, Exception):
            logger.error(f"并发验证异常: {item}")
            continue
        
        code, result = item
        results[code] = result
    
    return results


# ============================================================
# 统计函数
# ============================================================

def get_validation_stats(results: Dict[str, Dict]) -> Dict:
    """
    统计验证结果
    
    返回:
        {
            'total': int,
            'success': int,
            'high_confidence': int,
            'medium_confidence': int,
            'low_confidence': int,
            'none_confidence': int,
            'success_rate': float,
            'high_confidence_rate': float,
            'avg_difference': float
        }
    """
    total = len(results)
    success = sum(1 for r in results.values() if r['price'] is not None)
    high = sum(1 for r in results.values() if r['confidence'] == 'high')
    medium = sum(1 for r in results.values() if r['confidence'] == 'medium')
    low = sum(1 for r in results.values() if r['confidence'] == 'low')
    none = sum(1 for r in results.values() if r['confidence'] == 'none')
    
    # 计算平均差异
    differences = [
        r['validation']['difference_pct'] 
        for r in results.values() 
        if r['validation'].get('difference_pct') is not None
    ]
    avg_diff = sum(differences) / len(differences) if differences else 0
    
    return {
        'total': total,
        'success': success,
        'high_confidence': high,
        'medium_confidence': medium,
        'low_confidence': low,
        'none_confidence': none,
        'success_rate': round(success / total * 100, 2) if total > 0 else 0,
        'high_confidence_rate': round(high / total * 100, 2) if total > 0 else 0,
        'avg_difference': round(avg_diff, 2)
    }
