FROM python:3.12-slim AS backend

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY migrations ./migrations
COPY wsgi.py .
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

RUN useradd --create-home appuser
USER appuser

ENV FLASK_APP=wsgi.py
EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
