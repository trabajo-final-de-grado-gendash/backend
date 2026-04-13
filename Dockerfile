FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/api/src:/app/decision_agent/src:/app/vanna_agent/src:/app/viz_agent/src

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire workspace
COPY . /app

# Install local sub-packages
RUN if [ -f ./api/pyproject.toml ]; then pip install --no-cache-dir -e ./api; fi
RUN if [ -f ./decision_agent/pyproject.toml ]; then pip install --no-cache-dir -e ./decision_agent; fi
RUN if [ -f ./vanna_agent/pyproject.toml ]; then pip install --no-cache-dir -e ./vanna_agent; fi
RUN if [ -f ./viz_agent/pyproject.toml ]; then pip install --no-cache-dir -e ./viz_agent; fi

EXPOSE 8000

# Prepare entrypoint
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
