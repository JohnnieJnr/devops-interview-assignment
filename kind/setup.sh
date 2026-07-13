#!/usr/bin/env bash
# Optional. Only needed if you want to test your manifests against a real cluster.
# You do NOT need to deploy against Kind to complete this task — the deploy/
# directory just needs applyable manifests.

set -euo pipefail

CLUSTER_NAME="${CLUSTER_NAME:-iam-takehome}"

if ! command -v kind >/dev/null 2>&1; then
  echo "kind is not installed. See https://kind.sigs.k8s.io/docs/user/quick-start/"
  exit 1
fi

if kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
  echo "Cluster ${CLUSTER_NAME} already exists."
else
  kind create cluster --config "$(dirname "$0")/cluster.yaml" --name "${CLUSTER_NAME}"
fi

kubectl cluster-info --context "kind-${CLUSTER_NAME}"

echo ""
echo "Cluster ready. Your manifests would apply to context: kind-${CLUSTER_NAME}"
