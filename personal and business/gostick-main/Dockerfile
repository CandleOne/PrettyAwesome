# Stage 1: Build Node dependencies
FROM node:18-alpine AS backend-builder
WORKDIR /app/server
COPY server/package*.json ./
RUN npm ci --only=production

# Stage 2: Build frontend assets
FROM node:18-alpine AS frontend-prep
WORKDIR /app
COPY . .

# Stage 3: Final image - serve both backend API and frontend
FROM node:18-alpine
WORKDIR /app

# Prisma on Alpine needs OpenSSL runtime libraries
RUN apk add --no-cache openssl

# Copy backend from builder
COPY --from=backend-builder /app/server/node_modules ./server/node_modules
COPY server ./server

# Copy frontend files
COPY include ./include
COPY img ./img
COPY src ./src
COPY Assets ./Assets
COPY *.html ./
COPY *.css ./
COPY *.png ./
COPY *.mov ./
COPY *.jpg ./
COPY *.js ./
COPY robots.txt sitemap.xml ./

# Set working directory for server
WORKDIR /app/server

# Ensure Prisma is generated for the Linux runtime and the SQLite database is migrated
# before the app starts.
CMD ["sh", "-c", "npx prisma generate && npx prisma migrate deploy && node src/server.js"]

# Expose port
EXPOSE 5000
