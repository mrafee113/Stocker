from django.db import models
from django.utils.functional import cached_property
from django_celery_beat import models as celery_beat_models
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField

from utils.typing import celery_task
from utils.tasks import get_celery_task_string


class Stock(models.Model):
    index = models.CharField(
        max_length=20,
        verbose_name='index',
        help_text='TSETMC uses this id as a unique identifier for stocks.'
    )
    symbol = models.CharField(
        max_length=50,
        verbose_name='symbol'
    )
    url = models.URLField(
        max_length=300,
        blank=True,
        verbose_name='url'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ticker = None

    @cached_property
    def ticker(self):
        if self._ticker is None:
            from tsetmc.client import Ticker
            try:
                self._ticker = Ticker(symbol=self.symbol)
            except Exception:
                try:
                    self._ticker = Ticker(index=self.index)
                except Exception as exc:
                    print(exc)

        return self._ticker

    class Meta:
        unique_together = ['index', 'symbol']
        ordering = ['symbol', 'index']
        verbose_name = 'stock'
        verbose_name_plural = 'stocks'

    def __str__(self):
        return 'index: {}, symbol: {}'.format(self.index, self.symbol)

    def __repr__(self):
        return str(self)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.url:
            if self.index:
                self.url = settings.TSE_STOCK_DETAILS_URL.format(ticker_index=self.index)


class PeriodicTask(models.Model):
    stocks = ArrayField(
        models.CharField(max_length=50, blank=True),
        default=list,
        verbose_name='stocks',
    )
    name = models.CharField(
        max_length=200, unique=True,
        verbose_name='Name',
        help_text='Short Description For This Task',
    )
    task = models.CharField(
        max_length=200,
        verbose_name='Task Name',
        help_text=_('The Name of the Celery Task that Should be Run.  '
                    '(Example: "proj.tasks.import_contacts")'),
    )

    interval = models.ForeignKey(
        celery_beat_models.IntervalSchedule, on_delete=models.CASCADE,
        null=True, blank=True, verbose_name=_('Interval Schedule'),
        help_text=_('Interval Schedule to run the task on.  '
                    'Set only one schedule type, leave the others null.'),
    )
    crontab = models.ForeignKey(
        celery_beat_models.CrontabSchedule, on_delete=models.CASCADE, null=True, blank=True,
        verbose_name=_('Crontab Schedule'),
        help_text=_('Crontab Schedule to run the task on.  '
                    'Set only one schedule type, leave the others null.'),
    )
    clocked = models.ForeignKey(
        celery_beat_models.ClockedSchedule, on_delete=models.CASCADE, null=True, blank=True,
        verbose_name=_('Clocked Schedule'),
        help_text=_('Clocked Schedule to run the task on.  '
                    'Set only one schedule type, leave the others null.'),
    )
    expires = models.DateTimeField(
        blank=True, null=True,
        verbose_name=_('Expires Datetime'),
        help_text=_(
            'Datetime after which the schedule will no longer '
            'trigger the task to run'),
    )
    one_off = models.BooleanField(
        default=False,
        verbose_name=_('One-off Task'),
        help_text=_(
            'If True, the schedule will only run the task a single time'),
    )
    start_time = models.DateTimeField(
        blank=True, null=True,
        verbose_name=_('Start Datetime'),
        help_text=_(
            'Datetime when the schedule should begin '
            'triggering the task to run'),
    )
    enabled = models.BooleanField(
        default=True,
        verbose_name=_('Enabled'),
        help_text=_('Set to False to disable the schedule'),
    )
    last_run_at = models.DateTimeField(
        auto_now=False, auto_now_add=False,
        editable=False, blank=True, null=True,
        verbose_name=_('Last Run Datetime'),
        help_text=_(
            'Datetime that the schedule last triggered the task to run. '
            'Reset to None if enabled is set to False.'),
    )
    total_run_count = models.PositiveIntegerField(
        default=0, editable=False,
        verbose_name=_('Total Run Count'),
        help_text=_(
            'Running count of how many times the schedule '
            'has triggered the task'),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
        help_text=_(
            'Detailed description about the details of this Periodic Task'),
    )

    class Meta:
        verbose_name = 'periodic task'
        verbose_name_plural = 'periodic tasks'
        ordering = ['name']
        default_related_name = 'periodic_tasks'

    @property
    def stock_objects(self):
        return Stock.objects.filter(id__in=self.stocks)

    def __str__(self):
        s = '{name}: {schedule} {stocks}'
        schedule = '{{no schedule}}'
        schedule = f'{self.interval}' if self.interval else schedule
        schedule = f'{self.crontab}' if self.crontab else schedule
        schedule = f'{self.clocked}' if self.clocked else schedule
        stocks = [stock.symbol for stock in self.stock_objects]
        stocks = ", ".join(stocks[:5]) + ' ...' if len(stocks) > 5 \
            else ", ".join(stocks)
        stocks = f'with {stocks}' if stocks else stocks

        return s.format(name=self.name, schedule=schedule, stocks=stocks)

    def __repr__(self):
        return str(self)

    def equals_task(self, task: celery_task) -> bool:
        if isinstance(task, celery_task):
            if self.task == get_celery_task_string(task):
                return True

        return False

    def validate_unique(self, *args, **kwargs):
        super().validate_unique(*args, **kwargs)

        schedule_types = ['interval', 'crontab', 'clocked']
        selected_schedule_types = [s for s in schedule_types
                                   if getattr(self, s)]

        if len(selected_schedule_types) == 0:
            raise ValidationError('One of clocked, interval or crontab must be set.')

        err_msg = 'Only one of clocked, interval or crontab, must be set.'
        if len(selected_schedule_types) > 1:
            error_info = {}
            for selected_schedule_type in selected_schedule_types:
                error_info[selected_schedule_type] = [err_msg]

            raise ValidationError(error_info)

        if self.clocked and not self.one_off:
            err_msg = 'clocked must be one off, one_off must set True'
            raise ValidationError(err_msg)

    def save(self, *args, **kwargs):
        self.validate_unique()
        super().save(*args, **kwargs)

    @property
    def schedule(self):
        for attr in ['interval', 'crontab', 'clocked']:
            if getattr(self, attr):
                return getattr(self, attr).schedule


class UserTask(models.Model):
    task = models.CharField(
        max_length=200,
        verbose_name='Task Name',
        help_text='The Name of the Celery Task that Should be Run.  '
                  '(Example: "proj.tasks.import_contacts")'
    )
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE,
                             related_name='tasks')

    class Meta:
        ordering = ('user__username', 'task')
        verbose_name = 'user task'
        verbose_name_plural = 'user tasks'

    def __str__(self):
        return f'user: {self.user.username}, task: {self.task}'

    def __repr__(self):
        return str(self)
