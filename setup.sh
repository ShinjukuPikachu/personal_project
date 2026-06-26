#!/usr/bin/env bash
set -euo pipefail
echo "Installing Python deps..."
pip install -r requirements.txt
echo "Building Docker image..."
docker build -t release-pilot:latest .
echo "Applying K8s manifests..."
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
echo "Waiting for rollout..."
kubectl rollout status deployment/release-pilot
echo ""
echo "Service ready at http://localhost:30080/graphql"
