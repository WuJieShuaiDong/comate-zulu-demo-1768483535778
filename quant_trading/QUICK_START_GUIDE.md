# 妖股基因系统 - 快速上手指南

## 🎯 两个核心问题的解决方案

### 问题1: ModuleNotFoundError 

**你的错误**:
```bash
python3 -c "from demon_stock_gene import DemonStockGene; DemonStockGene().update_gene_database()"
# ❌ ModuleNotFoundError: No module named 'demon_stock_gene'
```

**正确做法**:
```bash
# 方法1: 先进入 quant_trading 目录
cd quant_trading
python3 -c "from demon_stock_gene import DemonStockGene; DemonStockGene().update_gene_database()"

# 方法2: 使用完整路径
cd /Users/xiaoliu/ComateProjects/comate-zulu-demo-1768483535778/quant_trading
python3 -c "from demon_stock_gene import DemonStockGene; DemonStockGene().update_gene_database()"

# 方法3: 使用维护脚本（推荐）
cd quant_trading
./daily_maintenance.sh
```

---

### 问题2: 自动化每日维护

**一键配置（推荐）**:
```bash
cd quant_trading
./setup_cron.sh
```

**效果**: 
- ✅ 每个交易日 15:35 自动运行
- ✅ 日志自动保存
- ✅ 无需手动干预

---

## 🚀 完整使用流程

### 第一步：首次构建基因库（收盘后运行）

**重要**: 必须在**收盘后（15:30之后）或周末**运行，交易时间内接口不稳定！

```bash
cd quant_trading

# 选项1: 使用快速启动脚本（最简单）
./quick_start_demon_gene.sh
# 选择: 1 (测试版100只，10-20分钟)

# 选项2: 直接命令
python3 -c "from demon_stock_gene import DemonStockGene; DemonStockGene().build_gene_database(max_stocks=100)"
```

**首次构建预计耗时**: 10-20分钟（100只）

---

### 第二步：配置自动维护

```bash
cd quant_trading
./setup_cron.sh
```

**输入 `y` 确认**，然后验证：

```bash
# 查看定时任务
crontab -l

# 应该看到类似：
# 35 15 * * 1-5 /Users/xiaoliu/.../quant_trading/daily_maintenance.sh
```

---

### 第三步：启动交易机器人

```bash
cd quant_trading

# 前台运行（测试）
python3 auto_trader.py

# 或后台运行（生产）
nohup python3 auto_trader.py > logs/trader.log 2>&1 &
```

---

## 📅 日常使用

### 自动化运行（已配置 cron）

**无需任何操作！** 系统会在每个交易日 15:35 自动：
1. 增量更新妖股基因库（3-5分钟）
2. 记录日志到 `logs/daily_maintenance_YYYYMMDD.log`
3. 清理7天前的旧日志

### 查看维护日志

```bash
# 查看今天的维护日志
tail -f quant_trading/logs/daily_maintenance_$(date +%Y%m%d).log

# 查看最近的维护记录
ls -lht quant_trading/logs/daily_maintenance_*.log | head -5
```

### 手动触发维护（可选）

```bash
cd quant_trading
./daily_maintenance.sh
```

---

## 🔍 验证系统是否工作

### 1. 检查基因库

```bash
cd quant_trading

# 查看基因库文件
ls -lh data/demon_gene_db.json

# 查看妖股排行榜
./quick_start_demon_gene.sh  # 选择选项4
```

### 2. 查看交易日志

```bash
# 实时查看交易机器人日志
tail -f quant_trading/data/bot.log

# 搜索妖股相关日志
grep "妖股" quant_trading/data/bot.log | tail -20
```

### 3. 测试妖股基因查询

```bash
cd quant_trading
python3 << 'EOF'
from demon_stock_gene import DemonStockGene

tracker = DemonStockGene()
print(f"基因库总数: {len(tracker.gene_db)} 只\n")

# 获取高分妖股
high_gene = tracker.get_high_gene_stocks(min_score=60)
if high_gene:
    print("妖股排行榜 Top 10:")
    for i, stock in enumerate(high_gene[:10], 1):
        print(f"{i:2d}. {stock['name']:8s} ({stock['symbol']}) "
              f"基因:{stock['gene_score']:3.0f}分")
else:
    print("基因库为空，请先运行构建命令")
EOF
```

---

## ⚠️ 常见问题解决

### Q1: 基因库构建失败（网络错误）

**原因**: akshare 接口在交易时间内不稳定

**解决方案**:
1. **必须在收盘后（15:30之后）或周末运行**
2. 如果仍失败，等待10分钟后重试
3. 检查网络连接

```bash
# 重试构建
cd quant_trading
python3 -c "from demon_stock_gene import DemonStockGene; DemonStockGene().build_gene_database(max_stocks=100)"
```

---

### Q2: cron 任务不执行

**检查方法**:
```bash
# 1. 确认任务已添加
crontab -l

# 2. 查看明天的日志（需等到15:35后）
tail -f quant_trading/logs/daily_maintenance_$(date -v +1d +%Y%m%d).log
```

**macOS 特殊处理**:
1. 系统偏好设置 → 安全性与隐私 → 隐私
2. 完全磁盘访问 → 添加 Terminal 或 iTerm
3. 重启 Terminal

---

### Q3: 基因库总是0只

**原因**: 首次构建未成功

**解决方案**:
```bash
cd quant_trading

# 删除空基因库
rm -f data/demon_gene_db.json

# 收盘后重新构建（必须等到15:30后！）
python3 -c "from demon_stock_gene import DemonStockGene; DemonStockGene().build_gene_database(max_stocks=100)"
```

---

## 📊 系统状态检查清单

在正式使用前，请确认以下事项：

- [ ] 基因库已构建（`data/demon_gene_db.json` 存在且>1KB）
- [ ] 定时任务已配置（`crontab -l` 能看到任务）
- [ ] 维护脚本可执行（`./daily_maintenance.sh` 能运行）
- [ ] 交易机器人能启动（`python3 auto_trader.py` 无报错）
- [ ] 日志目录已创建（`logs/` 目录存在）

**检查命令**:
```bash
cd quant_trading

echo "1. 基因库文件:"
ls -lh data/demon_gene_db.json 2>/dev/null || echo "   ❌ 未构建"

echo -e "\n2. 定时任务:"
crontab -l 2>/dev/null | grep daily_maintenance || echo "   ❌ 未配置"

echo -e "\n3. 维护脚本:"
[ -x daily_maintenance.sh ] && echo "   ✅ 可执行" || echo "   ❌ 无执行权限"

echo -e "\n4. 日志目录:"
[ -d logs ] && echo "   ✅ 已创建" || echo "   ❌ 不存在"

echo -e "\n5. 基因库数量:"
python3 -c "from demon_stock_gene import DemonStockGene; print(f'   {len(DemonStockGene().gene_db)} 只')"
```

---

## 🎯 推荐操作时间表

| 时间 | 操作 | 说明 |
|------|------|------|
| **首次使用** | 构建基因库（100只） | 10-20分钟，验证功能 |
| **周末** | 完整构建（5000只） | 30-60分钟，正式使用 |
| **每日15:35** | 自动增量更新 | 3-5分钟，cron自动执行 |
| **盘中9:30-15:00** | 交易机器人运行 | 自动选股交易 |

---

## 📞 快速命令参考卡

```bash
# ===== 进入项目目录 =====
cd quant_trading

# ===== 基因库管理 =====
# 首次构建（收盘后）
python3 -c "from demon_stock_gene import DemonStockGene; DemonStockGene().build_gene_database(max_stocks=100)"

# 手动更新
./daily_maintenance.sh

# 查询排行榜
./quick_start_demon_gene.sh  # 选4

# ===== 自动化配置 =====
# 配置定时任务
./setup_cron.sh

# 查看定时任务
crontab -l

# ===== 日志查看 =====
# 维护日志
tail -f logs/daily_maintenance_$(date +%Y%m%d).log

# 交易日志
tail -f data/bot.log

# ===== 交易机器人 =====
# 启动
python3 auto_trader.py

# 后台启动
nohup python3 auto_trader.py > logs/trader.log 2>&1 &

# 停止
pkill -f auto_trader.py
```

---

## ✅ 成功标志

当你看到以下输出时，说明系统已正常工作：

```bash
# 1. 基因库构建成功
💾 基因库保存成功: 100 只股票

# 2. 交易机器人启动日志
✅ 赚钱效应追踪模块加载成功
✅ 妖股基因模块加载成功
🧬 妖股基因追踪器已激活 (基因库: 100 只)

# 3. 龙头识别日志
🧬 妖股基因增强后的龙头排行：
  1. 某某股份(600xxx) 总分:95 (龙头:75 + 基因:85) [超级妖股🔥]
```

---

**创建时间**: 2026-01-27  
**适用版本**: v3.0  
**维护者**: Zulu AI

**下一步**: 收盘后运行 `cd quant_trading && python3 -c "from demon_stock_gene import DemonStockGene; DemonStockGene().build_gene_database(max_stocks=100)"`