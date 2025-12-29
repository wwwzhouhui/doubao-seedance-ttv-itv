FROM python:3.11-slim

# 设置维护者信息
LABEL maintainer="seedance-api"
LABEL version="1.0.0"
LABEL description="豆包 Seedance 视频生成 API 服务 (纯API版)"

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TZ=Asia/Shanghai

# 豆包 API 配置
ENV DOUBAO_BASE_URL=https://doubao.happieapi.top
ENV DOUBAO_SESSION_COOKIE=""

# API鉴权Token (可选，不配置则不启用鉴权)
ENV AUTH_TOKEN=""

# 服务配置
ENV API_HOST=0.0.0.0
# Render 平台会通过 PORT 环境变量指定端口，默认 10000
ENV PORT=10000

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 复制依赖文件
COPY requirements-api.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements-api.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制应用文件
COPY api.py .

# 暴露端口 (Render 默认使用 10000)
EXPOSE 10000

# 启动命令 - 使用 shell 形式以支持环境变量替换
# Render 平台会自动注入 PORT 环境变量
CMD uvicorn api:app --host 0.0.0.0 --port ${PORT:-10000}
