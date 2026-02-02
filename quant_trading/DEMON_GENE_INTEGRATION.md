# 妖股基因系统集成指南

## 📋 目录
- [快速开始](#快速开始)
- [集成步骤](#集成步骤)
- [API接口说明](#api接口说明)
- [实战案例](#实战案例)
- [性能优化](#性能优化)

---

## 🚀 快速开始

### 1. 首次构建基因库（收盘后运行，耗时20-40分钟）

```bash
cd quant_trading
python3 -c "from demon_stock_gene import DemonStockGene; DemonStockGene().build_gene_database(max_stocks=5000)"
```

### 2. 每日增量更新（建议每日收盘后运行，耗时3-5分钟）

```bash
python3 -c "from demon_stock_gene import DemonStockGene; DemonStockGene().update_gene_database()"
```

### 3. 测试验证

```bash
python3 test_demon_gene.py
```

---

## 🔧 集成步骤

### 步骤1: 在 auto_trader.py 导入模块

在文件顶部添加导入：

```python
# 导入妖股基因识别模块
try:
    from demon_stock_gene import DemonStockGene
    DEMON_GENE_AVAILABLE = True
    logging.info("✅ 妖股基因模块加载成功")
except ImportError:
    DEMON_GENE_AVAILABLE = False
    logging.warning("⚠️  demon_stock_gene.py 未找到，将不使用妖股基因增强")
```

### 步骤2: 初始化妖股基因追踪器

在 `AutoTrader` 类的 `__init__` 方法中添加：

```python
def __init__(self, trader: BaseTrader):
    self.trader = trader
    
    # 初始化赚钱效应追踪器
    if MONEY_EFFECT_AVAILABLE:
        self.money_tracker = MoneyEffectTracker()
    else:
        self.money_tracker = None
    
    # 初始化妖股基因追踪器（新增）
    if DEMON_GENE_AVAILABLE:
        self.demon_gene_tracker = DemonStockGene()
        logging.info("🧬 妖股基因追踪器初始化成功")
    else:
        self.demon_gene_tracker = None
```

### 步骤3: 增强龙头股识别逻辑

修改 `select_stocks` 方法，在龙头评分环节叠加妖股基因分数：

```python
def select_stocks(self):
    """
    智能选股策略（集成妖股基因）
    """
    sentiment_result = check_market_sentiment_enhanced(self.money_tracker)
    
    # ... 原有代码 ...
    
    # 获取龙头股候选
    if self.money_tracker:
        leaders = self.money_tracker.find_leading_stocks(min_score=60)
    else:
        leaders = []
    
    # 【核心增强】叠加妖股基因评分
    enhanced_leaders = []
    for stock in leaders:
        symbol = stock['symbol']
        base_score = stock['score']
        
        # 获取妖股基因评分
        gene_score = 0
        if self.demon_gene_tracker:
            gene_score = self.demon_gene_tracker.get_gene_score(symbol)
        
        # 基因加成规则
        if gene_score >= 80:
            bonus = 20  # 超级妖股基因，优先级最高
            stock['gene_bonus'] = bonus
            stock['gene_level'] = '超级妖股'
        elif gene_score >= 60:
            bonus = 10  # 强妖股基因
            stock['gene_bonus'] = bonus
            stock['gene_level'] = '强妖股'
        else:
            bonus = 0
            stock['gene_bonus'] = 0
            stock['gene_level'] = '普通'
        
        # 更新最终评分
        stock['final_score'] = base_score + bonus
        stock['gene_score'] = gene_score
        enhanced_leaders.append(stock)
    
    # 按最终评分排序
    enhanced_leaders.sort(key=lambda x: x['final_score'], reverse=True)
    
    # 日志输出
    logging.info(f"🧬 妖股基因增强后龙头:")
    for stock in enhanced_leaders[:5]:
        logging.info(f"  {stock['name']} ({stock['symbol']}): "
                    f"基础{stock['score']} + 基因{stock['gene_bonus']} = {stock['final_score']} "
                    f"[{stock['gene_level']}]")
    
    # 选出Top N只股票
    max_positions = sentiment_result['max_positions']
    selected = enhanced_leaders[:max_positions]
    
    return selected
```

### 步骤4: 优化止盈策略

在 `check_positions` 方法中，根据妖股基因调整止盈策略：

```python
def check_positions(self):
    """
    持仓检查（集成妖股基因止盈策略）
    """
    for symbol, pos in list(self.trader.positions.items()):
        # ... 原有代码 ...
        
        # 获取妖股基因评分
        gene_score = 0
        if self.demon_gene_tracker:
            gene_score = self.demon_gene_tracker.get_gene_score(symbol)
        
        # 动态止盈策略
        if gene_score >= 80:
            # 超级妖股：只在断板时走
            if latest_price < pos['cost'] * (1 - STOP_LOSS_PCT):
                self.trader.sell(symbol, latest_price, "妖股止损")
            # 否则持有不动，不设止盈
        elif gene_score >= 60:
            # 强妖股：30%止盈
            if latest_price >= pos['cost'] * 1.30:
                self.trader.sell(symbol, latest_price, "强妖股止盈30%")
            elif latest_price < pos['cost'] * (1 - STOP_LOSS_PCT):
                self.trader.sell(symbol, latest_price, "止损")
        else:
            # 普通股：20%止盈
            if latest_price >= pos['cost'] * (1 + TAKE_PROFIT_PCT):
                self.trader.sell(symbol, latest_price, f"止盈{TAKE_PROFIT_PCT*100:.0f}%")
            elif latest_price < pos['cost'] * (1 - STOP_LOSS_PCT):
                self.trader.sell(symbol, latest_price, "止损")
```

---

## 📚 API接口说明

### 核心类: `DemonStockGene`

#### 初始化
```python
from demon_stock_gene import DemonStockGene
tracker = DemonStockGene()
```

#### 主要方法

**1. 构建基因库（首次运行）**
```python
tracker.build_gene_database(max_stocks=5000)
```
- **参数**: `max_stocks` - 最大扫描股票数
- **耗时**: 约20-40分钟
- **输出**: `data/demon_gene_db.json`

**2. 增量更新（每日运行）**
```python
tracker.update_gene_database()
```
- **耗时**: 约3-5分钟
- **策略**: 更新涨停股 + 高分妖股

**3. 查询基因评分**
```python
score = tracker.get_gene_score('600519')  # 返回 0-100
```
- **性能**: < 0.01秒 (JSON缓存)

**4. 获取完整基因数据**
```python
data = tracker.get_gene_data('600519')
# 返回: {
#     'name': '贵州茅台',
#     'gene_score': 85,
#     'max_continuous_board': 5,
#     'last_board_date': '2024-03-15',
#     'monthly_max_gain': 68.5,
#     'avg_amplitude': 9.2,
#     'zt_count_6m': 8,
#     'update_time': '2026-01-27'
# }
```

**5. 获取高分妖股列表**
```python
demons = tracker.get_high_gene_stocks(min_score=60)
# 返回: [
#     {'symbol': '600519', 'name': '贵州茅台', 'gene_score': 85, ...},
#     ...
# ]
```

**6. 统计信息**
```python
stats = tracker.get_statistics()
# 返回: {
#     'total_stocks': 5000,
#     'high_gene_count': 234,
#     'super_demon_count': 45,
#     'avg_gene_score': 32.5,
#     'max_gene_stock': {...}
# }
```

### 便捷函数

```python
from demon_stock_gene import quick_query, get_demon_list

# 快速查询
result = quick_query('600519')

# 快速获取妖股列表
demons = get_demon_list(min_score=70)
```

---

## ?? 实战案例

### 案例1: 龙头股识别增强

**场景**: 今日涨停池中有3只股票，需要判断哪只是真龙头

```python
candidates = [
    {'symbol': '300750', 'name': '宁德时代', 'base_score': 65},
    {'symbol': '600519', 'name': '贵州茅台', 'base_score': 62},
    {'symbol': '000858', 'name': '五粮液', 'base_score': 60}
]

tracker = DemonStockGene()

for stock in candidates:
    gene_score = tracker.get_gene_score(stock['symbol'])
    
    if gene_score >= 80:
        bonus = 20
    elif gene_score >= 60:
        bonus = 10
    else:
        bonus = 0
    
    final_score = stock['base_score'] + bonus
    
    print(f"{stock['name']}: 基础{stock['base_score']} + 基因{bonus} = {final_score}")

# 输出示例:
# 宁德时代: 基础65 + 基因20 = 85  ← 选这只！
# 贵州茅台: 基础62 + 基因10 = 72
# 五粮液: 基础60 + 基因0 = 60
```

### 案例2: 动态止盈策略

**场景**: 持仓中有不同基因等级的股票，需要差异化止盈

```python
positions = [
    {'symbol': '300750', 'cost': 100, 'current': 120},  # 超级妖股
    {'symbol': '600519', 'cost': 100, 'current': 125},  # 强妖股
    {'symbol': '000858', 'cost': 100, 'current': 122}   # 普通股
]

tracker = DemonStockGene()

for pos in positions:
    gene_score = tracker.get_gene_score(pos['symbol'])
    profit_pct = (pos['current'] - pos['cost']) / pos['cost'] * 100
    
    if gene_score >= 80:
        action = "持有不动" if profit_pct < 50 else "考虑止盈"
    elif gene_score >= 60:
        action = "止盈" if profit_pct >= 30 else "继续持有"
    else:
        action = "止盈" if profit_pct >= 20 else "继续持有"
    
    print(f"{pos['symbol']}: 盈利{profit_pct:.1f}% → {action}")

# 输出:
# 300750: 盈利20.0% → 持有不动  (超级妖股，继续拿)
# 600519: 盈利25.0% → 继续持有 (强妖股，30%才走)
# 000858: 盈利22.0% → 止盈     (普通股，20%就走)
```

### 案例3: 盘中快速决策

**场景**: 盘中出现新涨停，需要快速判断是否追入

```python
tracker = DemonStockGene()

new_zt_symbol = "300999"
gene_score = tracker.get_gene_score(new_zt_symbol)

if gene_score >= 80:
    decision = "🔥 优先追入！超级妖股"
elif gene_score >= 60:
    decision = "✅ 可以追入，强妖股"
elif gene_score >= 40:
    decision = "⚠️  谨慎追入，中等妖股"
else:
    decision = "❌ 不建议追，无妖股基因"

print(f"{new_zt_symbol} 基因评分: {gene_score} → {decision}")
```

---

## ⚡ 性能优化

### 1. 缓存策略

基因数据存储在 `data/demon_gene_db.json`，使用JSON格式：
- **查询速度**: < 0.01秒
- **内存占用**: 约5-10MB (5000只股票)
- **缓存有效期**: 每日更新

### 2. 增量更新策略

```python
# 策略1: 仅更新涨停股
today_zt_stocks = get_zt_pool()  # 约50-100只
update_stocks(today_zt_stocks)   # 耗时: 5-10分钟

# 策略2: 更新高分妖股
high_gene_stocks = get_high_gene_stocks(min_score=60)  # 约200-300只
update_stocks(high_gene_stocks)  # 耗时: 20-30分钟
```

### 3. 并行处理（可选）

对于大规模更新，可使用多线程：

```python
from concurrent.futures import ThreadPoolExecutor

def update_with_parallel(symbols, max_workers=5):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(calculate_gene_score, s) for s in symbols]
        results = [f.result() for f in futures]
    return results
```

### 4. 容错设计

```python
# 部分股票数据缺失不影响整体运行
try:
    gene_data = calculate_gene_score(symbol)
    if gene_data:
        gene_db[symbol] = gene_data
except Exception as e:
    logging.warning(f"⚠️  {symbol} 计算失败: {e}")
    continue  # 跳过失败的股票，继续处理下一只
```

---

## 📊 评分标准详解

### 评分维度（总分100分）

| 维度 | 权重 | 评分标准 |
|------|------|----------|
| **连板历史** | 40分 | ≥5板:40分, ≥3板:30分, ≥2板:20分, 1板:10分 |
| **暴涨记录** | 30分 | 月涨≥80%:30分, ≥50%:20分, ≥30%:10分 |
| **炒作频率** | 20分 | 半年涨停≥5次:20分, ≥3次:15分, ≥1次:10分 |
| **活跃度** | 10分 | 日均振幅≥10%:10分, ≥8%:5分 |

### 等级划分

- **超级妖股** (≥80分): 具备极强炒作基因，优先级最高
- **强妖股** (60-79分): 有明显妖股特征，可重点关注
- **中等妖股** (40-59分): 有一定炒作潜力，谨慎跟进
- **普通股** (<40分): 无明显妖股基因，常规策略

---

## 🔍 数据文件说明

### demon_gene_db.json 结构

```json
{
  "600519": {
    "name": "贵州茅台",
    "gene_score": 85,
    "max_continuous_board": 5,
    "last_board_date": "2024-03-15",
    "monthly_max_gain": 68.5,
    "avg_amplitude": 9.2,
    "zt_count_6m": 8,
    "update_time": "2026-01-27"
  },
  "300750": {
    "name": "宁德时代",
    "gene_score": 92,
    ...
  }
}
```

### 文件维护

- **备份**: 建议定期备份 `demon_gene_db.json`
- **清理**: 每季度清理一次，移除长期无交易的股票
- **恢复**: 如文件损坏，重新运行 `build_gene_database()`

---

## ❓ FAQ

**Q1: 首次构建需要多久？**
A: 扫描5000只股票约需20-40分钟，建议收盘后运行。

**Q2: 每日更新必须做吗？**
A: 建议每日运行，保持数据时效性。如果某天未更新，不影响使用，只是数据略旧。

**Q3: 如何处理ST股票？**
A: 系统自动计算所有股票，但在实际选股时可通过股票名称过滤ST股。

**Q4: 基因评分会变吗？**
A: 会的。随着股票走势变化（新连板、新暴涨），基因评分会动态更新。

**Q5: 能用于其他市场吗？**
A: 当前仅支持A股。如需支持港股/美股，需修改数据接口。

---

## 📝 更新日志

### v1.0 (2026-01-27)
- ✅ 完成核心功能开发
- ✅ 实现4维评分系统
- ✅ 集成到auto_trader.py
- ✅ 测试套件完成

---

## 📞 技术支持

如有问题，请查看:
1. `test_demon_gene.py` - 测试示例
2. `demon_stock_gene.py` - 源码注释
3. 或联系开发团队

**开发者**: Zulu AI  
**版本**: 1.0  
**最后更新**: 2026-01-27