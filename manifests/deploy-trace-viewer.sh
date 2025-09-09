#!/bin/bash

# Deploy Trace Viewer Integration for Claude Research
# This script deploys the complete trace viewer integration

set -e

echo "🚀 Deploying Claude Research Trace Viewer Integration..."

# Check if namespace exists
if ! kubectl get namespace claude-research >/dev/null 2>&1; then
    echo "❌ Namespace 'claude-research' not found. Please create it first:"
    echo "kubectl create namespace claude-research"
    exit 1
fi

echo "📋 Updating CRD with trace settings..."
kubectl apply -f crd.yaml

echo "💾 Creating artifacts persistent volume claim..."
kubectl apply -f artifacts-pvc.yaml

echo "🎬 Deploying trace viewer service..."
kubectl apply -f trace-viewer-deployment.yaml

echo "🔄 Restarting operator to pick up new CRD fields..."
kubectl rollout restart deployment/operator -n claude-research

echo "🔄 Restarting backend to pick up new API endpoints..."
kubectl rollout restart deployment/backend -n claude-research

echo "🔄 Restarting frontend to pick up new UI components..."
kubectl rollout restart deployment/frontend -n claude-research

echo "⏳ Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/trace-viewer -n claude-research
kubectl wait --for=condition=available --timeout=300s deployment/operator -n claude-research
kubectl wait --for=condition=available --timeout=300s deployment/backend -n claude-research
kubectl wait --for=condition=available --timeout=300s deployment/frontend -n claude-research

echo "✅ Trace viewer integration deployed successfully!"
echo ""
echo "📖 What's new:"
echo "• Browser traces are now automatically recorded during research sessions"
echo "• Interactive trace viewer available in session detail pages"
echo "• Artifacts (traces, screenshots, PDFs) are stored persistently"
echo "• New API endpoints for artifact serving and trace viewing"
echo ""
echo "🔍 To verify the deployment:"
echo "kubectl get pods -n claude-research"
echo "kubectl get pvc -n claude-research"
echo ""
echo "🎯 Create a new research session to test trace recording!"