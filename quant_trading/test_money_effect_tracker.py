"""
money_effect_tracker 单元测试
测试各项功能的正确性和性能
"""

import unittest
import time
from money_effect_tracker import MoneyEffectTracker
import logging

logging.basicConfig(level=logging.WARNING)  # 减少测试时的日志输出


class TestMoneyEffectTracker(unittest.TestCase):
    """赚钱效应追踪器测试类"""
    
    @classmethod
    def setUpClass(cls):
        """测试前的准备工作"""
        print("\n" + "="*60)
        print("🧪 开始测试 MoneyEffectTracker")
        print("="*60)
        cls.tracker = MoneyEffectTracker()
    
    def test_01_initialization(self):
        """测试1: 初始化"""
        print("\n[测试1] 模块初始化...")
        self.assertIsNotNone(self.tracker)
        self.assertEqual(self.tracker.cache_duration, 300)
        print("✅ 初始化成功")
    
    def test_02_cache_mechanism(self):
        """测试2: 缓存机制"""
        print("\n[测试2] 缓存机制...")
        
        # 第一次调用（会触发数据获取）
        start = time.time()
        result1 = self.tracker.get_money_effect_score()
        time1 = time.time() - start
        
        # 第二次调用（应该使用缓存）
        start = time.time()
        result2 = self.tracker.get_money_effect_score()
        time2 = time.time() - start
        
        self.assertEqual(result1['total_score'], result2['total_score'])
        self.assertLess(time2, time1 * 0.1, "缓存未生效")
        
        print(f"✅ 缓存生效 (首次: {time1:.2f}s, 缓存: {time2:.4f}s)")
    
    def test_03_money_effect_score(self):
        """测试3: 赚钱效应评分"""
        print("\n[测试3] 赚钱效应评分...")
        
        result = self.tracker.get_money_effect_score()
        
        # 检查返回值结构
        self.assertIn('total_score', result)
        self.assertIn('level', result)
        self.assertIn('details', result)
        
        # 检查评分范围
        self.assertGreaterEqual(result['total_score'], 0)
        self.assertLessEqual(result['total_score'], 100)
        
        # 检查情绪等级
        self.assertIn(result['level'], ['STRONG', 'MODERATE', 'WEAK'])
        
        print(f"✅ 评分: {result['total_score']}/100 ({result['level']})")
        
        # 验证评分逻辑一致性
        if result['level'] == 'STRONG':
            self.assertGreaterEqual(result['total_score'], 70)
        elif result['level'] == 'MODERATE':
            self.assertGreaterEqual(result['total_score'], 40)
            self.assertLess(result['total_score'], 70)
        else:
            self.assertLess(result['total_score'], 40)
        
        print("✅ 评分逻辑一致性验证通过")
    
    def test_04_find_leading_stocks(self):
        """测试4: 龙头股识别"""
        print("\n[测试4] 龙头股识别...")
        
        # 测试不同评分阈值
        leaders_high = self.tracker.find_leading_stocks(min_score=80)
        leaders_medium = self.tracker.find_leading_stocks(min_score=60)
        leaders_low = self.tracker.find_leading_stocks(min_score=40)
        
        # 高阈值结果应该是中等阈值的子集
        self.assertLessEqual(len(leaders_high), len(leaders_medium))
        self.assertLessEqual(len(leaders_medium), len(leaders_low))
        
        print(f"✅ 识别结果 (阈值80: {len(leaders_high)}只, "
              f"阈值60: {len(leaders_medium)}只, "
              f"阈值40: {len(leaders_low)}只)")
        
        # 检查返回数据结构
        if leaders_low:
            stock = leaders_low[0]
            required_keys = ['symbol', 'name', 'board_count', 'score', 'reasons']
            for key in required_keys:
                self.assertIn(key, stock, f"缺少字段: {key}")
            
            # 检查评分是否满足阈值
            self.assertGreaterEqual(stock['score'], 40)
            
            print(f"✅ 数据结构验证通过")
            print(f"   示例: {stock['name']} (评分{stock['score']}, {stock['board_count']}板)")
    
    def test_05_board_sustainability(self):
        """测试5: 板块持续性分析"""
        print("\n[测试5] 板块持续性分析...")
        
        # 先获取热门板块
        score_result = self.tracker.get_money_effect_score()
        
        if 'details' in score_result and 'top_sectors' in score_result['details']:
            top_sectors = list(score_result['details']['top_sectors'].keys())[:2]
            
            for sector in top_sectors:
                result = self.tracker.get_board_sustainability(sector)
                
                # 检查返回值
                if 'error' not in result:
                    self.assertIn('board_name', result)
                    self.assertIn('sustainability', result)
                    self.assertIn(result['sustainability'], ['HIGH', 'MEDIUM', 'LOW'])
                    
                    print(f"✅ {sector}: {result['sustainability']}")
        else:
            print("⚠️  无热门板块数据，跳过测试")
    
    def test_06_performance(self):
        """测试6: 性能测试"""
        print("\n[测试6] 性能测试...")
        
        # 测试单次调用性能
        start = time.time()
        self.tracker.get_money_effect_score()
        time1 = time.time() - start
        
        start = time.time()
        self.tracker.find_leading_stocks(min_score=60)
        time2 = time.time() - start
        
        # 要求单次执行 <5秒（使用缓存后应该很快）
        self.assertLess(time1, 5.0, "评分计算超时")
        self.assertLess(time2, 5.0, "龙头识别超时")
        
        print(f"✅ 评分计算: {time1:.2f}s")
        print(f"✅ 龙头识别: {time2:.2f}s")
        print(f"✅ 性能测试通过 (均 <5秒)")
    
    def test_07_edge_cases(self):
        """测试7: 边界情况"""
        print("\n[测试7] 边界情况测试...")
        
        # 测试无效板块名称
        result = self.tracker.get_board_sustainability("不存在的板块12345")
        self.assertIn('error', result)
        print("✅ 无效板块名称处理正常")
        
        # 测试极端评分阈值
        leaders = self.tracker.find_leading_stocks(min_score=150)  # 超出100
        self.assertEqual(len(leaders), 0)
        print("✅ 极端阈值处理正常")
    
    @classmethod
    def tearDownClass(cls):
        """测试结束清理"""
        print("\n" + "="*60)
        print("✅ 所有测试完成")
        print("="*60)


def run_performance_benchmark():
    """性能基准测试"""
    print("\n" + "="*60)
    print("⚡ 性能基准测试")
    print("="*60)
    
    tracker = MoneyEffectTracker()
    
    # 测试冷启动（无缓存）
    tracker.cache_time = None
    start = time.time()
    tracker.get_money_effect_score()
    cold_start_time = time.time() - start
    
    # 测试热启动（有缓存）
    warm_times = []
    for i in range(5):
        start = time.time()
        tracker.get_money_effect_score()
        warm_times.append(time.time() - start)
    
    avg_warm_time = sum(warm_times) / len(warm_times)
    
    print(f"\n冷启动时间: {cold_start_time:.2f}s")
    print(f"热启动平均时间: {avg_warm_time:.4f}s")
    print(f"缓存加速比: {cold_start_time/avg_warm_time:.1f}x")
    
    # 综合调用测试
    print("\n综合功能调用测试 (5次):")
    total_times = []
    
    for i in range(5):
        start = time.time()
        tracker.get_money_effect_score()
        tracker.find_leading_stocks(min_score=60)
        total_times.append(time.time() - start)
    
    avg_total = sum(total_times) / len(total_times)
    print(f"平均耗时: {avg_total:.2f}s")
    
    if avg_total < 5.0:
        print("✅ 性能达标 (<5秒)")
    else:
        print("⚠️  性能需优化 (>5秒)")
    
    print("="*60)


if __name__ == "__main__":
    # 运行单元测试
    unittest.main(verbosity=2, exit=False)
    
    # 运行性能基准测试
    print("\n")
    run_performance_benchmark()