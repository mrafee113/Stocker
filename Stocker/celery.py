import os
from celery import Celery
from celery.schedules import crontab

from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Stocker.settings')
app = Celery('Stocker')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'celery_run_tsetmc_tasks': {
        'task': 'tasks.celery_run_tsetmc_tasks',
        'schedule': settings.CELERY_ANALYSIS_SCHEDULE
    }
}
