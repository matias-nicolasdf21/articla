# Interfaz de Articla (Next.js). La construye docker-compose.yml.
FROM node:22-alpine
WORKDIR /web
COPY package.json ./
RUN npm install --no-audit --no-fund
COPY . .
RUN npm run build
ENV NODE_ENV=production
EXPOSE 3000
CMD ["npm", "start"]
