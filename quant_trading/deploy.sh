#!/bin/bash
# 量化交易系统 - 服务器一键部署脚本
# 适用于 Ubuntu 20.04/22.04

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          量化交易系统 - 服务器自动部署脚本                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
   echo "❌ 请使用root用户运行此脚本"
   echo "   执行: sudo bash deploy.sh"
   exit 1
fi

echo "?? 步骤 1/6: 更新系统..."
apt update && apt upgrade -y

echo ""
echo "🐍 步骤 2/6: 安装Python环境..."
apt install -y python3 python3-pip python3-venv

echo ""
echo "🔧 步骤 3/6: 安装必要工具..."
apt install -y git curl wget vim screen htop

echo ""
echo "📚 步骤 4/6: 安装Python依赖..."
pip3 install --upgrade pip
pip3 install akshare pandas numpy requests streamlit

echo ""
echo "🔥 步骤 5/6: 配置防火墙..."
# 检查是否安装ufw
if command -v ufw &> /dev/null; then
    ufw allow 8503/tcp
    echo "✓ UFW防火墙规则已添加"
else
    echo "⚠️  未检测到UFW，请手动在云服务商控制台配置安全组："
    echo "   允许入方向 TCP 8503 端口"
fi

echo ""
echo "🚀 步骤 6/6: 创建启动脚本..."

# 获取当前目录
CURRENT_DIR=$(pwd)

# 创建systemd服务 - 交易机器人
cat > /etc/systemd/system/quant-trader.service << EOF
[Unit]
Description=Quant Trading Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$CURRENT_DIR
ExecStart=/usr/bin/python3 auto_trader.py
Restart=always
RestartSec=10
StandardOutput=append:$CURRENT_DIR/logs/trader.log
StandardError=append:$CURRENT_DIR/logs/trader-error.log

[Install]
WantedBy=multi-user.target
EOF

# 创建systemd服务 - 前端面板
cat > /etc/systemd/system/quant-web.service << EOF
[Unit]
Description=Quant Trading Web Dashboard
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$CURRENT_DIR
ExecStart=/usr/bin/streamlit run app.py --server.port 8503 --server.address 0.0.0.0
Restart=always
RestartSec=10
StandardOutput=append:$CURRENT_DIR/logs/app.log
StandardError=append:$CURRENT_DIR/logs/app-error.log

[Install]
WantedBy=multi-user.target
EOF

# 创建日志目录
mkdir -p logs data

# 重载systemd
systemctl daemon-reload

# 启用开机自启
systemctl enable quant-trader
systemctl enable quant-web

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    ✅ 部署完成！                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "📋 接下来的操作："
echo ""
echo "1️⃣  启动服务："
echo "   systemctl start quant-trader"
echo "   systemctl start quant-web"
echo ""
echo "2️⃣  查看状态："
echo "   systemctl status quant-trader"
echo "   systemctl status quant-web"
echo ""
echo "3️⃣  查看日志："
echo "   tail -f logs/trader.log"
echo "   tail -f logs/app.log"
echo ""
echo "4️⃣  访问系统："
echo "   http://$(curl -s ifconfig.me):8503"
echo ""
echo "5️⃣  停止服务："
echo "   systemctl stop quant-trader quant-web"
echo ""
echo "6️⃣  重启服务："
echo "   systemctl restart quant-trader quant-web"
echo ""
echo "💡 提示："
echo "   - 请确保在云服务商控制台开放 8503 端口"
echo "   - 所有服务已配置为开机自启动"
echo "   - 日志保存在 logs/ 目录下"
echo ""
echo "🎉 祝交易顺利！"