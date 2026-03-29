"""
数据源健康度追踪器
v6.18: 根据接口历史表现动态调整可信度

核心功能：
1. 追踪每个数据源的成功率、延迟、稳定性
2. 计算可靠性评分（0-1）
3. 提供降级策略建议

设计原则：
- 第一性原理：解决"单源模式可信度评估不科学"的核心问题
- 极简主义：最小可行方案，不过度设计
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class DataSourceHealthTracker:
    """数据源健康度追踪器"""
    
    def __init__(self):
        # 健康度统计（持久化存储）
        self.health_stats = {}
        
        # 运行时统计（内存）
        self.runtime_stats = defaultdict(lambda: {
            'success_count': 0,
            'fail_count': 0,
            'total_latency': 0.0,
            'latency_count': 0,
            'consecutive_failures': 0,
            'last_success': None,
            'last_fail': None,
        })
        
        # 可靠性缓存
        self.reliability_cache = {}
        
        # 滑动窗口大小
        self.window_size = 100
        
    def record_request(self, source_name: str, success: bool, 
                       latency: float, error: Optional[str] = None):
        """
        记录一次请求结果
        
        参数:
            source_name: 数据源名称（如 'sina_price', 'akshare_yjbb'）
            success: 是否成功
            latency: 响应时间（秒）
            error: 错误信息（可选）
        """
        stats = self.runtime_stats[source_name]
        
        # 更新计数
        if success:
            stats['success_count'] += 1
            stats['consecutive_failures'] = 0
            stats['last_success'] = datetime.now()
        else:
            stats['fail_count'] += 1
            stats['consecutive_failures'] += 1
            stats['last_fail'] = datetime.now()
            
            if error:
                logger.warning(f"数据源 {source_name} 请求失败: {error}")
        
        # 更新延迟
        if latency > 0:
            stats['total_latency'] += latency
            stats['latency_count'] += 1
        
        # 清除可靠性缓存（下次重新计算）
        if source_name in self.reliability_cache:
            del self.reliability_cache[source_name]
    
    def get_success_rate(self, source_name: str) -> float:
        """获取成功率（滑动窗口）"""
        stats = self.runtime_stats[source_name]
        total = stats['success_count'] + stats['fail_count']
        
        if total == 0:
            return 0.5  # 无数据时返回中等值
        
        return stats['success_count'] / total
    
    def get_avg_latency(self, source_name: str) -> float:
        """获取平均延迟"""
        stats = self.runtime_stats[source_name]
        
        if stats['latency_count'] == 0:
            return 1.0  # 无数据时返回1秒
        
        return stats['total_latency'] / stats['latency_count']
    
    def get_reliability(self, source_name: str) -> float:
        """
        获取可靠性评分（0-1）
        
        计算公式:
        reliability = success_rate * 0.5 + latency_score * 0.3 + stability_score * 0.2
        
        其中:
        - success_rate: 成功率
        - latency_score: 响应速度得分（越快越好）
        - stability_score: 稳定性得分（连续失败越少越好）
        """
        # 检查缓存
        if source_name in self.reliability_cache:
            return self.reliability_cache[source_name]
        
        stats = self.runtime_stats[source_name]
        
        # 成功率得分（权重50%）
        success_rate = self.get_success_rate(source_name)
        success_score = success_rate
        
        # 延迟得分（权重30%）
        avg_latency = self.get_avg_latency(source_name)
        # 假设2秒以上为慢，得分接近0
        latency_score = max(0, 1 - avg_latency / 2.0)
        
        # 稳定性得分（权重20%）
        consecutive_fails = stats['consecutive_failures']
        # 连续失败5次以上，稳定性得分接近0
        stability_score = max(0, 1 - consecutive_fails * 0.2)
        
        # 综合评分
        reliability = (
            success_score * 0.5 + 
            latency_score * 0.3 + 
            stability_score * 0.2
        )
        
        # 缓存结果
        self.reliability_cache[source_name] = reliability
        
        return reliability
    
    def get_confidence_adjustment(self, source_name: str, 
                                  base_confidence: str) -> str:
        """
        根据可靠性调整可信度
        
        参数:
            source_name: 数据源名称
            base_confidence: 基础可信度（'high', 'medium', 'low', 'none'）
        
        返回:
            调整后的可信度
        """
        reliability = self.get_reliability(source_name)
        
        # 可靠性分级
        # 0.9-1.0: 优秀
        # 0.7-0.9: 良好
        # 0.5-0.7: 一般
        # 0.0-0.5: 较差
        
        if base_confidence == 'high':
            # 高可信度：如果可靠性<0.9，降级为medium
            if reliability < 0.9:
                return 'medium'
            return 'high'
        
        elif base_confidence == 'medium':
            # 中可信度：如果可靠性<0.7，降级为low
            if reliability < 0.7:
                return 'low'
            return 'medium'
        
        elif base_confidence == 'low':
            # 低可信度：如果可靠性>0.7，升级为medium
            if reliability > 0.7:
                return 'medium'
            return 'low'
        
        return base_confidence
    
    def get_stats_report(self, source_name: str) -> Dict:
        """获取数据源统计报告"""
        stats = self.runtime_stats[source_name]
        
        total = stats['success_count'] + stats['fail_count']
        
        return {
            'source': source_name,
            'total_requests': total,
            'success_count': stats['success_count'],
            'fail_count': stats['fail_count'],
            'success_rate': round(self.get_success_rate(source_name) * 100, 2),
            'avg_latency': round(self.get_avg_latency(source_name), 3),
            'consecutive_failures': stats['consecutive_failures'],
            'reliability': round(self.get_reliability(source_name), 3),
            'last_success': stats['last_success'].isoformat() if stats['last_success'] else None,
            'last_fail': stats['last_fail'].isoformat() if stats['last_fail'] else None,
        }
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """获取所有数据源的统计报告"""
        return {
            name: self.get_stats_report(name)
            for name in self.runtime_stats.keys()
        }
    
    def save_to_file(self, filepath: str):
        """保存统计信息到文件"""
        data = {
            'runtime_stats': {
                name: {
                    **stats,
                    'last_success': stats['last_success'].isoformat() if stats['last_success'] else None,
                    'last_fail': stats['last_fail'].isoformat() if stats['last_fail'] else None,
                }
                for name, stats in self.runtime_stats.items()
            },
            'timestamp': datetime.now().isoformat(),
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"健康度统计已保存到 {filepath}")
    
    def load_from_file(self, filepath: str):
        """从文件加载统计信息"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            for name, stats in data.get('runtime_stats', {}).items():
                self.runtime_stats[name] = {
                    'success_count': stats.get('success_count', 0),
                    'fail_count': stats.get('fail_count', 0),
                    'total_latency': stats.get('total_latency', 0.0),
                    'latency_count': stats.get('latency_count', 0),
                    'consecutive_failures': stats.get('consecutive_failures', 0),
                    'last_success': datetime.fromisoformat(stats['last_success']) if stats.get('last_success') else None,
                    'last_fail': datetime.fromisoformat(stats['last_fail']) if stats.get('last_fail') else None,
                }
            
            logger.info(f"健康度统计已从 {filepath} 加载")
            
        except FileNotFoundError:
            logger.info(f"健康度统计文件 {filepath} 不存在，使用默认值")
        except Exception as e:
            logger.error(f"加载健康度统计失败: {e}")


# 全局单例
_health_tracker = None

def get_health_tracker() -> DataSourceHealthTracker:
    """获取全局健康度追踪器"""
    global _health_tracker
    if _health_tracker is None:
        _health_tracker = DataSourceHealthTracker()
    return _health_tracker
