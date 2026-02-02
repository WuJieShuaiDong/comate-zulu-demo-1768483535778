# 🚀 云端部署快速指南

本项目已完成本地测试，现在可以轻松部署到云服务器。

---

## 📦 已准备好的文件

- ✅ `requirements.txt` - Python依赖包列表
- ✅ `deploy.sh` - 服务器一键部署脚本
- ✅ `start_all.sh` - 本地启动脚本
- ✅ `DEPLOYMENT_GUIDE.md` - 完整部署文档

---

## 🎯 三步快速部署

### 第1步：推送代码到GitHub

```bash
# 在本地项目根目录执行
cd /Users/xiaoliu/ComateProjects/comate-zulu-demo-1768483535778

# 初始化git（如果还没有）
git init
git add .
git commit -m "准备部署到云端"

# 关联远程仓库（替换成你的GitHub仓库地址）
git remote add origin https://github.com/你的用户名/你的仓库名.git
git push -u origin main
```

### 第2步：购买并连接服务器

**推荐配置**：2核4G，5M带宽，Ubuntu 22.04

- 阿里云：https://www.aliyun.com (新用户首月约¥30)
- 腾讯云：https://cloud.tencent.com (新用户首月约¥25)

**连接服务器**：
```bash
# Mac/Linux用户
ssh root@你的服务器IP

# Windows用户：下载 FinalShell 或 PuTTY
```

### 第3步：一键部署

在服务器上执行：

```bash
# 1. 克隆项目
cd /root
git clone https://github.com/你的用户名/你的仓库名.git
cd 你的仓库名/quant_trading

# 2. 赋予执行权限
chmod +x deploy.sh

# 3. 运行部署脚本（约3分钟）
bash deploy.sh

# 4. 启动服务
systemctl start quant-trader
systemctl start quant-web

# 5. 检查状态
systemctl status quant-trader
systemctl status quant-web
```

### 访问系统

```
http://你的服务器IP:8503
```

---

## ⚠️ 重要提醒

### 1. 开放8503端口
在云服务商控制台配置安全组：
- 允许入方向
- TCP协议
- 端口：8503
- 来源：0.0.0.0/0

### 2. 配置文件检查
部署前确保以下文件存在：
- `data/account.json` - 初始持仓数据
- `demon_gene_db.json` - 妖股基因库
- `.gitignore` - 防止敏感数据上传

---

## 🔧 常用命令

```bash
# 查看服务状态
systemctl status quant-trader quant-web

# 重启服务
systemctl restart quant-trader quant-web

# 停止服务
systemctl stop quant-trader quant-web

# 查看日志
tail -f logs/trader.log
tail -f logs/app.log

# 查看交易记录
tail -20 data/trades.csv
```

---

## 💡 成本预算

| 项目 | 月费用 | 说明 |
|------|--------|------|
| 云服务器 | ¥30-99 | 新用户优惠价 |
| 域名（可选） | ¥10/年 | 首年优惠 |
| **合计** | **约¥50/月** | 7×24小时运行 |

---

## 📚 详细文档

如需更详细的说明，请查看：
- `DEPLOYMENT_GUIDE.md` - 完整部署指南
- `../README.md` - 项目功能说明

---

## 🆘 遇到问题？

### 常见问题

1. **无法访问8503端口**
   - 检查安全组规则是否配置
   - 检查服务是否正常运行

2. **服务启动失败**
   - 查看日志：`journalctl -u quant-trader -n 50`
   - 检查Python依赖是否安装完整

3. **内存不足**
   - 创建Swap交换空间（见完整部署指南）

---

**祝部署顺利！🎊**