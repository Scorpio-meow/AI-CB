#################################################################
# Build stage
FROM node:18-alpine AS builder
WORKDIR /app

# 安裝依賴
COPY package*.json ./
RUN npm ci

# 複製並構建
COPY . .
RUN npm run build

#################################################################
# Production stage: use nginx to serve static files
FROM nginx:stable-alpine

# 移除預設 nginx 靜態頁面並複製 build
RUN rm -rf /usr/share/nginx/html/*
COPY --from=builder /app/build /usr/share/nginx/html

# 複製自定義 nginx 設定（若有，否則使用預設）
# 若未提供 nginx.conf，預設配置已足夠

EXPOSE 3000

STOPSIGNAL SIGTERM

CMD ["nginx", "-g", "daemon off;"]
