#!/bin/bash

# Multi-Site Static Hosting Deployment Script
# Deploys the complete static hosting platform on OpenShift

set -e

echo "🚀 Deploying Multi-Site Static Hosting Platform on OpenShift"
echo "============================================================="

# Configuration
DOMAIN=${DOMAIN:-"apps.example.com"}
MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY:-"admin"}
MINIO_SECRET_KEY=${MINIO_SECRET_KEY:-"password123"}

echo "📋 Configuration:"
echo "  Base Domain: $DOMAIN"
echo "  MinIO Access Key: $MINIO_ACCESS_KEY"
echo ""

# Function to wait for deployment
wait_for_deployment() {
    local namespace=$1
    local deployment=$2
    local timeout=${3:-300}
    
    echo "⏳ Waiting for $deployment in $namespace to be ready..."
    kubectl wait --for=condition=available --timeout=${timeout}s deployment/$deployment -n $namespace
}

# Function to wait for job completion
wait_for_job() {
    local namespace=$1
    local job=$2
    local timeout=${3:-300}
    
    echo "⏳ Waiting for job $job in $namespace to complete..."
    kubectl wait --for=condition=complete --timeout=${timeout}s job/$job -n $namespace
}

echo "1️⃣ Creating namespaces..."
kubectl create namespace minio --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace static-hosting --dry-run=client -o yaml | kubectl apply -f -

echo "2️⃣ Deploying MinIO storage..."
kubectl apply -f manifests/minio.yaml

echo "3️⃣ Waiting for MinIO to be ready..."
wait_for_deployment minio minio

echo "4️⃣ Waiting for MinIO setup job to complete..."
wait_for_job minio minio-setup

echo "5️⃣ Deploying Custom Resource Definition..."
kubectl apply -f manifests/crd.yaml

echo "6️⃣ Setting up RBAC..."
kubectl apply -f manifests/rbac.yaml

echo "7️⃣ Deploying NGINX proxy..."
kubectl apply -f manifests/nginx-proxy.yaml

echo "8️⃣ Waiting for NGINX proxy to be ready..."
wait_for_deployment static-hosting nginx-proxy

echo "9️⃣ Deploying operator..."
kubectl apply -f manifests/operator.yaml

echo "🔟 Waiting for operator to be ready..."
wait_for_deployment static-hosting static-hosting-operator

echo "🌐 Setting up OpenShift routes..."
# Update routes with actual domain
sed "s/apps\.example\.com/$DOMAIN/g" manifests/routes.yaml | kubectl apply -f -

echo "✅ Deployment completed successfully!"
echo ""
echo "📖 Platform Overview:"
echo "  • MinIO storage deployed in 'minio' namespace"
echo "  • Static hosting operator deployed in 'static-hosting' namespace"
echo "  • NGINX proxy handling subdomain and path-based routing"
echo "  • Wildcard route configured: *.sites.$DOMAIN"
echo ""
echo "🎯 Next Steps:"
echo "1. Create a StaticSite resource:"
echo "   kubectl apply -f manifests/examples.yaml"
echo ""
echo "2. Check site status:"
echo "   kubectl get staticsites -n static-hosting"
echo ""
echo "3. View site logs:"
echo "   kubectl logs -l app=static-site-builder -n static-hosting"
echo ""
echo "4. Access your sites:"
echo "   https://<site-name>.sites.$DOMAIN"
echo "   https://sites.$DOMAIN/publish/<site-name>/"
echo ""
echo "🔍 Monitoring:"
echo "  kubectl get pods -n minio"
echo "  kubectl get pods -n static-hosting"
echo "  kubectl get staticsites -n static-hosting -w"
echo ""
echo "🎉 Happy hosting!"