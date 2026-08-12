#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

kind create cluster --config kind-config.yml

docker build -t ip-checker-image:latest .
kind load docker-image ip-checker-image:latest --name ip-checker-cluster

kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl wait --namespace ingress-nginx --for=condition=Ready pods --all --timeout=180s

helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add minio https://charts.min.io/
helm repo update

helm dependency build ./helm/ip-checker-chart

helm install ip-checker ./helm/ip-checker-chart --namespace ip-checker --create-namespace
helm install monitoring ./helm/monitoring-stack --namespace monitoring --create-namespace
