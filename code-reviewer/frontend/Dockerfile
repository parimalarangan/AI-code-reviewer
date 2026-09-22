# syntax=docker/dockerfile:1

# ---- Stage 1: build the static React bundle ---------------------------------
FROM node:20-slim AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

# ---- Stage 2: serve the static bundle with Nginx ----------------------------
# Using a two-stage build keeps the final image small: it contains only the
# compiled static files + Nginx, not Node.js, npm, or node_modules.
FROM nginx:1.27-alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
