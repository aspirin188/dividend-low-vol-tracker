"""
评分算法单元测试 — 红利低波跟踪系统
"""

import unittest
import pandas as pd
import numpy as np
from server.services.scorer import (
    filter_stocks, calculate_scores, prepare_results,
    min_max_normalize,
)


class TestMinMaxNormalize(unittest.TestCase):
    """min-max 归一化测试"""

    def test_normal_case(self):
        values = np.array([2.0, 4.0, 6.0, 8.0, 10.0])
        self.assertAlmostEqual(min_max_normalize(values, 2.0), 0.0)
        self.assertAlmostEqual(min_max_normalize(values, 10.0), 1.0)
        self.assertAlmostEqual(min_max_normalize(values, 6.0), 0.5)

    def test_empty_list(self):
        values = np.array([])
        self.assertEqual(min_max_normalize(values, 5.0), 0.5)

    def test_single_element(self):
        values = np.array([5.0])
        self.assertEqual(min_max_normalize(values, 5.0), 0.5)

    def test_all_same(self):
        values = np.array([3.0, 3.0, 3.0])
        self.assertEqual(min_max_normalize(values, 3.0), 0.5)


class TestFilterStocks(unittest.TestCase):
    """硬性筛选测试"""

    def _make_df(self, data):
        """创建测试 DataFrame"""
        return pd.DataFrame(data)

    def test_basic_filter(self):
        """基本筛选：股息率 >= 4%"""
        df = self._make_df([
            {'code': 'A', 'name': '正常', 'dividend_yield_ttm': 5.0, 'market_cap': 200,
             'annual_vol': 15.0, 'basic_eps': 1.0, 'payout_ratio': 50.0},
            {'code': 'B', 'name': '低股息', 'dividend_yield_ttm': 2.0, 'market_cap': 200,
             'annual_vol': 15.0, 'basic_eps': 1.0, 'payout_ratio': 50.0},
        ])
        result = filter_stocks(df)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['code'], 'A')

    def test_market_cap_filter(self):
        """市值筛选"""
        df = self._make_df([
            {'code': 'A', 'name': '大市值', 'dividend_yield_ttm': 5.0, 'market_cap': 200,
             'annual_vol': 15.0, 'basic_eps': 1.0, 'payout_ratio': 50.0},
            {'code': 'B', 'name': '小市值', 'dividend_yield_ttm': 5.0, 'market_cap': 50,
             'annual_vol': 15.0, 'basic_eps': 1.0, 'payout_ratio': 50.0},
        ])
        result = filter_stocks(df)
        self.assertEqual(len(result), 1)

    def test_st_filter(self):
        """ST 股票过滤"""
        df = self._make_df([
            {'code': 'A', 'name': 'ST公司', 'dividend_yield_ttm': 5.0, 'market_cap': 200,
             'annual_vol': 15.0, 'basic_eps': 1.0, 'payout_ratio': 50.0},
            {'code': 'B', 'name': '*ST公司', 'dividend_yield_ttm': 5.0, 'market_cap': 200,
             'annual_vol': 15.0, 'basic_eps': 1.0, 'payout_ratio': 50.0},
            {'code': 'C', 'name': '正常公司', 'dividend_yield_ttm': 5.0, 'market_cap': 200,
             'annual_vol': 15.0, 'basic_eps': 1.0, 'payout_ratio': 50.0},
        ])
        result = filter_stocks(df)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['code'], 'C')

    def test_negative_eps_filter(self):
        """EPS <= 0 过滤"""
        df = self._make_df([
            {'code': 'A', 'name': '盈利', 'dividend_yield_ttm': 5.0, 'market_cap': 200,
             'annual_vol': 15.0, 'basic_eps': 1.0, 'payout_ratio': 50.0},
            {'code': 'B', 'name': '亏损', 'dividend_yield_ttm': 5.0, 'market_cap': 200,
             'annual_vol': 15.0, 'basic_eps': -0.5, 'payout_ratio': 50.0},
        ])
        result = filter_stocks(df)
        self.assertEqual(len(result), 1)

    def test_missing_volatility_filter(self):
        """波动率缺失过滤"""
        df = self._make_df([
            {'code': 'A', 'name': '有波动率', 'dividend_yield_ttm': 5.0, 'market_cap': 200,
             'annual_vol': 15.0, 'basic_eps': 1.0, 'payout_ratio': 50.0},
            {'code': 'B', 'name': '无波动率', 'dividend_yield_ttm': 5.0, 'market_cap': 200,
             'annual_vol': None, 'basic_eps': 1.0, 'payout_ratio': 50.0},
        ])
        result = filter_stocks(df)
        self.assertEqual(len(result), 1)

    def test_payout_ratio_limit(self):
        """支付率超过 150% 过滤"""
        df = self._make_df([
            {'code': 'A', 'name': '正常', 'dividend_yield_ttm': 5.0, 'market_cap': 200,
             'annual_vol': 15.0, 'basic_eps': 1.0, 'payout_ratio': 80.0},
            {'code': 'B', 'name': '超高支付', 'dividend_yield_ttm': 5.0, 'market_cap': 200,
             'annual_vol': 15.0, 'basic_eps': 1.0, 'payout_ratio': 200.0},
        ])
        result = filter_stocks(df)
        self.assertEqual(len(result), 1)


class TestCalculateScores(unittest.TestCase):
    """综合评分测试"""

    def test_score_range(self):
        """评分范围应在 0-100"""
        df = pd.DataFrame([
            {'code': f'C{i}', 'name': f'Stock{i}', 'dividend_yield_ttm': 4.0 + i,
             'market_cap': 100 + i * 50, 'annual_vol': 10 + i * 2, 'basic_eps': 1.0,
             'payout_ratio': 50.0, 'industry': '银行'}
            for i in range(20)
        ])
        result = calculate_scores(df)
        scores = result['composite_score'].tolist()
        for s in scores:
            self.assertGreaterEqual(s, 0)
            self.assertLessEqual(s, 100)

    def test_ranking_order(self):
        """排名应按评分降序"""
        df = pd.DataFrame([
            {'code': f'C{i}', 'name': f'S{i}', 'dividend_yield_ttm': 4.0 + i,
             'market_cap': 100 + i * 50, 'annual_vol': 10 + i * 2, 'basic_eps': 1.0,
             'payout_ratio': 50.0, 'industry': '银行'}
            for i in range(10)
        ])
        result = calculate_scores(df)
        scores = result['composite_score'].tolist()
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_empty_df(self):
        """空 DataFrame"""
        result = calculate_scores(pd.DataFrame())
        self.assertTrue(result.empty)

    def test_high_dividend_low_vol_best(self):
        """高股息率 + 低波动率应该得分最高"""
        df = pd.DataFrame([
            {'code': 'A', 'name': '高息低波', 'dividend_yield_ttm': 8.0,
             'market_cap': 200, 'annual_vol': 10.0, 'basic_eps': 2.0,
             'payout_ratio': 50.0, 'industry': '银行'},
            {'code': 'B', 'name': '低息高波', 'dividend_yield_ttm': 4.0,
             'market_cap': 200, 'annual_vol': 30.0, 'basic_eps': 2.0,
             'payout_ratio': 50.0, 'industry': '银行'},
            {'code': 'C', 'name': '中等', 'dividend_yield_ttm': 6.0,
             'market_cap': 200, 'annual_vol': 20.0, 'basic_eps': 2.0,
             'payout_ratio': 50.0, 'industry': '银行'},
        ])
        result = calculate_scores(df)
        self.assertEqual(result.iloc[0]['code'], 'A')


class TestPrepareResults(unittest.TestCase):
    """结果整理测试"""

    def test_columns(self):
        """检查输出列"""
        df = pd.DataFrame([
            {'code': 'A', 'name': '测试', 'industry': '银行',
             'dividend_yield_ttm': 5.0, 'annual_vol': 15.0,
             'composite_score': 80.0, 'rank': 1,
             'market_cap': 200.0, 'payout_ratio': 50.0, 'basic_eps': 1.0}
        ])
        result = prepare_results(df, '2026-03-27')
        expected_cols = [
            'code', 'name', 'industry', 'dividend_yield', 'annual_vol',
            'composite_score', 'rank', 'market_cap', 'payout_ratio', 'eps',
            'data_date', 'updated_at'
        ]
        self.assertEqual(list(result.columns), expected_cols)
        self.assertEqual(result.iloc[0]['data_date'], '2026-03-27')

    def test_empty(self):
        """空输入"""
        result = prepare_results(pd.DataFrame())
        self.assertTrue(result.empty)


if __name__ == '__main__':
    unittest.main()
