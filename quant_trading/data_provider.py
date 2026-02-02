import requests
import pandas as pd
import logging
import time

def get_stock_history_tencent(symbol, count=100):
    """
    从腾讯财经获取个股历史数据 (前复权)
    URL: http://web.ifzq.gtimg.cn/appstock/app/fqkline/get
    """
    # 1. 构造代码格式 (sh600519 / sz000001)
    code_str = str(symbol)
    if code_str.startswith('6'): prefix = 'sh'
    elif code_str.startswith('8') or code_str.startswith('4'): prefix = 'bj'
    else: prefix = 'sz'
    qq_code = f"{prefix}{code_str}"
    
    # 2. 构造请求
    # param=代码,周期,,,数量,复权方式
    url = "http://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    params = {
        "_var": "kline_dayqfq",
        "param": f"{qq_code},day,,,{count},qfq",
        "r": time.time()
    }
    
    try:
        resp = requests.get(url, params=params, timeout=3)
        if resp.status_code != 200:
            return None
            
        # 3. 解析数据
        # 腾讯返回的是 JSON 格式，但可能包裹在变量赋值中，直接解析 JSON 即可
        # 格式: {"code":0,"msg":"","data":{"sh600519":{"day":[["2023-01-01","100.0","101.0",...],...]}}}
        content = resp.text
        # 如果返回的是 var xxxx = {...}，需要清洗
        if '=' in content:
            content = content.split('=', 1)[1]
            
        data_json = json.loads(content)
        
        # 提取 K 线列表
        if 'data' not in data_json or qq_code not in data_json['data']:
            return None
            
        # 优先取前复权 'qfqday'，如果没有则取不复权 'day'
        stock_data = data_json['data'][qq_code]
        kline_list = stock_data.get('qfqday', stock_data.get('day', []))
        
        if not kline_list:
            return None
            
        # 4. 转换为 DataFrame
        # 腾讯数据格式: [日期, 开盘, 收盘, 最高, 最低, 成交量, ...]
        # 注意: 返回的列数可能不固定 (有的只有6列，有的有9列)，只取前6列即可
        clean_list = [item[:6] for item in kline_list]
        df = pd.DataFrame(clean_list, columns=['date', 'open', 'close', 'high', 'low', 'volume'])
        
        # 类型转换
        cols = ['open', 'close', 'high', 'low', 'volume']
        for col in cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        df['date'] = pd.to_datetime(df['date'])
        
        # 腾讯的 date 是 '2023-01-01' 格式，刚好符合
        return df[['date', 'open', 'close', 'high', 'low', 'volume']]
        
    except Exception as e:
        logging.warning(f"腾讯接口获取 {symbol} 失败: {e}")
        return None

# 为了兼容现有代码，提供一个统一入口，带有重试机制
def get_stock_history_safe(symbol, count=120):
    for _ in range(3): # 重试3次
        df = get_stock_history_tencent(symbol, count)
        if df is not None and not df.empty:
            return df
        time.sleep(0.5)
    return None

import json