FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    FLASK_ENV=production \
    FLASK_DEBUG=False \
    PORT=5000

WORKDIR /app

RUN addgroup --system parent && adduser --system --ingroup parent parent

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY migrations ./migrations
COPY run.py wsgi.py Procfile ./

USER parent

EXPOSE 5000

CMD ["sh", "-c", "flask --app run.py db upgrade && gunicorn --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY:-2} --timeout ${GUNICORN_TIMEOUT:-120} wsgi:app"]
