FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=5000
ENV DB_HOST=127.0.0.1
ENV DB_PORT=3050
ENV DB_NAME=/app/WEBCAR.FDB
ENV DB_USER=sysdba
ENV DB_PASSWORD=masterkey

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libfbclient2 \
    firebird3.0-server \
    firebird3.0-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown firebird:firebird /app/WEBCAR.FDB || true \
    && chmod 664 /app/WEBCAR.FDB || true

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5000

ENTRYPOINT ["/entrypoint.sh"]
