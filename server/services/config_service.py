"""
配置管理服务 — 红利低波跟踪系统 (v6.20)

功能：
  - 参数化配置管理
  - 内存缓存加速
  - 参数校验
  - 默认值恢复

设计原则：
  - 单例模式，全局唯一
  - 启动时加载到内存，避免频繁查库
  - 更新时同步缓存和数据库
"""

import os
import sqlite3
from typing import Dict, Tuple, Optional, Any


class ConfigService:
    """配置管理服务"""
    
    _instance = None
    
    # 配置定义（用于初始化数据库）
    CONFIG_DEFINITIONS = [
        # A类：核心筛选参数
        {
            'config_key': 'MIN_DIVIDEND_YIELD',
            'config_value': '3.0',
            'config_type': 'float',
            'category': 'A筛选',
            'description': '筛选高股息股票的最低门槛。默认3%符合红利低波策略的基本要求。建议值：激进型2.0%，稳健型3.0%，保守型4.0%',
            'default_value': '3.0',
            'min_value': '1.0',
            'max_value': '10.0',
            'unit': '%',
        },
        {
            'config_key': 'MIN_MARKET_CAP',
            'config_value': '500',
            'config_type': 'float',
            'category': 'A筛选',
            'description': '筛选大盘股，确保流动性。默认500亿排除中小市值股票。建议值：大盘型800，均衡型500，宽泛型300',
            'default_value': '500',
            'min_value': '100',
            'max_value': '2000',
            'unit': '亿元',
        },
        {
            'config_key': 'MIN_ROE',
            'config_value': '8.0',
            'config_type': 'float',
            'category': 'A筛选',
            'description': '筛选盈利能力强的公司。默认8%过滤掉盈利能力差的公司。建议值：优选型10%，均衡型8%，宽泛型6%',
            'default_value': '8.0',
            'min_value': '0',
            'max_value': '30.0',
            'unit': '%',
        },
        {
            'config_key': 'MIN_DIVIDEND_YEARS',
            'config_value': '3',
            'config_type': 'int',
            'category': 'A筛选',
            'description': '筛选分红稳定公司。默认3年确保公司有持续分红意愿。建议值：严格型5年，均衡型3年，宽泛型2年',
            'default_value': '3',
            'min_value': '1',
            'max_value': '10',
            'unit': '年',
        },
        
        # B类：风控参数
        {
            'config_key': 'MAX_PAYOUT_RATIO',
            'config_value': '150',
            'config_type': 'float',
            'category': 'B风控',
            'description': '防止分红不可持续。默认150%过滤掉过度分红的公司。过高可能透支未来分红能力',
            'default_value': '150',
            'min_value': '50',
            'max_value': '300',
            'unit': '%',
        },
        {
            'config_key': 'MAX_DIVIDEND_YIELD',
            'config_value': '30.0',
            'config_type': 'float',
            'category': 'B风控',
            'description': '过滤异常数据。默认30%排除数据异常或即将退市的股票。超过此值通常是陷阱',
            'default_value': '30.0',
            'min_value': '10',
            'max_value': '50',
            'unit': '%',
        },
        {
            'config_key': 'MAX_DEBT_RATIO',
            'config_value': '70',
            'config_type': 'float',
            'category': 'B风控',
            'description': '控制财务风险（非金融地产）。默认70%过滤高负债公司。建议值：保守型60%，均衡型70%，宽泛型80%',
            'default_value': '70',
            'min_value': '30',
            'max_value': '100',
            'unit': '%',
        },
        {
            'config_key': 'MAX_DEBT_RATIO_FINANCE',
            'config_value': '85',
            'config_type': 'float',
            'category': 'B风控',
            'description': '金融地产行业特殊处理。默认85%适应银行业高负债特点',
            'default_value': '85',
            'min_value': '50',
            'max_value': '100',
            'unit': '%',
        },
        {
            'config_key': 'VOL_WINDOW',
            'config_value': '120',
            'config_type': 'int',
            'category': 'B风控',
            'description': '计算波动率的交易日窗口。120日≈6个月（响应快），252日≈1年（更稳定）。建议根据投资风格选择',
            'default_value': '120',
            'min_value': '120',
            'max_value': '252',
            'unit': '日',
        },
        
        # C类：评分权重参数
        {
            'config_key': 'WEIGHT_DIVIDEND',
            'config_value': '0.5',
            'config_type': 'float',
            'category': 'C权重',
            'description': '股息率因子在评分中的权重。默认0.5强调分红收益。提高权重更重视股息率',
            'default_value': '0.5',
            'min_value': '0',
            'max_value': '1.0',
            'unit': '-',
        },
        {
            'config_key': 'WEIGHT_VOL',
            'config_value': '0.3',
            'config_type': 'float',
            'category': 'C权重',
            'description': '波动率因子在评分中的权重。默认0.3强调低波动。提高权重更重视稳定性',
            'default_value': '0.3',
            'min_value': '0',
            'max_value': '1.0',
            'unit': '-',
        },
        {
            'config_key': 'WEIGHT_STABILITY',
            'config_value': '0.2',
            'config_type': 'float',
            'category': 'C权重',
            'description': '分红稳定性因子在评分中的权重。默认0.2作为辅助因子。提高权重更重视持续分红能力',
            'default_value': '0.2',
            'min_value': '0',
            'max_value': '1.0',
            'unit': '-',
        },
        
        # D类：v7.2质量因子增强参数
        {
            'config_key': 'ENABLE_PROFIT_GROWTH_FILTER',
            'config_value': 'true',
            'config_type': 'bool',
            'category': 'D质量',
            'description': '是否启用近3年净利润增速筛选。防止周期股美化报表，验证盈利能力持续性',
            'default_value': 'true',
            'min_value': None,
            'max_value': None,
            'unit': '-',
        },
        {
            'config_key': 'MIN_PROFIT_GROWTH_3Y',
            'config_value': '0',
            'config_type': 'float',
            'category': 'D质量',
            'description': '最低近3年净利润CAGR。0表示正值即可，负值表示容忍小幅下滑。建议值：严格型5%，均衡型0%，宽泛型-5%',
            'default_value': '0',
            'min_value': '-20',
            'max_value': '50',
            'unit': '%',
        },
        {
            'config_key': 'ENABLE_CASHFLOW_QUALITY_FILTER',
            'config_value': 'true',
            'config_type': 'bool',
            'category': 'D质量',
            'description': '是否启用经营现金流质量筛选。防止现金分红靠借款，验证分红可持续性',
            'default_value': 'true',
            'min_value': None,
            'max_value': None,
            'unit': '-',
        },
        {
            'config_key': 'MIN_CASHFLOW_PROFIT_RATIO',
            'config_value': '0.8',
            'config_type': 'float',
            'category': 'D质量',
            'description': '最低经营现金流/净利润比率。0.8表示盈利质量良好，1.0表示优秀。建议值：严格型1.0，均衡型0.8，宽泛型0.5',
            'default_value': '0.8',
            'min_value': '0',
            'max_value': '2.0',
            'unit': '-',
        },
        {
            'config_key': 'ENABLE_SHAREHOLDER_STABILITY_FILTER',
            'config_value': 'true',
            'config_type': 'bool',
            'category': 'D质量',
            'description': '是否启用股权结构稳定性筛选。确保大股东与中小股东利益绑定',
            'default_value': 'true',
            'min_value': None,
            'max_value': None,
            'unit': '-',
        },
        {
            'config_key': 'MIN_TOP1_SHAREHOLDER_RATIO',
            'config_value': '0.2',
            'config_type': 'float',
            'category': 'D质量',
            'description': '最低第一大股东持股比例。0.2表示至少20%。建议值：严格型0.3，均衡型0.2，宽泛型0.1',
            'default_value': '0.2',
            'min_value': '0',
            'max_value': '1.0',
            'unit': '-',
        },
    ]
    
    def __init__(self, db_path: str):
        """
        初始化配置服务
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path
        self._cache: Dict[str, Dict[str, Any]] = {}  # 内存缓存
        self._init_db()
        self._load_cache()
    
    @classmethod
    def get_instance(cls) -> 'ConfigService':
        """
        获取单例实例
        
        Returns:
            ConfigService 实例
        """
        if cls._instance is None:
            from flask import current_app
            db_path = os.path.join(current_app.instance_path, 'tracker.db')
            cls._instance = cls(db_path)
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """重置单例（用于测试）"""
        cls._instance = None
    
    def _init_db(self):
        """初始化数据库表和默认配置"""
        conn = sqlite3.connect(self.db_path)
        
        # 创建配置表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS system_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_key VARCHAR(50) UNIQUE NOT NULL,
                config_value VARCHAR(100) NOT NULL,
                config_type VARCHAR(20) NOT NULL,
                category VARCHAR(20) NOT NULL,
                description TEXT NOT NULL,
                default_value VARCHAR(100) NOT NULL,
                min_value VARCHAR(50),
                max_value VARCHAR(50),
                unit VARCHAR(20),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 插入默认配置（如果不存在）
        for config in self.CONFIG_DEFINITIONS:
            try:
                conn.execute('''
                    INSERT INTO system_config 
                    (config_key, config_value, config_type, category, description, default_value, min_value, max_value, unit)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    config['config_key'],
                    config['config_value'],
                    config['config_type'],
                    config['category'],
                    config['description'],
                    config['default_value'],
                    config.get('min_value'),
                    config.get('max_value'),
                    config.get('unit'),
                ))
            except sqlite3.IntegrityError:
                # 已存在，跳过
                pass
        
        conn.commit()
        conn.close()
    
    def _load_cache(self):
        """加载所有配置到内存缓存"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute('SELECT * FROM system_config').fetchall()
        conn.close()
        
        self._cache = {}
        for row in rows:
            self._cache[row['config_key']] = dict(row)
    
    def get(self, key: str) -> str:
        """
        获取配置值
        
        Args:
            key: 配置键名
            
        Returns:
            配置值（字符串）
        """
        if key not in self._cache:
            raise KeyError(f"配置项不存在: {key}")
        return self._cache[key]['config_value']
    
    def get_float(self, key: str) -> float:
        """
        获取浮点型配置值
        
        Args:
            key: 配置键名
            
        Returns:
            配置值（浮点数）
        """
        value = self.get(key)
        try:
            return float(value)
        except (ValueError, TypeError):
            raise ValueError(f"配置项 {key} 的值 '{value}' 无法转换为浮点数")
    
    def get_int(self, key: str) -> int:
        """
        获取整型配置值
        
        Args:
            key: 配置键名
            
        Returns:
            配置值（整数）
        """
        value = self.get(key)
        try:
            return int(float(value))
        except (ValueError, TypeError):
            raise ValueError(f"配置项 {key} 的值 '{value}' 无法转换为整数")
    
    def get_all(self) -> Dict[str, list]:
        """
        获取所有配置，按分类组织
        
        Returns:
            {category: [config1, config2, ...]}
        """
        result = {
            'A筛选': [],
            'B风控': [],
            'C权重': [],
        }
        
        for key in self._cache:
            config = self._cache[key]
            category = config['category']
            if category in result:
                result[category].append(config)
        
        return result
    
    def validate(self, key: str, value: str) -> Tuple[bool, str]:
        """
        校验配置值是否合法
        
        Args:
            key: 配置键名
            value: 配置值
            
        Returns:
            (是否合法, 错误消息)
        """
        if key not in self._cache:
            return False, f"配置项不存在: {key}"
        
        config = self._cache[key]
        config_type = config['config_type']
        min_value = config.get('min_value')
        max_value = config.get('max_value')
        
        # 类型检查
        try:
            if config_type == 'float':
                num_value = float(value)
            elif config_type == 'int':
                num_value = int(float(value))
            else:
                return True, ""  # 其他类型不校验
        except (ValueError, TypeError):
            return False, f"值 '{value}' 不是有效的{config_type}类型"
        
        # 范围检查
        if min_value is not None:
            try:
                min_num = float(min_value)
                if num_value < min_num:
                    return False, f"值 {num_value} 小于最小值 {min_num}"
            except (ValueError, TypeError):
                pass
        
        if max_value is not None:
            try:
                max_num = float(max_value)
                if num_value > max_num:
                    return False, f"值 {num_value} 大于最大值 {max_num}"
            except (ValueError, TypeError):
                pass
        
        # 权重和检查（C类参数特殊校验）
        if key.startswith('WEIGHT_'):
            weight_sum = 0.0
            for k in ['WEIGHT_DIVIDEND', 'WEIGHT_VOL', 'WEIGHT_STABILITY']:
                if k == key:
                    weight_sum += num_value
                else:
                    weight_sum += self.get_float(k)
            
            if abs(weight_sum - 1.0) > 0.001:
                return False, f"权重之和为 {weight_sum:.2f}，必须等于 1.0"
        
        return True, ""
    
    def update(self, key: str, value: str) -> Tuple[bool, str]:
        """
        更新配置值
        
        Args:
            key: 配置键名
            value: 配置值
            
        Returns:
            (是否成功, 消息)
        """
        # 校验
        is_valid, error_msg = self.validate(key, value)
        if not is_valid:
            return False, error_msg
        
        # 更新数据库
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            'UPDATE system_config SET config_value = ?, updated_at = CURRENT_TIMESTAMP WHERE config_key = ?',
            (value, key)
        )
        conn.commit()
        conn.close()
        
        # 更新缓存
        self._cache[key]['config_value'] = value
        
        return True, "配置已更新"
    
    def batch_update(self, configs: Dict[str, str]) -> Tuple[bool, str, int]:
        """
        批量更新配置
        
        Args:
            configs: {key: value, ...}
            
        Returns:
            (是否成功, 消息, 更新数量)
        """
        # 先校验所有配置的基本规则（类型、范围）
        for key, value in configs.items():
            # 临时禁用权重和校验
            config = self._cache.get(key)
            if not config:
                return False, f"配置项不存在: {key}", 0
            
            config_type = config['config_type']
            min_value = config.get('min_value')
            max_value = config.get('max_value')
            
            # 类型检查
            try:
                if config_type == 'float':
                    num_value = float(value)
                elif config_type == 'int':
                    num_value = int(float(value))
                else:
                    continue  # 其他类型不校验
            except (ValueError, TypeError):
                return False, f"{key}: 值 '{value}' 不是有效的{config_type}类型", 0
            
            # 范围检查
            if min_value is not None:
                try:
                    min_num = float(min_value)
                    if num_value < min_num:
                        return False, f"{key}: 值 {num_value} 小于最小值 {min_num}", 0
                except (ValueError, TypeError):
                    pass
            
            if max_value is not None:
                try:
                    max_num = float(max_value)
                    if num_value > max_num:
                        return False, f"{key}: 值 {num_value} 大于最大值 {max_num}", 0
                except (ValueError, TypeError):
                    pass
        
        # 特殊处理：权重和校验（需要在所有权重都更新后检查）
        weight_keys = ['WEIGHT_DIVIDEND', 'WEIGHT_VOL', 'WEIGHT_STABILITY']
        if any(k in configs for k in weight_keys):
            # 计算新的权重和
            weight_sum = 0.0
            for k in weight_keys:
                if k in configs:
                    weight_sum += float(configs[k])
                else:
                    weight_sum += self.get_float(k)
            
            if abs(weight_sum - 1.0) > 0.001:
                return False, f"权重之和为 {weight_sum:.2f}，必须等于 1.0", 0
        
        # 批量更新
        conn = sqlite3.connect(self.db_path)
        for key, value in configs.items():
            conn.execute(
                'UPDATE system_config SET config_value = ?, updated_at = CURRENT_TIMESTAMP WHERE config_key = ?',
                (value, key)
            )
            self._cache[key]['config_value'] = value
        conn.commit()
        conn.close()
        
        return True, "配置已更新", len(configs)
    
    def reset_to_default(self, category: str = None) -> int:
        """
        恢复默认值
        
        Args:
            category: 分类名称，None表示全部
            
        Returns:
            重置数量
        """
        conn = sqlite3.connect(self.db_path)
        count = 0
        
        if category:
            # 恢复指定分类
            for key, config in self._cache.items():
                if config['category'] == category:
                    conn.execute(
                        'UPDATE system_config SET config_value = ?, updated_at = CURRENT_TIMESTAMP WHERE config_key = ?',
                        (config['default_value'], key)
                    )
                    self._cache[key]['config_value'] = config['default_value']
                    count += 1
        else:
            # 恢复全部
            for key, config in self._cache.items():
                conn.execute(
                    'UPDATE system_config SET config_value = ?, updated_at = CURRENT_TIMESTAMP WHERE config_key = ?',
                    (config['default_value'], key)
                )
                self._cache[key]['config_value'] = config['default_value']
                count += 1
        
        conn.commit()
        conn.close()
        
        return count
