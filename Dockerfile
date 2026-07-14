FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir .

EXPOSE 7860
CMD ["sh", "-c", "gunicorn --workers 2 --threads 4 --timeout 150 --bind 0.0.0.0:${PORT} crowdcollect.app:app"]
