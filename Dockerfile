FROM python:3.12-slim as builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

FROM python:3.12-slim as final

WORKDIR /app

# Copy installed dependencies
COPY --from=builder /install /usr/local

# Copy application source code
COPY src/ ./src/

EXPOSE 5000

CMD ["python", "src/app.py"]
