# Playwright trace viewer service
FROM node:18-alpine

# Install Playwright with trace viewer
RUN npm install -g @playwright/test

# Create app directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application code
COPY . .

# Create artifacts mount point
RUN mkdir -p /artifacts

# Expose port
EXPOSE 3000

# Start the trace viewer service
CMD ["npm", "start"]