# Generated by Django 4.0 on 2022-08-26 09:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0009_alter_capitalincrease_next_stocks_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='DPS',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('issuance_date', models.DateField()),
                ('assembly_date', models.DateField()),
                ('fiscal_date', models.DateField()),
                ('dividends', models.BigIntegerField()),
                ('dps', models.IntegerField()),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='resources.company')),
            ],
        ),
    ]