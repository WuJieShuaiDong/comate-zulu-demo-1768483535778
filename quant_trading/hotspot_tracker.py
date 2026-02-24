"""
热点板块追踪器 - 抓住主线，避免接盘

核心功能:
1. 实时追踪板块强度排名
2. 识别热点周期（启动期/加速期/衰退期）
3. 资金流向监控
4. 接盘风险预警

数据源: 东方财富直接HTTP接口 (稳定)
"""

import requests
import pandas as pd
import numpy as np
import datetime
import logging
import json
import os
from collections import defaultdict
from notification import notifier  # 导入通知模块

# 热点追踪数据文件
DATA_DIR = "data"
HOTSPOT_FILE = os.path.join(DATA_DIR, "hotspot_history.json")


class HotspotTracker:
    """热点板块追踪器"""
    
    def __init__(self):
        self.history = self._load_history()
        self.today = datetime.date.today().strftime("%Y-%m-%d")
        
    def _load_history(self):
        """加载历史热点数据"""
        if os.path.exists(HOTSPOT_FILE):
            try:
                with open(HOTSPOT_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"daily_sectors": {}, "sector_stats": {}}
    
    def _save_history(self):
        """保存热点数据"""
        with open(HOTSPOT_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)
    
    def get_sector_ranking(self):
        """
        获取实时板块强度排名 (多数据源自动切换)
        返回: [(板块名, 涨幅, 领涨股, 资金流入, 热度周期), ...]
        """
        # 尝试方案1: 新浪财经行业板块
        results = self._get_sectors_sina()
        if results:
            logging.info(f"✅ 获取板块排名成功(新浪): {len(results)} 个")
            self._update_today_record(results[:10])
            return results
        
        # 尝试方案2: 东方财富
        results = self._get_sectors_eastmoney()
        if results:
            logging.info(f"✅ 获取板块排名成功(东财): {len(results)} 个")
            self._update_today_record(results[:10])
            return results
        
        # 尝试方案3: 使用缓存数据
        cached = self.history.get('daily_sectors', {}).get(self.today, [])
        if cached:
            logging.warning("⚠️ 使用缓存板块数据")
            return cached
        
        logging.error("❌ 所有板块数据源均不可用")
        return []
    
    def _get_sectors_sina(self):
        """新浪财经行业板块接口"""
        try:
            import re
            
            url = "http://vip.stock.finance.sina.com.cn/q/view/newSinaHy.php"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Referer": "http://finance.sina.com.cn/"
            }
            
            resp = requests.get(url, headers=headers, timeout=5)
            resp.encoding = 'gbk'
            content = resp.text
            
            if '{' not in content:
                return []
            
            # 提取JSON部分
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if not match:
                return []
            
            data = json.loads(match.group())
            
            results = []
            for code, info in data.items():
                # 新浪格式: "new_blhy玻璃行业1917.21-0.088-0.51...sh600629...华建集团"
                # 提取中文名称
                name_match = re.search(r'[\u4e00-\u9fa5]+', info)
                if not name_match:
                    continue
                name = name_match.group()
                
                # 提取涨跌幅 (第三个数值，通常是小数如-0.51表示-0.51%)
                numbers = re.findall(r'-?\d+\.?\d*', info)
                if len(numbers) < 3:
                    continue
                
                try:
                    # 第3个数字是涨跌幅（已经是百分比形式）
                    change_pct = float(numbers[2])
                except:
                    change_pct = 0
                
                # 简化强度计算
                strength = 50 + change_pct * 5
                strength = max(0, min(100, strength))
                
                cycle = self._judge_sector_cycle(name, change_pct, strength)
                
                results.append({
                    'name': name,
                    'change_pct': change_pct,
                    'strength': strength,
                    'up_count': 0,
                    'down_count': 0,
                    'leader': '',
                    'leader_pct': 0,
                    'cycle': cycle
                })
            
            results.sort(key=lambda x: x['change_pct'], reverse=True)
            return results[:30]
            
        except Exception as e:
            logging.debug(f"新浪接口失败: {e}")
            return []
    
    def _get_sectors_eastmoney(self):
        """东方财富概念板块接口 - 升级版：加入成交额和资金流向分析"""
        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            # 【新增字段】
            # f104: 上涨家数
            # f105: 下跌家数
            # f128: 领涨股代码
            # f140: 领涨股涨跌幅
            # f62: 成交额 (单位: 元)
            # f136: 资金净流入 (单位: 元)
            params = {
                "pn": 1, "pz": 50, "po": 1, "np": 1,
                "fltt": 2, "invt": 2, "fid": "f62",  # 按成交额排序
                "fs": "m:90+t:3",
                "fields": "f2,f3,f4,f8,f12,f14,f104,f105,f128,f140,f62,f136"
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Referer": "https://quote.eastmoney.com/"
            }
            
            resp = requests.get(url, params=params, headers=headers, timeout=5)
            data = resp.json()
            
            if not data.get('data') or not data['data'].get('diff'):
                return []
            
            results = []
            # 获取所有板块的总成交额，用于计算占比
            total_volume = sum(item.get('f62', 0) or 0 for item in data['data']['diff'])
            
            for item in data['data']['diff'][:50]:  # 扩大到50个候选
                name = item.get('f14', '')
                change_pct = float(item.get('f3', 0) or 0)
                up_count = int(item.get('f104', 0) or 0)
                down_count = int(item.get('f105', 0) or 0)
                leader = item.get('f128', '')
                leader_pct = float(item.get('f140', 0) or 0)
                
                # 【新增】成交额数据
                volume = float(item.get('f62', 0) or 0)  # 单位: 元
                volume_yi = volume / 1e8  # 转换为亿元
                
                # 【新增】资金流向数据
                net_inflow = float(item.get('f136', 0) or 0)  # 单位: 元
                net_inflow_yi = net_inflow / 1e8  # 转换为亿元
                
                # 资金流入率
                inflow_rate = (net_inflow / volume * 100) if volume > 0 else 0
                
                total = up_count + down_count
                strength = (up_count / total * 100) if total > 0 else 50
                
                # 【新增】综合评分算法（更灵活）
                # - 涨跌幅权重 30%
                # - 成交额权重 40%
                # - 资金流向权重 30%
                volume_score = min(100, (volume_yi / 100) * 100) if volume_yi > 0 else 0  # 100亿=满分
                fund_score = min(100, (inflow_rate + 10) * 5) if inflow_rate > -10 else 0  # 流入10%=满分
                change_score = min(100, (change_pct + 5) * 10) if change_pct > -5 else 0  # 涨5%=满分
                
                composite_score = change_score * 0.3 + volume_score * 0.4 + fund_score * 0.3
                
                cycle = self._judge_sector_cycle(name, change_pct, strength)
                
                results.append({
                    'name': name,
                    'change_pct': change_pct,
                    'strength': strength,
                    'up_count': up_count,
                    'down_count': down_count,
                    'leader': leader,
                    'leader_pct': leader_pct,
                    'cycle': cycle,
                    'volume_yi': volume_yi,  # 新增
                    'net_inflow_yi': net_inflow_yi,  # 新增
                    'inflow_rate': inflow_rate,  # 新增
                    'composite_score': composite_score  # 新增
                })
            
            # 按综合评分排序（而不是仅按涨跌幅）
            results.sort(key=lambda x: x['composite_score'], reverse=True)
            return results[:30]
            
        except Exception as e:
            logging.debug(f"东财接口失败: {e}")
            return []
    
    def _judge_sector_cycle(self, sector_name, change_pct, strength):
        """
        判断板块热度周期
        
        启动期(LAUNCH): 首次异动，涨幅适中，值得重点关注
        加速期(SURGE): 连续强势，涨幅扩大，可以跟随
        高潮期(PEAK): 涨幅过大，可能见顶
        衰退期(DECAY): 强度下降，资金撤离，避免接盘
        """
        # 获取该板块近期历史
        recent_days = self._get_sector_recent_history(sector_name, days=5)
        
        if not recent_days:
            # 无历史数据，根据今日表现判断
            if change_pct >= 5:
                return 'PEAK'  # 单日暴涨，可能是高潮
            elif change_pct >= 2:
                return 'LAUNCH'  # 适度上涨，可能是启动
            else:
                return 'NORMAL'
        
        # 计算连续上涨天数
        consecutive_up = 0
        for day_data in recent_days:
            if day_data.get('change_pct', 0) > 0:
                consecutive_up += 1
            else:
                break
        
        # 计算累计涨幅
        total_change = sum(d.get('change_pct', 0) for d in recent_days)
        
        # 判断周期
        if consecutive_up >= 4 or total_change >= 15:
            return 'PEAK'  # 高潮期：连涨4天以上或累计涨幅超15%
        elif consecutive_up >= 2 and change_pct >= 2:
            return 'SURGE'  # 加速期：连涨且今日强势
        elif consecutive_up == 1 and change_pct >= 1.5:
            return 'LAUNCH'  # 启动期：刚开始上涨
        elif strength < 50 or change_pct < 0:
            return 'DECAY'  # 衰退期：板块内下跌股票多
        else:
            return 'NORMAL'
    
    def _get_sector_recent_history(self, sector_name, days=5):
        """获取板块近期历史表现"""
        daily_data = self.history.get('daily_sectors', {})
        result = []
        
        # 获取最近N个交易日的数据
        dates = sorted(daily_data.keys(), reverse=True)[:days]
        
        for date in dates:
            sectors = daily_data.get(date, [])
            for s in sectors:
                if s.get('name') == sector_name:
                    result.append(s)
                    break
        
        return result
    
    def _update_today_record(self, top_sectors):
        """更新今日热点记录"""
        if 'daily_sectors' not in self.history:
            self.history['daily_sectors'] = {}
        
        # 检查是否有新热点出现（对比上次记录）
        old_sectors = self.history['daily_sectors'].get(self.today, [])
        old_names = {s['name'] for s in old_sectors if s['cycle'] in ['LAUNCH', 'SURGE']}
        
        new_names = {s['name'] for s in top_sectors if s['cycle'] in ['LAUNCH', 'SURGE']}
        
        # 如果发现了之前没出现过的新热点
        new_hotspots = new_names - old_names
        if new_hotspots:
            # 筛选出具体信息发送通知
            notify_list = [s for s in top_sectors if s['name'] in new_hotspots]
            if notify_list:
                notifier.notify_hotspot_change(notify_list)
        
        self.history['daily_sectors'][self.today] = top_sectors
        
        # 只保留最近30天数据
        daily_data = self.history['daily_sectors']
        if len(daily_data) > 30:
            dates = sorted(daily_data.keys())
            for old_date in dates[:-30]:
                del daily_data[old_date]
        
        self._save_history()
    
    def get_hot_sectors(self, avoid_peak=True):
        """
        获取值得关注的热点板块
        
        参数:
            avoid_peak: 是否过滤掉高潮期板块（避免接盘）
        
        返回:
            适合介入的板块列表，按优先级排序
        """
        all_sectors = self.get_sector_ranking()
        
        if not all_sectors:
            return []
        
        # 分类
        launch_sectors = []  # 启动期 - 最佳买点
        surge_sectors = []   # 加速期 - 可以跟随
        peak_sectors = []    # 高潮期 - 谨慎
        decay_sectors = []   # 衰退期 - 避免
        
        for s in all_sectors:
            cycle = s['cycle']
            
            if cycle == 'LAUNCH':
                launch_sectors.append(s)
            elif cycle == 'SURGE':
                surge_sectors.append(s)
            elif cycle == 'PEAK':
                peak_sectors.append(s)
            elif cycle == 'DECAY':
                decay_sectors.append(s)
        
        # 输出分析日志
        if launch_sectors:
            names = [s['name'] for s in launch_sectors[:3]]
            logging.info(f"🚀 启动期板块(优先): {', '.join(names)}")
        
        if surge_sectors:
            names = [s['name'] for s in surge_sectors[:3]]
            logging.info(f"📈 加速期板块(跟随): {', '.join(names)}")
        
        if peak_sectors:
            names = [s['name'] for s in peak_sectors[:3]]
            logging.warning(f"⚠️ 高潮期板块(谨慎): {', '.join(names)}")
        
        if decay_sectors:
            names = [s['name'] for s in decay_sectors[:3]]
            logging.warning(f"❌ 衰退期板块(回避): {', '.join(names)}")
        
        # 返回推荐板块
        if avoid_peak:
            return launch_sectors + surge_sectors
        else:
            return launch_sectors + surge_sectors + peak_sectors
    
    def _get_sector_code(self, sector_name):
        """获取板块代码 (从缓存的排名数据中查找)"""
        # 先尝试从今日数据获取
        today_sectors = self.history.get('daily_sectors', {}).get(self.today, [])
        for s in today_sectors:
            if s.get('name') == sector_name:
                return s.get('code', '')
        return ''
    
    def get_sector_stocks(self, sector_name, limit=20):
        """
        获取板块成分股，按强度排序
        
        返回最有潜力的成分股（龙头+补涨机会）
        """
        try:
            # 使用新浪行业板块成分股接口
            stocks = self._get_sector_stocks_sina(sector_name)
            
            if not stocks:
                # 降级：尝试东方财富接口
                stocks = self._get_sector_stocks_eastmoney(sector_name)
            
            if not stocks:
                logging.warning(f"无法获取 {sector_name} 成分股")
                return []
            
            # 计算评分并排序
            for stock in stocks:
                score = 0
                change_pct = stock.get('change_pct', 0)
                turnover = stock.get('turnover', 0)
                
                if 2 <= change_pct <= 5:
                    score += 30
                elif 0 <= change_pct < 2:
                    score += 20
                elif 5 < change_pct <= 7:
                    score += 15
                elif change_pct > 7:
                    score += 5
                
                if 5 <= turnover <= 12:
                    score += 25
                elif 3 <= turnover < 5:
                    score += 15
                elif 12 < turnover <= 20:
                    score += 10
                
                stock['score'] = score
            
            # 按评分排序
            stocks.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            return stocks[:limit]
            
        except Exception as e:
            logging.error(f"获取 {sector_name} 成分股失败: {e}")
            return []
    
    def _get_sector_stocks_sina(self, sector_name):
        """使用新浪接口获取行业板块成分股"""
        import re
        
        try:
            # 行业板块名称到代码的映射 (新浪格式)
            sector_code_map = {
                '酿酒行业': 'hangye_BY3',
                '酒店旅游': 'hangye_JL3',
                '金融行业': 'hangye_JR3',
                '银行': 'hangye_YH3',
                '保险': 'hangye_BX3',
                '证券': 'hangye_ZQ3',
                '房地产': 'hangye_DC3',
                '医药制造': 'hangye_YY3',
                '医疗器械': 'hangye_YL3',
                '家用电器': 'hangye_JD3',
                '食品饮料': 'hangye_SP3',
                '有色金属': 'hangye_YS3',
                '钢铁行业': 'hangye_GT3',
                '煤炭行业': 'hangye_MT3',
                '石油行业': 'hangye_SY3',
                '化工行业': 'hangye_HG3',
                '电力行业': 'hangye_DL3',
                '电子信息': 'hangye_DX3',
                '电子元件': 'hangye_DZ3',
                '通讯行业': 'hangye_TX3',
                '计算机': 'hangye_JI3',
                '软件服务': 'hangye_RJ3',
                '互联网': 'hangye_HL3',
                '传媒娱乐': 'hangye_CM3',
                '汽车行业': 'hangye_QC3',
                '机械行业': 'hangye_JX3',
                '仪器仪表': 'hangye_YQ3',
                '纺织服装': 'hangye_FZ3',
                '造纸印刷': 'hangye_ZZ3',
                '农林牧渔': 'hangye_NY3',
                '建筑建材': 'hangye_JC3',
                '交通运输': 'hangye_JT3',
                '航空航天': 'hangye_HK3',
                '船舶制造': 'hangye_CB3',
                '商业百货': 'hangye_SB3',
                '环保行业': 'hangye_HB3',
                '公用事业': 'hangye_GY3',
            }
            
            # 模糊匹配板块名称
            sector_code = None
            for name, code in sector_code_map.items():
                if name in sector_name or sector_name in name:
                    sector_code = code
                    break
            
            if not sector_code:
                logging.debug(f"未找到 {sector_name} 的板块代码")
                return []
            
            # 获取板块成分股
            url = f"http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"
            params = {
                "page": 1,
                "num": 50,
                "sort": "changepercent",
                "asc": 0,
                "node": sector_code,
                "symbol": "",
                "_s_r_a": "page"
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Referer": "http://finance.sina.com.cn/"
            }
            
            resp = requests.get(url, params=params, headers=headers, timeout=5)
            resp.encoding = 'gbk'
            
            # 解析返回数据 (JSON格式)
            data = resp.json()
            
            if not data:
                return []
            
            results = []
            for item in data[:30]:
                symbol = item.get('symbol', '')[2:]  # 去掉 sh/sz 前缀
                name = item.get('name', '')
                price = float(item.get('trade', 0) or 0)
                change_pct = float(item.get('changepercent', 0) or 0)
                turnover = float(item.get('turnoverratio', 0) or 0)
                
                # 筛选条件
                if price < 3 or price > 100:
                    continue
                if change_pct < -5 or change_pct > 9.9:
                    continue
                
                results.append({
                    'symbol': symbol,
                    'name': name,
                    'change_pct': change_pct,
                    'price': price,
                    'turnover': turnover
                })
            
            logging.info(f"✅ 获取 {sector_name} 成分股: {len(results)} 只")
            return results
            
        except Exception as e:
            logging.debug(f"新浪成分股接口失败 {sector_name}: {e}")
            return []
    
    def _get_sector_stocks_eastmoney(self, sector_name):
        """使用东方财富接口获取行业板块成分股"""
        try:
            # 东方财富行业板块代码映射
            sector_code_map = {
                '酿酒行业': 'BK0477',
                '白酒': 'BK0477',
                '酒店旅游': 'BK0430',
                '金融行业': 'BK0475',
                '银行': 'BK0475',
                '保险': 'BK0474',
                '证券': 'BK0473',
                '房地产': 'BK0451',
                '医药制造': 'BK0465',
                '医疗器械': 'BK0883',
                '家用电器': 'BK0459',
                '食品饮料': 'BK0438',
                '有色金属': 'BK0478',
                '钢铁行业': 'BK0449',
                '煤炭行业': 'BK0437',
                '石油行业': 'BK0481',
                '化工行业': 'BK0428',
                '电力行业': 'BK0432',
                '电子信息': 'BK0448',
                '通讯行业': 'BK0486',
                '计算机': 'BK0447',
                '软件服务': 'BK0490',
                '传媒娱乐': 'BK0426',
                '汽车行业': 'BK0480',
                '机械行业': 'BK0460',
                '纺织服装': 'BK0435',
                '农林牧渔': 'BK0470',
                '建筑建材': 'BK0452',
                '交通运输': 'BK0454',
                '航空航天': 'BK0427',
                '船舶制造': 'BK0427',
            }
            
            # 模糊匹配
            sector_code = None
            for name, code in sector_code_map.items():
                if name in sector_name or sector_name in name:
                    sector_code = code
                    break
            
            if not sector_code:
                return []
            
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                "pn": 1,
                "pz": 50,
                "po": 1,
                "np": 1,
                "fltt": 2,
                "invt": 2,
                "fid": "f3",
                "fs": f"b:{sector_code}",
                "fields": "f2,f3,f8,f12,f14"
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Referer": "https://quote.eastmoney.com/"
            }
            
            resp = requests.get(url, params=params, headers=headers, timeout=5)
            data = resp.json()
            
            if not data.get('data') or not data['data'].get('diff'):
                return []
            
            results = []
            for item in data['data']['diff'][:30]:
                symbol = item.get('f12', '')
                name = item.get('f14', '')
                price = float(item.get('f2', 0) or 0)
                change_pct = float(item.get('f3', 0) or 0)
                turnover = float(item.get('f8', 0) or 0)
                
                if price < 3 or price > 100:
                    continue
                if change_pct < -5 or change_pct > 9.9:
                    continue
                
                results.append({
                    'symbol': symbol,
                    'name': name,
                    'change_pct': change_pct,
                    'price': price,
                    'turnover': turnover
                })
            
            logging.info(f"✅ 获取 {sector_name} 成分股(东财): {len(results)} 只")
            return results
            
        except Exception as e:
            logging.debug(f"东财成分股接口失败 {sector_name}: {e}")
            return []
    
    def _get_stock_kline(self, symbol, count=30):
        """使用腾讯接口获取K线数据"""
        import time
        import json as json_module
        
        code_str = str(symbol)
        if code_str.startswith('6'):
            prefix = 'sh'
        elif code_str.startswith('8') or code_str.startswith('4'):
            prefix = 'bj'
        else:
            prefix = 'sz'
        qq_code = f"{prefix}{code_str}"
        
        url = "http://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        params = {
            "_var": "kline_dayqfq",
            "param": f"{qq_code},day,,,{count},qfq",
            "r": time.time()
        }
        
        try:
            resp = requests.get(url, params=params, timeout=3)
            content = resp.text
            if '=' in content:
                content = content.split('=', 1)[1]
            data_json = json_module.loads(content)
            
            if 'data' not in data_json or qq_code not in data_json['data']:
                return None
            
            stock_data = data_json['data'][qq_code]
            kline_list = stock_data.get('qfqday', stock_data.get('day', []))
            
            if not kline_list:
                return None
            
            # [日期, 开盘, 收盘, 最高, 最低, 成交量]
            clean_list = [item[:6] for item in kline_list]
            df = pd.DataFrame(clean_list, columns=['date', 'open', 'close', 'high', 'low', 'volume'])
            
            for col in ['open', 'close', 'high', 'low', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
        except:
            return None
    
    def _get_stock_industry(self, symbol):
        """
        获取个股所属行业 (使用东方财富接口)
        
        返回: 行业名称字符串，失败返回空字符串
        """
        try:
            # 方法1: 使用东方财富个股详情接口
            code_str = str(symbol)
            if code_str.startswith('6'):
                secid = f"1.{code_str}"
            elif code_str.startswith(('0', '3')):
                secid = f"0.{code_str}"
            elif code_str.startswith(('8', '4')):
                secid = f"0.{code_str}"
            else:
                secid = f"0.{code_str}"
            
            url = "https://push2.eastmoney.com/api/qt/stock/get"
            params = {
                "secid": secid,
                "fields": "f127"  # f127 是所属行业字段
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Referer": "https://quote.eastmoney.com/"
            }
            
            resp = requests.get(url, params=params, headers=headers, timeout=3)
            data = resp.json()
            
            if data.get('data'):
                industry = data['data'].get('f127', '')
                if industry and industry != '-':
                    return industry
            
            # 方法2: 降级使用腾讯接口
            if code_str.startswith('6'):
                qq_code = f"sh{code_str}"
            elif code_str.startswith(('8', '4')):
                qq_code = f"bj{code_str}"
            else:
                qq_code = f"sz{code_str}"
            
            url2 = f"http://qt.gtimg.cn/q={qq_code}"
            resp2 = requests.get(url2, timeout=3)
            resp2.encoding = 'gbk'
            content = resp2.text
            
            # 腾讯接口格式: v_sh600519="1~贵州茅台~600519~...~行业名~..."
            # 行业在第48个字段左右
            if '~' in content:
                parts = content.split('~')
                if len(parts) > 48:
                    industry = parts[48]
                    if industry and industry != '-':
                        return industry
            
            return ''
            
        except Exception as e:
            logging.debug(f"获取 {symbol} 所属行业失败: {e}")
            return ''

    def check_takeover_risk(self, symbol, sector_name=None):
        """
        检查个股的接盘风险 (使用腾讯K线接口)
        
        返回:
            risk_level: 'LOW' / 'MEDIUM' / 'HIGH'
            reason: 风险原因
        """
        try:
            df = self._get_stock_kline(symbol, count=30)
            
            if df is None or df.empty or len(df) < 10:
                return 'MEDIUM', '数据不足'
            
            df = df.tail(20)  # 近20日
            
            # 计算指标
            recent_high = df['high'].max()
            current_price = df['close'].iloc[-1]
            
            # 距离近期高点的位置
            position_pct = (current_price / recent_high - 1) * 100
            
            # 计算连涨天数
            consecutive_up = 0
            for i in range(len(df) - 1, 0, -1):
                if df.iloc[i]['close'] > df.iloc[i-1]['close']:
                    consecutive_up += 1
                else:
                    break
            
            # 计算近5日累计涨幅
            recent_5d_change = 0
            if len(df) >= 6:
                recent_5d_change = (current_price / df.iloc[-6]['close'] - 1) * 100
            
            # 判断风险
            risk_reasons = []
            
            # 高位风险
            if position_pct >= -3:  # 接近或创新高
                risk_reasons.append(f"接近高位({position_pct:.1f}%)")
            
            # 连涨风险
            if consecutive_up >= 5:
                risk_reasons.append(f"连涨{consecutive_up}天")
            elif consecutive_up >= 3:
                risk_reasons.append(f"已涨{consecutive_up}天")
            
            # 短期涨幅过大
            if recent_5d_change >= 25:
                risk_reasons.append(f"5日涨幅{recent_5d_change:.1f}%")
            elif recent_5d_change >= 15:
                risk_reasons.append(f"5日涨幅{recent_5d_change:.1f}%")
            
            # 综合判断
            if len(risk_reasons) >= 2 or (consecutive_up >= 5) or (recent_5d_change >= 25):
                return 'HIGH', '; '.join(risk_reasons)
            elif len(risk_reasons) >= 1:
                return 'MEDIUM', '; '.join(risk_reasons)
            else:
                return 'LOW', '风险可控'
                
        except Exception as e:
            logging.warning(f"检查接盘风险失败 {symbol}: {e}")
            return 'MEDIUM', '检查失败'
    
    def find_best_entry_stocks(self, max_count=10):
        """
        寻找最佳入场机会
        
        策略：
        1. 从启动期和加速期板块中选股
        2. 选择涨幅适中、换手活跃的个股
        3. 过滤掉高接盘风险的个股
        
        返回:
            [(symbol, name, sector, score, reason), ...]
        """
        hot_sectors = self.get_hot_sectors(avoid_peak=True)
        
        if not hot_sectors:
            logging.warning("未找到合适的热点板块")
            return []
        
        all_candidates = []
        
        # 遍历热点板块
        for sector in hot_sectors[:5]:  # 最多看5个板块
            sector_name = sector['name']
            sector_cycle = sector['cycle']
            
            # 获取板块成分股
            stocks = self.get_sector_stocks(sector_name, limit=10)
            
            for stock in stocks:
                symbol = stock['symbol']
                name = stock['name']
                
                # 检查接盘风险
                risk_level, risk_reason = self.check_takeover_risk(symbol, sector_name)
                
                if risk_level == 'HIGH':
                    logging.debug(f"跳过高风险股: {name} ({risk_reason})")
                    continue
                
                # 计算综合得分
                base_score = stock['score']
                
                # 周期加成
                if sector_cycle == 'LAUNCH':
                    cycle_bonus = 20  # 启动期加分
                elif sector_cycle == 'SURGE':
                    cycle_bonus = 10
                else:
                    cycle_bonus = 0
                
                # 风险扣分
                risk_penalty = 10 if risk_level == 'MEDIUM' else 0
                
                final_score = base_score + cycle_bonus - risk_penalty
                
                # 获取股票真实所属行业（而非搜索时的板块名称）
                real_industry = self._get_stock_industry(symbol)
                if not real_industry:
                    real_industry = sector_name  # 获取失败时使用搜索板块作为fallback
                
                all_candidates.append({
                    'symbol': symbol,
                    'name': name,
                    'sector': real_industry,  # 使用真实行业
                    'hot_sector': sector_name,  # 保留热点板块信息
                    'sector_cycle': sector_cycle,
                    'change_pct': stock['change_pct'],
                    'score': final_score,
                    'risk_level': risk_level,
                    'reason': f"{sector_cycle}期 | 风险:{risk_level}"
                })
        
        # 按得分排序
        all_candidates.sort(key=lambda x: x['score'], reverse=True)
        
        # 去重（同一只股票可能在多个板块）
        seen = set()
        unique_candidates = []
        for c in all_candidates:
            if c['symbol'] not in seen:
                seen.add(c['symbol'])
                unique_candidates.append(c)
        
        return unique_candidates[:max_count]


def test_hotspot_tracker():
    """测试热点追踪器"""
    tracker = HotspotTracker()
    
    print("\n=== 板块强度排名 ===")
    sectors = tracker.get_sector_ranking()
    for i, s in enumerate(sectors[:10], 1):
        print(f"{i}. {s['name']}: {s['change_pct']:.2f}% | 强度:{s['strength']:.0f}% | 周期:{s['cycle']}")
    
    print("\n=== 热点板块推荐 ===")
    hot = tracker.get_hot_sectors(avoid_peak=True)
    for s in hot[:5]:
        print(f"  {s['name']} ({s['cycle']}): +{s['change_pct']:.2f}%")
    
    print("\n=== 最佳入场机会 ===")
    candidates = tracker.find_best_entry_stocks(max_count=5)
    for c in candidates:
        print(f"  {c['name']}({c['symbol']}): 评分{c['score']} | {c['sector']} | {c['reason']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_hotspot_tracker()