# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-10-02 19:37
from django.db import migrations, models
import django.db.models.deletion
import uuid


def forwards_func(apps, schema_editor):
    EventIP = apps.get_model("ip", "EventIP")
    TempEventIP = apps.get_model("ip", "TempEventIP")
    db_alias = schema_editor.connection.alias

    for e in EventIP.objects.using(db_alias).all().order_by('eventDateTime').iterator():
        tmp = TempEventIP.objects.using(db_alias).create(
            eventIdentifierValue=str(e.id),
            eventType=e.eventType,
            task=e.task,
            application=e.application,
            eventVersion=e.eventVersion,
            eventOutcome=e.eventOutcome,
            eventOutcomeDetailNote=e.eventOutcomeDetailNote,
            linkingAgentIdentifierValue=e.linkingAgentIdentifierValue,
            linkingObjectIdentifierValue=e.linkingObjectIdentifierValue,
        )
        tmp.eventDateTime = e.eventDateTime
        tmp.save(update_fields=['eventDateTime'])


def reverse_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('ip', '0050_auto_20170925_1602'),
    ]

    operations = [
        migrations.AlterModelTable('EventIP', 'ip_tempeventip'),
        migrations.CreateModel(
            name='TempEventIP',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('eventIdentifierValue', models.UUIDField(primary_key=False, default=uuid.uuid4, editable=False)),
                ('eventType', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='configuration.EventType')),
                ('eventDateTime', models.DateTimeField(auto_now_add=True)),
                ('task', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='events', to='WorkflowEngine.ProcessTask')),
                ('application', models.CharField(max_length=255)),
                ('eventVersion', models.CharField(max_length=255)),
                ('eventOutcome', models.IntegerField(choices=[(0, 'Success'), (1, 'Failure')], default=None, null=True)),
                ('eventOutcomeDetailNote', models.CharField(max_length=1024)),
                ('linkingAgentIdentifierValue', models.CharField(max_length=255, blank=True)),
                ('linkingObjectIdentifierValue', models.CharField(max_length=255, blank=True)),
            ],
            options={
                'db_table': 'ip_eventip',
            },
        ),
        migrations.RunPython(forwards_func, reverse_func),
        migrations.DeleteModel('EventIP'),
        migrations.RenameModel('TempEventIP', 'EventIP'),
        migrations.AlterModelTable(name='eventip', table=None),
    ]
