from celery import shared_task


@shared_task
def celery_run_tsetmc_tasks():
    from tsetmc.tasks import TaskController
    TaskController.run_tasks()
