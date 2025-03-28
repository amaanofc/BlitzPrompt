"""Bridge file to help Render find the correct WSGI application."""

import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BlitzPrompt.settings')

# Import and configure Django
import django
django.setup()

# This is what Render looks for with 'gunicorn app:app'
from django.core.wsgi import get_wsgi_application
app = get_wsgi_application()

# Print debug info
print("Current directory:", os.path.dirname(os.path.abspath(__file__)))
print("Python path:", sys.path)
print("Environment:", os.environ.get('DJANGO_SETTINGS_MODULE'))
print("Database URL:", os.environ.get('DATABASE_URL', 'Not set')) 