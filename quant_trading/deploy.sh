#!/bin/bash
# 量化交易系统 - 服务器一键部署脚本 (通用版)
# 支持 Ubuntu/Debian/CentOS/Alibaba Cloud Linux

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          量化交易系统 - 服务器自动部署脚本 (通用版)             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
   echo "❌ 请使用root用户运行此脚本"
   echo "   执行: sudo bash deploy.sh"
   exit 1
fi

# 检测包管理器
if command -v apt-get &> /dev/null; then
    PKG_MANAGER="apt-get"
    echo "?? 检测到系统: Debian/Ubuntu 系列"
elif command -v yum &> /dev/null; then
    PKG_MANAGER="yum"
    echo "🔍 检测到系统: CentOS/RHEL/Aliyun 系列"
else
    echo "❌ 未知系统，无法自动安装依赖，请手动安装！"
    exit 1
fi

echo "📦 步骤 1/6: 更新系统..."
if [ "$PKG_MANAGER" = "apt-get" ]; then
    $PKG_MANAGER update -y
else
    $PKG_MANAGER makecache
fi

echo ""
echo "🐍 步骤 2/6: 安装Python环境..."
if [ "$PKG_MANAGER" = "apt-get" ]; then
    $PKG_MANAGER install -y python3 python3-pip python3-venv
else
    # CentOS 需要安装 Python 3 (有些旧版本默认只有python2)
    $PKG_MANAGER install -y python3 python3-pip
fi

echo ""
echo "🔧 步骤 3/6: 安装必要工具..."
$PKG_MANAGER install -y git wget vim screen

echo ""
echo "📚 步骤 4/6: 安装Python依赖..."
pip3 install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo ""
echo "🔥 步骤 5/6: 配置防火墙..."
# 尝试检测并配置防火墙，但不强求
if command -v ufw &> /dev/null; then
    ufw allow 8503/tcp
    echo "✓ UFW防火墙规则已添加"
elif command -v firewall-cmd &> /dev/null; then
    # CentOS firewalld
    if systemctl is-active --quiet firewalld; then
        firewall-cmd --zone=public --add-port=8503/tcp --permanent
        firewall-cmd --reload
        echo "✓ Firewalld防火墙规则已添加"
    fi
else
    echo "⚠️  未检测到常用防火墙，请确保在【阿里云控制台-安全组】开放 8503 端口！"
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
ExecStart=$(which python3) auto_trader.py
Restart=always
RestartSec=10
StandardOutput=append:$CURRENT_DIR/logs/trader.log
StandardError=append:$CURRENT_DIR/logs/trader-error.log

[Install]
WantedBy=multi-user.target
EOF

# 创建systemd服务 - 前端面板
# 查找 streamlit 路径
STREAMLIT_PATH=$(which streamlit)
if [ -z "$STREAMLIT_PATH" ]; then
    STREAMLIT_PATH="/usr/local/bin/streamlit"
fi

cat > /etc/systemd/system/quant-web.service << EOF
[Unit]
Description=Quant Trading Web Dashboard
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$CURRENT_DIR
ExecStart=$STREAMLIT_PATH run app.py --server.port 8503 --server.address 0.0.0.0
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
echo "3️⃣  访问系统："
echo "   请在浏览器输入: http://你的服务器IP:8503"
echo ""
echo "🎉 祝交易顺利！"