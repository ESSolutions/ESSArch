# Generated by Django 3.1.2 on 2021-08-13 18:58

from django.db import migrations
import picklefield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('fixity', '0016_auto_20210409_1410'),
    ]

    operations = [
        migrations.AlterField(
            model_name='validation',
            name='message',
            field=picklefield.fields.PickledObjectField(default=None, editable=False, null=True),
        ),
    ]
