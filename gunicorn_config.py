"""Gunicorn configuration file."""

# Server socket
bind = '0.0.0.0:8000'
backlog = 2048

# Worker processes
workers = 3
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = 'logs/gunicorn.access.log'
errorlog = 'logs/gunicorn.error.log'
loglevel = 'info'

# Process naming
proc_name = 'spam_detector'

# Server mechanics
daemon = False
pidfile = 'logs/gunicorn.pid'
user = None
group = None
umask = 0
tmp_upload_dir = None

# SSL
keyfile = None
certfile = None 