# 妖股基因系统自动化维护指南

## 📋 问题解决

### 问题1: ModuleNotFoundError: No module named 'demon_stock_gene'

**原因**: 在错误的目录下运行命令

**解决方案**:
```bash
# ❌ 错误（在项目根目录）
python3 -c "from demon_stock_gene import DemonStockGene; ..."

# ✅ 正确（在 quant_trading 目录）
cd quant_trading
python3 -c "from demon_stock_gene import DemonStockGene; ..."

# ✅ 或使用完整路径
cd /Users/xiaoliu/ComateProjects/comate-zulu-demo-1768483535778/quant_trading
python3 -c "from demon_stock_gene import DemonStockGene; ..."
```

---

## 🤖 自动化维护方案

### 方案1: Cron 定时任务（推荐）

#### 步骤1: 配置定时任务

```bash
cd quant_trading
./setup_cron.sh
```

**效果**: 
- ✅ 每个交易日（周一到周五）15:35 自动运行
- ✅ 自动增量更新妖股基因库
- ✅ 日志自动记录到 `logs/daily_maintenance_YYYYMMDD.log`

#### 步骤2: 验证定时任务

```bash
# 查看所有定时任务
crontab -l

# 应该看到类似输出：
# 35 15 * * 1-5 /Users/xiaoliu/.../quant_trading/daily_maintenance.sh
```

#### 步骤3: 手动测试

```bash
# 立即运行一次维护脚本（测试）
cd quant_trading
./daily_maintenance.sh
```

#### 步骤4: 查看日志

```bash
# 实时查看今天的维护日志
tail -f quant_trading/logs/daily_maintenance_$(date +%Y%m%d).log
```

---

### 方案2: LaunchAgent（macOS 推荐）

LaunchAgent 比 cron 更适合 macOS，开机自动加载且支持更复杂的调度。

#### 创建配置文件

```bash
cat > ~/Library/LaunchAgents/com.quant.demon_gene_maintenance.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.quant.demon_gene_maintenance</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/Users/xiaoliu/ComateProjects/comate-zulu-demo-1768483535778/quant_trading/daily_maintenance.sh</string>
    </array>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>15</integer>
        <key>Minute</key>
        <integer>35</integer>
        <key>Weekday</key>
        <integer>1</integer>
    </dict>
    
    <key>StandardOutPath</key>
    <string>/Users/xiaoliu/ComateProjects/comate-zulu-demo-1768483535778/quant_trading/logs/launchagent.log</string>
    
    <key>StandardErrorPath</key>
    <string>/Users/xiaoliu/ComateProjects/comate-zulu-demo-1768483535778/quant_trading/logs/launchagent_error.log</string>
    
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF
```

**注意**: 替换路径为你的实际项目路径！

#### 加载任务

```bash
# 加载配置
launchctl load ~/Library/LaunchAgents/com.quant.demon_gene_maintenance.plist

# 验证是否加载成功
launchctl list | grep demon_gene

# 手动触发测试
launchctl start com.quant.demon_gene_maintenance
```

#### 管理命令

```bash
# 停止任务
launchctl stop com.quant.demon_gene_maintenance

# 卸载任务
launchctl unload ~/Library/LaunchAgents/com.quant.demon_gene_maintenance.plist

# 查看状态
launchctl list | grep demon_gene
```

---

### 方案3: 手动运行（最简单）

如果不需要自动化，每天收盘后手动运行：

```bash
cd quant_trading
./daily_maintenance.sh
```

或使用 Python 命令：

```bash
cd quant_trading
python3 -c "from demon_stock_gene import DemonStockGene; DemonStockGene().update_gene_database()"
```

---

## 📊 维护脚本功能

`daily_maintenance.sh` 自动完成以下任务：

1. **智能检测**
   - 如果基因库不存在 → 自动构建测试版（100只）
   - 如果基因库已存在 → 执行增量更新

2. **日志记录**
   - 保存到 `logs/daily_maintenance_YYYYMMDD.log`
   - 自动清理7天前的旧日志

3. **统计报告**
   - 基因库总数
   - 超级妖股数量（≥80分）
   - 强妖股数量（60-79分）

---

## ?? 故障排查

### 问题1: cron 任务不执行

**检查方法**:
```bash
# 1. 确认任务已添加
crontab -l

# 2. 检查 cron 服务是否运行（macOS）
sudo launchctl list | grep cron

# 3. 查看系统日志
tail -f /var/log/system.log | grep cron
```

**解决方案**:
- macOS 需要给 Terminal/iTerm 授予"完全磁盘访问权限"
- 系统偏好设置 → 安全性与隐私 → 隐私 → 完全磁盘访问 → 添加 Terminal

### 问题2: Python 模块找不到

**原因**: cron 环境变量与手动运行不同

**解决方案**: 在 `daily_maintenance.sh` 中添加 Python 路径
```bash
# 在脚本顶部添加
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export PYTHONPATH="/Users/xiaoliu/ComateProjects/comate-zulu-demo-1768483535778/quant_trading:$PYTHONPATH"
```

### 问题3: 网络请求失败

**原因**: akshare 接口偶尔超时

**解决方案**: 脚本会自动重试，查看日志确认：
```bash
tail -f quant_trading/logs/daily_maintenance_$(date +%Y%m%d).log
```

---

## 📅 推荐执行时间

| 时间 | 任务 | 耗时 | 说明 |
|------|------|------|------|
| 15:35 | 增量更新 | 3-5分钟 | 每日交易日收盘后 |
| 周六10:00 | 完整重建 | 30-60分钟 | 可选，每周一次全量扫描 |

---

## ✅ 验证自动化是否工作

### 方法1: 手动触发测试

```bash
cd quant_trading
./daily_maintenance.sh
```

### 方法2: 查看明天的日志

```bash
# 明天 15:35 后查看
tail -f quant_trading/logs/daily_maintenance_$(date -v +1d +%Y%m%d).log
```

### 方法3: 检查基因库更新时间

```bash
ls -lh quant_trading/data/demon_gene_db.json
```

---

## 🎯 快速命令参考

```bash
# 配置自动化（一次性）
cd quant_trading && ./setup_cron.sh

# 手动维护
cd quant_trading && ./daily_maintenance.sh

# 查看今天日志
tail -f quant_trading/logs/daily_maintenance_$(date +%Y%m%d).log

# 查看定时任务
crontab -l

# 删除定时任务
crontab -e  # 手动删除包含 daily_maintenance.sh 的行
```

---

**创建时间**: 2026-01-27  
**维护者**: Zulu AI