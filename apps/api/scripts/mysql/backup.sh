#!/bin/sh -e

echo "Backup process started."

# It's often a good practice to source environment variables from a secure location
# Uncomment the line below if you store your environment variables in a separate file
# . /path/to/your/envfile

# Ensure that MYSQL_USER and MYSQL_PASSWORD are set in your environment variables
export MYSQL_USER="${MYSQL_USER}"
export MYSQL_PASSWORD="${MYSQL_PASSWORD}"  # Be cautious with password handling

# Save the current date in YYYY-MM-DD-HHMMSS format to a variable
current_datetime=$(date +%Y-%m-%d-%H%M%S)

backup_directory="/backups"
backup_filename="${backup_directory}/backup-${current_datetime}.sql.gz"

# Run mysqldump to export the database and gzip the output
mysqldump --user="$MYSQL_USER" --password="$MYSQL_PASSWORD" app | gzip > "$backup_filename"

echo "Backup has been created and saved to ${backup_filename}"
