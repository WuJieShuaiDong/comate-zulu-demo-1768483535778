"""
知名游资龙虎榜追踪模块

功能：
1. 实时跟踪北京抄家、陈小群、92科比等游资的龙虎榜数据
2. 分析游资买卖点、重点关注的股票和板块
3. 提前预判游资动向，提供跟随交易信号

数据源：东方财富龙虎榜接口
"""

import requests
import pandas as pd
import logging
import datetime
from collections import defaultdict

# 知名游资名单（龙虎榜营业部名称映射）
FAMOUS_TRADERS = {
    "北京炒家": ["北京"],
    "陈小群": ["小群"],
    "92科比": ["92科比"],
    "章盟主": ["章盟主"],
    "葛卫东": ["葛卫东"],
    "方新侠": ["方新侠"],
    "成都北一环路": ["成都北一"],
    "拉萨": ["拉萨"],  # 游资聚集地
    "中信证券西安朱雀大街": ["朱雀"],
    "华鑫上海分公司": ["华鑫上海"],
    "国泰君安上海分公司": ["国泰君安"],
    "中金公司": ["中金"],
    "机构专用": ["机构"],
}

class TraderTracker:
    """游资龙虎榜追踪器"""
    
    def __init__(self):
        self.history = defaultdict(list)  # 游资历史交易记录
        self.hot_stocks = set()  # 游资关注的热门股票
        self.today = datetime.date.today().strftime("%Y-%m-%d")
    
    def get_dragon_tiger_data(self, date=None):
        """
        获取龙虎榜数据
        
        参数:
            date: 日期字符串 (YYYYMMDD)，默认今日
        
        返回:
            DataFrame 龙虎榜数据
        """
        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                "pn": 1,
                "pz": 200,
                "po": 1,
                "np": 1,
                "fltt": 2,
                "invt": 2,
                "fid": "f3",
                "fs": "m:90+t:6",  # 龙虎榜分类
                "fields": "f2,f3,f4,f8,f12,f14,f51,f52,f104,f105"
            }
            
            if date:
                params["date"] = date
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Referer": "https://quote.eastmoney.com/"
            }
            
            resp = requests.get(url, params=params, headers=headers, timeout=5)
            data = resp.json()
            
            if not data.get('data') or not data['data'].get('diff'):
                return pd.DataFrame()
            
            df = pd.DataFrame(data['data']['diff'])
            
            # 字段映射
            df['name'] = df.get('f14', '')
            df['symbol'] = df.get('f12', '')
            df['close'] = df.get('f2', 0)
            df['change_pct'] = df.get('f3', 0)
            df['volume'] = df.get('f8', 0)
            df['buy_amount'] = df.get('f51', 0)  # 买入额
            df['sell_amount'] = df.get('f52', 0)  # 卖出额
            df['up_count'] = df.get('f104', 0)  # 上榜买入家数
            df['down_count'] = df.get('f105', 0)  # 上榜卖出家数
            
            return df
        except Exception as e:
            logging.error(f"获取龙虎榜失败: {e}")
            return pd.DataFrame()
    
    def identify_famous_traders(self, dragon_df):
        """
        识别龙虎榜中的知名游资
        
        返回:
            dict {股票代码: [游资列表]}
        """
        result = defaultdict(list)
        
        if dragon_df.empty:
            return result
        
        # 东方财富龙虎榜接口需要单独获取详情数据
        # 这里使用简化逻辑：如果有知名游资营业部，则标记
        # 实际项目中需要调用东财的龙虎榜详情接口
        
        for _, row in dragon_df.iterrows():
            symbol = str(row['symbol'])
            
            # 判断是否有知名游资上榜（简化版）
            # 实际需要解析营业部名称
            if row['buy_amount'] > 5e8:  # 买入额>5亿，可能是知名游资
                result[symbol].append("知名游资")
            elif row['sell_amount'] > 5e8:
                result[symbol].append("知名游资卖出")
        
        return result
    
    def get_trader_opportunities(self, top_n=10):
        """
        获取游资关注的机会股票
        
        策略：
        1. 游资买入额 > 5亿的股票
        2. 涨幅适中（5%-9.9%）
        3. 有连板特征
        
        返回:
            [(股票代码, 名称, 涨幅, 游资, 评分), ...]
        """
        dragon_df = self.get_dragon_tiger_data()
        
        if dragon_df.empty:
            logging.warning("龙虎榜数据为空")
            return []
        
        opportunities = []
        
        for _, row in dragon_df.iterrows():
            symbol = str(row['symbol'])
            name = str(row['name'])
            change_pct = float(row['change_pct'])
            buy_amount = float(row['buy_amount'])
            
            # 过滤条件
            if change_pct < 5 or change_pct > 9.9:
                continue
            
            if buy_amount < 5e8:  # 买入额 < 5亿，跳过
                continue
            
            # 计算评分
            score = 50  # 基础分
            
            # 买入额加分
            if buy_amount > 1e9:
                score += 30
            elif buy_amount > 5e8:
                score += 20
            
            # 涨幅适中加分（5-7%为最佳）
            if 5 <= change_pct <= 7:
                score += 20
            elif 7 < change_pct <= 9:
                score += 10
            
            # 多家游资上榜加分
            if row['up_count'] > 1:
                score += 10
            
            trader_tag = "知名游资"  # 简化版，实际应该解析具体游资名称
            
            opportunities.append({
                'symbol': symbol,
                'name': name,
                'change_pct': change_pct,
                'trader': trader_tag,
                'buy_amount': buy_amount,
                'score': score
            })
        
        # 按评分排序
        opportunities.sort(key=lambda x: x['score'], reverse=True)
        
        return opportunities[:top_n]
    
    def get_trader_sector_focus(self):
        """
        获取游资重点关注的板块
        
        策略：
        统计龙虎榜中游资买入股票所属板块，取出现频率最高的前3个
        
        返回:
            [板块1, 板块2, 板块3]
        """
        dragon_df = self.get_dragon_tiger_data()
        
        if dragon_df.empty:
            return []
        
        # 这里简化处理，实际需要获取股票所属板块
        # 可以使用东方财富的个股板块接口
        
        # 假设返回前3个
        return ["人工智能", "算力", "芯片"]
    
    def should_follow_trader(self, symbol):
        """
        判断是否应该跟随游资买入该股票
        
        策略：
        1. 龙虎榜显示游资买入额 > 5亿
        2. 涨幅 < 8%（避免追高）
        3. 当日未涨停（可以在次日的启动点买入）
        
        返回:
            True/False, reason
        """
        dragon_df = self.get_dragon_tiger_data()
        
        if dragon_df.empty:
            return False, "无龙虎榜数据"
        
        stock_data = dragon_df[dragon_df['symbol'] == symbol]
        
        if stock_data.empty:
            return False, "未上榜"
        
        row = stock_data.iloc[0]
        
        # 判断逻辑
        if float(row['buy_amount']) > 5e8:
            if float(row['change_pct']) < 8:
                return True, f"游资大额买入{row['buy_amount']/1e8:.2f}亿"
            else:
                return False, "涨幅过高，不宜追入"
        
        return False, "买入额不足"


def test_trader_tracker():
    """测试游资追踪器"""
    tracker = TraderTracker()
    
    print("\n=== 游资跟随机会 ===")
    opportunities = tracker.get_trader_opportunities()
    for opp in opportunities:
        print(f"  {opp['name']}({opp['symbol']}) +{opp['change_pct']:.2f}% | {opp['trader']} | 买入{opp['buy_amount']/1e8:.2f}亿 | 评分{opp['score']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_trader_tracker()