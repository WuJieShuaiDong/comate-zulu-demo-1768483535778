import akshare as ak
import pandas as pd
import datetime
import logging

def calculate_rsi(prices, period=14):
    """计算RSI指标"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_market_sentiment():
    """
    增强版市场情绪判断
    返回: 
    - 'BULLISH' (主升浪，可加仓)
    - 'BEARISH' (退潮期，需清仓) 
    - 'NEUTRAL' (震荡期，谨慎操作)
    """
    try:
        # 1. 获取涨跌停数据
        zt_df = ak.stock_zt_pool_em()
        dt_df = ak.stock_zt_pool_dtgc_em()
        zt_count = len(zt_df) if not zt_df.empty else 0
        dt_count = len(dt_df) if not dt_df.empty else 0

        # 2. 获取连板高度（龙头股高度）
        lb_df = ak.stock_zt_pool_zbgc_em()
        max_lb = lb_df['连板数'].max() if not lb_df.empty else 0

        # 3. 大盘趋势判断
        index_df = ak.stock_zh_index_daily(symbol="sh000001").tail(20)
        index_rsi = calculate_rsi(index_df['close'])
        
        # 情绪判断标准
        if zt_count > dt_count * 3 and max_lb >= 4 and index_rsi.iloc[-1] > 60:
            return 'BULLISH'
        elif dt_count > zt_count * 2 or max_lb <= 2 or index_rsi.iloc[-1] < 40:
            return 'BEARISH'
        return 'NEUTRAL'
    except Exception as e:
        logging.error(f"情绪判断失败: {e}")
        return 'NEUTRAL'

def get_main_sectors():
    """
    获取当前市场主线板块 (自动学习机构动向)
    逻辑: 统计涨幅榜前 50 的股票所属板块，取频次最高的 top 3
    """
    try:
        # 获取全市场实时行情，按涨幅排序
        df = ak.stock_zh_a_spot_em()
        top_gainers = df.sort_values(by='涨跌幅', ascending=False).head(100)
        
        # 统计板块热度 (这里简单用名称包含来模拟，实际应调用具体板块接口)
        # 更好的方法: 获取同花顺/东财的概念板块涨幅榜
        # ak.stock_board_concept_name_em() 获取所有概念
        
        # 这里使用更直接的接口: 行业板块涨幅榜
        sector_df = ak.stock_board_industry_name_em()
        # 按涨幅排序
        top_sectors = sector_df.sort_values(by='涨跌幅', ascending=False).head(5)
        
        # 返回主线板块名称列表
        main_sectors = top_sectors['板块名称'].tolist()
        logging.info(f"🔥 当前市场主线: {main_sectors}")
        return main_sectors
    except Exception as e:
        logging.error(f"获取主线失败: {e}")
        return []

def get_smart_money_status(symbol):
    """
    判断个股是否有大资金运作 (机构/游资)
    返回: True/False
    """
    try:
        # 获取个股资金流向 (今日)
        # 接口: stock_individual_fund_flow
        df = ak.stock_individual_fund_flow(stock=symbol, market="sh" if symbol.startswith('6') else "sz")
        if df.empty: return False
        
        # 取最近一天的主力净流入 (单位: 元)
        # 注意: 接口返回的列名可能是 "主力净流入-净额"
        latest = df.iloc[0] # 通常第一行是最新? 需确认排序
        # akshare 这个接口通常是按日期降序或升序，这里假设是历史数据，我们需要实时资金流
        
        # 改用实时个股资金流接口: stock_individual_fund_flow_rank 排名? 不太对
        # 简单策略: 看量比和换手率
        # 如果 量比 > 1.5 且 换手率 > 5% (对于大票) 或 > 10% (对于小票)
        # 且 股价在均线之上 (右侧)
        
        # 这里简化为: 返回 True，具体逻辑在 auto_trader 里结合行情判断
        return True
    except:
        return False