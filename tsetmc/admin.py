import functools

from django.contrib import admin
from django.utils.html import format_html
from django_celery_beat import admin as celery_beat_admin
from django_celery_beat import models as celery_beat_models
from django import forms
from django.urls import reverse
from django.forms.widgets import SelectMultiple, Select, SelectDateWidget

from tsetmc.models import UserTask, Stock, PeriodicTask


class StockAdmin(admin.ModelAdmin):
    readonly_fields = ['index', 'custom_symbol']
    list_display = ['custom_symbol', 'index']

    def custom_symbol(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            obj.url,
            obj.symbol
        )

    custom_symbol.short_description = 'symbol'
    exclude = ['symbol', 'url']
    search_fields = ['symbol']


class PeriodicTaskForm(celery_beat_admin.PeriodicTaskForm):
    stocks = forms.MultipleChoiceField(choices=list())
    regtask = None
    task = forms.ChoiceField(
        choices=list(),
        label='Task',
        required=True,
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if hasattr(self.instance, 'id') and self.instance.id:
            self.fields['task'] = forms.CharField(label='Task',
                                                  required=False,
                                                  max_length=200)

        self.fields['stocks'].widget.attrs['size'] = 40
        self.fields['stocks'].choices = [
            (stock_id, f'index: {index}, symbol: {symbol}')
            for stock_id, index, symbol in Stock.objects.values_list('id', 'index', 'symbol')
        ]

        if user.is_superuser:
            tasks = UserTask.objects.values_list('task', flat=True)
        else:
            tasks = UserTask.objects.filter(user=user).values_list('task', flat=True)
        self.fields['task'].choices = [('', '')] + [(task, task) for task in tasks]

    class Meta:
        model = PeriodicTask
        exclude = ()
        widgets = {
            'stocks': SelectMultiple(attrs={'required': True, 'size': 80})
        }

    def clean(self):
        data = super(celery_beat_admin.PeriodicTaskForm, self).clean()
        if self.instance.id is None:
            if 'task' not in data or not data['task']:
                exc = forms.ValidationError('Need name of task')
                self._errors['task'] = self.error_class(exc.messages)
                raise exc

        return data


class PeriodicTaskAdmin(celery_beat_admin.PeriodicTaskAdmin):
    form = PeriodicTaskForm
    model = PeriodicTask
    fieldsets = (
        (None, {
            'fields': ('name', 'task', 'enabled', 'description',),
            'classes': ('extrapretty', 'wide'),
        }),
        ('Schedule', {
            'fields': ('interval', 'crontab', 'clocked',
                       'start_time', 'expires', 'last_run_at', 'one_off'),
            'classes': ('extrapretty', 'wide'),
        }),
        ('Stocks', {
            'fields': ('stocks',),
            'classes': ('extrapretty', 'wide')
        }),
    )
    readonly_fields = ('last_run_at',)

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change, **kwargs)
        return functools.partial(form, user=request.user)

    def get_queryset(self, request):  # kalak morghabi
        qs = super(celery_beat_admin.PeriodicTaskAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        user_tasks = UserTask.objects.filter(user=request.user).values_list('task', flat=True)
        qs = qs.filter(task__in=user_tasks)
        return qs

    def get_readonly_fields(self, request, obj=None):
        if obj is None:  # creation mode
            return 'last_run_at',
        return 'last_run_at', 'task'

    def run_tasks(self, request, queryset):
        from tsetmc.tasks import TaskController
        TaskController.run_tasks(list(queryset))


class UserTaskForm(forms.ModelForm):
    task = celery_beat_admin.TaskChoiceField(
        label='Task (registered)',
        required=False
    )

    class Meta:
        model = UserTask
        exclude = ()


class UserTaskAdmin(admin.ModelAdmin):
    form = UserTaskForm

    def get_list_display(self, request):
        if request.user.is_superuser:
            return ['custom_user', 'task']
        return ['task']

    def get_list_display_links(self, request, list_display):
        if request.user.is_superuser:
            return ['task']
        return [None]

    def get_search_fields(self, request):
        if request.user.is_superuser:
            return ['user', 'task']
        return ['task']

    def get_list_filter(self, request):
        if request.user.is_superuser:
            return ['user']
        return []

    def custom_user(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:auth_user_change', args=(obj.user.id,)),
            obj.user
        )

    custom_user.short_description = 'user'


class ClockedScheduleForm(forms.ModelForm):
    clocked_time = forms.DateField()

    class Meta:
        model = celery_beat_models.ClockedSchedule
        exclude = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['clocked_time'].widget = SelectDateWidget()


class ClockedScheduleAdmin(admin.ModelAdmin):
    form = ClockedScheduleForm
    fields = ('clocked_time',)
    list_display = ('clocked_date',)

    def clocked_date(self, obj):
        return obj.clocked_time.date()

    clocked_date.short_description = 'clock date'

    def get_fields(self, request, obj=None):
        if obj is not None:
            if request.user.is_superuser:
                return 'clocked_time',
            return 'clocked_date',
        return 'clocked_time',

    def get_list_display_links(self, request, list_display):
        if request.user.is_superuser:
            return ['clocked_date']
        return [None]


class IntervalScheduleForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if not user.is_superuser and self.instance.id is None:
            self.fields['period'].choices = [('days', 'Days')]
            self.fields['period'].initial = 'days'

    class Meta:
        model = celery_beat_models.IntervalSchedule
        exclude = ()


class IntervalScheduleAdmin(admin.ModelAdmin):
    form = IntervalScheduleForm
    fields = ('every', 'period')
    list_display = ('every', 'period')

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change, **kwargs)
        return functools.partial(form, user=request.user)


class CrontabScheduleAdmin(admin.ModelAdmin):
    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return 'minute', 'hour', 'day_of_week', 'day_of_month', 'month_of_year', 'timezone'

        return 'day_of_week', 'day_of_month', 'month_of_year'

    list_display = ('__str__',)


admin.site.register(Stock, StockAdmin)
admin.site.register(PeriodicTask, PeriodicTaskAdmin)
admin.site.register(UserTask, UserTaskAdmin)

admin.site.unregister(celery_beat_models.ClockedSchedule)
admin.site.register(celery_beat_models.ClockedSchedule, ClockedScheduleAdmin)

admin.site.unregister(celery_beat_models.IntervalSchedule)
admin.site.register(celery_beat_models.IntervalSchedule, IntervalScheduleAdmin)

admin.site.unregister(celery_beat_models.CrontabSchedule)
admin.site.register(celery_beat_models.CrontabSchedule, CrontabScheduleAdmin)
