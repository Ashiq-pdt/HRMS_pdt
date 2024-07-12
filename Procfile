web: gunicorn --workers "project:create_app()" --timeout 0
worker: celery -A project worker -Ofair -P gevent --loglevel=INFO