FROM node:22-alpine AS base

WORKDIR /workspace/frontend

COPY package.json package-lock.json ./
RUN npm ci


FROM base AS development

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0"]


FROM base AS builder

COPY . .
RUN npm run build


FROM node:22-alpine AS production

WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

COPY --from=builder /workspace/frontend/public ./public
COPY --from=builder --chown=nextjs:nodejs \
    /workspace/frontend/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs \
    /workspace/frontend/.next/static ./.next/static

USER nextjs

EXPOSE 3000

CMD ["node", "server.js"]