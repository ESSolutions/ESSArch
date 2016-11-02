# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='EventType',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('eventType', models.IntegerField(default=0, unique=True)),
                ('eventDetail', models.CharField(max_length=255)),
            ],
            options={
                'ordering': ['eventType'],
                'verbose_name': 'Event Type',
            },
        ),
        migrations.CreateModel(
            name='Parameter',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('entity', models.CharField(unique=True, max_length=60)),
                ('value', models.CharField(max_length=70)),
            ],
            options={
                'ordering': ['entity'],
                'verbose_name': 'Parameter',
            },
        ),
        migrations.CreateModel(
            name='Path',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('entity', models.CharField(unique=True, max_length=60)),
                ('value', models.CharField(max_length=70)),
            ],
            options={
                'ordering': ['entity'],
                'verbose_name': 'Path',
            },
        ),
        migrations.CreateModel(
            name='Schema',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('entity', models.CharField(unique=True, max_length=60)),
                ('value', models.CharField(max_length=70)),
            ],
            options={
                'ordering': ['entity'],
                'verbose_name': 'XML Schema',
            },
        ),
    ]
