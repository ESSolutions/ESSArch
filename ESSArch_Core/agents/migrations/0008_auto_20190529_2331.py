# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-05-29 21:31
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('agents', '0007_auto_20190426_1504'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='agenttaglink',
            options={'verbose_name': 'Agent node relation', 'verbose_name_plural': 'Agent node relations'},
        ),
    ]
