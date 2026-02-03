# 1. 使用轻量级 Python 镜像
FROM python:3.11-slim

# 2. 设置工作目录
WORKDIR /app

# 3. 复制依赖清单并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 复制所有后端代码
COPY . .

# 5. 暴露 FastAPI 的 8000 端口
EXPOSE 8000

# 6. 启动命令（注意：这里不加 --reload，因为生产环境不需要）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]