#!/usr/bin/env bash
set -e

helm uninstall monitoring --namespace monitoring || true
helm uninstall ip-checker --namespace ip-checker || true

kubectl delete namespace monitoring --ignore-not-found=true
kubectl delete namespace ip-checker --ignore-not-found=true

kind delete cluster --name ip-checker-cluster
