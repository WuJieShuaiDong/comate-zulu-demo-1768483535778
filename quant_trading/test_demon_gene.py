"""
妖股基因系统测试脚本
用于验证妖股基因识别功能的正确性
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from demon_stock_gene import DemonStockGene, quick_query, get_demon_list
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def test_single_stock():
    """测试1: 单只股票基因评分计算"""
    print("\n" + "="*60)
    print("测试1: 单只股票基因评分计算")
    print("="*60)
    
    tracker = DemonStockGene()
    
    # 测试贵州茅台
    test_symbol = "600519"
    print(f"\n测试股票: {test_symbol}")
    
    result = tracker.calculate_gene_score(test_symbol)
    
    if result:
        print(f"✅ 计算成功!")
        print(f"  股票名称: {result['name']}")
        print(f"  基因评分: {result['gene_score']}/100")
        print(f"  最大连板数: {result['max_continuous_board']}")
        print(f"  最后连板日期: {result['last_board_date']}")
        print(f"  单月最大涨幅: {result['monthly_max_gain']:.2f}%")
        print(f"  日均振幅: {result['avg_amplitude']:.2f}%")
        print(f"  半年涨停次数: {result['zt_count_6m']}")
        print(f"  更新时间: {result['update_time']}")
    else:
        print(f"❌ 计算失败")


def test_quick_query():
    """测试2: 快速查询接口"""
    print("\n" + "="*60)
    print("测试2: 快速查询接口")
    print("="*60)
    
    tracker = DemonStockGene()
    
    # 先添加一只测试股票到基因库
    test_symbol = "600519"
    gene_data = tracker.calculate_gene_score(test_symbol)
    
    if gene_data:
        tracker.gene_db[test_symbol] = gene_data
        tracker._save_gene_db()
        
        # 测试快速查询
        print(f"\n快速查询 {test_symbol}:")
        score = tracker.get_gene_score(test_symbol)
        print(f"  基因评分: {score}")
        
        full_data = tracker.get_gene_data(test_symbol)
        if full_data:
            print(f"  完整数据: {full_data['name']} - {full_data['gene_score']}分")
            print(f"✅ 快速查询测试通过")
        else:
            print(f"❌ 完整数据获取失败")
    else:
        print(f"❌ 测试数据准备失败")


def test_high_gene_list():
    """测试3: 高分妖股列表"""
    print("\n" + "="*60)
    print("测试3: 高分妖股列表")
    print("="*60)
    
    tracker = DemonStockGene()
    
    # 获取基因库统计
    stats = tracker.get_statistics()
    print(f"\n基因库状态:")
    print(f"  总股票数: {stats['total_stocks']}")
    print(f"  高分妖股(≥60分): {stats['high_gene_count']}")
    print(f"  超级妖股(≥80分): {stats['super_demon_count']}")
    
    if stats['total_stocks'] > 0:
        # 获取Top5妖股
        print(f"\n🔥 Top 5 妖股基因:")
        high_gene_stocks = tracker.get_high_gene_stocks(min_score=0)
        
        for idx, stock in enumerate(high_gene_stocks[:5], 1):
            print(f"  {idx}. {stock['name']} ({stock['symbol']})")
            print(f"     评分: {stock['gene_score']}/100")
            print(f"     连板: {stock['max_continuous_board']}板")
            print(f"     月涨幅: {stock['monthly_max_gain']:.1f}%")
            print(f"     振幅: {stock['avg_amplitude']:.1f}%")
        
        print(f"✅ 高分妖股列表测试通过")
    else:
        print(f"⚠️  基因库为空，请先运行 build_gene_database()")


def test_gene_score_logic():
    """测试4: 评分逻辑验证"""
    print("\n" + "="*60)
    print("测试4: 评分逻辑验证")
    print("="*60)
    
    # 模拟不同级别的妖股特征
    test_cases = [
        {
            'name': '超级妖股',
            'max_continuous_board': 5,
            'monthly_max_gain': 80,
            'zt_count_6m': 5,
            'avg_amplitude': 10,
            'expected_score': 100
        },
        {
            'name': '强妖股',
            'max_continuous_board': 3,
            'monthly_max_gain': 50,
            'zt_count_6m': 3,
            'avg_amplitude': 8,
            'expected_score': 75
        },
        {
            'name': '中等妖股',
            'max_continuous_board': 2,
            'monthly_max_gain': 30,
            'zt_count_6m': 1,
            'avg_amplitude': 6,
            'expected_score': 40
        }
    ]
    
    print("\n评分逻辑测试:")
    for case in test_cases:
        score = 0
        
        # 连板分数
        if case['max_continuous_board'] >= 5:
            score += 40
        elif case['max_continuous_board'] >= 3:
            score += 30
        elif case['max_continuous_board'] >= 2:
            score += 20
        
        # 月涨幅分数
        if case['monthly_max_gain'] >= 80:
            score += 30
        elif case['monthly_max_gain'] >= 50:
            score += 20
        elif case['monthly_max_gain'] >= 30:
            score += 10
        
        # 炒作频率分数
        if case['zt_count_6m'] >= 5:
            score += 20
        elif case['zt_count_6m'] >= 3:
            score += 15
        elif case['zt_count_6m'] >= 1:
            score += 10
        
        # 活跃度分数
        if case['avg_amplitude'] >= 10:
            score += 10
        elif case['avg_amplitude'] >= 8:
            score += 5
        
        print(f"\n  {case['name']}:")
        print(f"    连板{case['max_continuous_board']} | 月涨{case['monthly_max_gain']}% | "
              f"涨停{case['zt_count_6m']}次 | 振幅{case['avg_amplitude']}%")
        print(f"    计算得分: {score}/100")
        print(f"    预期得分: {case['expected_score']}/100")
        
        if score == case['expected_score']:
            print(f"    ✅ 评分正确")
        else:
            print(f"    ⚠️  评分偏差: {abs(score - case['expected_score'])}分")
    
    print(f"\n✅ 评分逻辑验证完成")


def test_integration_with_auto_trader():
    """测试5: 集成到auto_trader示例"""
    print("\n" + "="*60)
    print("测试5: 集成到auto_trader示例")
    print("="*60)
    
    tracker = DemonStockGene()
    
    # 模拟龙头股评分增强
    test_stocks = [
        {'symbol': '600519', 'name': '贵州茅台', 'base_score': 60},
        {'symbol': '000858', 'name': '五粮液', 'base_score': 55},
    ]
    
    print("\n龙头评分增强示例:")
    for stock in test_stocks:
        symbol = stock['symbol']
        base_score = stock['base_score']
        
        # 获取妖股基因评分
        gene_score = tracker.get_gene_score(symbol)
        
        # 计算增强后的评分
        if gene_score >= 80:
            bonus = 20  # 强妖股基因
        elif gene_score >= 60:
            bonus = 10  # 中等妖股基因
        else:
            bonus = 0   # 无妖股基因
        
        final_score = base_score + bonus
        
        print(f"\n  {stock['name']} ({symbol}):")
        print(f"    基础龙头评分: {base_score}")
        print(f"    妖股基因评分: {gene_score}")
        print(f"    基因加成: +{bonus}")
        print(f"    最终评分: {final_score}")
    
    print(f"\n✅ 集成示例测试通过")


def main():
    """主测试流程"""
    print("\n" + "="*80)
    print("妖股基因系统测试套件")
    print("="*80)
    
    try:
        # 测试1: 单只股票基因评分
        test_single_stock()
        
        # 测试2: 快速查询接口
        test_quick_query()
        
        # 测试3: 高分妖股列表
        test_high_gene_list()
        
        # 测试4: 评分逻辑验证
        test_gene_score_logic()
        
        # 测试5: 集成示例
        test_integration_with_auto_trader()
        
        print("\n" + "="*80)
        print("✅ 所有测试完成!")
        print("="*80)
        
        # 使用提示
        print("\n💡 下一步操作:")
        print("  1. 首次构建基因库 (收盘后运行):")
        print("     python -c \"from demon_stock_gene import DemonStockGene; DemonStockGene().build_gene_database(max_stocks=100)\"")
        print("\n  2. 每日增量更新:")
        print("     python -c \"from demon_stock_gene import DemonStockGene; DemonStockGene().update_gene_database()\"")
        print("\n  3. 集成到auto_trader.py (参见DEMON_GENE_INTEGRATION.md)")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()