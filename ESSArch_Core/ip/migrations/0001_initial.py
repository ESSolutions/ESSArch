# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='EventIP',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('eventType', models.CharField(max_length=255)),
                ('eventDateTime', models.CharField(max_length=255)),
                ('eventDetail', models.CharField(max_length=255)),
                ('eventApplication', models.CharField(max_length=255)),
                ('eventVersion', models.CharField(max_length=255)),
                ('eventOutcome', models.CharField(max_length=255)),
                ('eventOutcomeDetailNote', models.CharField(max_length=1024)),
                ('linkingAgentIdentifierValue', models.CharField(max_length=255)),
            ],
            options={
                'ordering': ['eventType'],
                'verbose_name': 'Events related to IP',
            },
        ),
        migrations.CreateModel(
            name='InformationPackage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('Producer', models.CharField(max_length=255)),
                ('Label', models.CharField(max_length=255)),
                ('Content', models.CharField(max_length=255)),
                ('Responsible', models.CharField(max_length=255)),
                ('CreateDate', models.CharField(max_length=255)),
                ('State', models.CharField(max_length=255)),
                ('Status', models.CharField(max_length=255)),
                ('ObjectSize', models.CharField(max_length=255)),
                ('ObjectNumItems', models.CharField(max_length=255)),
                ('ObjectPath', models.CharField(max_length=255)),
                ('Startdate', models.CharField(max_length=255)),
                ('Enddate', models.CharField(max_length=255)),
                ('OAIStype', models.CharField(max_length=255)),
            ],
            options={
                'ordering': ['id'],
                'verbose_name': 'Information Package',
            },
        ),
        migrations.AddField(
            model_name='eventip',
            name='linkingObjectIdentifierValue',
            field=models.ForeignKey(related_name='events', to='ip.InformationPackage'),
        ),
    ]
