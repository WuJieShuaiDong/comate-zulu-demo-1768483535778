import streamlit as st
import pandas as pd
import akshare as ak
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import numpy as np
import os
import json
import time
import requests
from demon_stock_gene import DemonStockGene

# 导入热点追踪器
try:
    from hotspot_tracker import HotspotTracker
    HOTSPOT_AVAILABLE = True
except ImportError:
    HOTSPOT_AVAILABLE = False

# --- 页面配置 ---
st.set_page_config(page_title="高阶量化交易系统", layout="wide", page_icon="🚀")

# --- 访问认证 (外网部署时启用) ---
# 设置为 True 启用密码保护，False 关闭
ENABLE_AUTH = os.environ.get('ENABLE_AUTH', 'false').lower() == 'true'
AUTH_PASSWORD = os.environ.get('AUTH_PASSWORD', 'quant2026')

if ENABLE_AUTH:
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.title("🔐 量化交易系统 - 登录")
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            password = st.text_input("请输入访问密码", type="password", key="login_pwd")
            
            if st.button("🔓 登录", use_container_width=True):
                if password == AUTH_PASSWORD:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("❌ 密码错误，请重试")
            
            st.caption("💡 提示: 默认密码可通过环境变量 AUTH_PASSWORD 配置")
        
        st.stop()

st.title("🚀 A股高阶量化交易系统 (游资情绪版)")

# --- 功能模式选择 ---
mode = st.sidebar.radio("选择功能模块", [
    "🤖 自动化实盘监控 (AutoBot)",
    "🔥 进阶波段策略 (回测)",
    "?? 基础趋势回测 (双均线)"
])

# --- 侧边栏：高级数据校准 ---
with st.sidebar.expander("🛠️ 账户数据校准 (高级)"):
    st.caption("如果数据不准，可在此手动修正基准值")
    data_dir = "data"
    account_file = os.path.join(data_dir, "account.json")
    
    if os.path.exists(account_file):
        try:
            with open(account_file, 'r', encoding='utf-8') as f:
                acc_calib = json.load(f)
                
            new_init = st.number_input("修正初始资金", value=acc_calib.get('initial_capital', 1000000.0))
            new_last = st.number_input("修正昨日净值 (影响今日盈亏)", value=acc_calib.get('last_day_value', 1000000.0))
            new_yest_pnl = st.number_input("修正昨日盈亏 (仅展示)", value=acc_calib.get('yesterday_pnl', 0.0))
            
            st.markdown("---")
            st.caption("持仓成本修正 (慎用)")
            
            positions_calib = acc_calib.get('positions', {})
            new_costs = {}
            for sym, pos in positions_calib.items():
                cost_val = float(pos.get('cost', 0.0))
                c1, c2 = st.columns([1, 2])
                c1.text(f"{pos.get('name', sym)}")
                new_c = c2.number_input(f"修正成本 ({sym})", value=cost_val, key=f"cost_{sym}")
                new_costs[sym] = new_c

            if st.button("💾 保存全部修正"):
                try:
                    with open(account_file, 'r', encoding='utf-8') as f:
                        latest_acc = json.load(f)
                    
                    latest_acc['initial_capital'] = new_init
                    latest_acc['last_day_value'] = new_last
                    latest_acc['yesterday_pnl'] = new_yest_pnl
                    
                    for sym, new_c in new_costs.items():
                        if sym in latest_acc.get('positions', {}):
                            latest_acc['positions'][sym]['cost'] = new_c
                            
                    with open(account_file, 'w', encoding='utf-8') as f:
                        json.dump(latest_acc, f, ensure_ascii=False, indent=2)
                    st.success("数据已修正！请刷新页面。")
                except Exception as ex:
                    st.error(f"保存失败: {ex}")
        except Exception as e:
            st.error(f"读取失败: {e}")

# --- 通用工具函数 ---
@st.cache_data(ttl=3600)
def get_stock_data(symbol, start_date, end_date):
    """获取数据并计算核心指标"""
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    try:
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_str, end_date=end_str, adjust="qfq")
        if df.empty: return None
        df.rename(columns={"日期": "date", "开盘": "open", "收盘": "close", "最高": "high", "最低": "low", "成交量": "volume"}, inplace=True)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        return df
    except Exception as e:
        st.error(f"数据异常: {e}")
        return None

def get_realtime_quotes(stock_list):
    """
    获取实时行情 (腾讯财经接口 - 每次刷新实时获取)
    请求地址: http://qt.gtimg.cn/q=sh600519,sz000001
    """
    if not stock_list:
        return {}
    
    price_map = {}
    
    # 1. 构造腾讯接口需要的代码格式 (sh600519, sz000001)
    qq_codes = []
    code_map = {} # 映射 qq_code -> original_code
    
    for code in stock_list:
        code_str = str(code)
        # 腾讯接口对北交所的支持可能需要确认，目前 sh/sz 是稳的
        if code_str.startswith('6'):
            q_code = f"sh{code_str}"
        elif code_str.startswith('8') or code_str.startswith('4'):
            q_code = f"bj{code_str}" # 尝试兼容北交所
        else:
            q_code = f"sz{code_str}" # 00, 30 开头
            
        qq_codes.append(q_code)
        code_map[q_code] = code_str
        
    # 2. 批量请求
    try:
        url = f"http://qt.gtimg.cn/q={','.join(qq_codes)}"
        resp = requests.get(url, timeout=3)
        
        if resp.status_code == 200:
            # 解析返回数据
            # 格式: v_sh600519="1~贵州茅台~600519~1347.70~..."
            text = resp.text
            for line in text.splitlines():
                if '="' in line:
                    left, right = line.split('="')
                    q_code = left.split('_')[-1] # v_sh600519 -> sh600519
                    data_str = right.strip('";')
                    
                    if not data_str: continue
                    
                    parts = data_str.split('~')
                    if len(parts) > 30:
                        # 腾讯数据字段: 1:名称, 2:代码, 3:最新价, 4:昨收, 32:涨跌幅(%)
                        current_price = float(parts[3])
                        last_close = float(parts[4])
                        change_pct = float(parts[32])
                        
                        # 如果停牌或未开盘(价格为0)，用昨收价兜底
                        if current_price == 0:
                            current_price = last_close
                            
                        if current_price > 0:
                            original_code = code_map.get(q_code)
                            if original_code:
                                price_map[original_code] = {
                                    'price': current_price,
                                    'pct': change_pct
                                }
                                
    except Exception:
        pass
            
    return price_map

def calculate_indicators(df):
    """计算技术指标"""
    data = df.copy()
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['rsi'] = 100 - (100 / (1 + rs))
    
    data['bb_middle'] = data['close'].rolling(window=20).mean()
    data['bb_std'] = data['close'].rolling(window=20).std()
    data['bb_upper'] = data['bb_middle'] + 2 * data['bb_std']
    data['bb_lower'] = data['bb_middle'] - 2 * data['bb_std']
    
    data['vol_ma5'] = data['volume'].rolling(window=5).mean()
    data['vol_ratio'] = data['volume'] / data['vol_ma5']
    return data

# ==============================================================================
# 模式 0: 自动化实盘监控 (AutoBot)
# ==============================================================================
if mode == "🤖 自动化实盘监控 (AutoBot)":
    st.header("🤖 自动交易机器人监控面板")
    
    auto_refresh = st.sidebar.checkbox("开启自动刷新 (5s)", value=False)
    enable_realtime = st.sidebar.checkbox("开启实时行情", value=True, help="关闭以解决卡顿")

    if auto_refresh:
        time.sleep(5)
        st.rerun()

    data_dir = "data"
    account_file = os.path.join(data_dir, "account.json")
    trades_file = os.path.join(data_dir, "trades.csv")
    log_file = os.path.join(data_dir, "bot.log")
    
    if os.path.exists(account_file):
        try:
            with open(account_file, 'r', encoding='utf-8') as f:
                acc = json.load(f)
            
            positions = acc.get('positions', {})
            current_market_value = 0.0
            pos_data = []
            
            # 初始化妖股基因系统
            demon_tracker = None
            try:
                demon_tracker = DemonStockGene()
            except Exception as e:
                st.warning(f"妖股基因系统初始化失败: {e}")
            
            if positions:
                spot_map = {}
                if enable_realtime:
                    with st.spinner("正在同步行情..."):
                        stock_list = list(positions.keys())
                        spot_map = get_realtime_quotes(stock_list)
                    
                    with st.expander("🔍 行情调试信息"):
                        st.write(spot_map)
                    
                for symbol, pos in positions.items():
                    try:
                        cost = float(pos.get('cost', 0.0))
                        shares = int(pos.get('shares', 0))
                        
                        live_data = spot_map.get(symbol)
                        current_price = cost
                        daily_pct = 0.0
                        
                        if isinstance(live_data, dict):
                            current_price = float(live_data.get('price', cost))
                            daily_pct = float(live_data.get('pct', 0.0))
                        elif isinstance(live_data, (float, int)):
                            current_price = float(live_data)
                        
                        mkt_val = current_price * shares
                        current_market_value += mkt_val
                        
                        profit = (current_price - cost) * shares
                        if cost > 0:
                            profit_pct = (current_price - cost) / cost * 100
                        else:
                            profit_pct = 0.0
                        
                        # 获取妖股基因信息
                        gene_display = "-"
                        if demon_tracker:
                            try:
                                # 使用 get_gene_data 获取完整数据
                                gene_info = demon_tracker.get_gene_data(symbol)
                                if gene_info:
                                    gene_score = gene_info.get('gene_score', 0)
                                    max_board = gene_info.get('max_continuous_board', 0)
                                    if gene_score >= 80:
                                        gene_display = f"🔥 {gene_score:.0f}分 ({max_board}板)"
                                    elif gene_score >= 60:
                                        gene_display = f"✨ {gene_score:.0f}分 ({max_board}板)"
                                    elif gene_score > 0:
                                        gene_display = f"{gene_score:.0f}分"
                            except Exception as e:
                                pass
                        
                        pos_data.append({
                            "代码": symbol,
                            "名称": pos.get('name', symbol),
                            "持仓数量": shares,
                            "成本价": f"{cost:.2f}",
                            "最新价": f"{current_price:.2f}",
                            "当日涨跌": f"{daily_pct:+.2f}%",
                            "妖股基因": gene_display,
                            "持仓市值": f"{mkt_val:.2f}",
                            "浮动盈亏": f"{profit:+.2f}",
                            "盈亏比例": f"{profit_pct:+.2f}%"
                        })
                    except Exception as ex:
                        st.error(f"处理持仓 {symbol} 出错: {ex}")
            
            cash = float(acc.get('cash', 0.0))
            total_assets = cash + current_market_value
            initial_capital = float(acc.get('initial_capital', 1000000.0))
            last_day_value = float(acc.get('last_day_value', 1000000.0))
            yesterday_pnl = float(acc.get('yesterday_pnl', 0.0)) 
            
            total_pnl = total_assets - initial_capital
            total_pnl_pct = total_pnl / initial_capital * 100 if initial_capital != 0 else 0.0
            
            daily_pnl = total_assets - last_day_value
            daily_pnl_pct = daily_pnl / last_day_value * 100 if last_day_value != 0 else 0.0
            
            total_float_pnl = 0.0
            for item in pos_data:
                try:
                    p = float(item['浮动盈亏'].replace('+', '').replace(',', ''))
                    total_float_pnl += p
                except: pass
            realized_pnl = total_pnl - total_float_pnl
            
            st.subheader("📊 资产全景 (CNY)")
            
            sentiment = acc.get('sentiment', 'NEUTRAL')
            sentiment_map = {
                'BULLISH': "🔥 主升浪 (重仓出击)",
                'BEARISH': "❄️ 退潮期 (空仓防守)",
                'NEUTRAL': "🟡 震荡期 (控制仓位)"
            }
            # 读取最新日志中的情绪状态
            # 这里简单直接显示
            
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("总资产 (元)", f"{total_assets:,.2f}")
            kpi2.metric("可用现金 (元)", f"{cash:,.2f}")
            kpi3.metric("初始本金 (元)", f"{initial_capital:,.2f}")
            kpi4.metric("持仓市值 (元)", f"{current_market_value:,.2f}")
            
            st.markdown("---")
            
            pnl1, pnl2, pnl3, pnl4 = st.columns(4)
            pnl1.metric("累计总盈亏", f"{total_pnl:+,.2f}", delta=f"{total_pnl_pct:+.2f}%")
            pnl2.metric("今日盈亏", f"{daily_pnl:+,.2f}", delta=f"{daily_pnl_pct:+.2f}%")
            pnl3.metric("持仓浮动盈亏", f"{total_float_pnl:+,.2f}", help="当前持仓股票的账面盈亏总和")
            pnl4.metric("已实现盈亏 (估)", f"{realized_pnl:+,.2f}", help="历史交易产生的盈亏")

            nav_history = acc.get('nav_history', [])
            if nav_history:
                st.caption("📈 账户净值成长曲线")
                hist_df = pd.DataFrame(nav_history)
                current_point = pd.DataFrame([{
                    "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 
                    "total_value": total_assets
                }])
                chart_df = pd.concat([hist_df, current_point], ignore_index=True)
                st.line_chart(chart_df.set_index('date')['total_value'])

            st.subheader("💼 持仓详情")
            if pos_data:
                df_pos = pd.DataFrame(pos_data)
                st.dataframe(df_pos)
            else:
                st.info("当前空仓，正在扫描市场机会...")
        except Exception as e:
            st.error(f"解析账户文件失败: {e}")
            
    else:
        st.warning(f"未找到账户文件: {os.path.abspath(account_file)}")
        st.info("💡 请先在终端运行后台机器人: `python quant_trading/auto_trader.py`")

    # ==========================================================================
    # 🔥 热点板块追踪器
    # ==========================================================================
    st.subheader("🔥 热点板块追踪 (主线识别)")
    
    if HOTSPOT_AVAILABLE:
        try:
            hotspot_tracker = HotspotTracker()
            
            # 获取板块排名
            with st.spinner("正在扫描热点板块..."):
                sectors = hotspot_tracker.get_sector_ranking()
            
            if sectors:
                # 分类展示
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### 📊 板块强度排行")
                    
                    # 构建板块数据表格
                    sector_data = []
                    for i, s in enumerate(sectors[:15], 1):
                        cycle = s.get('cycle', 'NORMAL')
                        cycle_display = {
                            'LAUNCH': '🚀 启动期',
                            'SURGE': '📈 加速期', 
                            'PEAK': '⚠️ 高潮期',
                            'DECAY': '❌ 衰退期',
                            'NORMAL': '⚪ 平稳期'
                        }.get(cycle, '⚪ 平稳期')
                        
                        sector_data.append({
                            "排名": i,
                            "板块": s['name'],
                            "涨跌幅": f"{s['change_pct']:+.2f}%",
                            "周期": cycle_display
                        })
                    
                    df_sectors = pd.DataFrame(sector_data)
                    st.dataframe(df_sectors, use_container_width=True, hide_index=True)
                
                with col2:
                    st.markdown("#### ?? 入场机会分析")
                    
                    # 分类统计
                    launch_sectors = [s for s in sectors if s.get('cycle') == 'LAUNCH']
                    surge_sectors = [s for s in sectors if s.get('cycle') == 'SURGE']
                    peak_sectors = [s for s in sectors if s.get('cycle') == 'PEAK']
                    decay_sectors = [s for s in sectors if s.get('cycle') == 'DECAY']
                    
                    # 周期统计
                    stat1, stat2, stat3, stat4 = st.columns(4)
                    stat1.metric("🚀 启动期", f"{len(launch_sectors)}个")
                    stat2.metric("📈 加速期", f"{len(surge_sectors)}个")
                    stat3.metric("⚠️ 高潮期", f"{len(peak_sectors)}个")
                    stat4.metric("❌ 衰退期", f"{len(decay_sectors)}个")
                    
                    st.markdown("---")
                    
                    # 推荐关注
                    if launch_sectors:
                        st.success(f"**启动期板块 (最佳买点):** {', '.join([s['name'] for s in launch_sectors[:5]])}")
                    
                    if surge_sectors:
                        st.info(f"**加速期板块 (可以跟随):** {', '.join([s['name'] for s in surge_sectors[:5]])}")
                    
                    if peak_sectors:
                        st.warning(f"**高潮期板块 (谨慎追高):** {', '.join([s['name'] for s in peak_sectors[:3]])}")
                    
                    if not launch_sectors and not surge_sectors:
                        st.info("当前暂无明显的启动期/加速期板块，建议观望")
                
                # 最佳入场机会
                with st.expander("🎯 最佳入场机会 (低接盘风险)", expanded=False):
                    try:
                        best_entries = hotspot_tracker.find_best_entry_stocks(max_count=10)
                        if best_entries:
                            entry_data = []
                            for c in best_entries:
                                risk_display = {
                                    'LOW': '🟢 低',
                                    'MEDIUM': '🟡 中',
                                    'HIGH': '🔴 高'
                                }.get(c.get('risk_level', 'MEDIUM'), '🟡 中')
                                
                                cycle_display = {
                                    'LAUNCH': '🚀 启动',
                                    'SURGE': '📈 加速'
                                }.get(c.get('sector_cycle', ''), '')
                                
                                entry_data.append({
                                    "代码": c['symbol'],
                                    "名称": c['name'],
                                    "所属板块": c['sector'],
                                    "板块周期": cycle_display,
                                    "今日涨幅": f"{c.get('change_pct', 0):+.2f}%",
                                    "接盘风险": risk_display,
                                    "综合评分": f"{c.get('score', 0):.0f}"
                                })
                            
                            df_entries = pd.DataFrame(entry_data)
                            st.dataframe(df_entries, use_container_width=True, hide_index=True)
                        else:
                            st.info("当前未找到低风险入场机会，建议等待")
                    except Exception as e:
                        st.warning(f"获取入场机会失败: {e}")
                        
            else:
                st.warning("板块数据获取失败，请稍后刷新")
                
        except Exception as e:
            st.error(f"热点追踪器异常: {e}")
    else:
        st.info("热点追踪模块未加载，请确认 hotspot_tracker.py 文件存在")
    
    st.markdown("---")
    
    st.subheader("📝 历史交易日志")
    if os.path.exists(trades_file):
        try:
            trades_df = pd.read_csv(trades_file)
            if not trades_df.empty:
                st.dataframe(trades_df.sort_values(by='time', ascending=False))
            else:
                st.info("暂无交易记录 (文件为空)")
        except Exception as e:
            st.error(f"读取交易记录失败: {e}")
    else:
        st.info("暂无交易记录文件")
        
    st.subheader("📋 机器人运行日志")
    st.caption(f"🕐 数据更新时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 显示最近100行日志
            recent_logs = lines[-100:]
            
            # 日志内容展示 (默认展开)
            with st.expander("📜 实时日志 (最近100行)", expanded=True):
                # 使用代码块显示，更清晰
                log_text = "".join(recent_logs)
                st.code(log_text, language="log")
                
        except Exception as e:
            st.error(f"读取日志失败: {e}")
    else:
        st.warning(f"日志文件不存在: {os.path.abspath(log_file)}")
    
    # 添加手动刷新按钮
    col_refresh1, col_refresh2, col_refresh3 = st.columns([1, 1, 2])
    with col_refresh1:
        if st.button("🔄 刷新数据", use_container_width=True):
            st.rerun()
    with col_refresh2:
        if st.button("🗑️ 清除缓存", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

# ==============================================================================
# 模式 1: 进阶波段策略 (RSI + 布林带 + 止盈止损)
# ==============================================================================
elif mode == "🔥 进阶波段策略 (回测)":
    st.sidebar.header("🛠️ 波段策略参数")
    
    symbol = st.sidebar.text_input("股票代码", value="600519")
    start_date = st.sidebar.date_input("开始日期", value=datetime.date(2023, 1, 1))
    end_date = st.sidebar.date_input("结束日期", value=datetime.date.today())
    
    st.sidebar.subheader("1. 价格信号 (RSI & 布林)")
    rsi_buy_threshold = st.sidebar.slider("RSI 超卖阈值 (抄底)", 10, 40, 30, help="RSI低于此值视为超卖")
    rsi_sell_threshold = st.sidebar.slider("RSI 超买阈值 (逃顶)", 60, 90, 70, help="RSI高于此值视为超买")
    
    if st.sidebar.button("启动波段狙击"):
        with st.spinner("正在计算量价指标..."):
            raw_df = get_stock_data(symbol, start_date, end_date)
            if raw_df is not None:
                df = calculate_indicators(raw_df)
                
                # --- 交易逻辑 ---
                df['position_signal'] = 0 
                holding = False
                capital = 1000000.0
                portfolio_history = []
                
                for date, row in df.iterrows():
                    current_price = row['close']
                    if not holding:
                        if (row['close'] < row['bb_lower']) and (row['rsi'] < rsi_buy_threshold):
                            holding = True
                            capital -= current_price * 100
                    else:
                        if (row['close'] > row['bb_upper']) and (row['rsi'] > rsi_sell_threshold):
                            holding = False
                            capital += current_price * 100
                    
                    current_value = capital + (current_price * 100 if holding else 0)
                    portfolio_history.append(current_value)
                
                df['portfolio_value'] = portfolio_history
                
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
                fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='K线'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['portfolio_value'], line=dict(color='orange'), name='账户净值'), row=2, col=1)
                st.plotly_chart(fig, use_container_width=True)

# ==============================================================================
# 模式 2: 基础趋势回测
# ==============================================================================
elif mode == "📈 基础趋势回测 (双均线)":
    st.info("双均线策略回测演示")
    symbol = st.sidebar.text_input("股票代码", value="600519")
    
    if st.sidebar.button("开始回测"):
        with st.spinner("计算中..."):
            st.success("回测完成 (简化演示)")