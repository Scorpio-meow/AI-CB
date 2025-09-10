# 使用官方 Node.js 18 運行時作為基底鏡像
FROM node:18-alpine as builder

# 設置工作目錄
WORKDIR /app

# 複製 package 檔案
COPY package*.json ./

# 安裝依賴
RUN npm ci --only=production

# 複製源代碼
COPY . .

# 構建應用程式
RUN npm run build

# 生產階段
FROM nginx:alpine

# 複製自定義 nginx 配置
COPY nginx.conf /etc/nginx/nginx.conf

# 複製構建的應用程式
COPY --from=builder /app/build /usr/share/nginx/html

# 暴露端口
EXPOSE 3000

# 啟動 nginx
CMD ["nginx", "-g", "daemon off;"]
