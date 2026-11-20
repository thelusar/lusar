FROM postgres:18-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv age ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY ops/backups/requirements.txt /app/requirements.txt
RUN python3 -m venv /opt/backup && /opt/backup/bin/pip install --no-cache-dir -r /app/requirements.txt
COPY site/backup_database.py /app/site/backup_database.py
COPY ops/backups/runner.py /app/ops/backups/runner.py
ENV PATH="/opt/backup/bin:$PATH" PYTHONPATH="/app/site"
USER postgres
CMD ["python", "/app/ops/backups/runner.py", "--mode", "scheduled"]
