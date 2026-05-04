FROM node:22-alpine AS deps
WORKDIR /workspace/apps/frontend
COPY apps/frontend/package.json apps/frontend/package-lock.json* ./
RUN npm install

FROM node:22-alpine AS builder
WORKDIR /workspace/apps/frontend
COPY --from=deps /workspace/apps/frontend/node_modules ./node_modules
COPY apps/frontend .
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /workspace/apps/frontend/.next ./.next
COPY --from=builder /workspace/apps/frontend/public ./public
COPY --from=builder /workspace/apps/frontend/package.json ./package.json
COPY --from=builder /workspace/apps/frontend/node_modules ./node_modules
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup appuser && \
    chown -R appuser:appgroup /app
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD ["wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:3000/"]
USER appuser
CMD ["npm", "run", "start"]
