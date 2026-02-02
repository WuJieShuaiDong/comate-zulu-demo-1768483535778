# macOS launchd 服务安装指南

本目录包含 macOS launchd 配置文件示例，用于实现开机自动启动和崩溃自动重启。

## 安装步骤

### 1. 修改配置文件

编辑 `com.quantbot.trader.plist` 和 `com.quantbot.web.plist`，将所有 `YOUR_USERNAME` 替换为你的实际用户名。

**快速替换命令：**

```bash
# 假设你的用户名是 xiaoliu
sed -i '' 's/YOUR_USERNAME/xiaoliu/g' com.quantbot.trader.plist
sed -i '' 's/YOUR_USERNAME/xiaoliu/g' com.quantbot.web.plist
```

### 2. 复制到 LaunchAgents 目录

```bash
cp com.quantbot.trader.plist ~/Library/LaunchAgents/
cp com.quantbot.web.plist ~/Library/LaunchAgents/
```

### 3. 验证配置文件语法

```bash
plutil -lint ~/Library/LaunchAgents/com.quantbot.trader.plist
plutil -lint ~/Library/LaunchAgents/com.quantbot.web.plist
```

如果输出 "OK"，说明配置文件格式正确。

### 4. 加载服务

```bash
# 加载交易机器人服务
launchctl load ~/Library/LaunchAgents/com.quantbot.trader.plist

# 加载Web面板服务
launchctl load ~/Library/LaunchAgents/com.quantbot.web.plist
```

### 5. 验证服务状态

```bash
# 查看已加载的服务
launchctl list | grep quantbot
```

应该看到类似输出：
```
12345	0	com.quantbot.trader
12346	0	com.quantbot.web
```

### 6. 立即启动（可选）

```bash
launchctl start com.quantbot.trader
launchctl start com.quantbot.web
```

## 管理命令

### 停止服务

```bash
launchctl stop com.quantbot.trader
launchctl stop com.quantbot.web
```

### 重启服务

```bash
launchctl kickstart -k gui/$(id -u)/com.quantbot.trader
launchctl kickstart -k gui/$(id -u)/com.quantbot.web
```

### 卸载服务

```bash
launchctl unload ~/Library/LaunchAgents/com.quantbot.trader.plist
launchctl unload ~/Library/LaunchAgents/com.quantbot.web.plist
```

### 删除配置文件

```bash
rm ~/Library/LaunchAgents/com.quantbot.trader.plist
rm ~/Library/LaunchAgents/com.quantbot.web.plist
```

## 配置说明

### 交易机器人配置 (com.quantbot.trader.plist)

- **定时启动：** 每天 9:00 自动启动
- **自动重启：** 进程崩溃后自动重启
- **开机启动：** 默认注释掉，如需开启请取消注释 `RunAtLoad`

### Web面板配置 (com.quantbot.web.plist)

- **开机启动：** 默认启用
- **自动重启：** 进程崩溃后自动重启
- **端口：** 8503

## 查看日志

```bash
# 交易机器人日志
tail -f ~/ComateProjects/comate-zulu-demo-1768483535778/quant_trading/data/bot.log

# Web面板日志
tail -f ~/ComateProjects/comate-zulu-demo-1768483535778/quant_trading/data/web.log

# 错误日志
tail -f ~/ComateProjects/comate-zulu-demo-1768483535778/quant_trading/data/bot_error.log
tail -f ~/ComateProjects/comate-zulu-demo-1768483535778/quant_trading/data/web_error.log
```

## 故障排查

### 服务无法启动

1. 检查 Python 路径是否正确：
```bash
which python3
```

2. 检查 Streamlit 路径是否正确：
```bash
which streamlit
```

3. 查看系统日志：
```bash
log show --predicate 'subsystem == "com.apple.launchd"' --last 10m | grep quantbot
```

### 权限问题

确保脚本和数据目录有正确的权限：
```bash
chmod +x ~/ComateProjects/comate-zulu-demo-1768483535778/quant_trading/auto_trader.py
chmod 755 ~/ComateProjects/comate-zulu-demo-1768483535778/quant_trading/data/
```

## 注意事项

1. **路径必须是绝对路径**：launchd 不支持相对路径和 `~` 符号
2. **环境变量**：launchd 环境可能与终端不同，确保所有依赖都使用绝对路径
3. **权限**：plist 文件建议设置为只读：`chmod 644 ~/Library/LaunchAgents/com.quantbot.*.plist`

## 卸载服务

如果不再需要自动启动功能：

```bash
# 1. 停止服务
launchctl stop com.quantbot.trader
launchctl stop com.quantbot.web

# 2. 卸载服务
launchctl unload ~/Library/LaunchAgents/com.quantbot.trader.plist
launchctl unload ~/Library/LaunchAgents/com.quantbot.web.plist

# 3. 删除配置文件
rm ~/Library/LaunchAgents/com.quantbot.trader.plist
rm ~/Library/LaunchAgents/com.quantbot.web.plist
```

之后仍可使用 `start_all.sh` 手动启动服务。