# Generated by Django 3.0.3 on 2020-03-05 10:15

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('agents', '0011_auto_20190925_1848'),
    ]

    operations = [
        migrations.AlterField(
            model_name='agent',
            name='create_date',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='create date'),
        ),
    ]
