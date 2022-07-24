from utils.typing import celery_task


def get_celery_task_string(task: celery_task) -> str:
    return f'{task.__module__}.{task.__name__}'
