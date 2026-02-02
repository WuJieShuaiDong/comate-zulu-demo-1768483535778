#!/bin/bash
#
# 量化交易系统 - Docker 一键部署脚本
# 使用方法: ./docker-deploy.sh [命令]
#
# 命令:
#   start   - 构建并启动服务
#   stop    - 停止服务
#   restart - 重启服务
#   logs    - 查看日志
#   status  - 查看状态
#   clean   - 清理所有容器和镜像
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
CONTAINER_NAME="quant-trading"
IMAGE_NAME="quant-trading:latest"
PORT=8503

# 打印带颜色的信息
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[OK]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查Docker是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装！"
        echo ""
        echo "请先安装 Docker:"
        echo "  Mac:    brew install --cask docker"
        echo "  Ubuntu: curl -fsSL https://get.docker.com | sh"
        echo "  CentOS: curl -fsSL https://get.docker.com | sh"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker 服务未运行！请先启动 Docker Desktop"
        exit 1
    fi
    
    print_success "Docker 环境正常"
}

# 获取本机IP
get_local_ip() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # Mac
        ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1
    else
        # Linux
        hostname -I | awk '{print $1}'
    fi
}

# 构建镜像
build_image() {
    print_info "正在构建 Docker 镜像..."
    
    # 切换到项目根目录
    cd "$(dirname "$0")/.."
    
    docker build -f quant_trading/Dockerfile -t $IMAGE_NAME .
    
    print_success "镜像构建完成: $IMAGE_NAME"
}

# 启动容器
start_container() {
    print_info "正在启动容器..."
    
    # 检查是否已有同名容器
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_warn "发现已存在的容器，正在移除..."
        docker rm -f $CONTAINER_NAME > /dev/null 2>&1 || true
    fi
    
    # 创建数据目录
    cd "$(dirname "$0")"
    mkdir -p data logs
    
    # 读取密码配置 (如果有)
    AUTH_PWD="${AUTH_PASSWORD:-quant2026}"
    
    # 启动容器
    docker run -d \
        --name $CONTAINER_NAME \
        --restart unless-stopped \
        -p $PORT:8503 \
        -v "$(pwd)/data:/app/data" \
        -v "$(pwd)/logs:/app/logs" \
        -e TZ=Asia/Shanghai \
        -e ENABLE_AUTH=true \
        -e AUTH_PASSWORD=$AUTH_PWD \
        $IMAGE_NAME
    
    # 等待启动
    print_info "等待服务启动..."
    sleep 5
    
    # 检查状态
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_success "容器启动成功!"
        echo ""
        echo "========================================"
        echo -e "${GREEN}🎉 部署成功!${NC}"
        echo "========================================"
        echo ""
        LOCAL_IP=$(get_local_ip)
        echo -e "📱 本机访问:   ${BLUE}http://localhost:$PORT${NC}"
        echo -e "🌐 局域网访问: ${BLUE}http://${LOCAL_IP}:$PORT${NC}"
        echo -e "🔐 访问密码:   ${YELLOW}$AUTH_PWD${NC}"
        echo ""
        echo "提示: 外网访问需要配置云服务器安全组开放 $PORT 端口"
        echo "========================================"
    else
        print_error "容器启动失败，请查看日志: docker logs $CONTAINER_NAME"
        exit 1
    fi
}

# 停止容器
stop_container() {
    print_info "正在停止容器..."
    docker stop $CONTAINER_NAME > /dev/null 2>&1 || true
    docker rm $CONTAINER_NAME > /dev/null 2>&1 || true
    print_success "容器已停止"
}

# 查看日志
show_logs() {
    print_info "显示容器日志 (Ctrl+C 退出)..."
    docker logs -f --tail 100 $CONTAINER_NAME
}

# 查看状态
show_status() {
    echo ""
    echo "=== Docker 容器状态 ==="
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_success "容器运行中"
        docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        echo ""
        LOCAL_IP=$(get_local_ip)
        echo -e "📱 访问地址: ${BLUE}http://localhost:$PORT${NC}"
        echo -e "?? 局域网:   ${BLUE}http://${LOCAL_IP}:$PORT${NC}"
    else
        print_warn "容器未运行"
    fi
    echo ""
    
    echo "=== 机器人日志 (最近10行) ==="
    if [ -f "$(dirname "$0")/logs/bot.log" ]; then
        tail -10 "$(dirname "$0")/logs/bot.log"
    else
        echo "(日志文件不存在)"
    fi
}

# 清理
clean_all() {
    print_warn "即将清理所有容器和镜像..."
    read -p "确认清理? (y/N): " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        docker rm -f $CONTAINER_NAME > /dev/null 2>&1 || true
        docker rmi $IMAGE_NAME > /dev/null 2>&1 || true
        print_success "清理完成"
    else
        print_info "已取消"
    fi
}

# 主入口
main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║           🚀 量化交易系统 Docker 部署工具                  ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo ""
    
    check_docker
    
    case "${1:-start}" in
        start)
            build_image
            start_container
            ;;
        stop)
            stop_container
            ;;
        restart)
            stop_container
            build_image
            start_container
            ;;
        logs)
            show_logs
            ;;
        status)
            show_status
            ;;
        clean)
            clean_all
            ;;
        *)
            echo "使用方法: $0 {start|stop|restart|logs|status|clean}"
            echo ""
            echo "命令说明:"
            echo "  start   - 构建并启动服务 (默认)"
            echo "  stop    - 停止服务"
            echo "  restart - 重启服务"
            echo "  logs    - 查看实时日志"
            echo "  status  - 查看运行状态"
            echo "  clean   - 清理容器和镜像"
            exit 1
            ;;
    esac
}

main "$@"