#!/usr/bin/env bash
# exit on error
set -o errexit

# Print debug info
echo "Current directory: $(pwd)"
echo "Listing files: $(ls -la)"

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Apply migrations 
python manage.py makemigrations core
python manage.py migrate

# Load initial data
python manage.py loaddata core/fixtures/initial_data.json

# Create superuser if it doesn't exist
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@example.com', 'admin') if not User.objects.filter(username='admin').exists() else None" 