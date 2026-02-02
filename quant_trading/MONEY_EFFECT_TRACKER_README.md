# 多维赚钱效应追踪模块 (Money Effect Tracker)

## 📋 概述

`money_effect_tracker.py` 是一个用于量化市场情绪强度、识别龙头股、判断板块持续性的智能模块，旨在提升量化交易系统的抓大牛股能力。

**作者**: Zulu AI  
**版本**: 1.0  
**依赖**: akshare, pandas, numpy

---

## ?? 核心功能

### 1. 赚钱效应评分 (`get_money_effect_score`)

**功能**: 综合评估市场情绪强度，给出 0-100 分的量化评分

**评分维度**:
- **连板梯队得分 (40分)**: 高度板越多，赚钱效应越强
  - 5板以上：10分/只（妖股出现）
  - 3-4板：5分/只（龙头高度）
  - 2板：2分/只（跟风活跃）

- **板块集中度 (20分)**: 资金抱团越强，持续性越好
  - 前3大板块涨停数占比

- **龙头溢价 (20分)**: 龙头带动力越强，跟风越活跃
  - 板块龙一涨幅 / 板块平均涨幅

- **情绪持续性 (20分)**: 涨停数量持续维持高位
  - 涨停数 / (涨停数 + 跌停数)

**情绪等级划分**:
- `STRONG` (≥70分): 市场情绪强势，可主动建仓
- `MODERATE` (40-69分): 市场情绪一般，谨慎小仓位
- `WEAK` (<40分): 市场情绪弱势，建议空仓观望

**返回值**:
```python
{
    'total_score': 75.5,  # 总分
    'ladder_score': 32.0,  # 连板梯队分
    'concentration_score': 18.5,  # 板块集中度分
    'premium_score': 15.0,  # 龙头溢价分
    'sustainability_score': 10.0,  # 持续性分
    'level': 'STRONG',  # 情绪等级
    'details': {  # 详细数据
        'board_distribution': {5: 2, 4: 3, 3: 5, 2: 8},
        'top_sectors': {'人工智能': 12, '算力': 8, '芯片': 6},
        'zt_count': 53,
        'dt_count': 2
    }
}
```

---

### 2. 龙头股识别 (`find_leading_stocks`)

**功能**: 智能识别当前市场的潜在龙头股

**识别逻辑**:

#### 首板龙头（1板）
- ✅ 换手率 15-30%（黄金换手）
- ✅ 流通市值 <50亿（小盘股容易拉升）
- ✅ 题材新鲜度（依赖新闻热度）

#### 2-3板龙头
- ✅ 封板速度 <10:00（早盘封板强势）
- ✅ 连续放量（资金持续涌入）
- ✅ 同板块跟风 >3只（板块共振）

#### 高度板（>3板）
- ✅ 历史妖股基因（过去半年有过3板+记录）
- ✅ 每多1板加15分
- ✅ 5板以上直接加权50分

**参数**:
- `min_score`: 最低评分阈值（默认70分）

**返回值**:
```python
[
    {
        'symbol': '300xxx',
        'name': 'XX科技',
        'board_count': 3,  # 连板数
        'score': 85,  # 龙头评分
        'reasons': ['早盘封板 09:35:00', '板块共振 5只', '高度板 3板'],
        'sector': '人工智能',
        'seal_time': '09:35:00',
        'turnover': 22.5,  # 换手率
        'change_pct': 9.98  # 涨跌幅
    },
    # ... 更多龙头股
]
```

---

### 3. 板块持续性判断 (`get_board_sustainability`)

**功能**: 分析指定板块的持续性，判断是否值得跟随

**判断标准**:
- `HIGH`: 当前涨幅 >3% 且涨停数 >2（✅ 可追涨）
- `MEDIUM`: 当前涨幅 >1%（⚠️ 观察）
- `LOW`: 当前涨幅 ≤1%（❌ 回避）

**参数**:
- `board_name`: 板块名称（如"人工智能"）
- `days`: 回溯天数（默认5天）

**返回值**:
```python
{
    'board_name': '人工智能',
    'sustainability': 'HIGH',  # 持续性等级
    'avg_gain': 4.5,  # 平均涨幅
    'trend': 'UP',  # 趋势方向
    'active_days': 5,  # 活跃天数
    'recommendation': '✅ 可追涨',  # 操作建议
    'current_gain': 4.5  # 当前涨幅
}
```

---

## 🔧 使用方法

### 基础用法

```python
from money_effect_tracker import MoneyEffectTracker

# 初始化追踪器
tracker = MoneyEffectTracker()

# 1. 获取赚钱效应评分
score = tracker.get_money_effect_score()
print(f"市场情绪: {score['level']} ({score['total_score']}/100)")

# 2. 识别龙头股
leaders = tracker.find_leading_stocks(min_score=70)
for stock in leaders[:3]:
    print(f"{stock['name']}: 评分{stock['score']}, {stock['board_count']}连板")

# 3. 分析板块持续性
result = tracker.get_board_sustainability("人工智能")
print(f"持续性: {result['sustainability']}, 建议: {result['recommendation']}")
```

---

## 🚀 集成到 auto_trader.py

### 步骤1: 导入模块

```python
from money_effect_tracker import MoneyEffectTracker
```

### 步骤2: 初始化追踪器

```python
def run_bot():
    tracker = MoneyEffectTracker()
    # ... 其他初始化代码
```

### 步骤3: 市场情绪检查

```python
def should_trade_today(tracker):
    """判断今日是否适合交易"""
    score_result = tracker.get_money_effect_score()
    
    if score_result['level'] == 'STRONG':
        logging.info("🔥 市场情绪强势，启动主动选股")
        return True, 0.8  # (是否交易, 仓位比例)
    elif score_result['level'] == 'MODERATE':
        logging.info("⚠️ 市场情绪一般，小仓位试错")
        return True, 0.5
    else:
        logging.info("❌ 市场情绪弱势，空仓观望")
        return False, 0.0
```

### 步骤4: 龙头股优先扫描

```python
def get_priority_symbols(tracker):
    """获取优先交易的龙头股列表"""
    leaders = tracker.find_leading_stocks(min_score=70)
    
    if leaders:
        logging.info(f"🎯 识别到 {len(leaders)} 只龙头股")
        return [stock['symbol'] for stock in leaders[:5]]
    
    return []
```

### 步骤5: 修改主循环

```python
while True:
    try:
        # 1. 检查市场情绪
        can_trade, position_ratio = should_trade_today(tracker)
        
        if not can_trade:
            logging.info("今日不适合交易，休息...")
            time.sleep(1800)
            continue
        
        # 2. 获取龙头股优先列表
        priority_symbols = get_priority_symbols(tracker)
        
        # 3. 优先扫描龙头股
        for symbol in priority_symbols:
            if symbol not in trader.positions:
                signals = calculate_signals(symbol)
                if signals and signals['trend_up']:
                    # 根据仓位比例计算买入金额
                    buy_amount = 1000000 * position_ratio / 4
                    shares = int(buy_amount / signals['price'] / 100) * 100
                    
                    if shares >= 100:
                        trader.buy(symbol, name, signals['price'], shares, "龙头跟随")
                        break
        
        time.sleep(300)
        
    except Exception as e:
        logging.error(f"异常: {e}")
        time.sleep(60)
```

---

## ⚡ 性能优化

### 缓存机制
- 所有数据自动缓存 **5分钟**
- 避免频繁调用 akshare 接口
- 单次执行时间 <5秒

### 容错设计
- 部分接口失败不影响其他功能
- 自动降级处理网络异常
- 详细的日志输出便于调试

---

## 📊 测试用例

运行测试脚本：

```bash
cd quant_trading
python3 money_effect_tracker.py
```

运行集成示例：

```bash
python3 integration_example.py
```

---

## ⚠️ 注意事项

1. **数据源依赖**: 完全依赖 akshare 接口，可能受网络波动影响
2. **时间敏感**: 涨跌停数据仅在交易日有效，周末/节假日返回空值
3. **评分权重**: 评分公式可根据实盘效果调整权重
4. **龙头识别**: 首板龙头需结合题材新鲜度，当前版本简化处理
5. **板块历史**: 板块持续性分析暂时基于当日数据，后续可扩展历史回溯

---

## 🔮 未来优化方向

1. **历史数据回测**: 增加板块历史数据分析，提升持续性判断准确性
2. **题材识别**: 接入新闻接口，自动识别热点题材新鲜度
3. **妖股基因**: 建立妖股数据库，识别历史强势基因
4. **实时监控**: 支持盘中实时更新，动态调整龙头评分
5. **多因子融合**: 整合资金流、北向资金、融资融券等多维数据

---

## 📞 技术支持

如有问题或建议，请联系开发团队。

**版本历史**:
- v1.0 (2026-01-27): 初始版本，实现核心功能

---

## 📄 许可证

本模块仅供内部使用，请勿外传。