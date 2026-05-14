## ip-checker

A small Flask-based API that looks up IP address information using `ip-api.com`.

It exposes:

- `GET /health` – simple health check.
- `GET /` – usage instructions.
- `GET /ip/<ip>` – returns basic geo/IP info for the given IP.
- `GET /metrics` - return Prometheus metrics
- `POST /store` - post redis data to minio

---

## Configuration

The app reads configuration from environment variables (or a `.env` file in development via `python-dotenv`):

- **`FLASK_PORT`** – port the Flask app listens on (e.g. `5000`).
- **`IP_API_URL`** – URL template for the external IP API, e.g. `http://ip-api.com/json/{}`.
- **`LOG_LEVEL`** – logging level, e.g. `INFO`, `DEBUG`.
- **`BASE_URL`** – base URL for integration tests (defaults to `http://127.0.0.1:${FLASK_PORT}` if not set).

Example `.env`:

````bashpy
FLASK_PORT=5000
IP_API_URL=http://ip-api.com/json/{}
LOG_LEVEL=INFO
BASE_URL=http://ip-checker.local:8080

# REDIS_HOST=localhost
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
CACHE_TTL=3600

# MinIO
MINIO_ENDPOINT=minio:9000
# MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=ip-backup
BACKUP_INTERVAL=300```
---

## Running locally (without Docker)

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export FLASK_PORT=5000
export IP_API_URL="http://ip-api.com/json/{}"
export LOG_LEVEL=INFO

python src/app.py
````

---

## Running docker-compose

`docker-compose.yml` expects a `.env` file with at least `FLASK_PORT` defined:

```bash
FLASK_PORT=5000
IP_API_URL=http://ip-api.com/json/{}
LOG_LEVEL=INFO
BASE_URL=http://ip-checker.local:8080

# REDIS_HOST=localhost
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
CACHE_TTL=3600

# MinIO
MINIO_ENDPOINT=minio:9000
# MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=ip-backup
BACKUP_INTERVAL=300
```

Start the stack:

```bash
docker compose up --build
```

The service will be available at:

```bash
curl http://127.0.0.1:5000/health
```

---

## Running tests

Unit and integration tests are written using `pytest`.

### Run all tests

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-mock

pytest tests -v
```

- **Unit tests** are in `tests/unit`, and test the Flask app directly.
- **Integration tests** are in `tests/integration` and require the service to be running and accessible.

To run only unit tests:

```bash
pytest tests/unit -v
```

To run integration tests, first start the app (locally, via Docker, or in Kubernetes), then:

**For local/Docker (default):**

```bash
# Uses BASE_URL from .env (defaults to http://127.0.0.1:5000)
pytest tests/integration -v
```

**For Kubernetes/kind via Ingress:**

```bash
BASE_URL="http://ip-checker.local:8080" pytest tests/integration -v
```
---

## Kubernetes with kind

This repo includes manifests under `k8s/` and a kind cluster config `kind-config.yml`.

### 1. Create the kind cluster

```bash
kind create cluster --config kind-config.yml
```

This sets up a cluster named `ip-checker-cluster` and maps:

- **host port 8080 → cluster port 80**
- **host port 8443 → cluster port 443**

### 2. Build and load the image into kind

```bash
docker build -t ip-checker-image:latest .
kind load docker-image ip-checker-image:latest --name ip-checker-cluster
```

### 3. Apply namespace, Deployment, Service, and Ingress

```bash
kubectl apply -f k8s/namespace.yml
kubectl apply -f k8s/redis
kubectl apply -f k8s/ip-checker
kubectl apply -f k8s/minio
```

This will create:

- Namespace: `ip-checker`
- Deployment: `ip-checker`
- Service: `ip-checker` (ClusterIP, port 80 → targetPort 5000)
- Ingress: `ip-checker` with host `ip-checker.local`

### 4. Install an Ingress controller (required)

kind does **not** include an Ingress controller by default.  
Install `ingress-nginx` with:

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

kubectl wait --namespace ingress-nginx \
  --for=condition=Ready pods --all --timeout=180s
```

```bash
kubectl apply -f k8s/ingress.yml
```

### 5. Update `/etc/hosts` on your machine

Add the following line so the `ip-checker.local` host resolves to localhost:

```text
127.0.0.1 ip-checker.local
127.0.0.1 minio.ip-checker.local
127.0.0.1 grafana.ip-checker.local
```

The `grafana.ip-checker.local` line is only needed if you install the optional monitoring Helm chart (see below).

### 6. Accessing the service via Ingress

With everything running, you can call:

```bash
curl http://ip-checker.local:8080/health
curl http://ip-checker.local:8080/
curl http://ip-checker.local:8080/ip/8.8.8.8
curl -X POST http://ip-checker.local:8080/store
curl http://ip-checker.local:8080/metrics
```

### 7. Monitoring stack (Helm, optional)

The chart at `helm/monitoring-stack` deploys **Grafana** (with an Ingress), **Prometheus**, **Loki**, and **Promtail** (DaemonSet). Prometheus is configured to scrape the ip-checker Service at `ip-checker.ip-checker.svc.cluster.local:80` (see `global.ipCheckerMetricsTargets` in `helm/monitoring-stack/values.yaml`).

Prerequisites: Ingress controller from step 4, namespace `ip-checker` with the ip-checker app running so scraping and DNS names resolve.

From the **repository root**:

```bash
helm install monitoring ./helm/monitoring-stack --namespace ip-checker
```

After pods are ready, open Grafana at `http://grafana.ip-checker.local:8080/` (same kind port mapping as other Ingress hosts). Default credentials are in `values.yaml` (`grafana.adminUser` / `grafana.adminPassword`, typically `admin` / `admin`).

Use `kubectl -n ip-checker get pods` to verify `monitoring-prometheus`, `monitoring-grafana`, `monitoring-loki`, and `monitoring-promtail` (release name may differ if you choose another Helm release name). To tear everything down, see **[Uninstall (optional)](#uninstall-optional)**.

### 8. Delete the cluster

```
kind delete cluster --name ip-checker-cluster
```

---

## Run via helm

### 1. Create cluster
```
kind create cluster --config kind-config.yml
```

### 2. Build and load the image into kind
```
docker build -t ip-checker-image:latest .
kind load docker-image ip-checker-image:latest --name ip-checker-cluster
```

### 3. Install an Ingress controller
```
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl wait --namespace ingress-nginx --for=condition=Ready pods --all --timeout=180s
```

### 4. Add Helm repositories
```
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add minio https://charts.min.io/ 
helm repo update
```

### 5. Build Helm dependencies
```
cd helm/ip-checker-chart
helm dependency build .
```

### 6. Deploy application
```
helm install ip-checker ./helm/ip-checker-chart --namespace ip-checker --create-namespace 
```

### 7. Update /etc/hosts on your machine
```
127.0.0.1 ip-checker.local
127.0.0.1 minio.ip-checker.local
127.0.0.1 minio-console.ip-checker.local
127.0.0.1 grafana.ip-checker.local
```

The `grafana.ip-checker.local` line is only needed if you install the monitoring chart (step 9).

### 8. Accessing the service via Ingress

With everything running, you can call:

```bash
curl http://ip-checker.local:8080/health
curl http://ip-checker.local:8080/
curl http://ip-checker.local:8080/ip/8.8.8.8
curl -X POST http://ip-checker.local:8080/store
curl http://ip-checker.local:8080/metrics
```

### 9. Monitoring stack (Helm, optional)

With the `ip-checker` release already installed in namespace `ip-checker`, run one of the following from the **repository root**:

```bash
helm install monitoring ./helm/monitoring-stack --namespace ip-checker
```

If you are still in `helm/ip-checker-chart` after step 5, use:

```bash
helm install monitoring ../monitoring-stack --namespace ip-checker
```

This deploys Grafana (Ingress host `grafana.ip-checker.local`, port **8080** on the host via kind), Prometheus, Loki, and Promtail. Ensure `127.0.0.1 grafana.ip-checker.local` is in `/etc/hosts` (step 7). Scrape targets and credentials are documented in `helm/monitoring-stack/values.yaml` and in the post-install notes (`helm get notes monitoring -n ip-checker`). To remove releases, see **[Uninstall (optional)](#uninstall-optional)**.

---

## Uninstall (optional)

Use this when you want to remove workloads from the cluster but keep kind running, or before reinstalling from scratch.

### After **Kubernetes with kind** (manifests with `kubectl`)

If you installed the monitoring chart (see **Monitoring stack** under [Kubernetes with kind](#kubernetes-with-kind)), remove that Helm release first (skip this if you did not install monitoring):

```bash
helm uninstall monitoring --namespace ip-checker
```

Then delete the project namespace (app, Redis, MinIO, Ingress rules from `k8s/ingress.yml`, and Helm metadata stored in that namespace):

```bash
kubectl delete namespace ip-checker
```

The `ingress-nginx` controller stays until you delete the kind cluster (see **Delete the cluster** under [Kubernetes with kind](#kubernetes-with-kind)) or remove that controller separately.

### After **Run via helm**

If you installed monitoring, uninstall it first (skip the first line if you did not install monitoring), then the application chart:

```bash
helm uninstall monitoring --namespace ip-checker
helm uninstall ip-checker --namespace ip-checker
```

To drop the namespace and any leftover objects (for example stuck `Pending` PVCs from subcharts):

```bash
kubectl delete namespace ip-checker
```

---

## CI and Docker image publishing

GitHub Actions workflows under `.github/workflows/` provide:

- **`ci.yml`**: installs dependencies, runs lint (`pylint` and `hadolint`), and executes tests on each push/PR to `main`.
- **`docker-publish.yml`**: builds and pushes a Docker image to **GitHub Container Registry (GHCR)** as `ghcr.io/<owner>/<repo>:latest` after CI completes.

Ensure repository secrets are configured (for example `FLASK_PORT`, `IP_API_URL`, `LOG_LEVEL` if you use them in CI).

---

## Endpoints summary

- **`get /health`** → `{"status": "up"}`
- **`get /`** → usage instructions string.
- **`get /ip/<ip>`** → json with `ip`, `country`, `countrycode`, `city`, `isp`.
- **`post /store`** → triggers immediate backup of redis cache to minio (no parameters).
- **`get /metrics`** → Prometheus metrics in text format for monitoring (no parameters).
