#!/usr/bin/env bash
set -euo pipefail

echo "=== Release Pilot Setup ==="
echo ""
echo "1. Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "2. Building Docker image..."
docker build -t release-pilot:latest .

echo ""
echo "3. Creating K8s secret (if k8s/secret.yaml exists)..."
if [ -f k8s/secret.yaml ]; then
  kubectl apply -f k8s/secret.yaml
else
  echo "   SKIP: k8s/secret.yaml not found."
  echo "   Copy k8s/secret.yaml.example to k8s/secret.yaml and fill in your API keys."
fi

echo ""
echo "4. Applying K8s manifests..."
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

echo ""
echo "5. Waiting for rollout..."
kubectl rollout status deployment/release-pilot

echo ""
echo "=== Setup complete ==="
echo "Service available at: http://localhost:30080/graphql"
echo ""
echo "To run locally (without K8s):"
echo "  export \$(cat .env | xargs)   # load env vars"
echo "  uvicorn api:app --port 8080  # in one terminal"
echo "  python slackbot.py            # in another terminal"
