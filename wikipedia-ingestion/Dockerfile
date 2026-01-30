FROM python:3.11-slim

WORKDIR /app

# Make Python logs appear immediately in docker logs
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install dependencies
COPY wikipedia-ingestion/requirements.txt .
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt

# Copy application code (from root context)
COPY wikipedia-ingestion ./wikipedia-ingestion
COPY timeline_common ./timeline_common

# Run the ingestion script
CMD ["python", "-u", "wikipedia-ingestion/ingest_wikipedia.py"]
