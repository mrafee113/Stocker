# Generated by Django 4.0 on 2022-08-29 14:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0011_supervisormessage'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='tsetmc_market_explanation',
            field=models.CharField(default='', max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='company',
            name='tsetmc_overview_title',
            field=models.CharField(default='', max_length=200),
            preserve_default=False,
        ),
    ]
