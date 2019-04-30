# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2018-04-11 09:13
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('groups_manager', '0004_0_6_0_groupmember_expiration_date'),
        ('essauth', '0012_userprofile_notifications_enabled'),
    ]

    operations = [
        migrations.CreateModel(
            name='GroupType',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'default_permissions': [],
                'verbose_name': 'group type',
                'verbose_name_plural': 'group types',
            },
            bases=('groups_manager.grouptype',),
        ),
        migrations.AlterField(
            model_name='group',
            name='group_type',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='essauth_groups', to='essauth.GroupType', verbose_name='group type'),
        ),
    ]
