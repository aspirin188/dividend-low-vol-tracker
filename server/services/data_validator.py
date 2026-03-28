"""
数据双重验证框架
v6.15: 实现数据交叉验证机制

核心原则：
- 至少两个数据源
- 交叉验证数据一致性
- 标记数据可信度
- 透明化数据质量
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable


# ============================================================
# 验证规则
# ============================================================

VALIDATION_RULES = {
    'roe': {
        'type': 'percentage',
        'range': [-50, 100],
        'tolerance': 0.05,  # 5%相对差异
        'absolute_tolerance': 0.5,  # 0.5个百分点绝对差异
        'description': '净资产收益率',
    },
    'payout_ratio': {
        'type': 'percentage',
        'range': [0, 200],
        'tolerance': 0.10,
        'absolute_tolerance': 5.0,
        'description': '股利支付率',
    },
    'debt_ratio': {
        'type': 'percentage',
        'range': [0, 100],
        'tolerance': 0.05,
        'absolute_tolerance': 3.0,
        'description': '资产负债率',
    },
    'eps': {
        'type': 'currency',
        'range': [-10, 100],
        'tolerance': 0.10,
        'absolute_tolerance': 0.5,
        'description': '每股收益',
    },
    'dividend_yield': {
        'type': 'percentage',
        'range': [0, 20],
        'tolerance': 0.10,
        'absolute_tolerance': 0.5,
        'description': '股息率',
    },
    'dividend_per_share': {
        'type': 'currency',
        'range': [0, 20],
        'tolerance': 0.10,
        'absolute_tolerance': 0.1,
        'description': '每股股利',
    },
}


# ============================================================
# 一致性检查函数
# ============================================================

def check_consistency(value_a: Optional[float], 
                      value_b: Optional[float], 
                      field_name: str) -> Dict[str, Any]:
    """
    检查两个数据源的一致性
    
    参数:
        value_a: 数据源A的值
        value_b: 数据源B的值
        field_name: 字段名
    
    返回:
        {
            'is_consistent': bool or None,  # True=一致, False=不一致, None=无法验证
            'confidence': 'high'|'medium'|'low'|'none',  # 可信度
            'difference': float or None,  # 绝对差异
            'difference_pct': float or None,  # 相对差异
            'recommended_value': float or None,  # 推荐使用值
            'message': str,  # 描述信息
        }
    """
    rule = VALIDATION_RULES.get(field_name, {})
    
    # 情况1: 两个数据源都有值
    if value_a is not None and value_b is not None:
        # 转换为float
        try:
            value_a = float(value_a)
            value_b = float(value_b)
        except (ValueError, TypeError):
            return {
                'is_consistent': None,
                'confidence': 'none',
                'difference': None,
                'difference_pct': None,
                'recommended_value': None,
                'message': '数据格式错误',
            }
        
        # 检查范围
        if 'range' in rule:
            min_val, max_val = rule['range']
            if not (min_val <= value_a <= max_val and min_val <= value_b <= max_val):
                return {
                    'is_consistent': False,
                    'confidence': 'low',
                    'difference': abs(value_a - value_b),
                    'difference_pct': None,
                    'recommended_value': None,
                    'message': '数据超出合理范围',
                }
        
        # 计算差异
        difference = abs(value_a - value_b)
        avg_value = (value_a + value_b) / 2
        difference_pct = difference / abs(avg_value) if avg_value != 0 else 0
        
        # 获取容忍度
        tolerance = rule.get('tolerance', 0.05)
        abs_tolerance = rule.get('absolute_tolerance', 0.5)
        
        # 判断一致性级别
        if difference_pct <= tolerance and difference <= abs_tolerance:
            # 完全一致 - 高可信度
            return {
                'is_consistent': True,
                'confidence': 'high',
                'difference': round(difference, 4),
                'difference_pct': round(difference_pct, 4),
                'recommended_value': round(avg_value, 2),
                'message': f"数据一致（差异{difference_pct:.2%}）",
            }
        elif difference_pct <= tolerance * 2:
            # 轻微差异 - 中可信度
            return {
                'is_consistent': True,
                'confidence': 'medium',
                'difference': round(difference, 4),
                'difference_pct': round(difference_pct, 4),
                'recommended_value': round(avg_value, 2),
                'message': f"数据轻微差异（差异{difference_pct:.2%}）",
            }
        else:
            # 明显差异 - 低可信度
            return {
                'is_consistent': False,
                'confidence': 'low',
                'difference': round(difference, 4),
                'difference_pct': round(difference_pct, 4),
                'recommended_value': None,  # 需要进一步验证
                'message': f"数据明显差异（差异{difference_pct:.2%}）",
            }
    
    # 情况2: 只有一个数据源有值
    elif value_a is not None:
        try:
            value_a = float(value_a)
        except (ValueError, TypeError):
            value_a = None
        
        return {
            'is_consistent': None,
            'confidence': 'low',
            'difference': None,
            'difference_pct': None,
            'recommended_value': value_a,
            'message': '只有一个数据源（未验证）',
        }
    
    elif value_b is not None:
        try:
            value_b = float(value_b)
        except (ValueError, TypeError):
            value_b = None
        
        return {
            'is_consistent': None,
            'confidence': 'low',
            'difference': None,
            'difference_pct': None,
            'recommended_value': value_b,
            'message': '只有一个数据源（未验证）',
        }
    
    # 情况3: 两个数据源都没有值
    else:
        return {
            'is_consistent': None,
            'confidence': 'none',
            'difference': None,
            'difference_pct': None,
            'recommended_value': None,
            'message': '两个数据源都无数据',
        }


# ============================================================
# 数据源注册表
# ============================================================

class DataSourceRegistry:
    """数据源注册表"""
    
    def __init__(self):
        self.sources: Dict[str, List[Dict]] = {}
        
    def register(self, field_name: str, source_name: str, 
                fetch_func: Callable, priority: int = 1, 
                metadata: Optional[Dict] = None):
        """
        注册数据源
        
        参数:
            field_name: 字段名（如'roe', 'eps'）
            source_name: 数据源名称（如'akshare_yjbb'）
            fetch_func: 获取数据的函数
            priority: 优先级（数字越大优先级越高）
            metadata: 元数据
        """
        if field_name not in self.sources:
            self.sources[field_name] = []
        
        self.sources[field_name].append({
            'name': source_name,
            'fetch': fetch_func,
            'priority': priority,
            'metadata': metadata or {},
            'stats': {
                'success_count': 0,
                'fail_count': 0,
                'last_success': None,
                'last_fail': None,
            }
        })
        
        # 按优先级排序（降序）
        self.sources[field_name].sort(
            key=lambda x: x['priority'], 
            reverse=True
        )
        
        print(f"✓ 注册数据源: {field_name} <- {source_name} (优先级: {priority})")
    
    def get_sources(self, field_name: str) -> List[Dict]:
        """获取字段的所有数据源"""
        return self.sources.get(field_name, [])


# ============================================================
# 双重验证器
# ============================================================

class DualDataValidator:
    """双重数据验证器"""
    
    def __init__(self, registry: DataSourceRegistry):
        self.registry = registry
        self.validation_log: List[Dict] = []
        self.alerts: List[Dict] = []
        
    def validate_field(self, field_name: str, code: str, 
                      context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        验证单个字段的数据
        
        参数:
            field_name: 字段名
            code: 股票代码
            context: 上下文数据（如已获取的DataFrame）
        
        返回:
            {
                'field': str,
                'value': float or None,  # 推荐值
                'confidence': str,  # 可信度
                'message': str,
                'sources': List[str],
                'raw_values': Dict[str, float],  # 各数据源的原始值
                'consistency': Dict,  # 一致性检查结果
                'timestamp': str,
            }
        """
        print(f"  验证 {code} - {field_name}...", end=' ', flush=True)
        
        # 获取该字段的所有数据源
        sources = self.registry.get_sources(field_name)
        
        # 情况1: 没有数据源
        if len(sources) == 0:
            print("无数据源")
            return self._create_result(
                field_name=field_name,
                value=None,
                confidence='none',
                message='无可用数据源',
                sources=[],
                raw_values={},
                consistency=None,
            )
        
        # 情况2: 只有一个数据源
        if len(sources) == 1:
            source = sources[0]
            value = self._fetch_from_source(source, code, context)
            
            print(f"单一数据源: {value}")
            
            return self._create_result(
                field_name=field_name,
                value=value,
                confidence='low',
                message=f'单一数据源: {source["name"]}（未验证）',
                sources=[source['name']],
                raw_values={source['name']: value},
                consistency=None,
            )
        
        # 情况3: 有多个数据源，进行双重验证
        source_a = sources[0]  # 主数据源（优先级最高）
        source_b = sources[1]  # 副数据源（优先级次高）
        
        value_a = self._fetch_from_source(source_a, code, context)
        value_b = self._fetch_from_source(source_b, code, context)
        
        # 一致性检查
        consistency = check_consistency(value_a, value_b, field_name)
        
        # 记录验证日志
        log_entry = {
            'timestamp': datetime.now(),
            'field': field_name,
            'code': code,
            'source_a': source_a['name'],
            'value_a': value_a,
            'source_b': source_b['name'],
            'value_b': value_b,
            'consistency': consistency,
        }
        self.validation_log.append(log_entry)
        
        # 创建告警（如果需要）
        if consistency['confidence'] in ['low', 'none']:
            self._create_alert(field_name, code, consistency, 
                             source_a['name'], value_a, 
                             source_b['name'], value_b)
        
        # 打印结果
        confidence_emoji = {
            'high': '✓',
            'medium': '⚠️',
            'low': '✗',
            'none': '✗'
        }
        emoji = confidence_emoji.get(consistency['confidence'], '?')
        print(f"{emoji} {consistency['message']}")
        
        # 返回结果
        return self._create_result(
            field_name=field_name,
            value=consistency['recommended_value'],
            confidence=consistency['confidence'],
            message=consistency['message'],
            sources=[source_a['name'], source_b['name']],
            raw_values={
                source_a['name']: value_a,
                source_b['name']: value_b,
            },
            consistency=consistency,
        )
    
    def _fetch_from_source(self, source: Dict, code: str, 
                           context: Optional[Dict]) -> Optional[float]:
        """从数据源获取数据"""
        try:
            value = source['fetch'](code, context)
            
            # 更新统计
            source['stats']['success_count'] += 1
            source['stats']['last_success'] = datetime.now()
            
            return value
            
        except Exception as e:
            source['stats']['fail_count'] += 1
            source['stats']['last_fail'] = datetime.now()
            
            return None
    
    def _create_result(self, field_name: str, value: Optional[float],
                      confidence: str, message: str, sources: List[str],
                      raw_values: Dict, consistency: Optional[Dict]) -> Dict[str, Any]:
        """创建验证结果"""
        return {
            'field': field_name,
            'value': value,
            'confidence': confidence,
            'message': message,
            'sources': sources,
            'raw_values': raw_values,
            'consistency': consistency,
            'timestamp': datetime.now().isoformat(),
        }
    
    def _create_alert(self, field_name: str, code: str, 
                     consistency: Dict, source_a: str, value_a: Optional[float],
                     source_b: str, value_b: Optional[float]):
        """创建告警"""
        alert = {
            'level': 'warning' if consistency['confidence'] == 'low' else 'error',
            'field': field_name,
            'code': code,
            'message': consistency['message'],
            'source_a': source_a,
            'value_a': value_a,
            'source_b': source_b,
            'value_b': value_b,
            'difference': consistency.get('difference'),
            'difference_pct': consistency.get('difference_pct'),
            'timestamp': datetime.now(),
        }
        self.alerts.append(alert)
    
    def validate_batch(self, codes: List[str], fields: List[str],
                      context: Optional[Dict] = None) -> Dict[str, Dict[str, Dict]]:
        """
        批量验证多只股票的多个字段
        
        返回:
            {
                'code1': {
                    'field1': {...},
                    'field2': {...},
                },
                'code2': {...},
            }
        """
        results = {}
        total = len(codes) * len(fields)
        current = 0
        
        print(f"\n开始批量验证 {len(codes)} 只股票 × {len(fields)} 个字段 = {total} 次")
        print("=" * 60)
        
        for code in codes:
            results[code] = {}
            
            for field in fields:
                current += 1
                print(f"[{current}/{total}] ", end='')
                
                result = self.validate_field(field, code, context)
                results[code][field] = result
        
        return results
    
    def get_validation_report(self) -> Dict[str, Any]:
        """获取验证报告"""
        # 按可信度分组
        by_confidence = {'high': 0, 'medium': 0, 'low': 0, 'none': 0}
        for log in self.validation_log:
            confidence = log['consistency']['confidence']
            by_confidence[confidence] = by_confidence.get(confidence, 0) + 1
        
        total = sum(by_confidence.values())
        
        return {
            'total_validations': total,
            'by_confidence': by_confidence,
            'quality_score': self._calculate_quality_score(by_confidence, total),
            'alerts_count': len(self.alerts),
            'recent_alerts': self.alerts[-10:],
            'validation_log': self.validation_log[-20:],
        }
    
    def _calculate_quality_score(self, by_confidence: Dict[str, int], 
                                 total: int) -> float:
        """计算数据质量评分（0-100）"""
        if total == 0:
            return 0.0
        
        weights = {'high': 1.0, 'medium': 0.7, 'low': 0.3, 'none': 0.0}
        
        score = sum(
            by_confidence[conf] * weights[conf] 
            for conf in ['high', 'medium', 'low', 'none']
        )
        
        return round((score / total) * 100, 1)
    
    def get_field_quality_summary(self, field_name: str) -> Dict[str, Any]:
        """获取特定字段的质量摘要"""
        field_logs = [log for log in self.validation_log if log['field'] == field_name]
        
        by_confidence = {'high': 0, 'medium': 0, 'low': 0, 'none': 0}
        for log in field_logs:
            confidence = log['consistency']['confidence']
            by_confidence[confidence] += 1
        
        total = len(field_logs)
        
        return {
            'field': field_name,
            'total': total,
            'by_confidence': by_confidence,
            'quality_score': self._calculate_quality_score(by_confidence, total),
        }
