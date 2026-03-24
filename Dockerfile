FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS final

# Create new non-root user and set /app permisions
RUN useradd --uid 1000 --no-create-home appuser \
    && mkdir /app \
    && chown appuser:appuser /app

# Copy installed dependencies
COPY --from=builder /install /usr/local

# Copy application source code with correct ownership
COPY --chown=appuser:appuser src/ ./src/

# Switch to non-root user
USER appuser

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["python", "src/app.py"]
