FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY services/v3_api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services /app/services
RUN mkdir -p /app/data

EXPOSE 8001
CMD ["uvicorn", "services.v3_api.main:app", "--host", "0.0.0.0", "--port", "8001"]
