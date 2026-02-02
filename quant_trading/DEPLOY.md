# 量化交易系统 - 远程部署指南

## 📋 部署方案概览

| 方案 | 复杂度 | 成本 | 推荐场景 |
|-----|-------|------|---------|
| **方案1: 云服务器部署** | ⭐⭐ | ¥50-200/月 | 正式使用 |
| **方案2: 内网穿透** | ⭐ | 免费 | 临时演示 |
| **方案3: Docker部署** | ⭐⭐⭐ | 同方案1 | 多环境一致性 |

---

## 🚀 方案1: 云服务器部署 (推荐)

### 1.1 服务器要求

- **配置**: 2核4G内存 (最低1核2G)
- **系统**: Ubuntu 22.04 / CentOS 8
- **带宽**: 1-5Mbps
- **推荐厂商**: 阿里云/腾讯云/华为云

### 1.2 部署步骤

```bash
# 1. 登录服务器
ssh root@your_server_ip

# 2. 安装依赖
apt update && apt install -y python3 python3-pip git screen

# 3. 克隆项目
git clone your_repo_url /opt/quant_trading
cd /opt/quant_trading/quant_trading

# 4. 安装Python依赖
pip3 install -r ../requirements.txt

# 5. 配置防火墙 (开放8503端口)
ufw allow 8503/tcp
ufw enable

# 6. 启动服务 (使用screen保持后台运行)
screen -S quant_bot
python3 auto_trader.py &
streamlit run app.py --server.port 8503 --server.address 0.0.0.0
# 按 Ctrl+A+D 退出screen (服务继续运行)
```

### 1.3 访问地址

- http://your_server_ip:8503

---

## 🌐 方案2: 内网穿透 (免费临时方案)

### 2.1 使用 Cloudflare Tunnel (推荐)

```bash
# 1. 安装 cloudflared
brew install cloudflare/cloudflare/cloudflared  # Mac
# 或 Linux:
# wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
# chmod +x cloudflared-linux-amd64 && mv cloudflared-linux-amd64 /usr/local/bin/cloudflared

# 2. 登录 Cloudflare
cloudflared tunnel login

# 3. 启动隧道 (会生成临时公网URL)
cloudflared tunnel --url http://localhost:8503
```

### 2.2 使用 ngrok

```bash
# 1. 安装 ngrok
brew install ngrok  # Mac
# 或下载: https://ngrok.com/download

# 2. 启动隧道
ngrok http 8503
# 会显示公网URL如: https://abc123.ngrok.io
```

---

## 🐳 方案3: Docker部署

### 3.1 创建 Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY quant_trading/ ./quant_trading/

WORKDIR /app/quant_trading

# 暴露端口
EXPOSE 8503

# 启动命令
CMD ["sh", "-c", "python3 auto_trader.py & streamlit run app.py --server.port 8503 --server.address 0.0.0.0"]
```

### 3.2 构建和运行

```bash
# 构建镜像
docker build -t quant-trading .

# 运行容器
docker run -d \
  --name quant-trading \
  -p 8503:8503 \
  -v $(pwd)/data:/app/quant_trading/data \
  quant-trading
```

---

## 🔐 安全配置 (重要!)

### 添加登录认证

修改 `app.py`，在开头添加：

```python
# 简单密码保护
PASSWORD = "your_secure_password_here"

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    password = st.text_input("请输入访问密码", type="password")
    if st.button("登录"):
        if password == PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("密码错误")
    st.stop()
```

### HTTPS 配置 (Nginx反向代理)

```nginx
server {
    listen 443 ssl;
    server_name your_domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8503;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

---

## 📱 快速命令汇总

```bash
# 启动所有服务
cd /opt/quant_trading/quant_trading && ./start_all.sh start

# 查看状态
./start_all.sh status

# 查看日志
tail -f data/bot.log

# 停止服务
./start_all.sh stop
```

---

## ⚠️ 注意事项

1. **数据安全**: 不要暴露真实交易账户信息
2. **访问控制**: 生产环境必须添加密码保护
3. **HTTPS**: 正式使用建议配置SSL证书
4. **备份**: 定期备份 `data/` 目录

---

## 💡 推荐配置

| 用途 | 服务器配置 | 预算 |
|-----|----------|------|
| 个人测试 | 1核2G | ¥30-50/月 |
| 日常使用 | 2核4G | ¥80-150/月 |
| 多人访问 | 4核8G | ¥200-400/月 |