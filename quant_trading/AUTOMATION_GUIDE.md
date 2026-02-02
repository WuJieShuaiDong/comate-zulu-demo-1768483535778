# 量化交易系统 - 完整自动化配置指南

## 目录
1. [快速启动](#快速启动)
2. [系统架构](#系统架构)
3. [启动脚本使用](#启动脚本使用)
4. [macOS 自动化配置](#macos-自动化配置)
5. [监控与维护](#监控与维护)
6. [故障排查](#故障排查)

---

## 快速启动

### 一键启动所有服务

```bash
cd quant_trading
chmod +x start_all.sh stop_all.sh
./start_all.sh start
```

**启动内容：**
- 🤖 交易机器人（后台运行）
- 🖥️ Web监控面板（端口 8503）

**访问面板：**
打开浏览器访问 `http://localhost:8503`

---

## 系统架构

### 核心组件

```
quant_trading/
├── auto_trader.py          # 交易机器人主程序
├── app.py                  # Streamlit Web监控面板
├── demon_stock_gene.py     # 妖股基因识别模块
├── money_effect_tracker.py # 赚钱效应追踪模块
├── market_sentiment.py     # 市场情绪分析模块
├── start_all.sh           # 一键启动脚本
├── stop_all.sh            # 停止脚本
└── data/
    ├── account.json       # 账户数据
    ├── trades.csv         # 交易记录
    ├── bot.log            # 机器人日志
    ├── demon_gene_db.json # 妖股基因库
    ├── bot.pid            # 机器人进程ID
    └── web.pid            # Web服务进程ID
```

### 数据流

```
市场数据 (akshare)
    ↓
赚钱效应分析 + 妖股基因识别
    ↓
交易策略执行 (auto_trader.py)
    ↓
账户数据更新 (account.json)
    ↓
Web面板展示 (app.py)
```

---

## 启动脚本使用

### start_all.sh - 一键启动

**基本用法：**

```bash
# 启动所有服务
./start_all.sh start

# 停止所有服务
./start_all.sh stop

# 重启服务
./start_all.sh restart

# 查看运行状态
./start_all.sh status

# 查看实时日志
./start_all.sh logs
```

**功能特性：**
- ✅ 自动检查 Python3 环境
- ✅ 自动检查并安装依赖
- ✅ 后台启动，不阻塞终端
- ✅ PID 管理，避免重复启动
- ✅ 彩色输出，清晰易读
- ✅ 日志记录，方便调试

**启动成功示例：**

```
╔══════════════════════════════════════════════════════════════╗
║                   量化交易系统启动器                           ║
║                   Quant Trading System                       ║
╚══════════════════════════════════════════════════════════════╝

✓ Python3 已就绪
✓ 依赖检查通过

启动交易机器人...
✓ 交易机器人启动成功 (PID: 12345)
启动前端监控面板...
✓ 前端面板启动成功 (PID: 12346)
访问地址: http://localhost:8503

=== 系统状态 ===
● 交易机器人: 运行中 (PID: 12345)
● 前端面板: 运行中 (PID: 12346)
  访问地址: http://localhost:8503
```

### stop_all.sh - 优雅停止

**功能：**
- 停止交易机器人
- 停止Web面板
- 清理残留进程
- 删除PID文件

```bash
./stop_all.sh
```

---

## macOS 自动化配置

### 方案1: 使用 launchd (推荐)

launchd 是 macOS 的系统级进程管理器，支持：
- ✅ 开机自动启动
- ✅ 崩溃自动重启
- ✅ 定时启动
- ✅ 进程监控

#### 1.1 创建交易机器人服务

创建文件 `~/Library/LaunchAgents/com.quantbot.trader.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.quantbot.trader</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/Users/YOUR_USERNAME/ComateProjects/comate-zulu-demo-1768483535778/quant_trading/auto_trader.py</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>/Users/YOUR_USERNAME/ComateProjects/comate-zulu-demo-1768483535778/quant_trading</string>
    
    <key>StandardOutPath</key>
    <string>/Users/YOUR_USERNAME/ComateProjects/comate-zulu-demo-1768483535778/quant_trading/data/bot.log</string>
    
    <key>StandardErrorPath</key>
    <string>/Users/YOUR_USERNAME/ComateProjects/comate-zulu-demo-1768483535778/quant_trading/data/bot_error.log</string>
    
    <!-- 定时启动: 每天早上 9:00 -->
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    
    <!-- 崩溃自动重启 -->
    <key>KeepAlive</key>
    <true/>
    
    <!-- 开机自动启动 (可选) -->
    <key>RunAtLoad</key>
    <true/>
    
    <!-- 防止在交易时间外占用资源 -->
    <key>ThrottleInterval</key>
    <integer>60</integer>
</dict>
</plist>
```

**注意：** 请将 `YOUR_USERNAME` 替换为你的实际用户名

#### 1.2 创建Web面板服务

创建文件 `~/Library/LaunchAgents/com.quantbot.web.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.quantbot.web</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/streamlit</string>
        <string>run</string>
        <string>/Users/YOUR_USERNAME/ComateProjects/comate-zulu-demo-1768483535778/quant_trading/app.py</string>
        <string>--server.port</string>
        <string>8503</string>
        <string>--server.headless</string>
        <string>true</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>/Users/YOUR_USERNAME/ComateProjects/comate-zulu-demo-1768483535778/quant_trading</string>
    
    <key>StandardOutPath</key>
    <string>/Users/YOUR_USERNAME/ComateProjects/comate-zulu-demo-1768483535778/quant_trading/data/web.log</string>
    
    <key>StandardErrorPath</key>
    <string>/Users/YOUR_USERNAME/ComateProjects/comate-zulu-demo-1768483535778/quant_trading/data/web_error.log</string>
    
    <!-- 崩溃自动重启 -->
    <key>KeepAlive</key>
    <true/>
    
    <!-- 开机自动启动 -->
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
```

#### 1.3 加载服务

```bash
# 加载交易机器人
launchctl load ~/Library/LaunchAgents/com.quantbot.trader.plist

# 加载Web面板
launchctl load ~/Library/LaunchAgents/com.quantbot.web.plist

# 立即启动
launchctl start com.quantbot.trader
launchctl start com.quantbot.web
```

#### 1.4 管理服务

```bash
# 查看服务状态
launchctl list | grep quantbot

# 停止服务
launchctl stop com.quantbot.trader
launchctl stop com.quantbot.web

# 卸载服务
launchctl unload ~/Library/LaunchAgents/com.quantbot.trader.plist
launchctl unload ~/Library/LaunchAgents/com.quantbot.web.plist
```

### 方案2: 使用 crontab (简单)

适合只需要定时启动的场景。

```bash
# 编辑 crontab
crontab -e

# 添加以下任务（每天9:00启动）
0 9 * * 1-5 cd /Users/YOUR_USERNAME/ComateProjects/comate-zulu-demo-1768483535778/quant_trading && ./start_all.sh start >> /tmp/quantbot_cron.log 2>&1

# 查看已配置的任务
crontab -l
```

**局限性：**
- ❌ 不支持崩溃自动重启
- ❌ 不支持进程监控
- ❌ 调试较困难

---

## 监控与维护

### 日志查看

```bash
# 实时查看交易机器人日志
tail -f quant_trading/data/bot.log

# 实时查看Web面板日志
tail -f quant_trading/data/web.log

# 使用启动脚本查看日志（推荐）
cd quant_trading && ./start_all.sh logs
```

### 关键日志位置

| 日志文件 | 路径 | 说明 |
|---------|------|------|
| 机器人日志 | `data/bot.log` | 交易决策、市场分析 |
| Web日志 | `data/web.log` | Streamlit运行日志 |
| 交易记录 | `data/trades.csv` | 完整交易历史 |
| 账户数据 | `data/account.json` | 实时资产状态 |

### 健康检查

```bash
# 检查进程是否运行
ps aux | grep "auto_trader.py"
ps aux | grep "streamlit"

# 使用启动脚本检查状态
cd quant_trading && ./start_all.sh status

# 检查端口占用
lsof -i :8503
```

### 数据备份

```bash
# 手动备份
tar -czf backup_$(date +%Y%m%d).tar.gz quant_trading/data/

# 自动备份脚本（添加到 crontab）
0 16 * * 1-5 cd /path/to/project && tar -czf backups/data_$(date +\%Y\%m\%d).tar.gz quant_trading/data/
```

---

## 故障排查

### 问题1: 启动失败

**症状：** `./start_all.sh start` 报错或进程立即退出

**排查步骤：**

1. 检查 Python 环境
```bash
python3 --version
which python3
```

2. 检查依赖
```bash
pip3 list | grep -E "streamlit|akshare|pandas"
```

3. 手动运行测试
```bash
cd quant_trading
python3 auto_trader.py  # 看是否有明确错误
```

4. 查看日志
```bash
cat data/bot.log
cat data/web.log
```

### 问题2: 妖股基因库为空

**症状：** 日志显示 "妖股基因库为空"

**解决方案：**
```bash
cd quant_trading
python3 -c "from demon_stock_gene import DemonStockGene; DemonStockGene().build_gene_database(max_stocks=100)"
```

**建议：** 在周末网络稳定时构建基因库

### 问题3: Web面板无法访问

**症状：** 浏览器打不开 `http://localhost:8503`

**排查步骤：**

1. 检查进程
```bash
./start_all.sh status
```

2. 检查端口
```bash
lsof -i :8503
```

3. 重启服务
```bash
./start_all.sh restart
```

4. 手动启动调试
```bash
streamlit run app.py --server.port 8503
```

### 问题4: 权限错误

**症状：** `Permission denied: './start_all.sh'`

**解决方案：**
```bash
chmod +x start_all.sh stop_all.sh
```

### 问题5: launchd 服务不启动

**排查步骤：**

1. 检查 plist 语法
```bash
plutil -lint ~/Library/LaunchAgents/com.quantbot.trader.plist
```

2. 查看系统日志
```bash
log show --predicate 'subsystem == "com.apple.launchd"' --last 10m
```

3. 检查文件路径
```bash
ls -la /usr/local/bin/python3
ls -la /path/to/project/quant_trading/auto_trader.py
```

---

## 性能优化

### 1. 减少网络请求频率

编辑 `auto_trader.py`，调整扫描间隔：

```python
# 从 300 秒（5分钟）调整为 600 秒（10分钟）
time.sleep(600)
```

### 2. 限制候选股扫描数量

```python
# 从 30 只减少到 20 只
if scan_count >= 20:
    break
```

### 3. 使用缓存减少重复计算

妖股基因系统已内置缓存，无需额外配置。

---

## 安全建议

1. **敏感数据保护**
   - `account.json` 包含资产数据，建议设置权限：
   ```bash
   chmod 600 quant_trading/data/account.json
   ```

2. **日志文件定期清理**
   ```bash
   # 只保留最近7天的日志
   find quant_trading/data/ -name "*.log" -mtime +7 -delete
   ```

3. **备份重要数据**
   - 每周备份 `data/` 目录
   - 备份妖股基因库 `demon_gene_db.json`

4. **监控异常行为**
   - 定期检查 `trades.csv` 是否有异常交易
   - 监控账户净值变化

---

## 快速参考

### 常用命令

```bash
# 启动
cd quant_trading && ./start_all.sh start

# 停止
cd quant_trading && ./stop_all.sh

# 查看状态
cd quant_trading && ./start_all.sh status

# 查看日志
cd quant_trading && ./start_all.sh logs

# 重启
cd quant_trading && ./start_all.sh restart
```

### 关键文件权限

```bash
# 脚本可执行
chmod +x start_all.sh stop_all.sh daily_maintenance.sh

# 数据目录可写
chmod 755 data/

# 敏感文件保护
chmod 600 data/account.json
```

### 时间配置

| 事件 | 时间 | 说明 |
|------|------|------|
| 交易时段 | 9:15-11:30, 13:00-15:00 | 机器人活跃时段 |
| 定时维护 | 每天 15:35 | 更新妖股基因库 |
| 定时启动 | 每天 9:00 | launchd 自动启动 |
| 数据备份 | 每天 16:00 | 建议备份时间 |

---

## 联系与支持

如有问题，请查看：
1. 项目 README.md
2. 相关文档：
   - `DEMON_GENE_SYSTEM.md` - 妖股基因系统详解
   - `MONEY_EFFECT_SYSTEM.md` - 赚钱效应系统详解
   - `QUICK_START_GUIDE.md` - 快速入门指南

---

**版本：** 1.0  
**更新日期：** 2026-01-27  
**作者：** Zulu AI