FROM python:3.9-slim

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制依赖文件
COPY quant_trading/requirements-docker.txt ./requirements.txt

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目代码
COPY quant_trading/ ./

# 创建数据目录
RUN mkdir -p data logs

# 复制初始数据文件 (如果存在)
COPY quant_trading/data/ ./data/ 2>/dev/null || true

# 暴露端口
EXPOSE 8503

# 环境变量
ENV PYTHONUNBUFFERED=1
ENV ENABLE_AUTH=true
ENV AUTH_PASSWORD=quant2026

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8503/_stcore/health || exit 1

# 启动命令
CMD ["sh", "-c", "python3 -u auto_trader.py > logs/bot.log 2>&1 & streamlit run app.py --server.port 8503 --server.address 0.0.0.0 --server.headless true --browser.gatherUsageStats false"]