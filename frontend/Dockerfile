FROM node:20-alpine
WORKDIR /usr/src/app
COPY package.json tsconfig.json vite.config.ts ./
COPY src ./src
COPY index.html ./
RUN npm install --legacy-peer-deps && npm run build
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
