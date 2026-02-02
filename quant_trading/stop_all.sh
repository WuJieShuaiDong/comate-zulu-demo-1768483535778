#!/bin/bash

###############################################################################
# 量化交易系统 - 停止脚本
# 功能：停止所有运行中的服务
# 作者：Zulu AI
# 版本：1.0
###############################################################################

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 项目路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# PID文件
BOT_PID_FILE="$SCRIPT_DIR/data/bot.pid"
WEB_PID_FILE="$SCRIPT_DIR/data/web.pid"

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                   停止量化交易系统                             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

stop_process() {
    local name=$1
    local pid_file=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        
        if ps -p "$pid" > /dev/null 2>&1; then
            echo -e "${YELLOW}停止 $name (PID: $pid)...${NC}"
            kill $pid 2>/dev/null
            sleep 1
            
            # 强制杀死
            if ps -p "$pid" > /dev/null 2>&1; then
                kill -9 $pid 2>/dev/null
                sleep 1
            fi
            
            if ! ps -p "$pid" > /dev/null 2>&1; then
                echo -e "${GREEN}✓ $name 已停止${NC}"
                rm -f "$pid_file"
                return 0
            else
                echo -e "${RED}✗ $name 停止失败${NC}"
                return 1
            fi
        else
            echo -e "${YELLOW}$name 未运行，清理PID文件${NC}"
            rm -f "$pid_file"
            return 0
        fi
    else
        echo -e "${YELLOW}$name 未运行${NC}"
        return 0
    fi
}

# 停止交易机器人
stop_process "交易机器人" "$BOT_PID_FILE"

# 停止前端面板
stop_process "前端监控面板" "$WEB_PID_FILE"

# 额外清理：查找并停止所有相关进程
echo ""
echo -e "${YELLOW}额外清理: 检查残留进程...${NC}"

# 查找 auto_trader.py 进程
BOT_PIDS=$(pgrep -f "python3.*auto_trader.py" 2>/dev/null)
if [ -n "$BOT_PIDS" ]; then
    echo -e "${YELLOW}发现残留的交易机器人进程: $BOT_PIDS${NC}"
    kill -9 $BOT_PIDS 2>/dev/null
    echo -e "${GREEN}✓ 残留进程已清理${NC}"
fi

# 查找 streamlit 进程
WEB_PIDS=$(pgrep -f "streamlit.*app.py" 2>/dev/null)
if [ -n "$WEB_PIDS" ]; then
    echo -e "${YELLOW}发现残留的前端进程: $WEB_PIDS${NC}"
    kill -9 $WEB_PIDS 2>/dev/null
    echo -e "${GREEN}✓ 残留进程已清理${NC}"
fi

echo ""
echo -e "${GREEN}所有服务已停止${NC}"