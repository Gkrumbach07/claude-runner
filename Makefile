.PHONY: help build-all build-frontend build-backend build-operator build-runner deploy clean dev-frontend dev-backend lint test

# Default target
help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Docker image tags
FRONTEND_IMAGE ?= claude-runner-frontend:latest
BACKEND_IMAGE ?= claude-runner-backend:latest
OPERATOR_IMAGE ?= research-operator:latest
RUNNER_IMAGE ?= claude-runner:latest

# Build all Docker images
build-all: build-frontend build-backend build-operator build-runner ## Build all Docker images

# Build for local development (native platform)
build-all-local: build-frontend-local build-backend-local build-operator-local build-runner-local ## Build all images for local platform

# Build individual components
build-frontend: ## Build the frontend Docker image
	@echo "Building frontend image..."
	cd frontend && docker build --platform=linux/amd64 -t $(FRONTEND_IMAGE) .

build-backend: ## Build the backend API Docker image
	@echo "Building backend image..."
	cd backend && docker build --platform=linux/amd64 -t $(BACKEND_IMAGE) .

build-operator: ## Build the operator Docker image
	@echo "Building operator image..."
	cd operator && docker build --platform=linux/amd64 -t $(OPERATOR_IMAGE) .

build-runner: ## Build the Claude runner Docker image
	@echo "Building Claude runner image..."
	cd claude-runner && docker build --platform=linux/amd64 -t $(RUNNER_IMAGE) .

# Local development builds (native platform - faster for local testing)
build-frontend-local: ## Build frontend for local platform
	@echo "Building frontend image (local platform)..."
	cd frontend && docker build -t $(FRONTEND_IMAGE) .

build-backend-local: ## Build backend for local platform
	@echo "Building backend image (local platform)..."
	cd backend && docker build -t $(BACKEND_IMAGE) .

build-operator-local: ## Build operator for local platform
	@echo "Building operator image (local platform)..."
	cd operator && docker build -t $(OPERATOR_IMAGE) .

build-runner-local: ## Build Claude runner for local platform
	@echo "Building Claude runner image (local platform)..."
	cd claude-runner && docker build -t $(RUNNER_IMAGE) .

# Development targets
dev-frontend: ## Start frontend in development mode
	cd frontend && npm install && npm run dev

dev-backend: ## Start backend in development mode
	cd backend && go run main.go

dev-operator: ## Start operator in development mode
	cd operator && go run main.go

# Kubernetes deployment
deploy: ## Deploy all components to Kubernetes
	@echo "Deploying to Kubernetes..."
	cd k8s-manifests && ./deploy.sh

deploy-crd: ## Deploy only the Custom Resource Definition
	kubectl apply -f k8s-manifests/crd.yaml

deploy-rbac: ## Deploy only RBAC configuration
	kubectl apply -f k8s-manifests/rbac.yaml

deploy-secrets: ## Deploy secrets and config
	kubectl apply -f k8s-manifests/secrets.yaml

deploy-backend: ## Deploy only the backend service
	kubectl apply -f k8s-manifests/backend-deployment.yaml

deploy-operator: ## Deploy only the operator
	kubectl apply -f k8s-manifests/operator-deployment.yaml

deploy-frontend: ## Deploy only the frontend
	kubectl apply -f k8s-manifests/frontend-deployment.yaml

# Cleanup
clean: ## Clean up all Kubernetes resources
	@echo "Cleaning up Kubernetes resources..."
	cd k8s-manifests && ./deploy.sh clean

# Status and monitoring
status: ## Show deployment status
	@echo "Deployment Status:"
	@echo "=================="
	kubectl get pods -l 'app in (backend-api,research-operator,frontend)'
	@echo ""
	kubectl get services -l 'app in (backend-api,frontend)'
	@echo ""
	kubectl get researchsessions

logs-backend: ## View backend logs
	kubectl logs -l app=backend-api -f

logs-operator: ## View operator logs
	kubectl logs -l app=research-operator -f

logs-frontend: ## View frontend logs
	kubectl logs -l app=frontend -f

# Port forwarding for local access
port-forward-frontend: ## Port forward frontend service to localhost:3000
	kubectl port-forward svc/frontend-service 3000:3000

port-forward-backend: ## Port forward backend service to localhost:8080
	kubectl port-forward svc/backend-service 8080:8080

# Development setup with Kind
kind-create: ## Create a local Kubernetes cluster with Kind
	kind create cluster --name claude-research

kind-load: build-all-local ## Load all images into Kind cluster (using local builds for speed)
	kind load docker-image $(FRONTEND_IMAGE) --name claude-research
	kind load docker-image $(BACKEND_IMAGE) --name claude-research
	kind load docker-image $(OPERATOR_IMAGE) --name claude-research
	kind load docker-image $(RUNNER_IMAGE) --name claude-research

kind-deploy: kind-load deploy ## Deploy to Kind cluster

kind-clean: ## Delete the Kind cluster
	kind delete cluster --name claude-research

# Linting and testing
lint-frontend: ## Lint frontend code
	cd frontend && npm run lint

lint-backend: ## Lint backend code
	cd backend && go fmt ./... && go vet ./...

lint-operator: ## Lint operator code
	cd operator && go fmt ./... && go vet ./...

lint: lint-frontend lint-backend lint-operator ## Lint all code

# Testing
test-frontend: ## Run frontend tests
	cd frontend && npm test

test-backend: ## Run backend tests
	cd backend && go test ./...

test-operator: ## Run operator tests
	cd operator && go test ./...

test: test-frontend test-backend test-operator ## Run all tests

# Docker registry operations (customize REGISTRY as needed)
REGISTRY ?= your-registry.com

push-all: build-all ## Push all images to registry
	docker tag $(FRONTEND_IMAGE) $(REGISTRY)/$(FRONTEND_IMAGE)
	docker tag $(BACKEND_IMAGE) $(REGISTRY)/$(BACKEND_IMAGE)
	docker tag $(OPERATOR_IMAGE) $(REGISTRY)/$(OPERATOR_IMAGE)
	docker tag $(RUNNER_IMAGE) $(REGISTRY)/$(RUNNER_IMAGE)
	docker push $(REGISTRY)/$(FRONTEND_IMAGE)
	docker push $(REGISTRY)/$(BACKEND_IMAGE)
	docker push $(REGISTRY)/$(OPERATOR_IMAGE)
	docker push $(REGISTRY)/$(RUNNER_IMAGE)

# Utility targets
install-deps: ## Install development dependencies
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo "Installing Go dependencies..."
	cd backend && go mod tidy
	cd operator && go mod tidy

create-namespace: ## Create the default namespace if it doesn't exist
	kubectl create namespace default --dry-run=client -o yaml | kubectl apply -f -

# Example research session
create-example: ## Create an example research session
	kubectl apply -f - <<EOF
	apiVersion: research.example.com/v1
	kind: ResearchSession
	metadata:
	  name: example-research
	spec:
	  prompt: "Analyze this website and provide insights about its design and user experience"
	  websiteURL: "https://example.com"
	  llmSettings:
	    model: "claude-3-5-sonnet-20241022"
	    temperature: 0.7
	    maxTokens: 4000
	  timeout: 300
	EOF

# Full development setup
dev-setup: install-deps build-all kind-create kind-deploy ## Complete development setup
