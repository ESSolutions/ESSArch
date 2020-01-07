# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2018-01-28 19:14
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0045_auto_20171205_1437'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='profile',
            options={'ordering': ['name'], 'permissions': (('export_profile', 'Can export profile'),), 'verbose_name': 'profile', 'verbose_name_plural': 'profiles'},
        ),
        migrations.AlterModelOptions(
            name='submissionagreement',
            options={'ordering': ['name'], 'permissions': (('create_new_sa_generation', 'Can create new generations of SA'), ('export_sa', 'Can export SA')), 'verbose_name': 'submission agreement', 'verbose_name_plural': 'submission agreements'},
        ),
    ]
