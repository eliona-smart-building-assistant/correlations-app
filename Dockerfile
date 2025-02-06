FROM eliona/base-python:latest-3.11-alpine-eliona

WORKDIR /app

# Installiere alle notwendigen Pakete
RUN apk update && apk add --no-cache \
    git \
    postgresql-dev \
    gcc \
    g++ \
    musl-dev \
    python3-dev \
    libffi-dev \
    build-base

# Kopiere die Anforderungen und installiere sie
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 3000

CMD ["python", "main.py"]
