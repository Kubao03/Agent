# 1. 使用 Node 镜像
FROM node:20-alpine

# 2. 设置工作目录
WORKDIR /app

# 3. 复制 package.json 并安装依赖
COPY package*.json ./
RUN npm install

# 4. 复制所有前端代码
COPY . .

# 5. 暴露 Next.js 的 3000 端口
EXPOSE 3000

# 6. 以开发模式启动（实习项目建议先用 dev，方便演示）
CMD ["npm", "run", "dev"]