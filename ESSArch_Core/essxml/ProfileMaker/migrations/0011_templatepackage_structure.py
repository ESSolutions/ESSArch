# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-09-13 07:44
from django.db import migrations
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('ProfileMaker', '0010_auto_20170808_1114'),
    ]

    operations = [
        migrations.AddField(
            model_name='templatepackage',
            name='structure',
            field=jsonfield.fields.JSONField(default=[]),
        ),
    ]
