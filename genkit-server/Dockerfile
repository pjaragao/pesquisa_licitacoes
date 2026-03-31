# Dockerfile - Genkit Server (IA/Classificação)
FROM node:20-slim

WORKDIR /app

# Instala dependências Node primeiro (cache de camada)
COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force

# Instala tsx como dependência de desenvolvimento para rodar TypeScript
RUN npm install tsx

# Copia código-fonte
COPY tsconfig.json .
COPY src/ ./src/

EXPOSE 3400

CMD ["npx", "tsx", "src/index.ts"]
