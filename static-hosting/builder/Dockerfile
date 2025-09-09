# Multi-stage builder for static sites
FROM node:18-alpine as node-builder
FROM alpine:3.18 as base

# Install common dependencies
RUN apk add --no-cache \
    curl \
    wget \
    unzip \
    tar \
    gzip \
    git \
    bash \
    ca-certificates

# Install MinIO client
RUN wget -O /usr/local/bin/mc https://dl.min.io/client/mc/release/linux-amd64/mc && \
    chmod +x /usr/local/bin/mc

# Install Node.js for builds that need it
COPY --from=node-builder /usr/local/bin/node /usr/local/bin/
COPY --from=node-builder /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -sf /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm && \
    ln -sf /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

# Create working directories
RUN mkdir -p /workspace /output

# Copy build script
COPY build-and-upload.sh /usr/local/bin/build-and-upload.sh
RUN chmod +x /usr/local/bin/build-and-upload.sh

WORKDIR /workspace

ENTRYPOINT ["/usr/local/bin/build-and-upload.sh"]