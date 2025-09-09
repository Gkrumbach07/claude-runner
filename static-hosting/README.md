# Multi-Site Static Hosting Platform

A complete static site hosting platform for OpenShift that provides automated building, deployment, and hosting of static websites with subdomain and path-based routing.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   OpenShift     │    │     NGINX       │    │     MinIO       │
│    Routes       │    │     Proxy       │    │    Storage      │
│                 │    │                 │    │                 │
│ *.sites.apps... │───▶│ - Subdomain     │───▶│ /sites/<cr>/    │
│ sites.apps...   │    │ - Path routing  │    │ - index.html    │
│                 │    │ - SPA fallback  │    │ - assets/       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                ▲
                                │
┌─────────────────┐    ┌─────────────────┐
│   StaticSite    │    │  Build Jobs     │
│      CRD        │    │                 │
│                 │    │ - Git clone     │
│ - Git/Docker/URL│───▶│ - npm build     │
│ - Build config  │    │ - Upload files  │
│ - SPA mode      │    │ - Update status │
└─────────────────┘    └─────────────────┘
                                ▲
                                │
                       ┌─────────────────┐
                       │    Operator     │
                       │                 │
                       │ - Watch CRDs    │
                       │ - Create Jobs   │
                       │ - Update Status │
                       │ - Cleanup       │
                       └─────────────────┘
```

## Features

### 🚀 **Multi-Source Support**
- **Git repositories**: Clone from any Git repo with branch/path selection
- **Docker images**: Extract static files from container images
- **URL archives**: Download and extract from zip/tar.gz URLs

### 🔨 **Build Pipeline**
- **Framework support**: React, Vue, Angular, Gatsby, Next.js, etc.
- **Custom build commands**: Configure any build process
- **Node.js environment**: Built-in npm/yarn support
- **Output directory mapping**: Flexible build output handling

### 🌐 **Flexible Routing**
- **Subdomain routing**: `<site>.sites.apps.example.com`
- **Path-based routing**: `sites.apps.example.com/publish/<site>/`
- **Custom domains**: Optional custom domain support
- **SPA fallback**: Automatic `index.html` serving for SPAs

### ☁️ **Cloud-Native Storage**
- **MinIO object storage**: S3-compatible storage backend
- **Persistent volumes**: Kubernetes-native storage
- **Automatic cleanup**: Configurable retention policies
- **Archive tracking**: Build history and rollback support

### 🔒 **Security & Performance**
- **TLS termination**: Automatic HTTPS with OpenShift routes
- **Security headers**: Configurable HTTP security headers
- **Gzip compression**: Automatic asset compression
- **Caching**: Long-term caching for static assets
- **Network policies**: Kubernetes network isolation

## Quick Start

### 1. Deploy the Platform

```bash
# Clone the repository
git clone <repo-url>
cd static-hosting

# Deploy to OpenShift
./deploy.sh
```

### 2. Create Your First Site

```yaml
# my-site.yaml
apiVersion: hosting.example.com/v1
kind: StaticSite
metadata:
  name: my-docs
  namespace: static-hosting
spec:
  source:
    type: git
    git:
      repository: "https://github.com/example/docs.git"
      branch: "main"
  build:
    enabled: false
  spa: false
```

```bash
kubectl apply -f my-site.yaml
```

### 3. Monitor Deployment

```bash
# Watch site status
kubectl get staticsites -n static-hosting -w

# View build logs
kubectl logs -l static-site=my-docs -n static-hosting -f

# Check site URL
kubectl get staticsite my-docs -n static-hosting -o jsonpath='{.status.url}'
```

### 4. Access Your Site

- **Subdomain**: `https://my-docs.sites.apps.example.com`
- **Path-based**: `https://sites.apps.example.com/publish/my-docs/`

## Configuration Examples

### React Application

```yaml
apiVersion: hosting.example.com/v1
kind: StaticSite
metadata:
  name: react-app
spec:
  source:
    type: git
    git:
      repository: "https://github.com/example/react-app.git"
      branch: "main"
  build:
    enabled: true
    command: "npm ci && npm run build"
    outputDir: "build"
  spa: true  # Enable SPA routing
```

### Vue.js with Custom Build

```yaml
apiVersion: hosting.example.com/v1
kind: StaticSite
metadata:
  name: vue-portfolio
spec:
  source:
    type: git
    git:
      repository: "https://github.com/example/vue-app.git"
      branch: "production"
  build:
    enabled: true
    command: "npm install && npm run build:prod"
    outputDir: "dist"
  spa: true
  headers:
    X-Frame-Options: "DENY"
    Content-Security-Policy: "default-src 'self'"
```

### Static Files from Docker

```yaml
apiVersion: hosting.example.com/v1
kind: StaticSite
metadata:
  name: nginx-docs
spec:
  source:
    type: docker
    docker:
      image: "nginx:alpine"
      path: "/usr/share/nginx/html"
  build:
    enabled: false
```

### Archive from URL

```yaml
apiVersion: hosting.example.com/v1
kind: StaticSite
metadata:
  name: bootstrap-site
spec:
  source:
    type: url
    url:
      archive: "https://github.com/twbs/bootstrap/releases/download/v5.3.0/bootstrap-5.3.0-dist.zip"
      path: "bootstrap-5.3.0-dist"
  build:
    enabled: false
```

## API Reference

### StaticSite Resource

#### Spec Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source` | Object | Yes | Source configuration |
| `source.type` | String | Yes | Source type: `git`, `docker`, or `url` |
| `source.git` | Object | Conditional | Git source configuration |
| `source.docker` | Object | Conditional | Docker source configuration |
| `source.url` | Object | Conditional | URL source configuration |
| `build` | Object | No | Build configuration |
| `build.enabled` | Boolean | No | Enable build step (default: false) |
| `build.command` | String | No | Build command (default: "npm run build") |
| `build.outputDir` | String | No | Build output directory (default: "dist") |
| `spa` | Boolean | No | Enable SPA mode (default: false) |
| `domain` | String | No | Custom domain override |
| `headers` | Object | No | Custom HTTP headers |

#### Status Fields

| Field | Type | Description |
|-------|------|-------------|
| `phase` | String | Current phase: `Pending`, `Building`, `Uploading`, `Ready`, `Failed`, `Deleting` |
| `message` | String | Status message or error details |
| `url` | String | Public URL where site is accessible |
| `lastBuildTime` | String | Timestamp of last successful build |
| `jobName` | String | Name of current/last build job |
| `buildNumber` | Integer | Incremental build number |

## Operations

### Updating a Site

```bash
# Trigger rebuild by updating the resource
kubectl patch staticsite my-docs -n static-hosting --type merge -p '{"spec":{"source":{"git":{"branch":"develop"}}}}'

# Or edit directly
kubectl edit staticsite my-docs -n static-hosting
```

### Viewing Logs

```bash
# Build logs
kubectl logs -l static-site=my-docs -n static-hosting

# Operator logs
kubectl logs -l app=static-hosting-operator -n static-hosting

# NGINX proxy logs
kubectl logs -l app=nginx-proxy -n static-hosting
```

### Debugging

```bash
# Check site status
kubectl describe staticsite my-docs -n static-hosting

# Check build job
kubectl get jobs -l static-site=my-docs -n static-hosting

# Check MinIO storage
kubectl exec -it -n minio deployment/minio -- mc ls myminio/sites/
```

### Cleanup

```bash
# Delete a site
kubectl delete staticsite my-docs -n static-hosting

# This will:
# - Remove the StaticSite resource
# - Clean up MinIO storage
# - Remove associated jobs
```

## Storage Layout

MinIO storage is organized as follows:

```
sites/
├── my-docs/              # Site: my-docs
│   ├── index.html
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
├── react-app/            # Site: react-app
│   ├── index.html
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   └── manifest.json
└── .archives/            # Build archives
    ├── my-docs-20231219-143022.zip
    └── react-app-20231219-143156.zip
```

## Monitoring

### Metrics

The platform exposes metrics for monitoring:

- Build success/failure rates
- Build duration
- Storage utilization
- Request metrics via NGINX

### Health Checks

- **MinIO**: `http://minio.minio.svc:9000/minio/health/live`
- **NGINX**: `http://nginx-proxy.static-hosting.svc/health`
- **Operator**: Built-in Kubernetes probes

### Alerting

Consider setting up alerts for:

- Failed builds (>5% failure rate)
- Storage approaching capacity (>80%)
- High build queue length
- Service availability

## Troubleshooting

### Common Issues

#### Build Failures

```bash
# Check build logs
kubectl logs -l static-site=my-site -n static-hosting

# Common causes:
# - Missing package.json
# - Build command not found
# - Output directory doesn't exist
# - Network connectivity issues
```

#### Site Not Accessible

```bash
# Check NGINX proxy status
kubectl get pods -l app=nginx-proxy -n static-hosting

# Check MinIO storage
kubectl exec -it -n minio deployment/minio -- mc ls myminio/sites/my-site/

# Check routes
kubectl get routes -n static-hosting
```

#### Storage Issues

```bash
# Check MinIO status
kubectl get pods -n minio

# Check PVC
kubectl get pvc -n minio

# Manual MinIO access
kubectl port-forward -n minio svc/minio 9001:9001
# Access: http://localhost:9001
```

### Performance Tuning

#### Build Performance

- Increase build job resources
- Use build caching
- Optimize Docker images
- Use faster storage classes

#### Serving Performance

- Enable gzip compression (already configured)
- Use CDN for global distribution
- Optimize image sizes
- Implement asset versioning

## Security Considerations

### Access Control

- RBAC for operator permissions
- Network policies for pod isolation
- MinIO bucket policies
- Route-level access controls

### Data Protection

- TLS encryption in transit
- Storage encryption at rest
- Secure credential management
- Regular security updates

### Best Practices

1. **Use specific image tags** instead of `latest`
2. **Implement resource limits** for build jobs
3. **Regular backup** of MinIO data
4. **Monitor build logs** for security issues
5. **Keep dependencies updated**

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review existing GitHub issues
3. Create a new issue with detailed information
4. Include relevant logs and configurations

---

**Happy hosting!** 🚀