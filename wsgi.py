"""
WSGI config for BlitzPrompt project - root level config to guide Render deployment.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BlitzPrompt.settings')

application = get_wsgi_application() 