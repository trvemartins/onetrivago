FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port (Fly.io uses 8080)
EXPOSE 8080

# Run with gunicorn
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:8080"]
