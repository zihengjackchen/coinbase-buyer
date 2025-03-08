# Use Python 3.12 as the base image
FROM python:3.12-slim

# Install cron and necessary utilities
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy project files
COPY main.py config.py requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy cron job file
COPY crypto-cron /etc/cron.d/crypto-cron

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/crypto-cron

# Apply the cron job
RUN crontab /etc/cron.d/crypto-cron

# Create the log file to be able to run tail
RUN touch /var/log/cron.log

# Start cron, echo API key, and run in foreground
CMD ["/bin/bash", "-c", "printenv > /etc/environment && cron && tail -f /var/log/cron.log"]
