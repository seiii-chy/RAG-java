FROM python:3.11-slim
LABEL authors="lhy"

# 设置工作目录
WORKDIR /app 

ARG ENV_FILE
COPY ${ENV_FILE} .env

# 安装依赖
COPY  requirements.txt . 
RUN pip install --upgrade pip
RUN apt-get update && \
    apt-get install -y \
        pkg-config \
        libmariadb-dev \
        libmariadb-dev-compat \
        gcc \
        python3-dev
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -U huggingface_hub
ENV HF_ENDPOINT=https://hf-mirror.com

# 复制应用代码
COPY . .


# 启动命令
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]