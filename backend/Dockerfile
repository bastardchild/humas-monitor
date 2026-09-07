FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY migrations ./migrations

# Litestream for S3-compatible replication (optional, runs only if LITESTREAM_REPLICA_URL set)
ADD https://github.com/benbjohnson/litestream/releases/download/v0.3.13/litestream-v0.3.13-linux-amd64.tar.gz /tmp/litestream.tar.gz
RUN tar -xzf /tmp/litestream.tar.gz -C /usr/local/bin litestream && rm /tmp/litestream.tar.gz && chmod +x /usr/local/bin/litestream
COPY litestream.yml /etc/litestream.yml

EXPOSE 8000

CMD ["sh","-c","if [ -n \"$LITESTREAM_REPLICA_URL\" ]; then litestream replicate --exec \"uvicorn app.main:app --host 0.0.0.0 --port 8000\"; else uvicorn app.main:app --host 0.0.0.0 --port 8000; fi"]
