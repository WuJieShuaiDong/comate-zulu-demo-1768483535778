"""
money_effect_tracker 集成示例
展示如何在 auto_trader.py 中使用赚钱效应追踪模块
"""

from money_effect_tracker import MoneyEffectTracker
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def demo_integration():
    """演示如何集成到交易系统"""
    
    print("="*70)
    print("📊 赚钱效应追踪模块 - 集成示例")
    print("="*70)
    
    # 初始化追踪器
    tracker = MoneyEffectTracker()
    
    # ========================================
    # 场景1: 在选股前判断市场情绪
    # ========================================
    print("\n【场景1】市场情绪检查 - 决定是否开仓")
    print("-"*70)
    
    score_result = tracker.get_money_effect_score()
    
    print(f"\n当前市场赚钱效应: {score_result['total_score']:.1f}/100 ({score_result['level']})")
    
    # 根据评分决定策略
    if score_result['level'] == 'STRONG':
        print("✅ 市场情绪强势，可以主动选股建仓")
        position_ratio = 0.8  # 80%仓位
    elif score_result['level'] == 'MODERATE':
        print("⚠️  市场情绪一般，谨慎小仓位试错")
        position_ratio = 0.5  # 50%仓位
    else:
        print("❌ 市场情绪弱势，建议空仓观望")
        position_ratio = 0.0  # 空仓
    
    print(f"建议仓位: {position_ratio*100:.0f}%")
    
    # ========================================
    # 场景2: 智能龙头识别
    # ========================================
    print("\n【场景2】龙头股识别 - 精准狙击强势股")
    print("-"*70)
    
    # 降低评分阈值以便展示
    leaders = tracker.find_leading_stocks(min_score=50)
    
    if leaders:
        print(f"\n发现 {len(leaders)} 只潜在龙头:\n")
        
        for i, stock in enumerate(leaders[:3], 1):
            print(f"{i}. {stock['name']} ({stock['symbol']})")
            print(f"   ?? 评分: {stock['score']}/100")
            print(f"   📈 连板: {stock['board_count']}板")
            print(f"   💡 理由: {', '.join(stock['reasons'])}")
            if stock['sector']:
                print(f"   🏷️  板块: {stock['sector']}")
            print()
        
        # 模拟自动选股逻辑
        top_leader = leaders[0]
        print(f">>> 自动选股推荐: {top_leader['name']} (评分 {top_leader['score']})")
    else:
        print("⚠️  当前无高评分龙头，建议观望")
    
    # ========================================
    # 场景3: 板块持续性分析
    # ========================================
    print("\n【场景3】板块持续性分析 - 判断板块是否值得跟随")
    print("-"*70)
    
    # 从评分结果中获取热门板块
    if 'details' in score_result and 'top_sectors' in score_result['details']:
        top_sectors = list(score_result['details']['top_sectors'].keys())[:3]
        
        if top_sectors:
            print(f"\n分析前3大热门板块:\n")
            
            for sector in top_sectors:
                result = tracker.get_board_sustainability(sector)
                
                if 'error' not in result:
                    print(f"📊 {result['board_name']}")
                    print(f"   持续性: {result['sustainability']}")
                    print(f"   当前涨幅: {result.get('current_gain', 0):.2f}%")
                    print(f"   操作建议: {result['recommendation']}")
                    print()
        else:
            print("⚠️  暂无明显热门板块")
    
    # ========================================
    # 场景4: 综合决策流程
    # ========================================
    print("\n【场景4】综合决策流程 - 完整交易逻辑")
    print("-"*70)
    
    print("\n决策树:")
    print("├─ 1. 检查市场赚钱效应评分")
    print(f"│  └─ 当前: {score_result['total_score']:.1f}/100 ({score_result['level']})")
    
    if score_result['level'] in ['STRONG', 'MODERATE']:
        print("├─ 2. 识别龙头股")
        if leaders:
            print(f"│  └─ 发现 {len(leaders)} 只潜力龙头")
            print("├─ 3. 分析主线板块持续性")
            if 'details' in score_result and 'top_sectors' in score_result['details']:
                top = list(score_result['details']['top_sectors'].keys())[0]
                print(f"│  └─ 主线板块: {top}")
            print("└─ 4. ✅ 执行买入策略")
        else:
            print("└─ 2. ⚠️  无高分龙头，继续观察")
    else:
        print("└─ 2. ❌ 情绪弱势，空仓观望")
    
    print("\n" + "="*70)
    print("✅ 集成示例完成")
    print("="*70)


def show_integration_code():
    """展示集成代码片段"""
    
    print("\n" + "="*70)
    print("💻 集成代码示例 (auto_trader.py)")
    print("="*70)
    
    code = '''
# 在 auto_trader.py 文件开头导入
from money_effect_tracker import MoneyEffectTracker

# 在 run_bot() 函数中初始化
tracker = MoneyEffectTracker()

# 在选股循环前检查市场情绪
def should_trade_today():
    """判断今日是否适合交易"""
    score_result = tracker.get_money_effect_score()
    
    if score_result['level'] == 'STRONG':
        logging.info("🔥 市场情绪强势，启动主动选股")
        return True, 0.8  # 返回 (是否交易, 仓位比例)
    elif score_result['level'] == 'MODERATE':
        logging.info("⚠️  市场情绪一般，小仓位试错")
        return True, 0.5
    else:
        logging.info("❌ 市场情绪弱势，空仓观望")
        return False, 0.0

# 在选股时优先考虑龙头股
def get_priority_symbols():
    """获取优先交易的龙头股列表"""
    leaders = tracker.find_leading_stocks(min_score=70)
    
    if leaders:
        logging.info(f"🎯 识别到 {len(leaders)} 只龙头股")
        return [stock['symbol'] for stock in leaders[:5]]  # 返回前5只
    
    return []

# 修改后的主循环
while True:
    try:
        # 1. 检查市场情绪
        can_trade, position_ratio = should_trade_today()
        
        if not can_trade:
            logging.info("今日不适合交易，休息...")
            time.sleep(1800)  # 休息30分钟
            continue
        
        # 2. 获取龙头股优先列表
        priority_symbols = get_priority_symbols()
        
        # 3. 优先扫描龙头股
        for symbol in priority_symbols:
            if symbol not in trader.positions:
                signals = calculate_signals(symbol)
                if signals and signals['trend_up']:
                    # 根据仓位比例计算买入金额
                    buy_amount = 1000000 * position_ratio / 4  # 假设分4只
                    shares = int(buy_amount / signals['price'] / 100) * 100
                    
                    if shares >= 100:
                        trader.buy(symbol, name, signals['price'], shares, "龙头跟随")
                        break
        
        time.sleep(300)
        
    except Exception as e:
        logging.error(f"异常: {e}")
        time.sleep(60)
'''
    
    print(code)
    print("="*70)


if __name__ == "__main__":
    demo_integration()
    show_integration_code()