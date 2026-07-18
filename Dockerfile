FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ ./src/

ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "cleaner.main"]
