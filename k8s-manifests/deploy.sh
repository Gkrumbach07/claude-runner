#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Claude Research Runner Deployment Script${NC}"
echo "=========================================="

# Function to check if kubectl is available
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        echo -e "${RED}Error: kubectl is not installed or not in PATH${NC}"
        exit 1
    fi
}

# Function to check if we can connect to k8s cluster
check_cluster() {
    if ! kubectl cluster-info &> /dev/null; then
        echo -e "${RED}Error: Cannot connect to Kubernetes cluster${NC}"
        echo "Please ensure your kubeconfig is properly configured."
        exit 1
    fi
}

# Function to build docker images (placeholder)
build_images() {
    echo -e "${YELLOW}Building Docker images...${NC}"
    echo "Note: You need to build and push the following images:"
    echo "- claude-runner-backend:latest"
    echo "- claude-runner-frontend:latest"
    echo "- research-operator:latest"
    echo "- claude-runner:latest"
    echo ""
    echo "Example build commands:"
    echo "  docker build -t claude-runner-backend:latest ../backend/"
    echo "  docker build -t claude-runner-frontend:latest ../frontend/"
    echo "  docker build -t research-operator:latest ../operator/"
    echo "  docker build -t claude-runner:latest ../claude-runner/"
    echo ""
    read -p "Have you built and pushed all required images? (y/N): " confirm
    if [[ $confirm != [yY] && $confirm != [yY][eE][sS] ]]; then
        echo -e "${RED}Please build and push the required images first.${NC}"
        exit 1
    fi
}

# Function to deploy CRD
deploy_crd() {
    echo -e "${YELLOW}Deploying Custom Resource Definition...${NC}"
    kubectl apply -f crd.yaml
    echo -e "${GREEN}✓ CRD deployed${NC}"
}

# Function to deploy RBAC
deploy_rbac() {
    echo -e "${YELLOW}Deploying RBAC configuration...${NC}"
    kubectl apply -f rbac.yaml
    echo -e "${GREEN}✓ RBAC deployed${NC}"
}

# Function to deploy secrets
deploy_secrets() {
    echo -e "${YELLOW}Deploying secrets and config...${NC}"
    echo -e "${RED}Warning: Please update the Anthropic API key in secrets.yaml before deploying!${NC}"
    read -p "Have you updated the API key in secrets.yaml? (y/N): " confirm
    if [[ $confirm != [yY] && $confirm != [yY][eE][sS] ]]; then
        echo -e "${RED}Please update the API key first.${NC}"
        echo "To encode your API key: echo -n 'your-actual-api-key' | base64"
        exit 1
    fi
    kubectl apply -f secrets.yaml
    echo -e "${GREEN}✓ Secrets and config deployed${NC}"
}

# Function to deploy backend
deploy_backend() {
    echo -e "${YELLOW}Deploying backend API service...${NC}"
    kubectl apply -f backend-deployment.yaml
    echo -e "${GREEN}✓ Backend deployed${NC}"
}

# Function to deploy operator
deploy_operator() {
    echo -e "${YELLOW}Deploying research operator...${NC}"
    kubectl apply -f operator-deployment.yaml
    echo -e "${GREEN}✓ Operator deployed${NC}"
}

# Function to deploy frontend
deploy_frontend() {
    echo -e "${YELLOW}Deploying frontend application...${NC}"
    kubectl apply -f frontend-deployment.yaml
    echo -e "${GREEN}✓ Frontend deployed${NC}"
}

# Function to wait for deployments
wait_for_deployments() {
    echo -e "${YELLOW}Waiting for deployments to be ready...${NC}"
    kubectl wait --for=condition=available --timeout=300s deployment/backend-api
    kubectl wait --for=condition=available --timeout=300s deployment/research-operator
    kubectl wait --for=condition=available --timeout=300s deployment/frontend
    echo -e "${GREEN}✓ All deployments are ready${NC}"
}

# Function to display status
show_status() {
    echo -e "${BLUE}Deployment Status:${NC}"
    echo "=================="
    kubectl get pods -l 'app in (backend-api,research-operator,frontend)'
    echo ""
    kubectl get services -l 'app in (backend-api,frontend)'
    echo ""
    echo -e "${GREEN}Frontend URL: http://claude-research.local (add to /etc/hosts)${NC}"
    echo -e "${GREEN}Or use: kubectl port-forward svc/frontend-service 3000:3000${NC}"
}

# Main deployment process
main() {
    echo -e "${BLUE}Starting deployment process...${NC}"
    
    check_kubectl
    check_cluster
    build_images
    
    deploy_crd
    deploy_rbac
    deploy_secrets
    deploy_backend
    deploy_operator
    deploy_frontend
    
    wait_for_deployments
    show_status
    
    echo -e "${GREEN}Deployment completed successfully!${NC}"
}

# Handle command line arguments
case "${1:-}" in
    "crd")
        check_kubectl && check_cluster && deploy_crd
        ;;
    "rbac")
        check_kubectl && check_cluster && deploy_rbac
        ;;
    "secrets")
        check_kubectl && check_cluster && deploy_secrets
        ;;
    "backend")
        check_kubectl && check_cluster && deploy_backend
        ;;
    "operator")
        check_kubectl && check_cluster && deploy_operator
        ;;
    "frontend")
        check_kubectl && check_cluster && deploy_frontend
        ;;
    "status")
        check_kubectl && check_cluster && show_status
        ;;
    "clean")
        echo -e "${YELLOW}Cleaning up resources...${NC}"
        kubectl delete -f frontend-deployment.yaml --ignore-not-found
        kubectl delete -f operator-deployment.yaml --ignore-not-found
        kubectl delete -f backend-deployment.yaml --ignore-not-found
        kubectl delete -f secrets.yaml --ignore-not-found
        kubectl delete -f rbac.yaml --ignore-not-found
        kubectl delete -f crd.yaml --ignore-not-found
        echo -e "${GREEN}✓ Resources cleaned up${NC}"
        ;;
    *)
        main
        ;;
esac
