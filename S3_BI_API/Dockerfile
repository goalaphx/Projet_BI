# Use lightweight Python
FROM python:3.9-slim

WORKDIR /app

# Install Flask, Mongo driver, and CORS support
RUN pip install flask pymongo flask-cors

# Copy the app code
COPY app.py .

# Run the API
CMD ["python", "app.py"]