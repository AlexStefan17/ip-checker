## ip-checker

A small Flask-based API that looks up IP address information using `ip-api.com`.

It exposes:

- `GET /health` – simple health check.
- `GET /` – usage instructions.
- `GET /ip/<ip>` – returns basic geo/IP info for the given IP.

---

## Configuration

The app reads configuration from environment variables (or a `.env` file in development via `python-dotenv`):

- **`FLASK_PORT`** – port the Flask app listens on (e.g. `5000`).
- **`IP_API_URL`** – URL template for the external IP API, e.g. `http://ip-api.com/json/{}`.
- **`LOG_LEVEL`** – logging level, e.g. `INFO`, `DEBUG`.
- **`BASE_URL`** – base URL for integration tests (defaults to `http://127.0.0.1:${FLASK_PORT}` if not set).

Example `.env`:

```bash
FLASK_PORT=5000
IP_API_URL=http://ip-api.com/json/{}
LOG_LEVEL=INFO
BASE_URL=http://127.0.0.1:5000
```

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
```

Test it:

```bash
curl http://127.0.0.1:5000/health
curl http://127.0.0.1:5000/
curl http://127.0.0.1:5000/ip/8.8.8.8
```

---

## Running with Docker / docker-compose

### Build and run with Docker directly

```bash
docker build -t ip-checker-image:latest .

docker run --rm \
  -p 5000:5000 \
  -e FLASK_PORT=5000 \
  -e IP_API_URL="http://ip-api.com/json/{}" \
  -e LOG_LEVEL=INFO \
  ip-checker-image:latest
```

Then:

```bash
curl http://127.0.0.1:5000/health
```

### Using docker-compose

`docker-compose.yml` expects a `.env` file with at least `FLASK_PORT` defined:

```bash
FLASK_PORT=5000
IP_API_URL=http://ip-api.com/json/{}
LOG_LEVEL=INFO
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

**For Kubernetes/kind via port-forward:**

```bash
kubectl -n ip-checker port-forward svc/ip-checker 8000:80
BASE_URL="http://127.0.0.1:8000" pytest tests/integration -v
```

The integration tests read `BASE_URL` from your `.env` file, or you can override it via environment variable when running pytest.

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
kubectl apply -f k8s/
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

### 5. Update `/etc/hosts` on your machine

Add the following line so the `ip-checker.local` host resolves to localhost:

```text
127.0.0.1 ip-checker.local
```

### 6. Accessing the service via Ingress

With everything running, you can call:

```bash
curl http://ip-checker.local:8080/health
curl http://ip-checker.local:8080/
curl http://ip-checker.local:8080/ip/8.8.8.8
```

---

## CI and Docker image publishing

GitHub Actions workflows under `.github/workflows/` provide:

- **`ci.yml`**: installs dependencies, runs lint (`pylint` and `hadolint`), and executes tests on each push/PR to `main`.
- **`docker-publish.yml`**: builds and pushes a Docker image to **GitHub Container Registry (GHCR)** as `ghcr.io/<owner>/<repo>:latest` after CI completes.

Ensure repository secrets are configured (for example `FLASK_PORT`, `IP_API_URL`, `LOG_LEVEL` if you use them in CI).

---

## Endpoints summary

- **`GET /health`** → `{"status": "UP"}`
- **`GET /`** → usage instructions string.
- **`GET /ip/<ip>`** → JSON with `ip`, `country`, `countryCode`, `city`, `isp`.

# ip-checker
ip-checker app

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py

curl http://127.0.0.1:5000/ip/8.8.8.8
curl http://127.0.0.1:5000/health
