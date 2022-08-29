from datetime import date

from django.db.models import Q

from utils.tasks import get_celery_task_string
from utils.typing import celery_task, module
from utils import filter_local_names
from utils.datetime import datetime_from_date, today, now
from tsetmc.models import PeriodicTask
from tsetmc.client.download import download as stock_data_download

# after creating a new user import the module of user here
from tsetmc.tasks_module import example_user

all_modules = [example_user]


# end of modules

class TaskController:
    @classmethod
    def get_module_task_functions(cls, module_value: module) -> list[celery_task]:
        names: list[str] = filter_local_names(dir(module_value))
        tasks: list[celery_task] = list()
        for name in names:
            task = getattr(module_value, name)
            if isinstance(task, celery_task):
                tasks.append(task)

        return tasks

    @classmethod
    def get_task_functions(cls, modules: list[module]) -> list[celery_task]:
        tasks: list[celery_task] = list()
        for module_value in modules:
            tasks.extend(cls.get_module_task_functions(module_value))

        return tasks

    @classmethod
    def get_date_tasks(cls, date_value: date) -> list[PeriodicTask]:
        datetime_value = datetime_from_date(date_value)
        queryset = PeriodicTask.objects.filter(
            Q(start_time__lte=datetime_value) | Q(start_time=None),
            Q(expires__gt=datetime_value) | Q(expires=None),
            Q(one_off=True, total_run_count=0) | Q(one_off=None),
            enabled=True,
        )  # filter active Periodic Tasks

        tasks: list[PeriodicTask] = list()
        # interval-based and crontab-based
        for attr in ['interval', 'crontab']:
            for ptask in queryset.filter(**dict({f'{attr}__isnull': False})):
                if ptask.last_run_at is not None and \
                        getattr(ptask, attr).schedule.is_due(ptask.last_run_at):
                    tasks.append(ptask)

                elif ptask.start_time is not None and \
                        ptask.start_time.date() == today() and \
                        getattr(ptask, attr).schedule.is_due(ptask.start_time):
                    tasks.append(ptask)

                else:  # the task is active but has never been run
                    tasks.append(ptask)

        # clocked-based
        for ptask in queryset.filter(clocked__isnull=False, clocked__clocked_time__date=date_value):
            tasks.append(ptask)

        return tasks

    @classmethod
    def download_tasks_data(cls, tasks: list[PeriodicTask]):
        symbols = set()
        for task in tasks:
            for stock in task.stock_objects:
                symbols |= {stock.symbol}

        stock_data_download(list(symbols))

    @classmethod
    def run_tasks(cls, tasks: list[PeriodicTask] = None):
        if tasks is None:
            tasks: list[PeriodicTask] = cls.get_date_tasks(today())  # filter today
        cls.download_tasks_data(tasks)

        task_functions: list[celery_task] = cls.get_task_functions(all_modules)
        tasks: list[tuple[celery_task, PeriodicTask]] = \
            [(task, ptask)
             for task in task_functions
             for ptask in tasks
             if ptask.equals_task(task)]

        for task_function, periodic_task in tasks:
            stocks: list[str] = [stock.symbol for stock in periodic_task.stock_objects]
            if not stocks:
                continue

            task_function.delay(stocks, periodic_task)

            periodic_task.last_run_at = now()
            periodic_task.total_run_count += 1

        cls.cleanup()

    @classmethod
    def cleanup(cls):
        datetime_value = now()
        queryset = PeriodicTask.objects.filter(
            Q(expires__lt=datetime_value),
            Q(one_off=True, total_run_count__gte=1),
        )
        queryset.delete()
