FROM python:3.12-slim

# Install cron
RUN apt-get update && apt-get install -y cron

# Set the working directory
WORKDIR /app

# Set environment variables
ENV DBHOST=localhost
ENV DBPORT=3306
ENV DBUSER=root
ENV DBPASS=root

ENV DELAY=2
ENV MAXID=12000
ENV MAXERRORNUMBER=5
ENV LASTRUNCHECK=48
ENV PROXY=None
ENV NOTIFICATIONURL=None

# Install Python dependencies
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Copy all application files
COPY db.py db.py
COPY main.py main.py

# Add the cron job
#RUN echo "6 20 * * 4 /usr/local/bin/python /app/main.py >> /var/log/trendshift.log 2>&1" > /etc/cron.d/trendshift-cron \
#    && chmod 0644 /etc/cron.d/trendshift-cron \
#    && crontab /etc/cron.d/trendshift-cron

RUN echo "CRON: 0 1 * * 6 DBHOST=$DBHOST DBPORT=$DBPORT DBUSER=$DBUSER DBPASS=$DBPASS DELAY=$DELAY MAXID=$MAXID MAXERRORNUMBER=$MAXERRORNUMBER LASTRUNCHECK=$LASTRUNCHECK PROXY=$PROXY NOTIFICATIONURL=$NOTIFICATIONURL /usr/local/bin/python /app/main.py >> /var/log/trendshift.log 2>&1" > /etc/cron.d/trendshift-cron \
    && chmod 0644 /etc/cron.d/trendshift-cron \
    && crontab /etc/cron.d/trendshift-cron

# Create the log file to be able to run tail
RUN touch /var/log/trendshift.log

# Start cron and keep the container running
CMD ["sh", "-c", "cron && tail -f /var/log/trendshift.log"]
