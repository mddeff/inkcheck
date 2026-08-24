FROM python:3.12-slim

# gosu lets the entrypoint fix bind-mount ownership as root, then drop to a
# non-root user for the actual app process.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --create-home --uid 1000 appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py db.py pdf.py ./
COPY templates ./templates
COPY static ./static
COPY config ./config
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENV DATABASE_PATH=/data/inkcheck.db
ENV CHECK_LAYOUT_PATH=/app/config/check_layout.yml

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/', timeout=2).status == 200 else 1)"

ENTRYPOINT ["entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
