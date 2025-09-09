# Clean Backend Proxy Architecture

This document describes the simplified, production-ready architecture using the backend as a transparent reverse proxy to MinIO.

## Overview

Instead of a separate NGINX proxy, we use the existing backend as a transparent reverse proxy. This provides a **clean, single-service setup** with one public Route and keeps MinIO internal.

## Key Benefits

✅ **Simple**: Single public endpoint, MinIO stays internal  
✅ **Fast**: Transparent streaming, no credential exposure  
✅ **Secure**: Anonymous GET only, non-root containers  
✅ **Observable**: Built-in logging with site, method, status, upstream time  
✅ **Cacheable**: Smart cache headers for HTML vs hashed assets  
✅ **Healthy**: Built-in health checks for published sites  

## Architecture Flow

```
[Client Request]
       ↓
[OpenShift Route: sites.apps.example.com]
       ↓
[Backend Service: Transparent Proxy]
       ↓
[MinIO: Anonymous GET from sites/<cr>/...]
       ↓
[Stream Response Back to Client]
```

## URL Patterns

| Pattern | Example | Description |
|---------|---------|-------------|
| `/<cr>/...` | `/my-site/index.html` | Direct routing to site |
| `/publish/<cr>/...` | `/publish/my-site/about.html` | Alternative path routing |
| `/api/sites/<cr>/health` | `/api/sites/my-site/health` | Health check endpoint |

## Backend Proxy Features

### 🔄 **Transparent Streaming**
- No MinIO credentials needed by backend
- Direct byte streaming from MinIO to client
- Automatic content-type detection
- Security header injection

### 📦 **Smart Caching**
```go
// HTML files: no caching
Cache-Control: no-store

// Hashed assets: long-term caching  
Cache-Control: public, max-age=31536000, immutable

// Regular assets: moderate caching
Cache-Control: public, max-age=3600
```

### 🎯 **SPA Fallback**
- On 404, try serving `index.html`
- Perfect for React Router, Vue Router, etc.
- Maintains proper HTTP status codes

### 🩺 **Health Checks**
```bash
curl https://sites.apps.example.com/api/sites/my-site/health
```

Response:
```json
{
  "site": "my-site",
  "status": "healthy", 
  "index_exists": true,
  "last_modified": "Wed, 19 Dec 2023 14:30:22 GMT",
  "content_length": "2048"
}
```

### 📊 **Observability**
```
PROXY GET /my-site/index.html 200 45ms site=my-site
PROXY GET /my-site/app.js 200 12ms site=my-site  
PROXY GET /my-site/missing.html 200 23ms (SPA fallback)
```

## MinIO Configuration

### Anonymous GET Access
```bash
# Set download-only policy (no upload/delete)
mc anonymous set download myminio/sites

# Verify policy
mc anonymous get myminio/sites
# Returns: download
```

### Storage Layout
```
sites/
├── my-site/              # Each CR gets its own folder
│   ├── index.html        # Always overwritten on new build
│   ├── assets/
│   └── static/
├── react-app/
│   ├── index.html
│   └── build/
└── .archives/            # Build history
    ├── my-site-20231219-143022.zip
    └── react-app-20231219-143156.zip
```

## Security Model

### 🔒 **Access Control**
- MinIO: Anonymous GET only on `sites/` bucket
- Backend: Non-root container, restricted SCC compatible
- Route: TLS termination, automatic HTTPS redirect

### 🛡️ **Security Headers**
```
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff  
X-XSS-Protection: 1; mode=block
```

### 🚫 **Path Traversal Protection**
```go
// Clean and validate file paths
filePath = filepath.Clean(filePath)
if strings.HasPrefix(filePath, "../") {
    return 400 // Bad Request
}
```

## Performance Characteristics

### ⚡ **Fast Streaming**
- Direct byte streaming via `io.Copy()`
- No intermediate buffering
- Preserves original content-length
- Supports range requests (via MinIO)

### 🎯 **Efficient Caching**
- HTML: `Cache-Control: no-store` (always fresh)
- Hashed assets: `max-age=31536000, immutable` (1 year)
- Regular assets: `max-age=3600` (1 hour)

### 📈 **Scalability**
- Stateless backend (horizontal scaling)
- MinIO handles concurrent reads
- OpenShift Route load balancing

## Deployment Simplicity

### Single Route
```yaml
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: static-sites
spec:
  host: sites.apps.example.com
  to:
    kind: Service
    name: backend-service
  tls:
    termination: edge
```

### Internal MinIO
```yaml
# ClusterIP only - no external exposure
apiVersion: v1
kind: Service
metadata:
  name: minio
spec:
  type: ClusterIP  # Internal only
  ports:
  - port: 9000
```

## Monitoring & Debugging

### 📋 **Health Monitoring**
```bash
# Check backend health
curl https://sites.apps.example.com/health

# Check site health  
curl https://sites.apps.example.com/api/sites/my-site/health

# Check MinIO directly (internal)
kubectl exec -it -n minio deployment/minio -- mc ls myminio/sites/
```

### 📊 **Logs & Metrics**
```bash
# Backend proxy logs
kubectl logs -l component=backend -n static-hosting

# Look for proxy entries
PROXY GET /my-site/index.html 200 45ms site=my-site
```

### 🔍 **Debugging Flow**
1. **Route**: Check OpenShift route status
2. **Backend**: Check backend pod logs and health
3. **MinIO**: Check MinIO connectivity and file existence
4. **Storage**: Verify PVC and file permissions

## Best Practices

### 🏗️ **Build Process**
1. Jobs publish to `sites/<cr>/` (overwrites completely)
2. Use `mc mirror --overwrite --remove` for clean deploys
3. Generate `site.zip` archives for rollback capability

### 🔧 **Operations**
1. Monitor backend proxy logs for errors
2. Set up alerts on 5xx responses from MinIO
3. Implement rate limiting if needed (per-site basis)
4. Regular MinIO storage cleanup for old archives

### 🚀 **Performance**
1. Use CDN in front of OpenShift Route for global users
2. Enable gzip compression in OpenShift Route if needed
3. Monitor backend memory usage under load
4. Consider MinIO clustering for high availability

## Migration from NGINX

If migrating from separate NGINX proxy:

1. ✅ Remove NGINX deployment and service
2. ✅ Update Route to point to backend-service
3. ✅ Backend handles all proxy logic transparently
4. ✅ Same URL patterns work (backward compatible)
5. ✅ Better observability and simpler operations

## Summary

This architecture provides a **clean, fast, and secure** static site hosting platform with:

- **Single service**: Backend handles both API and static file serving
- **Transparent proxy**: No credentials needed, direct streaming
- **Smart caching**: Optimized for modern web apps
- **Built-in health checks**: Monitor site availability
- **OpenShift native**: Secure, scalable, observable

The result is a production-ready platform that's simpler to operate than separate proxy services while maintaining all the performance and security benefits.