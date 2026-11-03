#!/bin/sh -e

# The directory where backups are stored
BACKUP_DIRECTORY="/backups"

# Check if a file name was provided as a parameter
if [ $# -eq 0 ]; then
  echo "No file name provided. Please provide a file name to check."
  exit 1
fi

# The file name is taken from the first argument provided to the script
file_name="$1"

# Full path to the file
full_file_path="${BACKUP_DIRECTORY}/${file_name}"

# Check if the file exists
if [ -f "$full_file_path" ]; then
  echo "File ${file_name} exists."
else
  echo "File ${file_name} does not exist."
  exit 1
fi

# Ensure that MYSQL_USER and MYSQL_PASSWORD are set
export MYSQL_USER="${MYSQL_USER}"
export MYSQL_PASSWORD="${MYSQL_PASSWORD}"  # Caution: Ensure this is secure
export MYSQL_DB="${MYSQL_DB}"  # Name of the database to drop and recreate

echo "Dropping the database..."
mysql --user="$MYSQL_USER" --password="$MYSQL_PASSWORD" -e "DROP DATABASE IF EXISTS $MYSQL_DB;"

echo "Creating a new database..."
mysql --user="$MYSQL_USER" --password="$MYSQL_PASSWORD" -e "CREATE DATABASE $MYSQL_DB;"

echo "Applying the backup
