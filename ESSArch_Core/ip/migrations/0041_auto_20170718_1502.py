# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-07-18 13:02
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ip', '0039_auto_20170703_1032'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eventip',
            name='eventApplication',
            field=models.ForeignKey(null=True, on_delete=models.deletion.CASCADE, related_name='events', to='WorkflowEngine.ProcessTask'),
        ),
        migrations.RenameField(
            model_name='eventip',
            old_name='eventApplication',
            new_name='task',
        ),
        migrations.AddField(
            model_name='eventip',
            name='application',
            field=models.CharField(default='ESSArch', max_length=255),
            preserve_default=False,
        ),
    ]
