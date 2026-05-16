# Stage 1: Build React/Vite frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python application image
FROM python:3.12-slim

RUN useradd -m -u 1000 argus

WORKDIR /app

# Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application source
COPY src/ ./src/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Data and log directories
RUN mkdir -p data logs && chown -R argus:argus /app

USER argus

EXPOSE 8000 9090 9100

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
