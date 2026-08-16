FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py db.py pdf.py ./
COPY templates ./templates
COPY static ./static
COPY config ./config

ENV DATABASE_PATH=/data/checkprint.db
ENV CHECK_LAYOUT_PATH=/app/config/check_layout.yml

EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
