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

# Set working directory for server
WORKDIR /app/server

# Expose port
EXPOSE 5000

# Start the backend server
CMD ["node", "src/server.js"]
