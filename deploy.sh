#!/bin/bash
# Build and deploy the QA Status Reporter

set -e

PROJECT_ID="crx-dev-svc"
IMAGE_NAME="qa-status-reporter"
IMAGE_TAG="latest"
FULL_IMAGE="gcr.io/${PROJECT_ID}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "=== Building QA Status Reporter ==="

# Build Docker image
echo "Building Docker image..."
docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .

# Tag for GCR
echo "Tagging image for GCR..."
docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${FULL_IMAGE}

# Push to GCR
echo "Pushing to GCR..."
docker push ${FULL_IMAGE}

echo "✓ Image pushed: ${FULL_IMAGE}"

# Deploy to Kubernetes
echo ""
echo "=== Deploying to Kubernetes ==="
kubectl apply -f cronjob.yaml

echo ""
echo "✓ Deployment complete!"
echo ""
echo "To test manually, run:"
echo "  kubectl create job --from=cronjob/qa-status-reporter test-run-1 -n dev"
echo ""
echo "To check logs:"
echo "  kubectl logs -n dev -l app=qa-status-reporter --tail=100"
echo ""
echo "To view cronjob status:"
echo "  kubectl get cronjob qa-status-reporter -n dev"
