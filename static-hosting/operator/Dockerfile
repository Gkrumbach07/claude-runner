FROM golang:1.21-alpine AS builder

WORKDIR /app

# Copy go mod files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY *.go ./

# Build the operator
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o operator .

# Final stage
FROM alpine:3.18

RUN apk --no-cache add ca-certificates

WORKDIR /root/

COPY --from=builder /app/operator .

CMD ["./operator"]