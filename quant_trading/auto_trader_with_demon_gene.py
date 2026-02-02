"""
集成妖股基因系统的完整示例
这是对原有 auto_trader.py 的增强版本，展示如何集成妖股基因识别
"""

# 在原有导入基础上，新增妖股基因模块导入
try:
    from demon_stock_gene import DemonStockGene
    DEMON_GENE_AVAILABLE = True
    logging.info("✅ 妖股基因模块加载成功")
except ImportError:
    DEMON_GENE_AVAILABLE = False
    logging.warning("⚠️  demon_stock_gene.py 未找到，将不使用妖股基因增强")


# ==============================================================================
# 在 AutoTrader 类中集成妖股基因
# ==============================================================================

class AutoTrader:
    def __init__(self, trader: BaseTrader):
        self.trader = trader
        
        # 初始化赚钱效应追踪器
        if MONEY_EFFECT_AVAILABLE:
            self.money_tracker = MoneyEffectTracker()
        else:
            self.money_tracker = None
        
        # 【新增】初始化妖股基因追踪器
        if DEMON_GENE_AVAILABLE:
            self.demon_gene_tracker = DemonStockGene()
            logging.info("🧬 妖股基因追踪器初始化成功")
        else:
            self.demon_gene_tracker = None
    
    def select_stocks(self):
        """
        智能选股策略（集成妖股基因）
        
        增强逻辑:
        1. 使用赚钱效应追踪识别龙头候选
        2. 叠加妖股基因评分，优先选择有炒作历史的股票
        3. 根据市场情绪动态调整持仓数量
        """
        # 判断市场情绪
        sentiment_result = check_market_sentiment_enhanced(self.money_tracker)
        sentiment = sentiment_result['sentiment']
        max_positions = sentiment_result['max_positions']
        
        logging.info(f"💰 市场情绪: {sentiment}, 建议持仓: {max_positions}只")
        
        if sentiment == 'BEARISH':
            logging.info("🚫 市场弱势，空仓观望")
            return []
        
        # 获取龙头股候选
        if self.money_tracker:
            leaders = self.money_tracker.find_leading_stocks(min_score=60)
            logging.info(f"🎯 识别到 {len(leaders)} 只龙头候选")
        else:
            # 降级方案：使用传统涨停池
            leaders = self._get_fallback_stocks()
        
        if not leaders:
            logging.warning("⚠️  未找到合适龙头，本轮不操作")
            return []
        
        # 【核心增强】叠加妖股基因评分
        enhanced_leaders = []
        
        for stock in leaders:
            symbol = stock['symbol']
            name = stock['name']
            base_score = stock.get('score', 50)
            
            # 获取妖股基因评分
            gene_score = 0
            gene_bonus = 0
            gene_level = '普通'
            
            if self.demon_gene_tracker:
                gene_score = self.demon_gene_tracker.get_gene_score(symbol)
                
                # 基因加成规则
                if gene_score >= 80:
                    gene_bonus = 20  # 超级妖股基因，优先级最高
                    gene_level = '超级妖股'
                elif gene_score >= 60:
                    gene_bonus = 10  # 强妖股基因
                    gene_level = '强妖股'
                else:
                    gene_bonus = 0
                    gene_level = '普通'
            
            # 计算最终评分
            final_score = base_score + gene_bonus
            
            # 保存增强后的数据
            enhanced_stock = stock.copy()
            enhanced_stock['base_score'] = base_score
            enhanced_stock['gene_score'] = gene_score
            enhanced_stock['gene_bonus'] = gene_bonus
            enhanced_stock['gene_level'] = gene_level
            enhanced_stock['final_score'] = final_score
            
            enhanced_leaders.append(enhanced_stock)
        
        # 按最终评分排序
        enhanced_leaders.sort(key=lambda x: x['final_score'], reverse=True)
        
        # 日志输出（展示妖股基因增强效果）
        logging.info(f"🧬 妖股基因增强后龙头排名:")
        for idx, stock in enumerate(enhanced_leaders[:10], 1):
            logging.info(
                f"  {idx}. {stock['name']} ({stock['symbol']}): "
                f"基础{stock['base_score']:.0f} + 基因{stock['gene_bonus']} "
                f"= {stock['final_score']:.0f} [{stock['gene_level']}]"
            )
        
        # 选出Top N只股票
        selected = enhanced_leaders[:max_positions]
        
        logging.info(f"✅ 最终选定 {len(selected)} 只股票")
        return selected
    
    def check_positions(self):
        """
        持仓检查（集成妖股基因动态止盈）
        
        增强逻辑:
        1. 超级妖股(≥80分): 不设止盈，断板才走
        2. 强妖股(60-79分): 30%止盈
        3. 普通股(<60分): 20%止盈
        """
        if not self.trader.positions:
            return
        
        logging.info("🔍 检查持仓...")
        
        for symbol, pos in list(self.trader.positions.items()):
            try:
                # 获取最新价格
                latest_price = get_latest_price(symbol)
                if latest_price is None:
                    continue
                
                cost = pos['cost']
                profit_pct = (latest_price - cost) / cost
                
                # 【新增】获取妖股基因评分
                gene_score = 0
                if self.demon_gene_tracker:
                    gene_score = self.demon_gene_tracker.get_gene_score(symbol)
                
                # 动态止盈策略
                should_sell = False
                sell_reason = ""
                
                # 1. 止损判断（所有股票统一）
                if profit_pct < -STOP_LOSS_PCT:
                    should_sell = True
                    sell_reason = f"止损{profit_pct*100:.1f}%"
                
                # 2. 根据妖股基因等级设置不同止盈策略
                elif gene_score >= 80:
                    # 超级妖股：只在断板时走（这里简化为不设止盈）
                    # 实际可通过检查是否涨停来判断是否断板
                    logging.info(f"  {pos['name']} 超级妖股({gene_score}分)，持有不动 [盈利{profit_pct*100:.1f}%]")
                
                elif gene_score >= 60:
                    # 强妖股：30%止盈
                    if profit_pct >= 0.30:
                        should_sell = True
                        sell_reason = f"强妖股止盈{profit_pct*100:.1f}%"
                    else:
                        logging.info(f"  {pos['name']} 强妖股({gene_score}分)，继续持有 [盈利{profit_pct*100:.1f}%]")
                
                else:
                    # 普通股：20%止盈
                    if profit_pct >= TAKE_PROFIT_PCT:
                        should_sell = True
                        sell_reason = f"普通股止盈{profit_pct*100:.1f}%"
                    else:
                        logging.info(f"  {pos['name']} 普通股({gene_score}分)，继续持有 [盈利{profit_pct*100:.1f}%]")
                
                # 执行卖出
                if should_sell:
                    self.trader.sell(symbol, latest_price, sell_reason)
                    logging.info(f"  💰 {pos['name']} {sell_reason}")
            
            except Exception as e:
                logging.error(f"检查持仓 {symbol} 失败: {e}")
    
    def _get_fallback_stocks(self):
        """降级方案：当赚钱效应追踪不可用时，使用传统涨停池"""
        try:
            today = datetime.date.today().strftime("%Y%m%d")
            zt_pool = ak.stock_zt_pool_em(date=today)
            
            if zt_pool.empty:
                return []
            
            # 简单转换格式
            stocks = []
            for _, row in zt_pool.head(20).iterrows():
                stocks.append({
                    'symbol': row.get('代码', ''),
                    'name': row.get('名称', ''),
                    'score': 50,  # 默认基础分
                    'reasons': ['涨停']
                })
            
            return stocks
        
        except Exception as e:
            logging.error(f"获取涨停池失败: {e}")
            return []


# ==============================================================================
# 辅助函数示例
# ==============================================================================

def get_demon_gene_report():
    """
    生成妖股基因日报
    用于每日收盘后查看妖股基因库状态
    """
    if not DEMON_GENE_AVAILABLE:
        print("⚠️  妖股基因模块未安装")
        return
    
    tracker = DemonStockGene()
    
    # 统计信息
    stats = tracker.get_statistics()
    
    print("\n" + "="*60)
    print("📊 妖股基因库日报")
    print("="*60)
    print(f"总股票数: {stats['total_stocks']}")
    print(f"高分妖股(≥60分): {stats['high_gene_count']}")
    print(f"超级妖股(≥80分): {stats['super_demon_count']}")
    print(f"平均基因评分: {stats['avg_gene_score']}")
    
    if stats['max_gene_stock']:
        max_stock = stats['max_gene_stock']
        print(f"最强妖股: {max_stock['name']} ({max_stock['symbol']}) - {max_stock['gene_score']}分")
    
    # Top 10 妖股
    print(f"\n🔥 Top 10 妖股基因:")
    high_gene_stocks = tracker.get_high_gene_stocks(min_score=0)
    
    for idx, stock in enumerate(high_gene_stocks[:10], 1):
        print(f"{idx:2d}. {stock['name']:8s} ({stock['symbol']}) "
              f"{stock['gene_score']:3.0f}分 "
              f"[{stock['max_continuous_board']}板 | "
              f"月涨{stock['monthly_max_gain']:.0f}% | "
              f"半年{stock['zt_count_6m']}次涨停]")
    
    print("="*60 + "\n")


def daily_maintenance():
    """
    每日维护任务
    建议在收盘后运行（15:30之后）
    """
    print("\n🔧 开始每日维护任务...")
    
    # 1. 更新妖股基因库
    if DEMON_GENE_AVAILABLE:
        print("\n1️⃣ 更新妖股基因库...")
        tracker = DemonStockGene()
        tracker.update_gene_database()
    
    # 2. 生成日报
    print("\n2️⃣ 生成妖股基因日报...")
    get_demon_gene_report()
    
    print("\n✅ 每日维护完成!")


# ==============================================================================
# 使用示例
# ==============================================================================

if __name__ == "__main__":
    import sys
    
    # 根据命令行参数执行不同任务
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "build":
            # 首次构建基因库
            print("🚀 开始构建妖股基因库（首次运行）...")
            tracker = DemonStockGene()
            max_stocks = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
            tracker.build_gene_database(max_stocks=max_stocks)
        
        elif command == "update":
            # 每日更新
            print("🔄 开始增量更新妖股基因库...")
            tracker = DemonStockGene()
            tracker.update_gene_database()
        
        elif command == "report":
            # 生成日报
            get_demon_gene_report()
        
        elif command == "maintain":
            # 每日维护
            daily_maintenance()
        
        elif command == "query":
            # 查询单只股票
            if len(sys.argv) > 2:
                symbol = sys.argv[2]
                tracker = DemonStockGene()
                data = tracker.get_gene_data(symbol)
                
                if data:
                    print(f"\n🧬 {data['name']} ({symbol}) 妖股基因:")
                    print(f"  基因评分: {data['gene_score']}/100")
                    print(f"  最大连板: {data['max_continuous_board']}板")
                    print(f"  月涨幅: {data['monthly_max_gain']:.1f}%")
                    print(f"  日均振幅: {data['avg_amplitude']:.1f}%")
                    print(f"  半年涨停: {data['zt_count_6m']}次")
                else:
                    print(f"⚠️  未找到 {symbol} 的基因数据")
            else:
                print("用法: python auto_trader_with_demon_gene.py query 股票代码")
        
        else:
            print(f"❌ 未知命令: {command}")
            print("\n可用命令:")
            print("  build [数量]  - 构建基因库（首次运行）")
            print("  update       - 增量更新基因库")
            print("  report       - 生成妖股日报")
            print("  maintain     - 每日维护（更新+日报）")
            print("  query 代码   - 查询单只股票基因")
    
    else:
        print("\n💡 使用示例:")
        print("  # 首次构建基因库（扫描100只股票测试）")
        print("  python auto_trader_with_demon_gene.py build 100")
        print("")
        print("  # 每日更新")
        print("  python auto_trader_with_demon_gene.py update")
        print("")
        print("  # 生成日报")
        print("  python auto_trader_with_demon_gene.py report")
        print("")
        print("  # 查询单只股票")
        print("  python auto_trader_with_demon_gene.py query 600519")
        print("")
        print("  # 每日维护（推荐收盘后运行）")
        print("  python auto_trader_with_demon_gene.py maintain")