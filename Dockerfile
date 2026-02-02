# 使用轻量级 Python 基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置时区为上海
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安装系统依赖 (编译依赖和常用工具)
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY quant_trading/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
# 注意：我们只复制代码，数据目录将在运行时通过挂载卷映射
COPY quant_trading/ .

# 创建数据目录（确保目录存在）
RUN mkdir -p data logs

# 声明数据卷（告诉 Docker 这些目录需要持久化）
VOLUME ["/app/data", "/app/logs"]

# 暴露前端端口
EXPOSE 8503

# 创建启动脚本
RUN echo '#!/bin/bash\n\
python3 auto_trader.py > logs/trader.log 2>&1 &\n\
streamlit run app.py --server.port 8503 --server.address 0.0.0.0\n\
' > start.sh && chmod +x start.sh

# 启动命令
CMD ["./start.sh"]