"""
验证结果缓存模块
v6.18: 智能缓存机制，避免重复验证

设计原则：
- 第一性原理：解决"重复验证浪费时间"的问题
- 极简主义：最小可行缓存，使用内存字典
- 价格实时验证，其他字段缓存1天
"""

import time
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ValidationCache:
    """验证结果缓存（内存版）"""
    
    def __init__(self):
        # 缓存存储
        self.cache: Dict[str, Dict[str, Any]] = {}
        
        # TTL配置（秒）
        self.ttl_config = {
            'price': 60,           # 价格缓存60秒
            'roe': 86400,          # ROE缓存1天
            'debt_ratio': 86400,   # 负债率缓存1天
            'payout_ratio': 86400, # 支付率缓存1天
            'eps': 86400,          # EPS缓存1天
            'dividend_yield': 86400,  # 股息率缓存1天
        }
        
        # 默认TTL
        self.default_ttl = 3600  # 1小时
        
        # 统计信息
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
        }
    
    def _make_key(self, code: str, field: str) -> str:
        """生成缓存键"""
        return f"{field}:{code}"
    
    def get(self, code: str, field: str) -> Optional[Dict]:
        """
        获取缓存
        
        返回:
            None: 缓存未命中或已过期
            Dict: 缓存数据
        """
        key = self._make_key(code, field)
        
        if key not in self.cache:
            self.stats['misses'] += 1
            return None
        
        cached = self.cache[key]
        
        # 检查是否过期
        age = time.time() - cached['timestamp']
        ttl = self.ttl_config.get(field, self.default_ttl)
        
        if age > ttl:
            # 已过期，删除
            del self.cache[key]
            self.stats['evictions'] += 1
            self.stats['misses'] += 1
            return None
        
        # 缓存命中
        self.stats['hits'] += 1
        cached['from_cache'] = True
        cached['cache_age'] = int(age)
        
        return cached
    
    def set(self, code: str, field: str, value: Any, 
           confidence: str = 'unknown', metadata: Optional[Dict] = None):
        """
        设置缓存
        
        参数:
            code: 股票代码
            field: 字段名
            value: 验证结果值
            confidence: 可信度
            metadata: 其他元数据
        """
        key = self._make_key(code, field)
        
        self.cache[key] = {
            'value': value,
            'confidence': confidence,
            'metadata': metadata or {},
            'timestamp': time.time(),
            'datetime': datetime.now().isoformat(),
        }
    
    def should_validate(self, code: str, field: str, force: bool = False) -> bool:
        """
        判断是否需要重新验证
        
        参数:
            code: 股票代码
            field: 字段名
            force: 是否强制重新验证
        
        返回:
            True: 需要验证
            False: 可以使用缓存
        """
        if force:
            return True
        
        cached = self.get(code, field)
        return cached is None
    
    def invalidate(self, code: str, field: Optional[str] = None):
        """
        使缓存失效
        
        参数:
            code: 股票代码
            field: 字段名（None表示删除该股票所有缓存）
        """
        if field:
            key = self._make_key(code, field)
            if key in self.cache:
                del self.cache[key]
        else:
            # 删除该股票的所有缓存
            keys_to_delete = [k for k in self.cache.keys() if k.endswith(f":{code}")]
            for key in keys_to_delete:
                del self.cache[key]
    
    def clear(self):
        """清空所有缓存"""
        self.cache.clear()
        logger.info("缓存已清空")
    
    def get_stats(self) -> Dict:
        """获取缓存统计信息"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'total_entries': len(self.cache),
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'evictions': self.stats['evictions'],
            'hit_rate': round(hit_rate, 2),
        }
    
    def cleanup_expired(self):
        """清理过期缓存"""
        current_time = time.time()
        keys_to_delete = []
        
        for key, cached in self.cache.items():
            # 提取字段名
            field = key.split(':')[0]
            ttl = self.ttl_config.get(field, self.default_ttl)
            
            age = current_time - cached['timestamp']
            if age > ttl:
                keys_to_delete.append(key)
        
        # 删除过期缓存
        for key in keys_to_delete:
            del self.cache[key]
            self.stats['evictions'] += 1
        
        if keys_to_delete:
            logger.info(f"清理过期缓存: {len(keys_to_delete)}个")
        
        return len(keys_to_delete)


# 全局单例
_cache = None

def get_cache() -> ValidationCache:
    """获取全局缓存实例"""
    global _cache
    if _cache is None:
        _cache = ValidationCache()
    return _cache
