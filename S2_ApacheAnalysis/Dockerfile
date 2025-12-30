# Use Debian 12 (Bookworm) for Java 17 support
FROM python:3.10-slim-bookworm

# Install Java 17
RUN apt-get update && \
    apt-get install -y openjdk-17-jre-headless && \
    apt-get clean;

# Install specific stable version of PySpark
RUN pip install pyspark==3.4.1

# Set environment variables
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
WORKDIR /app

CMD ["python", "spark_analysis.py"]