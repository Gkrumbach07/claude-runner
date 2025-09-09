FROM golang:1.21-alpine AS builder

WORKDIR /app

# Copy go mod files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY *.go ./

# Build the backend
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o backend .

# Final stage
FROM alpine:3.18

RUN apk --no-cache add ca-certificates

WORKDIR /root/

# Create non-root user for security
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup

# Copy binary
COPY --from=builder /app/backend .

# Change ownership
RUN chown appuser:appgroup backend

# Use non-root user
USER appuser

EXPOSE 8080

CMD ["./backend"]