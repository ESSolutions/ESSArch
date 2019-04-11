# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-04-11 11:12
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tags', '0032_structure_published'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='structure',
            options={'get_latest_by': 'create_date', 'permissions': (('publish_structure', 'Can publish structures'), ('create_new_structure_version', 'Can create new structure versions'))},
        ),
        migrations.AddField(
            model_name='structure',
            name='published_date',
            field=models.DateTimeField(null=True),
        ),
    ]
