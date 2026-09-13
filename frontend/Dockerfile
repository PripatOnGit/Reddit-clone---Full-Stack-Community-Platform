FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

RUN npm install -g serve

EXPOSE 80

CMD ["serve", "-s", "dist", "-l", "80"]
