release: ./manage.py migrate
web: gunicorn --bind 0.0.0.0:$PORT rdoasis.wsgi
worker: REMAP_SIGTERM=SIGQUIT celery --app rdoasis.celery worker --loglevel INFO --without-heartbeat
