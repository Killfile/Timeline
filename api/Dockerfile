FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY api/requirements.txt .
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt

# Copy API code (will be at /app/api/)
COPY api/ ./api/

# Copy shared utilities
COPY timeline_common/ ./timeline_common/

# Copy shared schema (needed for validation)
COPY wikipedia-ingestion/import_schema.json ./wikipedia-ingestion/

# Expose API port
EXPOSE 8000

# Run the API server from /app so python can find the api module
CMD ["sh", "-c", "cd /app && uvicorn api.api:app --host 0.0.0.0 --port 8000 --reload"]
