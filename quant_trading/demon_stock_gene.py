"""
妖股基因识别系统
用于识别具有反复炒作潜力的股票，提升龙头股识别准确率
作者: Zulu AI
版本: 1.0
创建时间: 2026-01-27
"""

import akshare as ak
import pandas as pd
import numpy as np
import json
import os
import datetime
import logging
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import time

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 数据文件路径
DATA_DIR = "data"
GENE_DB_FILE = os.path.join(DATA_DIR, "demon_gene_db.json")
GENE_CACHE_FILE = os.path.join(DATA_DIR, "demon_gene_cache.json")


class DemonStockGene:
    """妖股基因识别与评分系统"""
    
    def __init__(self):
        """初始化妖股基因系统"""
        self.gene_db = self._load_gene_db()
        self.cache = {}
        self.cache_time = None
        
        # 确保数据目录存在
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
    
    def _load_gene_db(self) -> Dict:
        """加载妖股基因数据库"""
        if os.path.exists(GENE_DB_FILE):
            try:
                with open(GENE_DB_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logging.info(f"✅ 妖股基因库加载成功: {len(data)} 只股票")
                    return data
            except Exception as e:
                logging.error(f"❌ 基因库加载失败: {e}")
                return {}
        else:
            logging.warning("⚠️  基因库不存在，将创建新库")
            return {}
    
    def _save_gene_db(self):
        """保存妖股基因数据库"""
        try:
            with open(GENE_DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.gene_db, f, ensure_ascii=False, indent=2)
            logging.info(f"💾 基因库保存成功: {len(self.gene_db)} 只股票")
        except Exception as e:
            logging.error(f"❌ 基因库保存失败: {e}")
    
    def _get_stock_history(self, symbol: str, days: int = 180, max_retries: int = 3) -> Optional[pd.DataFrame]:
        """
        获取股票历史K线数据（带重试机制）
        
        参数:
            symbol: 股票代码 (如 '600519')
            days: 获取天数 (默认180天)
            max_retries: 最大重试次数
        
        返回:
            DataFrame 包含: 日期, 开盘, 收盘, 最高, 最低, 成交量等
        """
        import socket
        from urllib3.exceptions import ProtocolError
        from requests.exceptions import ConnectionError, Timeout
        
        # 计算起止日期
        end_date = datetime.date.today().strftime("%Y%m%d")
        start_date = (datetime.date.today() - datetime.timedelta(days=days)).strftime("%Y%m%d")
        
        for retry in range(max_retries):
            try:
                # 获取历史数据（设置超时）
                df = ak.stock_zh_a_hist(
                    symbol=symbol, 
                    period="daily", 
                    start_date=start_date, 
                    end_date=end_date, 
                    adjust="qfq"  # 前复权
                )
                
                if df.empty:
                    return None
                
                # 标准化列名
                df.columns = ['日期', '开盘', '收盘', '最高', '最低', '成交量', 
                             '成交额', '振幅', '涨跌幅', '涨跌额', '换手率']
                
                return df
            
            except (ConnectionError, socket.error, ProtocolError, Timeout) as e:
                if retry < max_retries - 1:
                    wait_time = (retry + 1) * 2  # 递增等待时间：2秒、4秒、6秒
                    logging.warning(f"⚠️  {symbol} 网络错误，{wait_time}秒后重试 ({retry+1}/{max_retries}): {type(e).__name__}")
                    time.sleep(wait_time)
                else:
                    logging.warning(f"⚠️  {symbol} 重试{max_retries}次后仍失败，跳过")
                    return None
            
            except Exception as e:
                logging.warning(f"⚠️  获取 {symbol} 历史数据失败: {e}")
                return None
        
        return None
    
    def _calculate_max_continuous_board(self, df: pd.DataFrame) -> Tuple[int, str]:
        """
        计算最大连板数
        
        参数:
            df: 历史K线DataFrame
        
        返回:
            (最大连板数, 最后连板日期)
        """
        if df is None or df.empty:
            return 0, ""
        
        max_continuous = 0
        current_continuous = 0
        last_board_date = ""
        
        # 涨停阈值: 9.9% (考虑浮点误差)
        for _, row in df.iterrows():
            change_pct = row['涨跌幅']
            date = row['日期']
            
            if change_pct >= 9.9:  # 涨停
                current_continuous += 1
                last_board_date = date
                max_continuous = max(max_continuous, current_continuous)
            else:
                current_continuous = 0
        
        return max_continuous, last_board_date
    
    def _calculate_monthly_max_gain(self, df: pd.DataFrame) -> float:
        """
        计算单月最大涨幅
        
        参数:
            df: 历史K线DataFrame
        
        返回:
            单月最大涨幅 (百分比)
        """
        if df is None or df.empty:
            return 0.0
        
        # 按月分组
        df['月份'] = pd.to_datetime(df['日期']).dt.to_period('M')
        monthly_gains = {}
        
        for month, group in df.groupby('月份'):
            if len(group) < 2:
                continue
            
            start_price = group.iloc[0]['开盘']
            end_price = group.iloc[-1]['收盘']
            highest_price = group['最高'].max()
            
            # 月涨幅 = (月内最高 - 月初开盘) / 月初开盘
            if start_price > 0:
                gain = (highest_price - start_price) / start_price * 100
                monthly_gains[str(month)] = gain
        
        return max(monthly_gains.values()) if monthly_gains else 0.0
    
    def _calculate_zt_count(self, df: pd.DataFrame, days: int = 180) -> int:
        """
        计算指定天数内的涨停次数
        
        参数:
            df: 历史K线DataFrame
            days: 统计天数
        
        返回:
            涨停次数
        """
        if df is None or df.empty:
            return 0
        
        # 涨停阈值: 9.9%
        zt_count = len(df[df['涨跌幅'] >= 9.9])
        return zt_count
    
    def _calculate_avg_amplitude(self, df: pd.DataFrame) -> float:
        """
        计算日均振幅
        
        参数:
            df: 历史K线DataFrame
        
        返回:
            日均振幅 (百分比)
        """
        if df is None or df.empty:
            return 0.0
        
        # 振幅列已在数据中
        avg_amplitude = df['振幅'].mean()
        return avg_amplitude
    
    def calculate_gene_score(self, symbol: str, name: str = "") -> Optional[Dict]:
        """
        计算单只股票的妖股基因评分
        
        参数:
            symbol: 股票代码
            name: 股票名称 (可选)
        
        返回:
            {
                'name': 股票名称,
                'gene_score': 基因评分 (0-100),
                'max_continuous_board': 最大连板数,
                'last_board_date': 最后连板日期,
                'monthly_max_gain': 单月最大涨幅,
                'avg_amplitude': 日均振幅,
                'zt_count_6m': 半年涨停次数,
                'update_time': 更新时间
            }
        """
        try:
            # 获取历史数据
            df = self._get_stock_history(symbol, days=180)
            
            if df is None or df.empty:
                logging.warning(f"⚠️  {symbol} 数据为空，跳过")
                return None
            
            # 获取股票名称
            if not name:
                try:
                    stock_info = ak.stock_individual_info_em(symbol=symbol)
                    name = stock_info[stock_info['item'] == '股票简称']['value'].values[0]
                except:
                    name = symbol
            
            # === 计算各项指标 ===
            max_continuous_board, last_board_date = self._calculate_max_continuous_board(df)
            monthly_max_gain = self._calculate_monthly_max_gain(df)
            zt_count_6m = self._calculate_zt_count(df, days=180)
            avg_amplitude = self._calculate_avg_amplitude(df)
            
            # === 计算妖股基因评分 (0-100) ===
            score = 0
            
            # 1. 连板历史 (0-40分)
            if max_continuous_board >= 5:
                score += 40
            elif max_continuous_board >= 3:
                score += 30
            elif max_continuous_board >= 2:
                score += 20
            elif max_continuous_board >= 1:
                score += 10
            
            # 2. 暴涨记录 (0-30分)
            if monthly_max_gain >= 80:
                score += 30
            elif monthly_max_gain >= 50:
                score += 20
            elif monthly_max_gain >= 30:
                score += 10
            
            # 3. 炒作频率 (0-20分)
            if zt_count_6m >= 5:
                score += 20
            elif zt_count_6m >= 3:
                score += 15
            elif zt_count_6m >= 1:
                score += 10
            
            # 4. 活跃度 (0-10分)
            if avg_amplitude >= 10:
                score += 10
            elif avg_amplitude >= 8:
                score += 5
            
            # 构建结果
            result = {
                'name': name,
                'gene_score': round(score, 2),
                'max_continuous_board': int(max_continuous_board),
                'last_board_date': last_board_date,
                'monthly_max_gain': round(monthly_max_gain, 2),
                'avg_amplitude': round(avg_amplitude, 2),
                'zt_count_6m': int(zt_count_6m),
                'update_time': datetime.datetime.now().strftime("%Y-%m-%d")
            }
            
            return result
        
        except Exception as e:
            logging.error(f"❌ 计算 {symbol} 基因评分失败: {e}")
            return None
    
    def build_gene_database(self, max_stocks: int = 5000, batch_save_interval: int = 50):
        """
        构建全市场妖股基因数据库 (首次运行，带容错和批量保存)
        
        参数:
            max_stocks: 最大扫描股票数 (默认5000只)
            batch_save_interval: 批量保存间隔 (每N只股票保存一次)
        
        注意:
            - 首次运行耗时约20-40分钟
            - 建议在收盘后执行
            - 会自动保存到 data/demon_gene_db.json
            - 支持中断恢复（已保存的数据不会丢失）
        """
        logging.info("🚀 开始构建妖股基因数据库...")
        start_time = time.time()
        
        try:
            # 获取全市场股票列表（多数据源备用）
            stock_list = None
            
            # 数据源优先级：腾讯财经 > 东方财富 > 新浪财经
            data_sources = [
                ("腾讯财经", lambda: ak.stock_zh_a_spot()),
                ("东方财富", lambda: ak.stock_zh_a_spot_em()),
                ("新浪财经", lambda: ak.stock_zh_a_spot_sina())
            ]
            
            for source_name, fetch_func in data_sources:
                for retry in range(2):
                    try:
                        logging.info(f"尝试从 {source_name} 获取股票列表...")
                        stock_list = fetch_func()
                        
                        if stock_list is not None and not stock_list.empty:
                            logging.info(f"✅ 成功从 {source_name} 获取数据")
                            break
                    except Exception as e:
                        logging.warning(f"⚠️  {source_name} 失败: {e}")
                        if retry < 1:
                            time.sleep(3)
                
                if stock_list is not None and not stock_list.empty:
                    break
            
            if stock_list is None or stock_list.empty:
                raise Exception("所有数据源均失败，请稍后重试")
            
            if stock_list is None or stock_list.empty:
                raise Exception("股票列表为空")
            
            logging.info(f"📊 获取到 {len(stock_list)} 只股票")
            
            # 限制数量
            stock_list = stock_list.head(max_stocks)
            
            success_count = 0
            fail_count = 0
            network_fail_count = 0
            
            for idx, row in stock_list.iterrows():
                symbol = str(row['代码'])
                name = str(row['名称'])
                
                # 跳过已处理的股票（支持中断恢复）
                if symbol in self.gene_db:
                    continue
                
                # 进度显示
                if (idx + 1) % 10 == 0:
                    logging.info(f"进度: {idx+1}/{len(stock_list)} ({(idx+1)/len(stock_list)*100:.1f}%) | "
                               f"成功:{success_count} 失败:{fail_count}")
                
                # 计算基因评分
                gene_data = self.calculate_gene_score(symbol, name)
                
                if gene_data:
                    self.gene_db[symbol] = gene_data
                    success_count += 1
                else:
                    fail_count += 1
                    # 区分网络失败和数据问题
                    if fail_count > network_fail_count + 10:
                        network_fail_count = fail_count
                
                # 批量保存（防止中断丢失数据）
                if (idx + 1) % batch_save_interval == 0:
                    self._save_gene_db()
                    logging.info(f"💾 已保存 {len(self.gene_db)} 只股票数据")
                
                # 动态调整延迟（网络失败多时增加延迟）
                if network_fail_count > 5:
                    time.sleep(0.5)  # 增加延迟
                else:
                    time.sleep(0.1)  # 正常延迟
            
            # 最终保存
            self._save_gene_db()
            
            elapsed = time.time() - start_time
            logging.info(f"✅ 基因库构建完成!")
            logging.info(f"📈 成功: {success_count} 只, 失败: {fail_count} 只, 成功率: {success_count/(success_count+fail_count)*100:.1f}%")
            logging.info(f"⏱️  耗时: {elapsed/60:.1f} 分钟")
            
            # 统计高分妖股
            high_gene_stocks = self.get_high_gene_stocks(min_score=60)
            super_demons = [s for s in high_gene_stocks if s['gene_score'] >= 80]
            logging.info(f"🔥 妖股基因≥60分: {len(high_gene_stocks)} 只 (超级妖股≥80分: {len(super_demons)} 只)")
            
            # 如果失败率过高，给出提示
            if fail_count > success_count * 0.3:
                logging.warning("⚠️  失败率较高，建议:")
                logging.warning("   1. 检查网络连接")
                logging.warning("   2. 稍后重新运行（已保存的数据会保留）")
                logging.warning("   3. 或等到周末时段再试")
            
        except Exception as e:
            logging.error(f"❌ 基因库构建失败: {e}")
            logging.info("💡 提示: 已处理的数据已保存，可以稍后重新运行继续构建")
    
    def update_gene_database(self):
        """
        增量更新妖股基因数据库 (每日运行)
        
        策略:
            - 更新今日涨停股的基因数据
            - 更新基因库中已有的高分股票
            - 耗时约3-5分钟
        """
        logging.info("🔄 开始增量更新妖股基因库...")
        start_time = time.time()
        
        try:
            # 1. 获取今日涨停股
            today = datetime.date.today().strftime("%Y%m%d")
            zt_pool = ak.stock_zt_pool_em(date=today)
            
            if zt_pool.empty:
                logging.warning("⚠️  今日无涨停股，跳过更新")
                return
            
            logging.info(f"📊 今日涨停: {len(zt_pool)} 只")
            
            update_count = 0
            
            # 2. 更新涨停股
            for _, row in zt_pool.iterrows():
                symbol = row.get('代码', '')
                name = row.get('名称', '')
                
                if not symbol:
                    continue
                
                gene_data = self.calculate_gene_score(symbol, name)
                
                if gene_data:
                    self.gene_db[symbol] = gene_data
                    update_count += 1
                
                time.sleep(0.1)
            
            # 3. 更新基因库中的高分股票 (基因分≥60)
            high_gene_symbols = [s for s, d in self.gene_db.items() 
                                if d.get('gene_score', 0) >= 60]
            
            logging.info(f"🔥 更新高分妖股: {len(high_gene_symbols)} 只")
            
            for symbol in high_gene_symbols:
                name = self.gene_db[symbol].get('name', '')
                gene_data = self.calculate_gene_score(symbol, name)
                
                if gene_data:
                    self.gene_db[symbol] = gene_data
                    update_count += 1
                
                time.sleep(0.1)
            
            # 保存更新
            self._save_gene_db()
            
            elapsed = time.time() - start_time
            logging.info(f"✅ 增量更新完成!")
            logging.info(f"?? 更新: {update_count} 只")
            logging.info(f"⏱️  耗时: {elapsed/60:.1f} 分钟")
            
        except Exception as e:
            logging.error(f"❌ 增量更新失败: {e}")
    
    def get_gene_score(self, symbol: str) -> float:
        """
        查询单只股票的妖股基因评分 (快速查询)
        
        参数:
            symbol: 股票代码
        
        返回:
            基因评分 (0-100)，如果不存在返回0
        """
        if symbol in self.gene_db:
            return self.gene_db[symbol].get('gene_score', 0)
        else:
            return 0.0
    
    def get_gene_data(self, symbol: str) -> Optional[Dict]:
        """
        获取单只股票的完整基因数据
        
        参数:
            symbol: 股票代码
        
        返回:
            完整基因数据字典，如果不存在返回None
        """
        return self.gene_db.get(symbol, None)
    
    def get_high_gene_stocks(self, min_score: int = 60) -> List[Dict]:
        """
        获取高分妖股列表
        
        参数:
            min_score: 最低基因评分阈值 (默认60)
        
        返回:
            [
                {
                    'symbol': 股票代码,
                    'name': 股票名称,
                    'gene_score': 基因评分,
                    'max_continuous_board': 最大连板数,
                    ...
                },
                ...
            ]
            按基因评分降序排列
        """
        high_gene_stocks = []
        
        for symbol, data in self.gene_db.items():
            score = data.get('gene_score', 0)
            if score >= min_score:
                stock_data = {'symbol': symbol}
                stock_data.update(data)
                high_gene_stocks.append(stock_data)
        
        # 按评分降序排序
        high_gene_stocks.sort(key=lambda x: x['gene_score'], reverse=True)
        
        return high_gene_stocks
    
    def get_statistics(self) -> Dict:
        """
        获取妖股基因库统计信息
        
        返回:
            {
                'total_stocks': 总股票数,
                'high_gene_count': 高分妖股数 (≥60分),
                'super_demon_count': 超级妖股数 (≥80分),
                'avg_gene_score': 平均基因评分,
                'max_gene_stock': 最高分妖股信息
            }
        """
        if not self.gene_db:
            return {
                'total_stocks': 0,
                'high_gene_count': 0,
                'super_demon_count': 0,
                'avg_gene_score': 0,
                'max_gene_stock': None
            }
        
        scores = [d.get('gene_score', 0) for d in self.gene_db.values()]
        high_gene_count = sum(1 for s in scores if s >= 60)
        super_demon_count = sum(1 for s in scores if s >= 80)
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # 找到最高分妖股
        max_gene_stock = None
        max_score = 0
        for symbol, data in self.gene_db.items():
            score = data.get('gene_score', 0)
            if score > max_score:
                max_score = score
                max_gene_stock = {
                    'symbol': symbol,
                    'name': data.get('name', ''),
                    'gene_score': score
                }
        
        return {
            'total_stocks': len(self.gene_db),
            'high_gene_count': high_gene_count,
            'super_demon_count': super_demon_count,
            'avg_gene_score': round(avg_score, 2),
            'max_gene_stock': max_gene_stock
        }


# =============================================================================
# 便捷函数
# =============================================================================

def quick_query(symbol: str) -> Optional[Dict]:
    """
    快速查询单只股票的妖股基因
    
    示例:
        >>> result = quick_query('600519')
        >>> print(f"基因评分: {result['gene_score']}")
    """
    tracker = DemonStockGene()
    return tracker.get_gene_data(symbol)


def get_demon_list(min_score: int = 60) -> List[Dict]:
    """
    快速获取妖股列表
    
    示例:
        >>> demons = get_demon_list(min_score=70)
        >>> for stock in demons[:10]:
        >>>     print(f"{stock['name']}: {stock['gene_score']}分")
    """
    tracker = DemonStockGene()
    return tracker.get_high_gene_stocks(min_score)


# =============================================================================
# 主函数 (测试入口)
# =============================================================================

if __name__ == "__main__":
    tracker = DemonStockGene()
    
    print("=" * 60)
    print("妖股基因识别系统 v1.0")
    print("=" * 60)
    
    # 显示统计信息
    stats = tracker.get_statistics()
    print(f"\n📊 基因库统计:")
    print(f"  总股票数: {stats['total_stocks']}")
    print(f"  高分妖股 (≥60分): {stats['high_gene_count']}")
    print(f"  超级妖股 (≥80分): {stats['super_demon_count']}")
    print(f"  平均基因评分: {stats['avg_gene_score']}")
    
    if stats['max_gene_stock']:
        max_stock = stats['max_gene_stock']
        print(f"  最强妖股: {max_stock['name']} ({max_stock['symbol']}) - {max_stock['gene_score']}分")
    
    # 显示Top10妖股
    print(f"\n🔥 Top 10 妖股基因:")
    high_gene_stocks = tracker.get_high_gene_stocks(min_score=0)
    for idx, stock in enumerate(high_gene_stocks[:10], 1):
        print(f"  {idx}. {stock['name']} ({stock['symbol']}): {stock['gene_score']}分 "
              f"[连板{stock['max_continuous_board']} | 月涨{stock['monthly_max_gain']:.1f}% | "
              f"振幅{stock['avg_amplitude']:.1f}%]")
    
    print("\n" + "=" * 60)
    print("使用说明:")
    print("  1. 首次构建: tracker.build_gene_database()")
    print("  2. 每日更新: tracker.update_gene_database()")
    print("  3. 查询评分: tracker.get_gene_score('600519')")
    print("  4. 获取妖股: tracker.get_high_gene_stocks(min_score=70)")
    print("=" * 60)