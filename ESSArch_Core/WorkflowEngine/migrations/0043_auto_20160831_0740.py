# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('preingest', '0042_auto_20160826_1338'),
    ]

    operations = [
        migrations.AlterField(
            model_name='processtask',
            name='processstep',
            field=models.ForeignKey(related_name='tasks', blank=True, to='preingest.ProcessStep', null=True),
        ),
        migrations.AlterField(
            model_name='processtask',
            name='time_done',
            field=models.DateTimeField(null=True, verbose_name='done at', blank=True),
        ),
        migrations.AlterField(
            model_name='processtask',
            name='time_started',
            field=models.DateTimeField(null=True, verbose_name='started at', blank=True),
        ),
    ]
