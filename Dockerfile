FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=5000 \
    HOME=/home/app

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app --home /home/app app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py todolib.py ./
COPY templates ./templates
COPY static ./static

RUN mkdir -p /app/data && chown -R app:app /app

USER app

EXPOSE 5000
VOLUME ["/app/data"]

CMD ["sh", "-c", "gunicorn -w ${GUNICORN_WORKERS:-2} -b 0.0.0.0:${PORT:-5000} app:app"]
