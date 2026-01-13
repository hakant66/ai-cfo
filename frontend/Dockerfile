FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* pnpm-lock.yaml* ./
RUN if [ -f pnpm-lock.yaml ]; then npm install -g pnpm && pnpm install; else npm install; fi

COPY . ./

CMD ["npm", "run", "dev", "--", "-H", "0.0.0.0", "-p", "3000"]
