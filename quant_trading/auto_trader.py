import pandas as pd
import akshare as ak
import time
import datetime
import os
import json
import logging
from abc import ABC, abstractmethod
import random
import requests
from data_provider import get_stock_history_safe
from notification import notifier  # 导入通知模块

try:
    from market_sentiment import get_market_sentiment, get_main_sectors
except ImportError:
    # 如果直接导入失败，使用备用方案
    import importlib.util
    import sys
    current_dir = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location("market_sentiment", os.path.join(current_dir, "market_sentiment.py"))
    market_sentiment_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(market_sentiment_module)
    get_market_sentiment = market_sentiment_module.get_market_sentiment
    get_main_sectors = market_sentiment_module.get_main_sectors

# 导入赚钱效应追踪模块
try:
    from money_effect_tracker import MoneyEffectTracker
    MONEY_EFFECT_AVAILABLE = True
    logging.info("✅ 赚钱效应追踪模块加载成功")
except ImportError:
    MONEY_EFFECT_AVAILABLE = False
    logging.warning("⚠️  money_effect_tracker.py 未找到，将使用传统情绪判断")

# 导入妖股基因识别模块
try:
    from demon_stock_gene import DemonStockGene
    DEMON_GENE_AVAILABLE = True
    logging.info("✅ 妖股基因模块加载成功")
except ImportError:
    DEMON_GENE_AVAILABLE = False
    logging.warning("⚠️  demon_stock_gene.py 未找到，将不使用妖股基因增强")

# 导入热点板块追踪模块
try:
    from hotspot_tracker import HotspotTracker
    HOTSPOT_AVAILABLE = True
    logging.info("✅ 热点板块追踪模块加载成功")
except ImportError:
    HOTSPOT_AVAILABLE = False
    logging.warning("⚠️  hotspot_tracker.py 未找到，将不使用热点追踪增强")

# --- 尝试导入 QMT 库 (防报错处理) ---
try:
    from xtquant import xtdata, xttrader
    from xtquant.xttype import StockAccount
    from xtquant import xtconstant
    QMT_INSTALLED = True
except ImportError:
    QMT_INSTALLED = False
    logging.warning("未检测到 xtquant 库，QMT 实盘模式将不可用")

# --- 配置区 ---
TRADING_MODE = "SIMULATION" # 可选: "SIMULATION" / "REAL_QMT"

DATA_DIR = "data"
ACCOUNT_FILE = os.path.join(DATA_DIR, "account.json")
TRADES_FILE = os.path.join(DATA_DIR, "trades.csv")
LOG_FILE = os.path.join(DATA_DIR, "bot.log")

# --- QMT 专属配置 (请修改这里!) ---
QMT_CONFIG = {
    # path: QMT安装目录/userdata_mini
    "mini_qmt_path": r"D:\国金QMT\userdata_mini", 
    # account: 你的资金账号 (如 '888123456')
    "account_id": "YOUR_ACCOUNT_ID",
    # type: 账号类型 (STOCK: 股票, CREDIT: 信用/两融)
    "account_type": "STOCK" 
}

# 确保数据目录存在
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# 策略参数 (游资风格)
MAX_POSITIONS = 4        # 100万本金，分4只票，每只25万，集中火力
STOP_LOSS_PCT = 0.08     # 游资容忍度稍高，8%止损
TAKE_PROFIT_PCT = 0.30   # 捉妖股，不止盈，断板才走 (代码逻辑中会动态调整)

# 初始化日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# ==============================================================================
# 交易接口基类
# ==============================================================================
class BaseTrader(ABC):
    @abstractmethod
    def buy(self, symbol, name, price, shares, reason): pass
    @abstractmethod
    def sell(self, symbol, price, reason): pass
    @abstractmethod
    def sync_assets(self): pass
    
    @property
    @abstractmethod
    def positions(self): pass

    def log_trade(self, action, symbol, name, price, shares, reason):
        record = {
            'time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'action': action,
            'symbol': symbol,
            'name': name,
            'price': price,
            'shares': shares,
            'amount': price * shares,
            'reason': reason
        }
        file_exists = os.path.exists(TRADES_FILE)
        df = pd.DataFrame([record])
        df.to_csv(TRADES_FILE, mode='a', header=not file_exists, index=False, encoding='utf-8-sig')
        logging.info(f"交易执行[{TRADING_MODE}]: {action} {symbol} {name} @ {price}, 原因: {reason}")

# ==============================================================================
# 1. 模拟交易实现
# ==============================================================================
class VirtualTrader(BaseTrader):
    def __init__(self):
        self.load()
        self.update_market_value()
        self.check_daily_roll()

    def load(self):
        if os.path.exists(ACCOUNT_FILE):
            with open(ACCOUNT_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.cash = data.get('cash', 100000.0)
                self._positions = data.get('positions', {}) 
                self.total_value = data.get('total_value', 100000.0)
                self.initial_capital = data.get('initial_capital', 100000.0)
                self.last_day_value = data.get('last_day_value', 100000.0)
                self.yesterday_pnl = data.get('yesterday_pnl', 0.0)
                self.nav_history = data.get('nav_history', [])
                self.last_update_date = data.get('last_update_date', datetime.date.today().strftime("%Y-%m-%d"))
        else:
            self.cash = 100000.0
            self._positions = {}
            self.total_value = 100000.0
            self.initial_capital = 100000.0
            self.last_day_value = 100000.0
            self.yesterday_pnl = 0.0
            self.nav_history = []
            self.last_update_date = datetime.date.today().strftime("%Y-%m-%d")
            self.sync_assets()

    @property
    def positions(self):
        return self._positions

    def fetch_realtime_prices(self, symbols):
        """使用腾讯接口批量获取实时行情 (稳定且快)，返回 {symbol: {'price': 最新价, 'last_close': 昨收价, 'change_pct': 涨跌幅}}"""
        if not symbols: return {}
        
        # 构造代码列表 (sh600519, sz000001)
        qq_codes = []
        code_map = {}
        for code in symbols:
            s_code = str(code)
            if s_code.startswith('6'): prefix = 'sh'
            elif s_code.startswith('8') or s_code.startswith('4'): prefix = 'bj'
            else: prefix = 'sz'
            q_code = f"{prefix}{s_code}"
            qq_codes.append(q_code)
            code_map[q_code] = s_code
            
        url = f"http://qt.gtimg.cn/q={','.join(qq_codes)}"
        try:
            resp = requests.get(url, timeout=3)
            price_map = {}
            if resp.status_code == 200:
                # 格式: v_sh600519="1~贵州茅台~600519~当前价~昨收~..."
                # 字段: 0:未知, 1:名称, 2:代码, 3:当前价, 4:昨收, ..., 32:涨跌幅(%)
                for line in resp.text.splitlines():
                    if '="' in line:
                        var, val = line.split('="')
                        q_code = var.split('_')[-1]
                        data = val.strip('";').split('~')
                        if len(data) > 32:
                            try:
                                current_price = float(data[3])
                                last_close = float(data[4])
                                change_pct = float(data[32])
                                original_code = code_map.get(q_code)
                                if original_code:
                                    price_map[original_code] = {
                                        'price': current_price,
                                        'last_close': last_close,
                                        'change_pct': change_pct
                                    }
                            except:
                                pass
            return price_map
        except Exception as e:
            logging.warning(f"腾讯接口获取行情失败: {e}")
            return {}

    def update_market_value(self):
        if not self._positions:
            self.total_value = self.cash
            return
        try:
            # 优化: 改用轻量级接口只查询持仓股，解决 RemoteDisconnected 问题
            symbols = list(self._positions.keys())
            price_map = self.fetch_realtime_prices(symbols)
            
            holdings_value = 0.0
            daily_position_pnl = 0.0  # 今日持仓浮动盈亏
            
            for symbol, pos in self._positions.items():
                # 优先使用实时价，获取失败或价格为0则用成本价兜底
                price_info = price_map.get(symbol, {})
                if isinstance(price_info, dict):
                    current_price = price_info.get('price', 0)
                    last_close = price_info.get('last_close', 0)
                else:
                    current_price = 0
                    last_close = 0
                
                if current_price <= 0:
                    current_price = pos['cost']
                
                shares = pos['shares']
                holdings_value += current_price * shares
                
                # 计算今日盈亏 = 持仓数量 × (当前价 - 昨收价)
                if last_close > 0:
                    daily_pnl_per_stock = shares * (current_price - last_close)
                    daily_position_pnl += daily_pnl_per_stock
                
            self.total_value = self.cash + holdings_value
            self.daily_pnl = daily_position_pnl  # 保存今日盈亏
            self.sync_assets()
            logging.info(f"模拟盘市值已更新: ￥{self.total_value:.2f}")
        except Exception as e:
            logging.error(f"更新市值失败: {e}")

    def check_daily_roll(self):
        today = datetime.date.today().strftime("%Y-%m-%d")
        if today != self.last_update_date:
            logging.info(f"执行日切: {self.last_update_date} -> {today}")
            # 昨日盈亏 = 昨日最终净值 - 昨日初始净值（即前天收盘净值）
            # 但我们只存了 last_day_value（前天收盘），所以：
            # yesterday_pnl 应该是 当前加载的 total_value（昨天收盘时的值）- last_day_value（前天收盘）
            # 注意：这里的 self.total_value 已经被 update_market_value 更新为今天的实时值了
            # 我们需要在日切前先保存昨天的收盘净值
            yesterday_close_value = self.total_value  # 这是昨天收盘时的净值（从文件加载）
            self.yesterday_pnl = yesterday_close_value - self.last_day_value
            
            # 记录到历史
            self.nav_history.append({
                "date": self.last_update_date, 
                "total_value": yesterday_close_value, 
                "daily_pnl": self.yesterday_pnl
            })
            
            # 更新基准：今天的起始净值 = 昨天的收盘净值
            self.last_day_value = yesterday_close_value
            self.last_update_date = today
            self.sync_assets()

    def sync_assets(self):
        data = {
            'cash': self.cash,
            'positions': self._positions,
            'total_value': self.total_value,
            'initial_capital': getattr(self, 'initial_capital', 100000.0),
            'last_day_value': getattr(self, 'last_day_value', 100000.0),
            'yesterday_pnl': getattr(self, 'yesterday_pnl', 0.0),
            'daily_pnl': getattr(self, 'daily_pnl', 0.0),  # 新增：今日持仓盈亏
            'nav_history': getattr(self, 'nav_history', []),
            'last_update_date': getattr(self, 'last_update_date', datetime.date.today().strftime("%Y-%m-%d")),
            'update_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(ACCOUNT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def buy(self, symbol, name, price, shares, reason):
        self.load()
        cost = price * shares
        if self.cash >= (cost + 100):
            self.cash -= cost
            if symbol not in self._positions:
                self._positions[symbol] = {'cost': price, 'shares': 0, 'name': name}
            old_shares = self._positions[symbol]['shares']
            old_cost = self._positions[symbol]['cost']
            new_shares = old_shares + shares
            new_cost = (old_cost * old_shares + cost) / new_shares
            self._positions[symbol]['shares'] = new_shares
            self._positions[symbol]['cost'] = new_cost
            self.log_trade("BUY", symbol, name, price, shares, reason)
            # 发送通知
            notifier.notify_trade("买入", symbol, name, price, shares, reason)
            self.sync_assets()
            return True
        else:
            logging.warning(f"资金不足，放弃买入 {symbol}")
            return False

    def sell(self, symbol, price, reason):
        self.load()
        if symbol in self._positions:
            shares = self._positions[symbol]['shares']
            income = price * shares
            self.cash += income
            name = self._positions[symbol]['name']
            del self._positions[symbol]
            self.log_trade("SELL", symbol, name, price, shares, reason)
            # 发送通知
            notifier.notify_trade("卖出", symbol, name, price, shares, reason)
            self.sync_assets()
            return True
        return False

# ==============================================================================
# 2. QMT 实盘交易实现 (RealQMTTrader)
# ==============================================================================
class RealQMTTrader(BaseTrader):
    def __init__(self):
        logging.info(">>> 启动 QMT 实盘模式 <<<")
        if not QMT_INSTALLED:
            raise ImportError("请先安装 xtquant 库！")
            
        self.session_id = int(time.time())
        self.qmt_path = QMT_CONFIG["mini_qmt_path"]
        self.acc = StockAccount(QMT_CONFIG["account_id"], QMT_CONFIG.get("account_type", "STOCK"))
        
        # 创建交易对象
        self.xt_trader = xttrader.XtQuantTrader(self.qmt_path, self.session_id)
        
        # 连接 QMT
        self.xt_trader.start()
        connect_res = self.xt_trader.connect()
        if connect_res == 0:
            logging.info("QMT 连接成功！")
        else:
            logging.error(f"QMT 连接失败，错误码: {connect_res}")
            
        # 订阅账号状态
        self.xt_trader.subscribe(self.acc)
        self._cached_positions = {}
        
        # 初始化同步
        self.sync_assets()

    def _convert_symbol(self, symbol):
        """将 600519 转换为 600519.SH 格式"""
        if symbol.startswith('6'):
            return f"{symbol}.SH"
        else:
            return f"{symbol}.SZ"

    def buy(self, symbol, name, price, shares, reason):
        qmt_code = self._convert_symbol(symbol)
        logging.info(f"[QMT] 正在下单买入: {qmt_code} {shares}股")
        
        # 限价买入 (xtconstant.FIX_PRICE)
        # 也可以用 LATEST_PRICE (最新价), MARKET_PEER_PRICE_PRIORITY (对手价)
        order_id = self.xt_trader.order_stock(
            self.acc, qmt_code, xtconstant.STOCK_BUY, shares, xtconstant.FIX_PRICE, price, "策略买入", name
        )
        
        if order_id > 0:
            logging.info(f"下单成功, 订单号: {order_id}")
            self.log_trade("BUY", symbol, name, price, shares, reason)
            return True
        else:
            logging.error(f"下单失败, 订单号: {order_id}")
            return False

    def sell(self, symbol, price, reason):
        qmt_code = self._convert_symbol(symbol)
        # 获取当前持仓量
        curr_shares = 0
        if symbol in self._cached_positions:
            curr_shares = self._cached_positions[symbol]['shares']
            
        if curr_shares == 0:
            logging.warning(f"无持仓，无法卖出 {symbol}")
            return False
            
        logging.info(f"[QMT] 正在下单卖出: {qmt_code} {curr_shares}股")
        
        # 限价卖出
        order_id = self.xt_trader.order_stock(
            self.acc, qmt_code, xtconstant.STOCK_SELL, curr_shares, xtconstant.FIX_PRICE, price, "策略卖出", symbol
        )
        
        if order_id > 0:
            logging.info(f"下单成功, 订单号: {order_id}")
            self.log_trade("SELL", symbol, "Unknown", price, curr_shares, reason)
            return True
        return False

    @property
    def positions(self):
        return self._cached_positions

    def sync_assets(self):
        """从 QMT 查询真实资产并写入 JSON"""
        try:
            # 1. 查询资产
            assets = self.xt_trader.query_stock_asset(self.acc)
            if assets:
                real_cash = assets.cash
                real_total_value = assets.total_asset
            else:
                logging.warning("未查询到资产信息")
                return

            # 2. 查询持仓
            positions = self.xt_trader.query_stock_positions(self.acc)
            
            # 3. 转换格式
            # positions 是一个 list，每个元素有 stock_code, volume, open_price 等属性
            new_positions = {}
            for p in positions:
                # QMT 返回的 code 是 600519.SH，我们需要去掉后缀给前端
                raw_code = p.stock_code
                simple_code = raw_code.split('.')[0]
                
                # 过滤掉持仓为0的 (已清仓)
                if p.volume > 0:
                    new_positions[simple_code] = {
                        "cost": p.open_price,
                        "shares": p.volume,
                        "name": simple_code # QMT position 对象通常不带名称，前端显示代码即可
                    }
            
            self._cached_positions = new_positions
            
            # 4. 写入文件 (供前端 app.py 展示)
            data = {
                'cash': real_cash,
                'positions': new_positions,
                'total_value': real_total_value,
                'update_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'mode': 'REAL_QMT'
            }
            
            with open(ACCOUNT_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logging.info(f"QMT 资产已同步: 现金 {real_cash:.2f}, 总值 {real_total_value:.2f}")
            
        except Exception as e:
            logging.error(f"QMT 同步失败: {e}")

# --- 策略核心 (已升级: 使用腾讯稳定数据源) ---
def calculate_signals(symbol):
    try:
        # 使用自研的稳定接口 (腾讯数据源)
        df = get_stock_history_safe(symbol, count=120)
        
        if df is None or df.empty or len(df) < 30: 
            return None
            
        # RSI计算
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 布林带
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']
        
        # 成交量
        df['vol_ma5'] = df['volume'].rolling(window=5).mean()
        
        # MACD趋势判断
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['trend_up'] = (df['macd'] > df['signal']).iloc[-1]  # 金叉=趋势向上
        
        latest = df.iloc[-1]
        vol_ratio = 1.0
        if latest['vol_ma5'] > 0: vol_ratio = latest['volume'] / latest['vol_ma5']
            
        return {
            'price': latest['close'], 
            'rsi': latest['rsi'], 
            'bb_lower': latest['bb_lower'], 
            'bb_upper': latest['bb_upper'], 
            'bb_middle': latest['bb_middle'],
            'vol_ratio': vol_ratio,
            'trend_up': latest['trend_up']  # 新增趋势标志
        }
    except Exception as e:
        logging.error(f"计算失败 {symbol}: {e}")
        return None

def check_market_sentiment_enhanced(tracker=None):
    """
    升级版市场情绪判断 (集成赚钱效应追踪) - 新增冰点识别
    返回: {
        'sentiment': 'BULLISH'/'NEUTRAL'/'BEARISH'/'FREEZING',  # 新增冰点期
        'score': 0-100分,
        'max_positions': 建议最大持仓数,
        'position_ratio': 建议单只仓位比例
    }
    """
    if MONEY_EFFECT_AVAILABLE and tracker:
        try:
            # 使用赚钱效应追踪系统
            result = tracker.get_money_effect_score()
            score = result['total_score']
            level = result['level']
            
            # 【核心升级】映射到四档情绪：主升期、混沌期、退潮期、冰点期
            if level == 'STRONG':
                sentiment = 'BULLISH'  # 主升期：重仓出击
                max_pos = 6
                pos_ratio = 1.0 / 6
            elif level == 'MODERATE':
                sentiment = 'NEUTRAL'  # 混沌期：轻仓试错
                max_pos = 2  # 降低为2只，控制风险
                pos_ratio = 1.0 / 4  # 单只仓位25%（轻仓）
            elif score >= 20:
                sentiment = 'BEARISH'  # 退潮期：观望为主
                max_pos = 0
                pos_ratio = 0.0
            else:  # score < 20
                sentiment = 'FREEZING'  # 冰点期：别人割肉我抄底
                max_pos = 3
                pos_ratio = 1.0 / 3
            
            logging.info(f"📊 赚钱效应评分: {score:.1f}/100 ({level}) → {sentiment}")
            return {
                'sentiment': sentiment,
                'score': score,
                'max_positions': max_pos,
                'position_ratio': pos_ratio,
                'details': result.get('details', {})
            }
        except Exception as e:
            logging.error(f"赚钱效应追踪失败，降级为传统方法: {e}")
    
    # 降级方案: 使用原有简单逻辑
    try:
        zt_df = ak.stock_zt_pool_em(date=datetime.date.today().strftime("%Y%m%d"))
        dt_df = ak.stock_zt_pool_dtgc_em(date=datetime.date.today().strftime("%Y%m%d"))
        
        zt_count = len(zt_df) if not zt_df.empty else 0
        dt_count = len(dt_df) if not dt_df.empty else 0
        
        logging.info(f"市场情绪(传统): 涨停 {zt_count} 只, 跌停 {dt_count} 只")
        
        if zt_count > dt_count * 2:
            sentiment = 'BULLISH'
            max_pos = 4
            pos_ratio = 0.25
        elif dt_count > zt_count:
            sentiment = 'BEARISH'
            max_pos = 0
            pos_ratio = 0.0
        else:
            sentiment = 'NEUTRAL'
            max_pos = 3
            pos_ratio = 0.33
        
        return {
            'sentiment': sentiment,
            'score': 50,  # 默认中性分数
            'max_positions': max_pos,
            'position_ratio': pos_ratio,
            'details': {}
        }
    except Exception as e:
        logging.error(f"情绪判断失败: {e}")
        return {
            'sentiment': 'NEUTRAL',
            'score': 50,
            'max_positions': 2,
            'position_ratio': 0.5,
            'details': {}
        }

def check_market_sentiment():
    """兼容旧接口"""
    result = check_market_sentiment_enhanced()
    return result['sentiment']

def is_trading_time():
    """判断当前是否为 A 股连续竞价交易时间 (9:15-11:30, 13:00-15:00)"""
    # 9:15 集合竞价结束，可以获取开盘价和竞价数据
    # 尾盘3分钟(14:57-15:00)集合竞价期间也保留监控
    now = datetime.datetime.now()
    
    # 1. 简单周末判断
    if now.weekday() >= 5: # 5=周六, 6=周日
        return False
        
    # 2. 时间段判断
    # 上午: 09:15 - 11:30 (提前15分钟，9:15集合竞价结束)
    # 下午: 13:00 - 15:00
    current_time = now.time()
    morning_start = datetime.time(9, 15)  # 修改: 从9:30改为9:15
    morning_end = datetime.time(11, 30)
    afternoon_start = datetime.time(13, 0)
    afternoon_end = datetime.time(15, 0)
    
    is_morning = morning_start <= current_time <= morning_end
    is_afternoon = afternoon_start <= current_time <= afternoon_end
    
    # 3. (可选) 节假日判断
    # 如果需要更精准，可以调用 ak.tool_trade_date_hist_sina() 获取日历
    # 但频繁调用接口可能超时，建议仅在每天启动时检查一次，或简化处理
    
    return is_morning or is_afternoon

def dynamic_position_management(sentiment_result):
    """
    动态仓位管理 (升级版)
    参数: sentiment_result = check_market_sentiment_enhanced() 的返回值
    """
    return sentiment_result['max_positions']

def get_dynamic_stop_profit(symbol, cost_price, current_price, sentiment_result, tracker=None, demon_tracker=None):
    """
    动态止盈策略 (妖股基因增强版)
    - 超级妖股(基因≥80): 不设止盈，断板才走 (捕捉10倍妖股)
    - 连板股: 不设止盈，断板才走
    - 强妖股(基因60-79): 提高止盈至40%
    - 普通股: 根据市场情绪动态调整 (20%-50%)
    """
    pct_change = (current_price - cost_price) / cost_price if cost_price > 0 else 0
    
    # 1. 检查妖股基因 (最高优先级)
    if DEMON_GENE_AVAILABLE and demon_tracker:
        try:
            gene_info = demon_tracker.get_gene_score(symbol)
            if gene_info:
                gene_score = gene_info.get('gene_score', 0)
                
                # 超级妖股: 不设止盈
                if gene_score >= 80:
                    logging.info(f"🔥 {symbol} 为超级妖股(基因{gene_score:.0f}分)，采用断板卖出策略")
                    return None
                
                # 强妖股: 提高止盈阈值
                elif gene_score >= 60:
                    logging.info(f"✨ {symbol} 为强妖股(基因{gene_score:.0f}分)，止盈阈值提高至40%")
                    return 0.40
        except Exception as e:
            logging.warning(f"查询妖股基因失败: {e}")
    
    # 2. 检查是否为连板股
    is_continuous_board = False
    if MONEY_EFFECT_AVAILABLE and tracker:
        try:
            leaders = tracker.find_leading_stocks(min_score=60)
            for stock in leaders:
                if stock['symbol'] == symbol and stock['board_count'] >= 2:
                    is_continuous_board = True
                    break
        except:
            pass
    
    if is_continuous_board:
        logging.info(f"📍 {symbol} 为连板股，采用断板卖出策略")
        return None
    
    # 3. 普通股: 根据市场情绪动态止盈
    sentiment = sentiment_result['sentiment']
    if sentiment == 'BULLISH':
        return 0.50  # 强势市场50%
    elif sentiment == 'NEUTRAL':
        return 0.30  # 震荡市场30%
    else:
        return 0.20  # 弱势市场20%

def run_bot():
    # 环境自适应检查
    current_mode = TRADING_MODE
    if current_mode == "REAL_QMT" and not QMT_INSTALLED:
        logging.error("❌ 检测到当前环境不支持 QMT (可能是 Mac/Linux 或未安装 xtquant)")
        logging.warning("⚠️ 自动降级为 [模拟交易模式] (SIMULATION) 以确保程序运行")
        current_mode = "SIMULATION"
        
    if current_mode == "REAL_QMT":
        try:
            trader = RealQMTTrader()
        except Exception as e:
            logging.error(f"QMT 初始化失败: {e}")
            logging.warning("⚠️ 降级为模拟模式")
            trader = VirtualTrader()
            current_mode = "SIMULATION"
    else:
        trader = VirtualTrader()
    
    # 初始化赚钱效应追踪器
    money_tracker = None
    if MONEY_EFFECT_AVAILABLE:
        try:
            money_tracker = MoneyEffectTracker()
            logging.info("?? 赚钱效应追踪器已激活")
        except Exception as e:
            logging.warning(f"赚钱效应追踪器初始化失败: {e}")
    
    # 初始化妖股基因追踪器
    demon_gene_tracker = None
    if DEMON_GENE_AVAILABLE:
        try:
            demon_gene_tracker = DemonStockGene()
            gene_count = len(demon_gene_tracker.gene_db)
            if gene_count > 0:
                logging.info(f"🧬 妖股基因追踪器已激活 (基因库: {gene_count} 只)")
            else:
                logging.warning("⚠️  妖股基因库为空，建议运行：python3 -c \"from demon_stock_gene import DemonStockGene; DemonStockGene().build_gene_database(max_stocks=100)\"")
        except Exception as e:
            logging.warning(f"妖股基因追踪器初始化失败: {e}")
    
    # 初始化热点板块追踪器
    hotspot_tracker = None
    if HOTSPOT_AVAILABLE:
        try:
            hotspot_tracker = HotspotTracker()
            logging.info("🔥 热点板块追踪器已激活 (自动识别主线+避免接盘)")
        except Exception as e:
            logging.warning(f"热点板块追踪器初始化失败: {e}")
            
    logging.info(f"=== 自动交易机器人启动 (当前模式: {current_mode}) ===")
    
    # 状态缓存
    last_sentiment = None
    
    while True:
        try:
            now = datetime.datetime.now()
            
            # 在交易时间段内才运行策略
            if is_trading_time():
                # 每一轮都同步最新资产
                trader.sync_assets()
                logging.info(f"--- 扫描开始 {now.strftime('%H:%M:%S')} ---")
                
                # 0. 判断市场情绪 (升级版: 多维赚钱效应)
                sentiment_result = check_market_sentiment_enhanced(money_tracker)
                sentiment = sentiment_result['sentiment']
                score = sentiment_result['score']
                
                # 检测情绪突变并通知
                if last_sentiment is not None and sentiment != last_sentiment:
                    notifier.notify_sentiment_change(last_sentiment, sentiment, score)
                last_sentiment = sentiment
                
                logging.info(f"📊 市场情绪: {sentiment} (评分: {score:.1f}/100)")
                
                # 1. 卖出检查
                current_positions = list(trader.positions.keys())
                
                # 1.1 如果是退潮期，强制清仓所有持仓 (暂时禁用，改为停止买入)
                if sentiment == 'BEARISH':
                    logging.warning("🌊 检测到市场退潮，暂停买入操作！")
                    # logging.warning("🌊 检测到市场退潮，执行全仓清空策略！")
                    # for symbol in current_positions:
                    #     pos = trader.positions[symbol]
                    #     res = calculate_signals(symbol)
                    #     if res:
                    #         trader.sell(symbol, res['price'], "市场退潮，强制清仓")
                    
                    # 即使是退潮期，也执行正常的止盈止损检查
                    for symbol in current_positions:
                        pos = trader.positions[symbol]
                        res = calculate_signals(symbol)
                        if res:
                            # 仅执行止损检查
                            current_price = res['price']
                            cost_price = pos['cost']
                            pct_change = (current_price - cost_price) / cost_price if cost_price > 0 else 0
                            if pct_change <= -STOP_LOSS_PCT:
                                trader.sell(symbol, current_price, f"止损 ({pct_change*100:.2f}%)")

                else:
                    # 正常的止盈止损逻辑 (集成动态止盈)
                    for symbol in current_positions:
                        pos = trader.positions[symbol]
                        res = calculate_signals(symbol)
                        if res:
                            current_price = res['price']
                            cost_price = pos['cost']
                            pct_change = (current_price - cost_price) / cost_price if cost_price > 0 else 0
                            
                            sell_reason = None
                            
                            # 止损逻辑保持不变
                            if pct_change <= -STOP_LOSS_PCT:
                                sell_reason = f"止损 ({pct_change*100:.2f}%)"
                            else:
                                # 动态止盈逻辑（妖股基因增强版）
                                dynamic_take_profit = get_dynamic_stop_profit(
                                    symbol, cost_price, current_price, 
                                    sentiment_result, money_tracker, demon_gene_tracker
                                )
                                
                                if dynamic_take_profit is None:
                                    # 连板股，检查是否断板
                                    if res['rsi'] > 80 and res['price'] < res['bb_middle']:
                                        sell_reason = "连板股断板信号"
                                elif pct_change >= dynamic_take_profit:
                                    sell_reason = f"动态止盈 ({pct_change*100:.2f}% >= {dynamic_take_profit*100:.0f}%)"
                                
                                # 技术逃顶
                                if sell_reason is None and res['price'] > res['bb_upper'] and res['rsi'] > 70:
                                    sell_reason = "技术逃顶"
                                
                            if sell_reason:
                                trader.sell(symbol, current_price, sell_reason)
                
                # 2. 买入扫描 (优先龙头股 + 主线跟随)
                max_pos = dynamic_position_management(sentiment_result)
                current_pos_count = len(trader.positions)
                
                if current_pos_count < max_pos:
                    log_msg = {
                        'BULLISH': "🔥 市场主升浪，开启激进买入模式 (仓位上限: {})",
                        'BEARISH': "❄️ 市场退潮期，禁止买入",
                        'NEUTRAL': "🟡 市场震荡期，谨慎买入 (仓位上限: {})",
                        'FREEZING': "❄️ 冰点期，抄底博反弹 (仓位上限: {})"
                    }[sentiment].format(max_pos)
                    logging.info(log_msg)
                    
                    if sentiment != 'BEARISH':
                        # 【冰点期特殊策略】别人割肉，我们抄底
                        if sentiment == 'FREEZING':
                            logging.info("❄️ 冰点期策略启动：寻找超跌龙头抄底机会")
                        
                        # 【核心升级】优先扫描龙头股 + 妖股基因增强
                        priority_symbols = []
                        enhanced_leaders = []
                        
                        if MONEY_EFFECT_AVAILABLE and money_tracker:
                            try:
                                # 根据市场强度调整龙头评分阈值
                                min_score = 70 if score >= 70 else 60
                                leaders = money_tracker.find_leading_stocks(min_score=min_score)
                                
                                if leaders:
                                    logging.info(f"🎯 识别到 {len(leaders)} 只龙头股 (评分≥{min_score})")
                                    
                                    # 叠加妖股基因评分
                                    if DEMON_GENE_AVAILABLE and demon_gene_tracker:
                                        for stock in leaders:
                                            symbol = stock['symbol']
                                            base_score = stock['score']
                                            
                                            # 获取妖股基因评分
                                            gene_info = demon_gene_tracker.get_gene_score(symbol)
                                            gene_score = gene_info.get('gene_score', 0) if gene_info else 0
                                            
                                            # 基因加成规则
                                            gene_bonus = 0
                                            if gene_score >= 80:
                                                gene_bonus = 20  # 超级妖股基因
                                                stock['is_super_demon'] = True
                                            elif gene_score >= 60:
                                                gene_bonus = 10  # 强妖股基因
                                                stock['is_demon'] = True
                                            
                                            # 更新总评分
                                            stock['original_score'] = base_score
                                            stock['gene_score'] = gene_score
                                            stock['final_score'] = base_score + gene_bonus
                                            enhanced_leaders.append(stock)
                                        
                                        # 按最终评分重新排序
                                        enhanced_leaders.sort(key=lambda x: x['final_score'], reverse=True)
                                        priority_symbols = [s['symbol'] for s in enhanced_leaders[:10]]
                                        
                                        # 输出前3只增强龙头详情
                                        logging.info("🧬 妖股基因增强后的龙头排行：")
                                        for i, stock in enumerate(enhanced_leaders[:3], 1):
                                            gene_tag = ""
                                            if stock.get('is_super_demon'):
                                                gene_tag = " [超级妖股🔥]"
                                            elif stock.get('is_demon'):
                                                gene_tag = " [妖股基因✨]"
                                            
                                            logging.info(
                                                f"  {i}. {stock['name']}({stock['symbol']}) "
                                                f"总分:{stock['final_score']:.0f} "
                                                f"(龙头:{stock['original_score']:.0f} + 基因:{stock['gene_score']:.0f}){gene_tag}"
                                            )
                                    else:
                                        # 无妖股基因模块，使用原始龙头列表
                                        enhanced_leaders = leaders
                                        priority_symbols = [s['symbol'] for s in leaders[:10]]
                                        
                                        for i, stock in enumerate(leaders[:3], 1):
                                            logging.info(
                                                f"  {i}. {stock['name']}({stock['symbol']}) "
                                                f"评分:{stock['score']:.0f} 连板:{stock['board_count']}板"
                                            )
                            except Exception as e:
                                logging.warning(f"龙头识别失败: {e}")
                        
                        # 2.1 优先买入龙头股
                        for symbol in priority_symbols:
                            if current_pos_count >= max_pos:
                                break
                            if symbol in trader.positions:
                                continue
                            
                            try:
                                # 获取实时行情
                                spot_df = ak.stock_zh_a_spot_em()
                                stock_info = spot_df[spot_df['代码'] == symbol]
                                
                                if stock_info.empty:
                                    continue
                                
                                row = stock_info.iloc[0]
                                name = str(row['名称'])
                                
                                signals = calculate_signals(symbol)
                                if signals and signals['trend_up']:
                                    # 龙头股可适当放宽买入条件
                                    logging.info(f"✨ 龙头股买入机会: {name}")
                                    
                                    # 根据仓位比例计算金额
                                    target_pos_cash = trader.total_value * sentiment_result['position_ratio']
                                    buy_price = signals['price']
                                    shares = int(target_pos_cash / buy_price / 100) * 100
                                    
                                    if shares >= 100:
                                        reason = f"龙头跟随 (赚钱效应:{score:.1f}分)"
                                        if trader.buy(symbol, name, buy_price, shares, reason):
                                            current_pos_count += 1
                                            
                                time.sleep(0.5)
                            except Exception as e:
                                logging.error(f"龙头股 {symbol} 处理失败: {e}")
                        
                        # 2.2 【核心升级】使用热点追踪器寻找最佳入场机会（避免接盘）
                        if current_pos_count < max_pos and HOTSPOT_AVAILABLE and hotspot_tracker:
                            try:
                                logging.info("🔍 启动热点追踪扫描...")
                                
                                # 获取热点板块分析
                                hot_sectors = hotspot_tracker.get_hot_sectors(avoid_peak=True)
                                
                                if hot_sectors:
                                    # 显示当前热点周期
                                    for s in hot_sectors[:3]:
                                        cycle_emoji = {'LAUNCH': '🚀', 'SURGE': '📈'}.get(s['cycle'], '⚪')
                                        logging.info(f"  {cycle_emoji} {s['name']}: +{s['change_pct']:.2f}% ({s['cycle']}期)")
                                
                                # 获取最佳入场机会（已过滤高接盘风险）
                                best_entries = hotspot_tracker.find_best_entry_stocks(max_count=10)
                                
                                if best_entries:
                                    logging.info(f"🎯 热点追踪器识别到 {len(best_entries)} 只低风险机会")
                                    
                                    for candidate in best_entries:
                                        if current_pos_count >= max_pos:
                                            break
                                        
                                        symbol = candidate['symbol']
                                        name = candidate['name']
                                        sector = candidate['sector']
                                        sector_cycle = candidate['sector_cycle']
                                        risk_level = candidate['risk_level']
                                        
                                        # 跳过已持仓和龙头列表中的股票
                                        if symbol in trader.positions:
                                            continue
                                        if symbol in priority_symbols:
                                            continue
                                        
                                        # 技术面验证
                                        signals = calculate_signals(symbol)
                                        if signals and signals['trend_up']:
                                            # 【量价关系强化】无量股票坚决不碰
                                            vol_ratio = signals.get('vol_ratio', 0)
                                            if vol_ratio < 1.2:
                                                logging.debug(f"跳过无量股: {name} (量比{vol_ratio:.2f})")
                                                continue
                                            
                                            # 启动期板块优先级更高
                                            if sector_cycle == 'LAUNCH':
                                                logging.info(f"🚀 启动期机会: {name} | 板块:{sector} | 量比:{vol_ratio:.2f} | 风险:{risk_level}")
                                            else:
                                                logging.info(f"📈 加速期机会: {name} | 板块:{sector} | 量比:{vol_ratio:.2f} | 风险:{risk_level}")
                                            
                                            target_pos_cash = trader.total_value * sentiment_result['position_ratio']
                                            buy_price = signals['price']
                                            shares = int(target_pos_cash / buy_price / 100) * 100
                                            
                                            if shares >= 100:
                                                reason = f"热点主线 ({sector}|{sector_cycle}期|量比{vol_ratio:.1f})"
                                                if trader.buy(symbol, name, buy_price, shares, reason):
                                                    current_pos_count += 1
                                        
                                        time.sleep(0.3)
                                else:
                                    logging.info("⚠️ 热点追踪器未找到低风险入场机会")
                                    
                            except Exception as e:
                                logging.warning(f"热点追踪扫描失败: {e}")
                        
                        # 2.3 如果热点追踪没填满仓位，降级到传统主线扫描
                        if current_pos_count < max_pos:
                            main_sectors = get_main_sectors()
                            logging.info(f"📋 降级扫描主线板块: {main_sectors}")
                            
                            spot_df = ak.stock_zh_a_spot_em()
                            spot_df.rename(columns={
                                '涨跌幅': 'change_pct', 
                                '量比': 'vol_ratio', 
                                '最新价': 'price', 
                                '总市值': 'market_cap', 
                                '板块名称': 'sector'
                            }, inplace=True)
                            
                            # 板块筛选
                            if 'sector' in spot_df.columns and main_sectors:
                                spot_df = spot_df[spot_df['sector'].isin(main_sectors)]
                            
                            # 基础过滤
                            min_cap = 5000000000  # 50亿
                            mask = (
                                (spot_df['price'] > 0) & 
                                (spot_df['market_cap'] > min_cap) & 
                                (spot_df['vol_ratio'] > 1.5) &
                                (spot_df['change_pct'] > -3.0) & 
                                (spot_df['change_pct'] < 7.0)
                            )
                            candidates = spot_df[mask].sort_values(by='vol_ratio', ascending=False)
                            
                            logging.info(f"符合主线条件的候选股: {len(candidates)}")
                            scan_count = 0
                            
                            for _, row in candidates.iterrows():
                                if current_pos_count >= max_pos:
                                    break
                                if scan_count >= 30:
                                    break
                                
                                symbol = str(row['代码'])
                                name = str(row['名称'])
                                
                                if symbol in trader.positions:
                                    continue
                                if symbol in priority_symbols:  # 避免重复扫描
                                    continue
                                
                                # 【新增】接盘风险检查
                                if HOTSPOT_AVAILABLE and hotspot_tracker:
                                    try:
                                        risk_level, risk_reason = hotspot_tracker.check_takeover_risk(symbol)
                                        if risk_level == 'HIGH':
                                            logging.debug(f"跳过高风险股: {name} ({risk_reason})")
                                            continue
                                    except:
                                        pass
                                
                                signals = calculate_signals(symbol)
                                scan_count += 1
                                
                                if signals:
                                    is_right_side = signals['trend_up'] and (signals['price'] > signals['bb_lower'])
                                    
                                    if is_right_side:
                                        logging.info(f"🎯 发现主线机会: {name} ({row.get('sector','')})")
                                        
                                        target_pos_cash = trader.total_value * sentiment_result['position_ratio']
                                        buy_price = signals['price']
                                        shares = int(target_pos_cash / buy_price / 100) * 100
                                        
                                        if shares >= 100:
                                            reason = f"主线跟随 (板块:{row.get('sector','未知')})"
                                            if trader.buy(symbol, name, buy_price, shares, reason):
                                                current_pos_count += 1
                                
                                time.sleep(0.5)
            else:
                logging.info("休市中...")
            
            time.sleep(300)
            
        except Exception as e:
            logging.error(f"异常: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_bot()