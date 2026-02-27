# ============================================
# Meeting Management API - Docker Image
# Python 3.11 + FastAPI + faster-whisper
# ============================================

FROM python:3.11-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    WHISPER_MODEL_DIR=/root/.cache/whisper

# 安装系统依赖（包括 ffmpeg）
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 先复制依赖文件，利用 Docker 缓存层
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY src/ ./src/
COPY templates/ ./templates/
COPY data/ ./data/

# 创建必要的目录并设置权限
RUN mkdir -p /app/output /app/data && \
    chmod 755 /app/output /app/data

# 暴露端口
EXPOSE 8765

# 健康检查
# start-period 给够 60 秒，因为 Whisper 模型冷启动较慢
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8765/api/v1/system/health || exit 1

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8765", "--app-dir", "src"]

# ============================================
# GPU 支持（需要 nvidia-docker）
# ============================================
# 如需 GPU 支持，请使用以下 Dockerfile 内容替换上面的内容：
#
# FROM nvidia/cuda:12.0-runtime-ubuntu22.04
# 
# ENV PYTHONDONTWRITEBYTECODE=1 \
#     PYTHONUNBUFFERED=1 \
#     PIP_NO_CACHE_DIR=1 \
#     PIP_DISABLE_PIP_VERSION_CHECK=1 \
#     WHISPER_MODEL_DIR=/root/.cache/whisper
# 
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     python3.11 \
#     python3-pip \
#     ffmpeg \
#     curl \
#     build-essential \
#     && rm -rf /var/lib/apt/lists/*
# 
# WORKDIR /app
# 
# COPY requirements.txt .
# RUN pip3 install --no-cache-dir -r requirements.txt
# 
# COPY src/ ./src/
# COPY templates/ ./templates/
# COPY data/ ./data/
# 
# RUN mkdir -p /app/output /app/data && \
#     chmod 755 /app/output /app/data
# 
# EXPOSE 8765
# 
# HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
#     CMD curl -f http://localhost:8765/api/v1/system/health || exit 1
# 
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8765", "--app-dir", "src"]
#
# 运行时需要添加: --runtime=nvidia 或 --gpus all
# ============================================
