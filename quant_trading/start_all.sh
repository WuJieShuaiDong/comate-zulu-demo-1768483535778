#!/bin/bash

###############################################################################
# 量化交易系统 - 一键启动脚本
# 功能：启动交易机器人和前端监控面板
# 作者：Zulu AI
# 版本：1.0
###############################################################################

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# PID文件
BOT_PID_FILE="$SCRIPT_DIR/data/bot.pid"
WEB_PID_FILE="$SCRIPT_DIR/data/web.pid"

# 日志文件
BOT_LOG="$SCRIPT_DIR/data/bot.log"
WEB_LOG="$SCRIPT_DIR/data/web.log"

###############################################################################
# 工具函数
###############################################################################

print_banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                   量化交易系统启动器                           ║"
    echo "║                   Quant Trading System                       ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}错误: 未找到 python3${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Python3 已就绪${NC}"
}

check_dependencies() {
    echo -e "${YELLOW}检查依赖...${NC}"
    
    # 跳过 requirements.txt 存在性检查，直接检查模块
    # if [ ! -f "$PROJECT_ROOT/requirements.txt" ]; then
    #     echo -e "${RED}错误: requirements.txt 不存在${NC}"
    #     exit 1
    # fi
    
    # 检查关键模块
    python3 -c "import streamlit, akshare, pandas" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}警告: 缺少必需依赖，正在安装...${NC}"
        pip3 install -r "$PROJECT_ROOT/requirements.txt" -q
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ 依赖安装成功${NC}"
        else
            echo -e "${RED}错误: 依赖安装失败${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✓ 依赖检查通过${NC}"
    fi
}

is_process_running() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

start_bot() {
    echo -e "${YELLOW}启动交易机器人...${NC}"
    
    if is_process_running "$BOT_PID_FILE"; then
        echo -e "${YELLOW}⚠ 交易机器人已在运行 (PID: $(cat $BOT_PID_FILE))${NC}"
        return 0
    fi
    
    # 后台启动
    cd "$SCRIPT_DIR"
    nohup python3 auto_trader.py > "$BOT_LOG" 2>&1 &
    local pid=$!
    echo $pid > "$BOT_PID_FILE"
    
    sleep 2
    
    if is_process_running "$BOT_PID_FILE"; then
        echo -e "${GREEN}✓ 交易机器人启动成功 (PID: $pid)${NC}"
        return 0
    else
        echo -e "${RED}✗ 交易机器人启动失败${NC}"
        rm -f "$BOT_PID_FILE"
        return 1
    fi
}

start_web() {
    echo -e "${YELLOW}启动前端监控面板...${NC}"
    
    if is_process_running "$WEB_PID_FILE"; then
        echo -e "${YELLOW}⚠ 前端面板已在运行 (PID: $(cat $WEB_PID_FILE))${NC}"
        return 0
    fi
    
    # 后台启动 Streamlit
    cd "$SCRIPT_DIR"
    nohup python3 -m streamlit run app.py --server.port 8503 --server.headless true > "$WEB_LOG" 2>&1 &
    local pid=$!
    echo $pid > "$WEB_PID_FILE"
    
    sleep 3
    
    if is_process_running "$WEB_PID_FILE"; then
        echo -e "${GREEN}✓ 前端面板启动成功 (PID: $pid)${NC}"
        echo -e "${BLUE}访问地址: http://localhost:8503${NC}"
        return 0
    else
        echo -e "${RED}✗ 前端面板启动失败${NC}"
        rm -f "$WEB_PID_FILE"
        return 1
    fi
}

stop_bot() {
    if is_process_running "$BOT_PID_FILE"; then
        local pid=$(cat "$BOT_PID_FILE")
        kill $pid 2>/dev/null
        sleep 1
        
        if ps -p $pid > /dev/null 2>&1; then
            kill -9 $pid 2>/dev/null
        fi
        
        rm -f "$BOT_PID_FILE"
        echo -e "${GREEN}✓ 交易机器人已停止${NC}"
    else
        echo -e "${YELLOW}交易机器人未运行${NC}"
    fi
}

stop_web() {
    if is_process_running "$WEB_PID_FILE"; then
        local pid=$(cat "$WEB_PID_FILE")
        kill $pid 2>/dev/null
        sleep 1
        
        if ps -p $pid > /dev/null 2>&1; then
            kill -9 $pid 2>/dev/null
        fi
        
        rm -f "$WEB_PID_FILE"
        echo -e "${GREEN}✓ 前端面板已停止${NC}"
    else
        echo -e "${YELLOW}前端面板未运行${NC}"
    fi
}

show_status() {
    echo -e "${BLUE}=== 系统状态 ===${NC}"
    
    if is_process_running "$BOT_PID_FILE"; then
        echo -e "${GREEN}● 交易机器人: 运行中 (PID: $(cat $BOT_PID_FILE))${NC}"
    else
        echo -e "${RED}○ 交易机器人: 未运行${NC}"
    fi
    
    if is_process_running "$WEB_PID_FILE"; then
        echo -e "${GREEN}● 前端面板: 运行中 (PID: $(cat $WEB_PID_FILE))${NC}"
        echo -e "${BLUE}  访问地址: http://localhost:8503${NC}"
    else
        echo -e "${RED}○ 前端面板: 未运行${NC}"
    fi
}

show_logs() {
    echo -e "${BLUE}=== 实时日志 (Ctrl+C 退出) ===${NC}"
    echo ""
    
    if [ -f "$BOT_LOG" ]; then
        tail -f "$BOT_LOG"
    else
        echo -e "${RED}日志文件不存在: $BOT_LOG${NC}"
    fi
}

###############################################################################
# 主逻辑
###############################################################################

case "$1" in
    start)
        print_banner
        check_python
        check_dependencies
        echo ""
        start_bot
        start_web
        echo ""
        show_status
        echo ""
        echo -e "${BLUE}提示:${NC}"
        echo "  查看状态: ./start_all.sh status"
        echo "  查看日志: ./start_all.sh logs"
        echo "  停止服务: ./start_all.sh stop"
        ;;
        
    stop)
        print_banner
        stop_bot
        stop_web
        ;;
        
    restart)
        print_banner
        echo -e "${YELLOW}重启服务...${NC}"
        stop_bot
        stop_web
        sleep 2
        start_bot
        start_web
        echo ""
        show_status
        ;;
        
    status)
        print_banner
        show_status
        ;;
        
    logs)
        show_logs
        ;;
        
    *)
        print_banner
        echo -e "${YELLOW}用法:${NC}"
        echo "  ./start_all.sh start    - 启动所有服务"
        echo "  ./start_all.sh stop     - 停止所有服务"
        echo "  ./start_all.sh restart  - 重启所有服务"
        echo "  ./start_all.sh status   - 查看运行状态"
        echo "  ./start_all.sh logs     - 查看实时日志"
        exit 1
        ;;
esac