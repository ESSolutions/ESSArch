# Generated by Django 3.1.2 on 2021-04-02 07:13

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fixity', '0013_auto_20210225_2133'),
    ]

    operations = [
        migrations.AlterField(
            model_name='actiontool',
            name='cmd',
            field=models.TextField(verbose_name='options, or command'),
        ),
        migrations.AlterField(
            model_name='actiontool',
            name='environment',
            field=models.CharField(choices=[('cli', 'Cli Env'), ('python', 'Python Env'), ('docker', 'Docker Env'), ('task', 'Task Env')], default='cli', max_length=20, verbose_name='environment'),
        ),
        migrations.AlterField(
            model_name='actiontool',
            name='file',
            field=models.FileField(blank=True, null=True, upload_to='stylesheets/', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['xslt'])]),
        ),
    ]
