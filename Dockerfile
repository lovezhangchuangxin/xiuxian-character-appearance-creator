# syntax=docker/dockerfile:1

# 基础镜像参数：网络受限时可用 --build-arg 固定本地已有的 digest，或指向镜像仓库
ARG NODE_IMAGE=node:26-alpine
ARG NGINX_IMAGE=nginx:alpine

# 构建阶段：安装锁定依赖并产出编辑器静态文件
FROM ${NODE_IMAGE} AS build
WORKDIR /app
RUN npm install -g pnpm@12.21.0

# 先复制清单文件，利用层缓存加速重复构建
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/editor/package.json apps/editor/
COPY packages/character-assets/package.json packages/character-assets/

RUN pnpm install --frozen-lockfile

COPY apps/editor apps/editor
COPY packages/character-assets packages/character-assets
COPY scripts/check-assets.mjs scripts/write-asset-manifest.mjs scripts/
COPY assets/sprites assets/sprites
COPY assets/thumbnails assets/thumbnails

# 素材校验、类型检查和 Vite 构建一次完成
RUN pnpm build

# 运行阶段：内置 nginx，无需在宿主机安装和配置
FROM ${NGINX_IMAGE}
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/apps/editor/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
