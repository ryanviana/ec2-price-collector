# Stage 1 - Build Stage
FROM node:18-alpine as builder
WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install all dependencies
RUN npm install

# Copy the rest of the application code
COPY . .

# Build the application
RUN npm run build

# Stage 2 - Production Stage
FROM node:18-alpine
WORKDIR /app

# Install only production dependencies
COPY package*.json ./
RUN npm install --only=production

# Copy built files from the builder stage
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules

# Copy environment variables
COPY .env ./

# Expose the application port
EXPOSE 3000

RUN apk --no-cache add curl

# Define the command to run the application
CMD ["node", "dist/main"]