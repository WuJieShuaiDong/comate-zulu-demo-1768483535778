# 基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 使用清华源加速 pip
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 安装依赖
COPY quant_trading/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码 (排除数据文件，由挂载卷提供)
COPY quant_trading/ .

# 创建必要目录
RUN mkdir -p logs data

# 暴露端口
EXPOSE 8503

# 启动命令 (同时启动机器人和前端)
CMD ["sh", "-c", "python auto_trader.py > logs/trader.log 2>&1 & python -m streamlit run app.py --server.port 8503 --server.address 0.0.0.0"]