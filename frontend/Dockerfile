FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . ./
RUN npm run build

FROM node:22-alpine

WORKDIR /app

RUN adduser -D appuser

COPY --from=build /app/dist ./dist
COPY --from=build /app/package.json /app/package-lock.json ./
COPY --from=build /app/vite.config.ts ./

RUN chown -R appuser:appuser /app

USER appuser

RUN npm ci --ignore-scripts

EXPOSE 4173

CMD ["npx", "vite", "preview", "--host", "0.0.0.0", "--port", "4173"]
