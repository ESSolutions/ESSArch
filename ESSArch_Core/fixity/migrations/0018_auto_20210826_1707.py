# Generated by Django 3.1.2 on 2021-08-26 15:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fixity', '0017_auto_20210813_2058'),
    ]

    operations = [
        migrations.AlterField(
            model_name='validation',
            name='filename',
            field=models.CharField(max_length=1024),
        ),
    ]
