# 1. 使用官方 Python 运行时作为父镜像
FROM python:3.9-slim AS builder

# 2. 设置工作目录
WORKDIR /app

# 3. 安装系统依赖 (如果需要)
# OCR 依赖已注释掉，因为相关 Python 包已移除 -> Now enabled
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# 4. 复制依赖文件并安装依赖
COPY requirements.txt .
# 安装 CPU 版本的 PyTorch 以减小体积 (使用国内源)
# 注意：如果您的 requirements.txt 中 torch 版本与 CPU 版本不兼容，可能需要调整
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu -i https://pypi.tuna.tsinghua.edu.cn/simple
# 安装其余依赖 (使用国内源)
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 5. 复制项目文件到工作目录
COPY . .

# 6. 暴露 Streamlit 运行的端口
EXPOSE 8501

# 7. 定义容器启动时运行的命令
# 使用 --server.enableCORS=false 避免潜在的跨域问题
# 使用 --server.address=0.0.0.0 允许从外部访问
# 添加 --server.fileWatcherType=none 禁用文件监控，避免与 PyTorch 冲突
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.enableCORS=false", "--server.fileWatcherType=none"] 