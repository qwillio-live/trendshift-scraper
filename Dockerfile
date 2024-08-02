FROM python:3.12-slim

# Install cron
RUN apt-get update && apt-get install -y cron

# Set the working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Copy application files
COPY db.py db.py
COPY main.py main.py
COPY trendshift.py trendshift.py

# Copy the script to create the cron job
COPY create-cron.sh /create-cron.sh
RUN chmod +x /create-cron.sh

# Create the log file to be able to run tail
RUN touch /var/log/trendshift.log

#expose the port such that can be accessed from outside in windows
EXPOSE 80

# Start cron, create the cron job, and run fastapi on exposed port
#CMD ["sh", "-c", "/create-cron.sh && cron && tail -f /var/log/trendshift.log"]
CMD ["sh", "-c", "/create-cron.sh && cron && fastapi run /app/main.py --port 80"]
