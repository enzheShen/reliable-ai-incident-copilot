FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN pip install "fastapi==0.115.11" "uvicorn==0.34.0"
COPY app.py ./app.py
RUN addgroup --system app && adduser --system --ingroup app app && chown -R app:app /app
USER app
EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
