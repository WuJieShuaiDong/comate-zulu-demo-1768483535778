# 量化交易系统云端部署完全指南 🚀

## 📋 部署概览

本指南将帮助您将量化交易系统部署到云服务器，实现7×24小时稳定运行。

---

## 第一步：购买云服务器 (约5分钟)

### 推荐方案对比

| 云服务商 | 配置推荐 | 价格/月 | 优点 |
|---------|---------|---------|------|
| **阿里云** | 2核4G/5M带宽 | ¥99 | 国内访问快，新用户优惠大 |
| **腾讯云** | 2核4G/5M带宽 | ¥95 | 送免费域名，界面友好 |
| **华为云** | 2核4G/5M带宽 | ¥89 | 性价比高 |

### 具体购买步骤 (以阿里云为例)

1. **注册账号**
   - 访问：https://www.aliyun.com
   - 点击右上角"免费注册"
   - 完成手机号验证和实名认证

2. **购买云服务器**
   - 进入"产品" → "云服务器ECS"
   - 选择"一键购买"
   ```
   地域：随便选（推荐：华东-上海）
   实例规格：2核4G
   镜像：Ubuntu 22.04 64位
   带宽：5Mbps
   系统盘：40GB
   购买时长：1个月（可按需选择）
   ```
   - 设置登录密码（务必记住！）
   - 勾选协议，点击"立即购买"

3. **获取服务器信息**
   - 进入"控制台" → "云服务器ECS" → "实例"
   - 记录下：
     - **公网IP**：例如 `120.55.123.45`
     - **登录密码**：刚才设置的密码

---

## 第二步：购买域名 (可选，约3分钟)

### 如果需要域名访问

1. **购买域名**
   - 在阿里云控制台搜索"域名注册"
   - 输入想要的域名（例如：myquant.top）
   - 选择便宜的后缀：.top/.xyz/.site（首年10-30元）
   - 购买并完成实名认证

2. **域名解析**
   - 进入"域名控制台"
   - 点击域名后的"解析"
   - 添加记录：
   ```
   记录类型：A
   主机记录：@
   记录值：你的服务器公网IP
   TTL：10分钟
   ```
   - 再添加一条：
   ```
   记录类型：A
   主机记录：www
   记录值：你的服务器公网IP
   TTL：10分钟
   ```

### 如果不需要域名
- 直接使用 `http://服务器公网IP:8503` 访问即可

---

## 第三步：连接服务器 (约2分钟)

### Windows用户

1. **下载SSH工具**
   - 推荐：[FinalShell](https://www.hostbuf.com/t/988.html)
   - 或使用：PuTTY、XShell

2. **连接服务器**
   - 打开FinalShell
   - 点击"SSH连接"
   - 输入：
     ```
     名称：我的量化服务器
     主机：你的服务器公网IP
     端口：22
     用户名：root
     密码：购买时设置的密码
     ```
   - 点击"确定"连接

### Mac/Linux用户

打开终端，输入：
```bash
ssh root@你的服务器公网IP
# 输入密码后回车
```

---

## 第四步：服务器环境配置 (约5分钟)

连接服务器后，**复制粘贴**以下命令（一次一条）：

### 1. 更新系统
```bash
apt update && apt upgrade -y
```

### 2. 安装Python 3.10
```bash
apt install -y python3.10 python3.10-venv python3-pip
```

### 3. 安装Git
```bash
apt install -y git
```

### 4. 安装依赖工具
```bash
apt install -y curl wget vim screen
```

---

## 第五步：部署项目 (约3分钟)

### 1. 克隆项目
```bash
cd /root
git clone https://github.com/你的用户名/你的项目名.git
cd 你的项目名/quant_trading
```

### 2. 安装Python依赖
```bash
pip3 install -r requirements.txt
```

如果没有 `requirements.txt`，手动安装：
```bash
pip3 install akshare pandas numpy requests streamlit
```

### 3. 配置防火墙（开放8503端口）
```bash
# 如果使用阿里云/腾讯云，需在控制台添加安全组规则
# 规则：允许 TCP 8503 端口入方向
```

**阿里云安全组配置**：
1. 进入ECS控制台 → 实例 → 更多 → 网络和安全组 → 安全组配置
2. 点击"配置规则" → "添加安全组规则"
3. 填写：
   ```
   规则方向：入方向
   授权策略：允许
   协议类型：TCP
   端口范围：8503/8503
   授权对象：0.0.0.0/0
   ```

---

## 第六步：启动系统 (约1分钟)

### 方式1：使用Screen保持后台运行 (推荐)

```bash
cd /root/你的项目名/quant_trading

# 启动交易机器人
screen -S trader
python3 auto_trader.py
# 按 Ctrl+A，然后按 D 退出screen（程序继续运行）

# 启动前端面板
screen -S web
streamlit run app.py --server.port 8503 --server.address 0.0.0.0
# 按 Ctrl+A，然后按 D 退出screen
```

### 方式2：使用启动脚本
```bash
cd /root/你的项目名/quant_trading
chmod +x start_all.sh
./start_all.sh start
```

### 查看运行状态
```bash
# 查看所有screen会话
screen -ls

# 恢复到某个screen
screen -r trader   # 查看交易机器人
screen -r web      # 查看前端面板

# 停止服务
screen -S trader -X quit
screen -S web -X quit
```

---

## 第七步：访问系统 ✅

### 浏览器访问
```
# 使用IP访问
http://你的服务器公网IP:8503

# 或使用域名访问（如果配置了域名）
http://你的域名.com:8503
```

---

## 🔧 常见问题解决

### 问题1：无法访问8503端口
**解决方案**：
```bash
# 1. 检查服务是否运行
ps aux | grep streamlit

# 2. 检查端口监听
netstat -tlnp | grep 8503

# 3. 检查防火墙
ufw status
ufw allow 8503/tcp
```

### 问题2：访问速度慢
**解决方案**：
- 在app.py开头添加CDN镜像：
```python
import os
os.environ['STREAMLIT_SERVER_ENABLE_STATIC_SERVING'] = 'true'
```

### 问题3：服务异常停止
**解决方案**：
```bash
# 查看日志
cd /root/你的项目名/quant_trading
tail -100 data/bot.log
tail -100 logs/app.log

# 重启服务
./start_all.sh restart
```

### 问题4：进程被杀（内存不足）
**解决方案**：
```bash
# 创建swap交换空间（临时增加内存）
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

---

## 🚀 进阶配置：开机自启动

创建systemd服务：

### 1. 创建交易机器人服务
```bash
cat > /etc/systemd/system/quant-trader.service << 'EOF'
[Unit]
Description=Quant Trading Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/你的项目名/quant_trading
ExecStart=/usr/bin/python3 auto_trader.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

### 2. 创建前端服务
```bash
cat > /etc/systemd/system/quant-web.service << 'EOF'
[Unit]
Description=Quant Trading Web
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/你的项目名/quant_trading
ExecStart=/usr/bin/streamlit run app.py --server.port 8503 --server.address 0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

### 3. 启用并启动服务
```bash
systemctl daemon-reload
systemctl enable quant-trader
systemctl enable quant-web
systemctl start quant-trader
systemctl start quant-web

# 查看状态
systemctl status quant-trader
systemctl status quant-web
```

---

## 📊 监控和维护

### 日常检查命令
```bash
# 查看服务状态
systemctl status quant-trader quant-web

# 查看实时日志
tail -f /root/你的项目名/quant_trading/data/bot.log

# 查看资源占用
htop  # 需要先安装：apt install htop

# 查看磁盘空间
df -h

# 重启服务
systemctl restart quant-trader quant-web
```

### 定期维护
```bash
# 每周清理日志（防止占满磁盘）
cd /root/你的项目名/quant_trading
find logs -name "*.log" -mtime +7 -delete
find data -name "*.log" -mtime +7 -delete
```

---

## 🎉 部署完成检查清单

- [ ] 服务器购买并获得公网IP
- [ ] 域名购买并完成解析（可选）
- [ ] SSH成功连接服务器
- [ ] Python环境安装成功
- [ ] 项目代码克隆成功
- [ ] 依赖安装完成
- [ ] 安全组规则配置（8503端口开放）
- [ ] 交易机器人启动成功
- [ ] 前端面板启动成功
- [ ] 浏览器可以访问系统

---

## 💡 成本估算

| 项目 | 费用 | 说明 |
|------|------|------|
| 云服务器 | ¥89-99/月 | 按月付费，首月可能更便宜 |
| 域名（可选） | ¥10-30/年 | 首年优惠，续费贵一些 |
| **总计** | **约¥100/月** | 不含域名 |

---

## 📞 需要帮助？

如果遇到问题，请提供：
1. 错误日志截图
2. 执行的命令
3. 服务器配置信息

我会立即帮您解决！

---

**祝部署顺利！🎊**