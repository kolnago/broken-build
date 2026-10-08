# Adapt the registry/mirror lines to your environment (e.g. Quay + Nexus).
ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE}
ARG PIP_INDEX_URL
ENV PIP_INDEX_URL=${PIP_INDEX_URL} PYTHONUNBUFFERED=1 \
    GOOGLE_GENAI_USE_ENTERPRISE=TRUE \
    ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false \
    ADK_TELEMETRY_IGNORE_RUN_CONFIG=1
WORKDIR /srv
COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir -r requirements.txt -c constraints.txt
COPY main.py ./
COPY agents ./agents
USER 1000
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
