FROM eliona/base-python:latest-3.11-alpine-eliona

WORKDIR /app

# Install necessary system dependencies
RUN apk update && apk add --no-cache \
    git \
    postgresql-dev \
    gcc \
    g++ \
    musl-dev \
    python3-dev \
    libffi-dev \
    build-base \
    cairo \
    pango \
    gdk-pixbuf \
    jpeg-dev \
    libpng-dev \
    libxml2 \
    libxslt \
    freetype \
    ttf-dejavu \
    ttf-droid \
    ttf-freefont \
    ttf-liberation

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application
COPY . .

# Expose the API port
EXPOSE 3000

# Start the application
CMD ["python", "main.py"]
