#!/usr/bin/env bash
# start.sh - Custom startup script for Render

# Print environment info for debugging
echo "Starting application in $(pwd)"
echo "Environment variables:"
echo "DATABASE_URL exists: $([ -n "$DATABASE_URL" ] && echo "Yes" || echo "No")"
echo "RENDER: ${RENDER:-Not set}"
echo "DJANGO_SETTINGS_MODULE: ${DJANGO_SETTINGS_MODULE:-BlitzPrompt.settings}"

# Check database connection
if [ -n "$DATABASE_URL" ]; then
  echo "Checking PostgreSQL connection..."
  
  # Ensure we're working with postgres:// for consistency
  DB_URL="$DATABASE_URL"
  if [[ $DB_URL == postgresql://* ]]; then
    echo "Converting postgresql:// to postgres:// for compatibility"
    DB_URL="${DB_URL/postgresql:\/\//postgres:\/\/}"
  fi
  
  # Extract host and port from DATABASE_URL
  if [[ $DB_URL == postgres://* ]]; then
    DB_HOST=$(echo $DB_URL | sed -E 's/postgres:\/\/[^:]+:[^@]+@([^:\/]+)([:]([0-9]+))?\/?.*/\1/')
    DB_PORT=$(echo $DB_URL | sed -E 's/postgres:\/\/[^:]+:[^@]+@([^:\/]+)([:]([0-9]+))?\/?.*/\3/')
    DB_PORT=${DB_PORT:-5432}
    
    echo "Extracted host: $DB_HOST, port: $DB_PORT"
    
    # Check if PostgreSQL is reachable
    if command -v nc &> /dev/null; then
      if nc -z $DB_HOST $DB_PORT -w 5; then
        echo "PostgreSQL is reachable on $DB_HOST:$DB_PORT"
      else
        echo "WARNING: PostgreSQL is NOT reachable on $DB_HOST:$DB_PORT"
      fi
    else
      echo "nc command not found, skipping connection check"
    fi
  else
    echo "DATABASE_URL doesn't match expected postgres:// format, skipping connection check"
  fi
  
  # Try a Django database check
  echo "Running Django database check..."
  python manage.py check --database default || {
    echo "Django database check failed."
    
    # Try database migration to see if it helps
    echo "Attempting database migration..."
    python manage.py migrate --noinput || {
      echo "Database migration failed. The database might not be properly configured."
    }
  }
else
  echo "No DATABASE_URL found, ensuring SQLite database is ready"
  if [ -f db.sqlite3 ]; then
    echo "Using existing SQLite database"
  else
    echo "Creating empty SQLite database"
    touch db.sqlite3
  fi
  
  # Run migrations if needed
  python manage.py migrate
fi

# Run the Django application with the correct WSGI path
echo "Starting Gunicorn with wsgi:application"
exec gunicorn wsgi:application 