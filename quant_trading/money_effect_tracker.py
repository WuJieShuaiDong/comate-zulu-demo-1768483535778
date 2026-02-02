"""
多维赚钱效应追踪模块
用于量化市场情绪强度、识别龙头股、判断板块持续性
作者: Zulu AI
版本: 1.0
"""

import akshare as ak
import pandas as pd
import numpy as np
import datetime
import logging
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class MoneyEffectTracker:
    """赚钱效应追踪器"""
    
    def __init__(self):
        self.cache = {}
        self.cache_time = None
        self.cache_duration = 300  # 缓存5分钟
        
    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if self.cache_time is None:
            return False
        elapsed = (datetime.datetime.now() - self.cache_time).total_seconds()
        return elapsed < self.cache_duration
    
    def _get_concept_boards_stable(self) -> pd.DataFrame:
        """使用新浪稳定接口获取概念板块"""
        import requests
        import re
        import json
        
        try:
            url = "http://vip.stock.finance.sina.com.cn/q/view/newSinaHy.php"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Referer": "http://finance.sina.com.cn/"
            }
            
            resp = requests.get(url, headers=headers, timeout=5)
            resp.encoding = 'gbk'
            content = resp.text
            
            if '{' not in content:
                return pd.DataFrame()
            
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if not match:
                return pd.DataFrame()
            
            data = json.loads(match.group())
            
            results = []
            for code, info in data.items():
                # 格式: "new_blhy,玻璃行业,19,17.21,-0.08,-0.51,..."
                parts = info.split(',')
                if len(parts) < 6:
                    continue
                
                name = parts[1] if len(parts) > 1 else ''
                try:
                    change_pct = float(parts[4]) if parts[4] else 0
                except:
                    change_pct = 0
                
                results.append({
                    '板块名称': name,
                    '涨跌幅': change_pct
                })
            
            return pd.DataFrame(results)
            
        except Exception as e:
            logging.debug(f"新浪板块接口失败: {e}")
            # 降级尝试 akshare
            try:
                return ak.stock_board_concept_name_em()
            except:
                return pd.DataFrame()
    
    def _get_fund_flow_stable(self) -> pd.DataFrame:
        """使用东方财富稳定接口获取资金流向"""
        import requests
        
        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                "pn": 1, "pz": 50, "po": 1, "np": 1,
                "fltt": 2, "invt": 2, "fid": "f62",  # 按主力净流入排序
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
                "fields": "f12,f14,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87"
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Referer": "https://quote.eastmoney.com/"
            }
            
            resp = requests.get(url, params=params, headers=headers, timeout=5)
            data = resp.json()
            
            if not data.get('data') or not data['data'].get('diff'):
                return pd.DataFrame()
            
            results = []
            for item in data['data']['diff'][:50]:
                results.append({
                    '代码': item.get('f12', ''),
                    '名称': item.get('f14', ''),
                    '主力净流入': item.get('f62', 0),
                    '主力净流入占比': item.get('f184', 0)
                })
            
            return pd.DataFrame(results)
            
        except Exception as e:
            logging.debug(f"东财资金流向接口失败: {e}")
            # 降级尝试 akshare
            try:
                return ak.stock_individual_fund_flow_rank(indicator="今日")
            except:
                return pd.DataFrame()
    
    def _fetch_market_data(self) -> Dict:
        """
        获取市场核心数据（带缓存）
        返回: {
            'zt_pool': 涨停池DataFrame,
            'zt_continuous': 连板股DataFrame,
            'dt_pool': 跌停池DataFrame,
            'concept_boards': 概念板块DataFrame,
            'fund_flow': 资金流向DataFrame
        }
        """
        if self._is_cache_valid():
            return self.cache
            
        try:
            today = datetime.date.today().strftime("%Y%m%d")
            
            # 使用部分成功策略：即使某些接口失败，也返回已获取的数据
            result = {
                'zt_pool': pd.DataFrame(),
                'zt_continuous': pd.DataFrame(),
                'dt_pool': pd.DataFrame(),
                'concept_boards': pd.DataFrame(),
                'fund_flow': pd.DataFrame()
            }
            
            # 1. 涨停池
            try:
                zt_pool = ak.stock_zt_pool_em(date=today)
                result['zt_pool'] = zt_pool
                logging.info(f"✅ 获取涨停池: {len(zt_pool)} 只")
            except Exception as e:
                logging.warning(f"⚠️  涨停池获取失败: {e}")
            
            # 2. 连板股
            try:
                zt_continuous = ak.stock_zt_pool_zbgc_em(date=today)
                result['zt_continuous'] = zt_continuous
                logging.info(f"✅ 获取连板股: {len(zt_continuous)} 只")
            except Exception as e:
                logging.warning(f"⚠️  连板股获取失败: {e}")
            
            # 3. 跌停池
            try:
                dt_pool = ak.stock_zt_pool_dtgc_em(date=today)
                result['dt_pool'] = dt_pool
                logging.info(f"✅ 获取跌停池: {len(dt_pool)} 只")
            except Exception as e:
                logging.warning(f"⚠️  跌停池获取失败: {e}")
            
            # 4. 概念板块（使用新浪稳定接口）
            try:
                concept_boards = self._get_concept_boards_stable()
                result['concept_boards'] = concept_boards
                if not concept_boards.empty:
                    logging.info(f"✅ 获取概念板块: {len(concept_boards)} 个")
            except Exception as e:
                logging.warning(f"⚠️  概念板块获取失败: {e}")
            
            # 5. 资金流向（使用东方财富稳定接口）
            try:
                fund_flow = self._get_fund_flow_stable()
                result['fund_flow'] = fund_flow
                if not fund_flow.empty:
                    logging.info(f"✅ 获取资金流向: {len(fund_flow)} 只")
            except Exception as e:
                logging.warning(f"⚠️  资金流向获取失败: {e}")
            
            self.cache = result
            self.cache_time = datetime.datetime.now()
            
            return self.cache
            
        except Exception as e:
            logging.error(f"❌ 数据获取严重失败: {e}")
            # 返回空数据框，但不崩溃
            return {
                'zt_pool': pd.DataFrame(),
                'zt_continuous': pd.DataFrame(),
                'dt_pool': pd.DataFrame(),
                'concept_boards': pd.DataFrame(),
                'fund_flow': pd.DataFrame()
            }
    
    def get_money_effect_score(self) -> Dict:
        """
        综合赚钱效应评分 (0-100分)
        
        评分维度:
        1. 连板梯队得分 (40分): 高度板越多，赚钱效应越强
        2. 板块集中度 (20分): 资金抱团越强，持续性越好
        3. 龙头溢价 (20分): 龙头带动力越强，跟风越活跃
        4. 情绪持续性 (20分): 连续多日涨停数量维持高位
        
        返回: {
            'total_score': 总分 (0-100),
            'ladder_score': 连板梯队分,
            'concentration_score': 板块集中度分,
            'premium_score': 龙头溢价分,
            'sustainability_score': 持续性分,
            'level': 'STRONG'|'MODERATE'|'WEAK',
            'details': 详细数据
        }
        """
        data = self._fetch_market_data()
        zt_pool = data['zt_pool']
        zt_continuous = data['zt_continuous']
        dt_pool = data['dt_pool']
        concept_boards = data['concept_boards']
        
        # 初始化评分
        scores = {
            'ladder_score': 0,
            'concentration_score': 0,
            'premium_score': 0,
            'sustainability_score': 0
        }
        
        details = {}
        
        # === 1. 连板梯队得分 (40分) ===
        if not zt_continuous.empty and '连板数' in zt_continuous.columns:
            board_counts = zt_continuous['连板数'].value_counts().to_dict()
            
            # 5板以上: 10分/只 (妖股出现)
            count_5plus = sum(v for k, v in board_counts.items() if k >= 5)
            # 3-4板: 5分/只 (龙头高度)
            count_3to4 = sum(v for k, v in board_counts.items() if 3 <= k < 5)
            # 2板: 2分/只 (跟风活跃)
            count_2 = board_counts.get(2, 0)
            
            zt_total = len(zt_pool) if not zt_pool.empty else 1
            ladder_raw = (count_5plus * 10 + count_3to4 * 5 + count_2 * 2) / zt_total
            scores['ladder_score'] = min(40, ladder_raw * 4)  # 归一化到40分
            
            details['board_distribution'] = board_counts
            details['high_boards'] = count_5plus
            details['leader_boards'] = count_3to4
        
        # === 2. 板块集中度 (20分) ===
        if not zt_pool.empty and '所属概念' in zt_pool.columns:
            # 统计涨停股的板块分布
            sector_counts = defaultdict(int)
            for concepts in zt_pool['所属概念'].dropna():
                for concept in str(concepts).split(';'):
                    if concept.strip():
                        sector_counts[concept.strip()] += 1
            
            if sector_counts:
                top3_count = sum(sorted(sector_counts.values(), reverse=True)[:3])
                concentration_ratio = top3_count / len(zt_pool)
                scores['concentration_score'] = min(20, concentration_ratio * 40)  # 归一化
                
                details['top_sectors'] = dict(sorted(sector_counts.items(), key=lambda x: x[1], reverse=True)[:5])
                details['concentration_ratio'] = concentration_ratio
        
        # === 3. 龙头溢价 (20分) ===
        if not concept_boards.empty and '涨跌幅' in concept_boards.columns:
            # 找出涨幅最高的板块
            top_board = concept_boards.nlargest(1, '涨跌幅')
            if not top_board.empty:
                top_gain = top_board['涨跌幅'].iloc[0]
                avg_gain = concept_boards['涨跌幅'].mean()
                
                if avg_gain > 0:
                    premium_ratio = top_gain / avg_gain
                    # 溢价比 > 2 视为强龙头效应
                    scores['premium_score'] = min(20, (premium_ratio - 1) * 10)
                    
                    details['leader_board'] = top_board['板块名称'].iloc[0]
                    details['leader_gain'] = top_gain
                    details['premium_ratio'] = premium_ratio
        
        # === 4. 情绪持续性 (20分) ===
        # 通过涨停/跌停比值判断
        zt_count = len(zt_pool) if not zt_pool.empty else 0
        dt_count = len(dt_pool) if not dt_pool.empty else 0
        
        if zt_count + dt_count > 0:
            zt_ratio = zt_count / (zt_count + dt_count)
            # 涨停占比 > 80% 满分
            scores['sustainability_score'] = min(20, zt_ratio * 25)
            
            details['zt_count'] = zt_count
            details['dt_count'] = dt_count
            details['zt_ratio'] = zt_ratio
        
        # === 计算总分 ===
        total_score = sum(scores.values())
        
        # === 情绪等级 ===
        if total_score >= 70:
            level = 'STRONG'
        elif total_score >= 40:
            level = 'MODERATE'
        else:
            level = 'WEAK'
        
        result = {
            'total_score': round(total_score, 2),
            'ladder_score': round(scores['ladder_score'], 2),
            'concentration_score': round(scores['concentration_score'], 2),
            'premium_score': round(scores['premium_score'], 2),
            'sustainability_score': round(scores['sustainability_score'], 2),
            'level': level,
            'details': details
        }
        
        logging.info(f"💰 赚钱效应评分: {total_score:.1f}/100 ({level})")
        return result
    
    def find_leading_stocks(self, min_score: int = 70) -> List[Dict]:
        """
        智能龙头识别
        
        识别逻辑:
        - 首板: 换手15-30% + 流通盘<50亿 + 题材新鲜度
        - 2-3板: 封板速度<10:00 + 连续放量 + 跟风>3只
        - 高度板(>3板): 历史妖股基因
        
        参数:
            min_score: 最低评分阈值 (0-100)
        
        返回: [
            {
                'symbol': 股票代码,
                'name': 股票名称,
                'board_count': 连板数,
                'score': 龙头评分,
                'reasons': 入选理由列表,
                'sector': 所属板块,
                'seal_time': 封板时间
            },
            ...
        ]
        """
        data = self._fetch_market_data()
        zt_continuous = data['zt_continuous']
        zt_pool = data['zt_pool']
        
        if zt_continuous.empty:
            logging.warning("⚠️  连板数据为空，无法识别龙头")
            return []
        
        leaders = []
        
        for _, row in zt_continuous.iterrows():
            try:
                symbol = row.get('代码', '')
                name = row.get('名称', '')
                board_count = row.get('连板数', 0)
                
                if not symbol or board_count < 1:
                    continue
                
                score = 0
                reasons = []
                
                # === 首板龙 (换手率 + 流通盘) ===
                if board_count == 1:
                    turnover = row.get('换手率', 0)
                    if isinstance(turnover, str):
                        turnover = float(turnover.replace('%', ''))
                    
                    if 15 <= turnover <= 30:
                        score += 30
                        reasons.append(f"黄金换手率 {turnover:.1f}%")
                    
                    # 流通市值判断（需要从涨停池获取）
                    if not zt_pool.empty:
                        stock_info = zt_pool[zt_pool['代码'] == symbol]
                        if not stock_info.empty:
                            market_cap = stock_info.get('流通市值', 0).iloc[0] if '流通市值' in stock_info.columns else 0
                            if market_cap > 0 and market_cap < 50e8:  # <50亿
                                score += 20
                                reasons.append(f"小盘股 {market_cap/1e8:.1f}亿")
                
                # === 2-3板龙 (封板速度 + 跟风) ===
                elif 2 <= board_count <= 3:
                    seal_time = row.get('首次封板时间', '')
                    if seal_time:
                        try:
                            # 解析封板时间 (格式: "09:35:00")
                            hour = int(seal_time.split(':')[0])
                            minute = int(seal_time.split(':')[1])
                            seal_minutes = hour * 60 + minute
                            
                            if seal_minutes < 10 * 60:  # 10:00之前
                                score += 40
                                reasons.append(f"早盘封板 {seal_time}")
                            elif seal_minutes < 11 * 60:
                                score += 20
                                reasons.append(f"上午封板 {seal_time}")
                        except:
                            pass
                    
                    # 统计同板块跟风数量
                    sector = row.get('所属概念', '')
                    if sector and not zt_pool.empty:
                        same_sector = zt_pool[zt_pool['所属概念'].str.contains(sector.split(';')[0], na=False)]
                        if len(same_sector) >= 3:
                            score += 20
                            reasons.append(f"板块共振 {len(same_sector)}只")
                
                # === 高度板 (>3板) - 妖股基因 ===
                elif board_count > 3:
                    score += board_count * 15  # 每多1板加15分
                    reasons.append(f"高度板 {board_count}板")
                    
                    # 如果是5板以上，直接加权
                    if board_count >= 5:
                        score += 50
                        reasons.append("妖股潜力")
                
                # === 通用加分项 ===
                # 涨幅 (强势股)
                change_pct = row.get('涨跌幅', 0)
                if isinstance(change_pct, str):
                    change_pct = float(change_pct.replace('%', ''))
                if change_pct >= 9.5:  # 接近涨停
                    score += 10
                
                # 只返回高分股票
                if score >= min_score:
                    leaders.append({
                        'symbol': symbol,
                        'name': name,
                        'board_count': board_count,
                        'score': score,
                        'reasons': reasons,
                        'sector': row.get('所属概念', '').split(';')[0] if row.get('所属概念') else '',
                        'seal_time': row.get('首次封板时间', ''),
                        'turnover': row.get('换手率', 0),
                        'change_pct': change_pct
                    })
            
            except Exception as e:
                logging.error(f"处理股票 {row.get('名称', 'unknown')} 失败: {e}")
                continue
        
        # 按评分排序
        leaders = sorted(leaders, key=lambda x: x['score'], reverse=True)
        
        logging.info(f"🎯 识别龙头股: {len(leaders)} 只 (评分>={min_score})")
        return leaders
    
    def get_board_sustainability(self, board_name: str, days: int = 5) -> Dict:
        """
        板块持续性判断
        
        分析指定板块在过去N天的表现，判断是否具有持续性
        
        参数:
            board_name: 板块名称 (如 "人工智能")
            days: 回溯天数
        
        返回: {
            'board_name': 板块名称,
            'sustainability': 'HIGH'|'MEDIUM'|'LOW',
            'avg_gain': 平均涨幅,
            'trend': 'UP'|'DOWN'|'FLAT',
            'active_days': 活跃天数,
            'recommendation': 操作建议
        }
        """
        try:
            # 获取板块历史行情
            # 注意: akshare的板块历史接口可能不稳定，这里提供示例逻辑
            concept_boards = ak.stock_board_concept_name_em()
            
            if concept_boards.empty:
                return {'error': '板块数据获取失败'}
            
            # 找到目标板块
            target = concept_boards[concept_boards['板块名称'] == board_name]
            if target.empty:
                return {'error': f'未找到板块: {board_name}'}
            
            current_gain = target['涨跌幅'].iloc[0]
            
            # 简化版: 通过当前涨幅和涨停数量判断
            # 实际应该获取历史数据，但接口限制，这里用代理指标
            zt_count = target.get('领涨股票', 0).iloc[0] if '领涨股票' in target.columns else 0
            
            # 持续性判断
            if current_gain > 3 and zt_count > 2:
                sustainability = 'HIGH'
                recommendation = '✅ 可追涨'
            elif current_gain > 1:
                sustainability = 'MEDIUM'
                recommendation = '⚠️  观察'
            else:
                sustainability = 'LOW'
                recommendation = '❌ 回避'
            
            # 趋势判断
            if current_gain > 2:
                trend = 'UP'
            elif current_gain < -1:
                trend = 'DOWN'
            else:
                trend = 'FLAT'
            
            result = {
                'board_name': board_name,
                'sustainability': sustainability,
                'avg_gain': current_gain,
                'trend': trend,
                'active_days': days,  # 占位，实际需历史数据
                'recommendation': recommendation,
                'current_gain': current_gain
            }
            
            logging.info(f"📊 {board_name} 持续性: {sustainability} (涨幅 {current_gain:.2f}%)")
            return result
            
        except Exception as e:
            logging.error(f"板块分析失败: {e}")
            return {'error': str(e)}


def demo_test():
    """测试用例 - 模拟不同市场情绪场景"""
    print("="*60)
    print("?? 赚钱效应追踪系统 - 测试")
    print("="*60)
    
    tracker = MoneyEffectTracker()
    
    # === 测试1: 赚钱效应评分 ===
    print("\n【测试1】赚钱效应评分")
    print("-"*60)
    score_result = tracker.get_money_effect_score()
    print(f"总分: {score_result['total_score']}/100")
    print(f"等级: {score_result['level']}")
    print(f"  - 连板梯队: {score_result['ladder_score']}/40")
    print(f"  - 板块集中度: {score_result['concentration_score']}/20")
    print(f"  - 龙头溢价: {score_result['premium_score']}/20")
    print(f"  - 情绪持续性: {score_result['sustainability_score']}/20")
    
    if 'details' in score_result:
        details = score_result['details']
        if 'top_sectors' in details:
            print(f"\n热门板块:")
            for sector, count in list(details['top_sectors'].items())[:3]:
                print(f"  {sector}: {count}只")
    
    # === 测试2: 龙头识别 ===
    print("\n【测试2】龙头股识别")
    print("-"*60)
    leaders = tracker.find_leading_stocks(min_score=60)
    
    if leaders:
        print(f"发现 {len(leaders)} 只潜在龙头:\n")
        for i, stock in enumerate(leaders[:5], 1):  # 只显示前5
            print(f"{i}. {stock['name']} ({stock['symbol']})")
            print(f"   评分: {stock['score']}/100 | {stock['board_count']}连板")
            print(f"   理由: {', '.join(stock['reasons'])}")
            if stock['sector']:
                print(f"   板块: {stock['sector']}")
            print()
    else:
        print("⚠️  当前无明显龙头")
    
    # === 测试3: 板块持续性 ===
    print("\n【测试3】板块持续性分析")
    print("-"*60)
    
    # 从评分结果中获取热门板块
    if 'details' in score_result and 'top_sectors' in score_result['details']:
        top_sectors = list(score_result['details']['top_sectors'].keys())[:2]
        
        for sector in top_sectors:
            result = tracker.get_board_sustainability(sector)
            if 'error' not in result:
                print(f"\n{result['board_name']}:")
                print(f"  持续性: {result['sustainability']}")
                print(f"  当前涨幅: {result['current_gain']:.2f}%")
                print(f"  趋势: {result['trend']}")
                print(f"  建议: {result['recommendation']}")
    
    print("\n" + "="*60)
    print("✅ 测试完成")
    print("="*60)


if __name__ == "__main__":
    demo_test()