# Build Stage
FROM node:18-slim AS build-stage
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Final Stage
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Copy built frontend from build stage
COPY --from=build-stage /app/frontend/dist /app/frontend/dist
EXPOSE 10000
CMD ["gunicorn", "-b", "0.0.0.0:10000", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "backend_api:app"]
