FROM python:3.11-slim

# 设置维护者信息
LABEL maintainer="doubao-seedance"
LABEL version="1.1.0"
LABEL description="豆包 Seedance 1.5 Pro 视频生成服务 (Gradio + 内置API + 视频代理)"

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
ENV API_BASE_URL=http://localhost:8000
ENV API_HOST=0.0.0.0
ENV API_PORT=8000
ENV GRADIO_PORT=7860
ENV ENABLE_INTERNAL_API=true

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制应用文件
# server/api.py 作为内部 API 服务 (提供视频代理等功能)
COPY server/api.py .
# app.py 作为 Gradio 前端入口 (自动启动内置 API)
COPY app.py .
# client.py 作为命令行客户端 (可选)
COPY client/client.py .

# 暴露端口 (7860=Gradio, 8000=API内部)
EXPOSE 7860 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:7860/ || exit 1

# 启动命令 - 直接运行 app.py，它会自动启动内置API服务
CMD ["python", "app.py"]
