# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-03-19 12:34
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('configuration', '0015_site'),
    ]

    operations = [
        migrations.AlterField(
            model_name='site',
            name='logo',
            field=models.ImageField(blank=True, null=True, upload_to=''),
        ),
    ]
