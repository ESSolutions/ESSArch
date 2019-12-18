# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-03-18 16:59
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

from ESSArch_Core.fields import JSONField


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tags', '0016_auto_20190305_1605'),
    ]

    operations = [
        migrations.CreateModel(
            name='Search',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('query', JSONField()),
                ('name', models.CharField(max_length=255)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='searches', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
