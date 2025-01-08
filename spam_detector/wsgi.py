"""
WSGI config for spam_detector project.
"""

import os
from django.core.wsgi import get_wsgi_application
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spam_detector.settings')

application = get_wsgi_application() 