"""
WSGI config for spam_detector project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spam_detector.settings')

application = get_wsgi_application() 