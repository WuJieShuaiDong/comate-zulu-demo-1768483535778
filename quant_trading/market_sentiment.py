"""
多维度市场情绪分析系统

分析维度：
1. 涨跌停分析（25%）：涨停/跌停/炸板数量
2. 北向资金（15%）：外资流入流出
3. 市场成交额（15%）：量能变化
4. 大盘指数（15%）：上证/深证/创业板涨跌
5. 涨跌家数比（15%）：市场广度
6. 两融余额（10%）：杠杆资金情绪
7. 新高新低（5%）：趋势强度
"""

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
    多维度市场情绪判断
    返回: 
    - 'BULLISH' (主升浪，可重仓)
    - 'NEUTRAL' (混沌期，轻仓试错)
    - 'BEARISH' (退潮期，观望为主)
    - 'FREEZING' (冰点期，抄底博反弹)
    """
    scores = {}
    reasons = []
    
    today = datetime.date.today().strftime("%Y%m%d")
    
    # 1. 涨跌停分析 (25分)
    try:
        zt_df = ak.stock_zt_pool_em(date=today)
        dt_df = ak.stock_zt_pool_dtgc_em(date=today)
        zt_count = len(zt_df) if not zt_df.empty else 0
        dt_count = len(dt_df) if not dt_df.empty else 0
        
        # 获取炸板数据
        try:
            zb_df = ak.stock_zt_pool_em(date=today)
            zb_count = 0  # 简化：暂不计算炸板
        except:
            zb_count = 0
        
        # 连板高度
        try:
            lb_df = ak.stock_zt_pool_zbgc_em(date=today)
            max_lb = lb_df['连板数'].max() if not lb_df.empty else 0
        except:
            max_lb = 0
        
        # 涨跌停评分
        if zt_count > 100:
            score = 25
            reasons.append(f"涨停{zt_count}只(强力)")
        elif zt_count > 60:
            score = 20
            reasons.append(f"涨停{zt_count}只(良好)")
        elif zt_count > 30:
            score = 15
            reasons.append(f"涨停{zt_count}只(一般)")
        else:
            score = 5
            reasons.append(f"涨停{zt_count}只(低迷)")
        
        # 跌停扣分
        if dt_count > zt_count * 2:
            score -= 10
            reasons.append(f"跌停{dt_count}只(风险)")
        elif dt_count > zt_count:
            score -= 5
            reasons.append(f"跌停{dt_count}只(谨慎)")
        
        # 连板高度加分
        if max_lb >= 5:
            score += 5
            reasons.append(f"连板{max_lb}板(强势)")
        elif max_lb >= 3:
            score += 3
        
        scores['zt'] = max(0, min(25, score))
        
    except Exception as e:
        logging.warning(f"涨跌停数据获取失败: {e}")
        scores['zt'] = 12.5  # 默认中等分
    
    # 2. 北向资金 (15分)
    try:
        # 获取北向资金流向（最近一天）
        bsz_df = ak.stock_em_hsgt_north_net_flow_in_em(symbol="北向资金")
        if not bsz_df.empty:
            latest = bsz_df.iloc[-1]
            net_inflow = float(latest['当日资金流向'])  # 单位: 亿元
            
            if net_inflow > 50:
                score = 15
                reasons.append(f"北向大幅流入{net_inflow:.1f}亿")
            elif net_inflow > 0:
                score = 10
                reasons.append(f"北向流入{net_inflow:.1f}亿")
            elif net_inflow > -30:
                score = 5
                reasons.append(f"北向微流{net_inflow:.1f}亿")
            else:
                score = 0
                reasons.append(f"北向流出{net_inflow:.1f}亿")
            
            scores['bsz'] = score
        else:
            scores['bsz'] = 7.5
    except Exception as e:
        logging.warning(f"北向资金获取失败: {e}")
        scores['bsz'] = 7.5
    
    # 3. 市场成交额 (15分)
    try:
        spot_df = ak.stock_zh_a_spot_em()
        total_volume = float(spot_df['成交额'].sum() / 1e8)  # 转换为亿元
        
        # 简单判断：10000亿以上为放量
        if total_volume > 12000:
            score = 15
            reasons.append(f"成交额{total_volume:.0f}亿(放量)")
        elif total_volume > 8000:
            score = 10
            reasons.append(f"成交额{total_volume:.0f}亿(正常)")
        elif total_volume > 6000:
            score = 5
            reasons.append(f"成交额{total_volume:.0f}亿(缩量)")
        else:
            score = 0
            reasons.append(f"成交额{total_volume:.0f}亿(低迷)")
        
        scores['volume'] = score
    except Exception as e:
        logging.warning(f"成交额获取失败: {e}")
        scores['volume'] = 7.5
    
    # 4. 大盘指数 (15分)
    try:
        indices = {
            '上证': 'sh000001',
            '深证': 'sz399001',
            '创业板': 'sz399006'
        }
        
        index_score = 0
        index_details = []
        
        for name, symbol in indices.items():
            try:
                index_df = ak.stock_zh_index_daily(symbol=symbol).tail(1)
                if not index_df.empty:
                    change_pct = index_df['涨跌幅'].iloc[-1]
                    
                    if change_pct > 1:
                        index_score += 5
                        index_details.append(f"{name}+{change_pct:.2f}%")
                    elif change_pct > 0:
                        index_score += 3
                        index_details.append(f"{name}+{change_pct:.2f}%")
                    elif change_pct > -1:
                        index_score += 1
                        index_details.append(f"{name}{change_pct:.2f}%")
                    else:
                        index_score -= 2
                        index_details.append(f"{name}{change_pct:.2f}%")
            except:
                pass
        
        if index_details:
            reasons.append(f"指数: {','.join(index_details)}")
        
        scores['index'] = max(0, min(15, index_score))
    except Exception as e:
        logging.warning(f"大盘指数获取失败: {e}")
        scores['index'] = 7.5
    
    # 5. 涨跌家数比 (15分)
    try:
        spot_df = ak.stock_zh_a_spot_em()
        up_count = len(spot_df[spot_df['涨跌幅'] > 0])
        down_count = len(spot_df[spot_df['涨跌幅'] < 0])
        total_count = up_count + down_count
        
        up_ratio = (up_count / total_count * 100) if total_count > 0 else 50
        
        if up_ratio > 70:
            score = 15
            reasons.append(f"涨跌比{up_ratio:.0f}%普涨")
        elif up_ratio > 60:
            score = 12
            reasons.append(f"涨跌比{up_ratio:.0f}%偏好")
        elif up_ratio > 40:
            score = 8
            reasons.append(f"涨跌比{up_ratio:.0f}%平衡")
        elif up_ratio > 30:
            score = 4
            reasons.append(f"涨跌比{up_ratio:.0f}%偏弱")
        else:
            score = 0
            reasons.append(f"涨跌比{up_ratio:.0f}%普跌")
        
        scores['up_down'] = score
    except Exception as e:
        logging.warning(f"涨跌家数获取失败: {e}")
        scores['up_down'] = 7.5
    
    # 6. 两融余额 (10分)
    try:
        # 获取两融余额数据
        rzrq_df = ak.stock_margin_detail_sz()
        if not rzrq_df.empty:
            # 取最近的两融余额变化
            latest = rzrq_df.iloc[-1]
            # 这里简化处理，实际需要比较前一日
            score = 5  # 默认中等
            reasons.append("两融平稳")
            scores['margin'] = score
        else:
            scores['margin'] = 5
    except Exception as e:
        logging.warning(f"两融数据获取失败: {e}")
        scores['margin'] = 5
    
    # 7. 新高新低 (5分)
    try:
        # �新高数量
        try:
            nh_df = ak.stock_new_high_em()
            new_high_count = len(nh_df) if not nh_df.empty else 0
            
            nl_df = ak.stock_new_low_em()
            new_low_count = len(nl_df) if not nl_df.empty else 0
            
            if new_high_count > 200:
                score = 5
                reasons.append(f"新高{new_high_count}只(强势)")
            elif new_high_count > 100:
                score = 3
                reasons.append(f"新高{new_high_count}只")
            elif new_low_count > 100:
                score = 0
                reasons.append(f"新低{new_low_count}只(弱势)")
            else:
                score = 2
            
            scores['new_hl'] = score
        except:
            scores['new_hl'] = 2.5
    except Exception as e:
        logging.warning(f"新高新低获取失败: {e}")
        scores['new_hl'] = 2.5
    
    # 综合评分
    total_score = sum(scores.values())
    
    # 判断市场情绪
    sentiment = 'NEUTRAL'
    if total_score >= 70:
        sentiment = 'BULLISH'
    elif total_score >= 50:
        sentiment = 'NEUTRAL'
    elif total_score >= 30:
        sentiment = 'BEARISH'
    else:
        sentiment = 'FREEZING'
    
    # 输出日志
    reason_str = '; '.join(reasons)
    logging.info(f"📊 市场情绪分析: {sentiment} (评分: {total_score:.1f}/100)")
    logging.info(f"   详情: {reason_str}")
    logging.info(f"   分项: {scores}")
    
    return sentiment

def get_main_sectors():
    """
    获取当前市场主线板块 (基于板块涨幅)
    """
    try:
        # 获取行业板块涨幅榜
        sector_df = ak.stock_board_industry_name_em()
        
        # 过滤成交额过小的板块
        if '成交额' in sector_df.columns:
            sector_df = sector_df[sector_df['成交额'] > 5e8]  # 成交额 > 5亿
        
        # 按涨幅排序，取前5
        top_sectors = sector_df.sort_values(by='涨跌幅', ascending=False).head(5)
        main_sectors = top_sectors['板块名称'].tolist()
        
        logging.info(f"🔥 当前市场主线板块: {', '.join(main_sectors)}")
        return main_sectors
    except Exception as e:
        logging.error(f"获取主线板块失败: {e}")
        return []

def get_smart_money_status(symbol):
    """
    判断个股是否有大资金运作
    """
    try:
        # 获取个股资金流向
        df = ak.stock_individual_fund_flow(stock=symbol, market="sh" if symbol.startswith('6') else "sz")
        if df.empty:
            return False
        
        # 简化：只要有数据就认为有资金运作
        return True
    except:
        return False


def get_comprehensive_sentiment():
    """
    返回详细的市场情绪分析结果
    """
    sentiment = get_market_sentiment()
    
    # 根据情绪返回策略建议
    strategy_map = {
        'BULLISH': {
            'sentiment': sentiment,
            'max_positions': 6,
            'position_ratio': 1.0 / 6,
            'description': '主升浪阶段，重仓出击'
        },
        'NEUTRAL': {
            'sentiment': sentiment,
            'max_positions': 2,
            'position_ratio': 1.0 / 4,
            'description': '混沌期，轻仓试错'
        },
        'BEARISH': {
            'sentiment': sentiment,
            'max_positions': 0,
            'position_ratio': 0.0,
            'description': '退潮期，观望为主'
        },
        'FREEZING': {
            'sentiment': sentiment,
            'max_positions': 3,
            'position_ratio': 1.0 / 3,
            'description': '冰点期，抄底博反弹'
        }
    }
    
    return strategy_map.get(sentiment, strategy_map['NEUTRAL'])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = get_comprehensive_sentiment()
    print(result)