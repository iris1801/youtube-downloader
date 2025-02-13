from celery import Celery
from flask import Flask

def make_celery(app: Flask):
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)
    return celery

# Configurazioni Celery
def create_celery_app(app):
    app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
    app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
    return make_celery(app)

from app import app
celery = create_celery_app(app)

