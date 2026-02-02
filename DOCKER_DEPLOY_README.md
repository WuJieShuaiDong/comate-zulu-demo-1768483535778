# 🐳 Docker 极简部署指南

这是最推荐的部署方式，**稳定、干净、不出错**。

---

## 🚀 部署步骤 (服务器上执行)

### 1. 安装 Docker (如果已安装可跳过)
```bash
# 一键安装 Docker
curl -fsSL https://get.docker.com | bash

# 启动 Docker
systemctl start docker
systemctl enable docker
```

### 2. 获取代码
```bash
# 克隆代码
git clone https://github.com/你的用户名/你的仓库名.git
cd 你的仓库名
```

### 3. 一键启动
```bash
# 启动所有服务 (后台运行)
docker compose up -d --build
```

**✅ 完成！** 系统已在 `http://你的服务器IP:8503` 运行。

---

## 🛠 常用维护命令

### 查看状态
```bash
# 查看容器状态
docker compose ps

# 查看实时日志 (包含交易机器人和前端日志)
docker compose logs -f
```

### 停止/重启
```bash
# 重启服务
docker compose restart

# 停止服务
docker compose down
```

### 更新代码
```bash
# 1. 拉取最新代码
git pull

# 2. 重建并重启 (数据不会丢失)
docker compose up -d --build
```

---

## 📂 数据去哪了？

数据会自动保存在服务器的当前目录下：
- 交易数据：`./quant_trading/data/`
- 运行日志：`./quant_trading/logs/`

即使删除容器，这些数据也**不会丢失**。