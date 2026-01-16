FROM python:3.12-slim as builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

COPY . .

FROM python:3.12-slim as final

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY --from=builder /app .

EXPOSE 5000

CMD ["python", "app.py"]
