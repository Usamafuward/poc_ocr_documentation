FROM python:3.11-slim

WORKDIR /app

# Copy the shared requirements file first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the backend application
COPY ./ocr_back /app/ocr_back

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Create directory for uploaded files
RUN mkdir -p /app/uploads

# Expose the port the app runs on
EXPOSE 8001

# Command to run the application
CMD ["uvicorn", "ocr_back.main:app", "--host", "0.0.0.0", "--port", "8001"]