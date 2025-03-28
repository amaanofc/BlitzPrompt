#!/usr/bin/env bash
# exit on error but continue for database operations
set -o errexit

# Print debug info
echo "Current directory: $(pwd)"
echo "Listing files: $(ls -la)"
echo "DATABASE_URL exists: $([ -n "$DATABASE_URL" ] && echo "Yes" || echo "No")"
echo "RENDER: ${RENDER:-Not set}"

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Test database connection
if [ -n "$DATABASE_URL" ]; then
  echo "PostgreSQL DATABASE_URL found. Testing connection..."
  
  # Ensure we're working with postgres:// for consistency
  DB_URL="$DATABASE_URL"
  if [[ $DB_URL == postgresql://* ]]; then
    echo "Converting postgresql:// to postgres:// for compatibility"
    DB_URL="${DB_URL/postgresql:\/\//postgres:\/\/}"
  fi
  
  # Extract connection details for testing
  if [[ $DB_URL == postgres://* ]]; then
    DB_USER=$(echo $DB_URL | sed -E 's/postgres:\/\/([^:]+):.*/\1/')
    DB_PASSWORD=$(echo $DB_URL | sed -E 's/postgres:\/\/[^:]+:([^@]+)@.*/\1/')
    DB_HOST=$(echo $DB_URL | sed -E 's/postgres:\/\/[^:]+:[^@]+@([^:\/]+)([:]([0-9]+))?\/?.*/\1/')
    DB_PORT=$(echo $DB_URL | sed -E 's/postgres:\/\/[^:]+:[^@]+@([^:\/]+)([:]([0-9]+))?\/?.*/\3/')
    DB_NAME=$(echo $DB_URL | sed -E 's/postgres:\/\/[^:]+:[^@]+@[^\/]+\/([^?]+).*/\1/')
    
    DB_PORT=${DB_PORT:-5432}
    
    echo "Extracted connection details:"
    echo "  Host: $DB_HOST"
    echo "  Port: $DB_PORT"
    echo "  Database: $DB_NAME"
    echo "  User: $DB_USER"
    
    # Try to check if PostgreSQL is installed
    if command -v psql &> /dev/null; then
      echo "PostgreSQL client found. Attempting connection test..."
      export PGPASSWORD="$DB_PASSWORD"
      if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\l" &>/dev/null; then
        echo "PostgreSQL connection successful."
      else
        echo "PostgreSQL connection failed. Check your DATABASE_URL."
      fi
    else
      echo "PostgreSQL client not found. Installing psql..."
      apt-get update && apt-get install -y postgresql-client || {
        echo "Failed to install PostgreSQL client. Continuing without connection test."
      }
      
      if command -v psql &> /dev/null; then
        echo "Attempting connection test with installed client..."
        export PGPASSWORD="$DB_PASSWORD"
        if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\l" &>/dev/null; then
          echo "PostgreSQL connection successful."
        else
          echo "PostgreSQL connection failed. Check your DATABASE_URL."
        fi
      fi
    fi
  else
    echo "DATABASE_URL doesn't match expected postgres:// or postgresql:// format."
  fi

  # Try applying migrations to PostgreSQL
  echo "Applying migrations to PostgreSQL database..."
  python manage.py makemigrations core
  python manage.py migrate || {
    echo "PostgreSQL migration failed, this may indicate a database connection issue."
    exit 1
  }
else
  echo "No DATABASE_URL found, using SQLite database"
  # Apply migrations to SQLite
  python manage.py makemigrations core
  python manage.py migrate
fi

# Load initial data with error handling
python manage.py loaddata core/fixtures/initial_data.json || echo "Could not load fixtures, continuing anyway"

# Create superuser if it doesn't exist
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@example.com', 'admin') if not User.objects.filter(username='admin').exists() else None" || echo "Could not create superuser, continuing anyway" 