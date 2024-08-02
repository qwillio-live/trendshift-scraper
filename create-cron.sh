#!/bin/sh

# Delete the existing cron job if it exists
rm -f /etc/cron.d/trendshift-cron

# Generate the cron job
echo "$CRONTIME DBHOST=$DBHOST DBPORT=$DBPORT DBUSER=$DBUSER DBPASS=$DBPASS DELAY=$DELAY MAXID=$MAXID MAXERRORNUMBER=$MAXERRORNUMBER LASTRUNCHECK=$LASTRUNCHECK PROXY=$PROXY NOTIFICATIONURL=$NOTIFICATIONURL /usr/local/bin/python /app/trendshift.py >> /var/log/trendshift.log 2>&1" > /etc/cron.d/trendshift-cron

# Set permissions
chmod 0644 /etc/cron.d/trendshift-cron

# Apply the cron job
crontab /etc/cron.d/trendshift-cron