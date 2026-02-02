# 使用轻量级 Python 基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置时区为上海
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装 (使用清华源加速)
COPY quant_trading/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目代码
# 注意：我们不再复制 data 目录，防止构建报错
# data 目录将在运行时通过 docker-compose 自动挂载
COPY quant_trading/ .

# 手动创建数据和日志目录
RUN mkdir -p data logs

# 声明数据卷
VOLUME ["/app/data", "/app/logs"]

# 暴露端口
EXPOSE 8503

# 创建启动脚本
RUN echo '#!/bin/bash\n\
python3 auto_trader.py > logs/trader.log 2>&1 &\n\
streamlit run app.py --server.port 8503 --server.address 0.0.0.0\n\
' > start.sh && chmod +x start.sh

# 启动命令
CMD ["./start.sh"]