FROM python:3.11-slim

WORKDIR /app

# Make Python logs appear immediately in docker logs
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt

# Copy application code
COPY . .

# Run the ingestion script
CMD ["python", "-u", "ingest_wikipedia.py"]
