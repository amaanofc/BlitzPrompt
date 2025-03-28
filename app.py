"""Bridge file for Render deployment that handles migrations."""

import os
import sys
import django

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BlitzPrompt.settings')

# Initialize Django
django.setup()

# Run migrations to ensure the database is set up correctly
from django.core.management import call_command

try:
    print("Running makemigrations...")
    call_command('makemigrations', 'core')
except Exception as e:
    print(f"Error during makemigrations: {e}")

try:
    print("Running migrate...")
    call_command('migrate')
    print("Migration completed successfully!")
except Exception as e:
    print(f"Error during migration: {e}")

# Load fixtures if the core_prompt table is empty
from django.db import connection

try:
    with connection.cursor() as cursor:
        # Check if the core_prompt table exists and is empty
        cursor.execute("SELECT COUNT(*) FROM core_prompt")
        count = cursor.fetchone()[0]
        if count == 0:
            print("Loading initial fixtures...")
            try:
                call_command('loaddata', 'core/fixtures/initial_data.json')
                print("Fixtures loaded successfully!")
            except Exception as e:
                print(f"Error loading fixtures: {e}")
except Exception as e:
    print(f"Error checking for core_prompt table: {e}")

# Create a superuser if none exists
from django.contrib.auth import get_user_model
User = get_user_model()

if not User.objects.filter(username='admin').exists():
    print("Creating admin superuser...")
    try:
        User.objects.create_superuser('admin', 'admin@example.com', 'admin')
        print("Admin user created successfully!")
    except Exception as e:
        print(f"Error creating admin user: {e}")

# This is what Render looks for with 'gunicorn app:app'
from django.core.wsgi import get_wsgi_application
app = get_wsgi_application()

# Print debug info
print("Current directory:", os.path.dirname(os.path.abspath(__file__)))
print("Python path:", sys.path)
print("Environment:", os.environ.get('DJANGO_SETTINGS_MODULE'))
print("Database URL:", os.environ.get('DATABASE_URL', 'Not set')) 