# Static Site Hosting Integration

Simple integration of MinIO-based static site hosting into the existing Claude Research stack.

## Architecture

```
[User] ──▶ Wildcard Route (*.sites.apps) ──▶ Service (backend)
                                    │
                                    ▼
                              [Go Backend]
                       ┌───────────┴───────────┐
                       │  1) Proxy static GETs │  e.g. GET https://<cr>.sites.apps/
                       │     to MinIO          │
                       │  2) Serve Next.js UI  │
                       │  3) Research API      │
                       └───────────┬───────────┘
                                   │
                                   ▼
                               [MinIO]
                       s3://sites/<cr>/(index.html, assets)

[Operator] ◀──── Job status ───── [Job]
     │                                 \
     │ creates Job                      \  unzip + upload:
     ▼                                   \  mc mirror /tmp/dist → s3://sites/<cr>/
   StaticSite CRD
```

## Components

### Existing (Enhanced)
- **Go Backend**: Added static site proxy functionality
- **Operator**: Added StaticSite CRD handling
- **Next.js Frontend**: Unchanged

### New (Minimal)
- **MinIO**: S3-compatible storage for static files
- **StaticSite CRD**: Simple custom resource for sites
- **Build Jobs**: Container jobs that build and upload sites
- **Wildcard Route**: `*.sites.apps.example.com` → backend

## Usage

### 1. Deploy MinIO
```bash
kubectl apply -f manifests/minio.yaml
```

### 2. Deploy StaticSite CRD
```bash
kubectl apply -f manifests/staticsite-crd.yaml
```

### 3. Deploy Wildcard Route
```bash
kubectl apply -f manifests/wildcard-route.yaml
```

### 4. Create a Static Site
```yaml
apiVersion: hosting.example.com/v1
kind: StaticSite
metadata:
  name: my-site
spec:
  source:
    type: git
    git:
      repository: "https://github.com/example/site.git"
      branch: "main"
  build:
    enabled: false  # Set to true for React/Vue/etc
  spa: false        # Set to true for SPA routing
```

### 5. Access Your Site
- **Subdomain**: `https://my-site.sites.apps.example.com/`
- **Path**: `https://sites.apps.example.com/publish/my-site/`

## Backend Proxy Features

### URL Routing
- Subdomain: `<cr>.sites.apps.domain` → `sites/<cr>/`
- Path: `/publish/<cr>/path` → `sites/<cr>/path`

### Caching
- HTML: `Cache-Control: no-store`
- Hashed assets: `Cache-Control: public,max-age=31536000,immutable`
- Regular assets: `Cache-Control: public,max-age=3600`

### SPA Support
- On 404, tries serving `index.html`
- Perfect for React Router, Vue Router, etc.

### Health Checks
```bash
curl https://sites.apps.example.com/api/sites/my-site/health
```

## Storage Layout

MinIO bucket `sites`:
```
sites/
├── my-site/           # Each StaticSite gets own folder
│   ├── index.html     # Always overwritten on build
│   ├── assets/
│   └── css/
├── react-app/
│   ├── index.html
│   └── build/
```

## Security

- **MinIO**: Anonymous GET only on `sites/` bucket
- **Backend**: Non-root container, OpenShift SCC compatible
- **Route**: TLS termination, automatic HTTPS redirect

## Observability

Backend logs include:
```
PROXY GET /my-site/index.html 200 45ms site=my-site
PROXY GET /my-site/app.js 200 12ms site=my-site
```

## Examples

### Simple HTML Site
```yaml
apiVersion: hosting.example.com/v1
kind: StaticSite
metadata:
  name: docs
spec:
  source:
    type: git
    git:
      repository: "https://github.com/example/docs.git"
```

### React App
```yaml
apiVersion: hosting.example.com/v1
kind: StaticSite
metadata:
  name: webapp
spec:
  source:
    type: git
    git:
      repository: "https://github.com/example/react-app.git"
  build:
    enabled: true
    command: "npm ci && npm run build"
    outputDir: "build"
  spa: true
```

## That's It!

No per-site Deployments or Routes needed. The operator stays focused on Jobs + CRD status. The backend handles all the proxy magic transparently.