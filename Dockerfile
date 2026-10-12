FROM python:3.12-slim AS backend
WORKDIR /app
COPY pyproject.toml README.md ./
COPY backend backend
COPY target_app target_app
COPY configs configs
COPY datasets datasets
RUN pip install --no-cache-dir ".[postgres]"
CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
