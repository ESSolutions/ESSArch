# Generated by Django 3.0.3 on 2020-02-28 09:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('maintenance', '0014_auto_20200226_1350'),
    ]

    operations = [
        migrations.AddField(
            model_name='appraisaljob',
            name='purpose',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='conversionjob',
            name='purpose',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
    ]
