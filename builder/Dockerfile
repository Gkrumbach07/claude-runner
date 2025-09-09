FROM node:18-alpine

# Install dependencies
RUN apk add --no-cache \
    curl \
    wget \
    unzip \
    git \
    bash

# Install MinIO client
RUN wget -O /usr/local/bin/mc https://dl.min.io/client/mc/release/linux-amd64/mc && \
    chmod +x /usr/local/bin/mc

# Create directories
RUN mkdir -p /workspace /tmp/dist

# Copy build script
COPY build-and-upload.sh /usr/local/bin/build-and-upload.sh
RUN chmod +x /usr/local/bin/build-and-upload.sh

WORKDIR /workspace

ENTRYPOINT ["/usr/local/bin/build-and-upload.sh"]