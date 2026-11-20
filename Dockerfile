FROM node:22-alpine

WORKDIR /app

COPY package.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm install \
      --strict-ssl=false \
      --no-audit \
      --no-fund \
      --fetch-retries=5 \
      --fetch-retry-mintimeout=20000 \
      --fetch-retry-maxtimeout=120000 \
      --maxsockets=3

COPY index.html tsconfig.json vite.config.ts ./
COPY src ./src

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
