#!/bin/bash
# DevAssist OpenShift Deployment Script
# 
# Usage:
#   ./deploy.sh                    # Deploy everything
#   ./deploy.sh --secrets-only     # Only create secrets
#   ./deploy.sh --build            # Build and push image first
#
# Prerequisites:
#   - oc login to your OpenShift cluster
#   - Access to quay.io/ayutiwar (or change the image registry)

set -e

NAMESPACE="${DEVASSIST_NAMESPACE:-devassist}"
IMAGE="quay.io/ayutiwar/devassist:latest"

echo "=========================================="
echo "DevAssist OpenShift Deployment"
echo "=========================================="
echo "Namespace: $NAMESPACE"
echo "Image: $IMAGE"
echo ""

# Parse arguments
BUILD=false
SECRETS_ONLY=false

for arg in "$@"; do
    case $arg in
        --build)
            BUILD=true
            ;;
        --secrets-only)
            SECRETS_ONLY=true
            ;;
    esac
done

# Create namespace if it doesn't exist
if ! oc get namespace "$NAMESPACE" &>/dev/null; then
    echo "Creating namespace: $NAMESPACE"
    oc create namespace "$NAMESPACE"
fi

# Set current namespace
oc project "$NAMESPACE"

# Build and push image if requested
if [ "$BUILD" = true ]; then
    echo ""
    echo "Building container image..."
    cd "$(dirname "$0")/../.."
    
    # Build with podman (or docker)
    if command -v podman &>/dev/null; then
        podman build -t "$IMAGE" .
        podman push "$IMAGE"
    else
        docker build -t "$IMAGE" .
        docker push "$IMAGE"
    fi
    
    echo "✓ Image built and pushed: $IMAGE"
    cd - >/dev/null
fi

echo ""
echo "Deploying resources..."

# Apply secrets first
echo "  Applying secrets..."
oc apply -f secrets.yaml

if [ "$SECRETS_ONLY" = true ]; then
    echo ""
    echo "✓ Secrets created. Edit them with:"
    echo "  oc edit secret devassist-secrets -n $NAMESPACE"
    exit 0
fi

# Apply database
echo "  Deploying database..."
oc apply -f database.yaml

# Wait for database to be ready
echo "  Waiting for database to be ready..."
oc rollout status deployment/devassist-db --timeout=120s

# Apply worker deployment
echo "  Deploying worker..."
oc apply -f deployment.yaml

# Wait for worker to be ready
echo "  Waiting for worker to be ready..."
oc rollout status deployment/devassist-worker --timeout=120s

echo ""
echo "=========================================="
echo "✓ Deployment complete!"
echo "=========================================="
echo ""
echo "Check status:"
echo "  oc get pods -n $NAMESPACE"
echo ""
echo "View logs:"
echo "  oc logs -f deployment/devassist-worker -n $NAMESPACE"
echo ""
echo "Edit secrets (update with real values):"
echo "  oc edit secret devassist-secrets -n $NAMESPACE"
echo ""
