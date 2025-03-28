"""Bridge file to help Render find the correct WSGI application."""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BlitzPrompt.settings')

# This is what Render looks for with 'gunicorn app:app'
app = get_wsgi_application() 