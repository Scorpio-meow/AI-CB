FROM node:18-alpine

WORKDIR /app

# 複製 package 文件
COPY package*.json ./

# 安裝依賴
RUN npm ci --only=production

# 複製應用程式代碼
COPY . .

# 構建應用程式
RUN npm run build

# 安裝 serve 來服務靜態文件
RUN npm install -g serve

# 暴露端口
EXPOSE 3000

# 啟動命令
CMD ["serve", "-s", "build", "-l", "3000"]
