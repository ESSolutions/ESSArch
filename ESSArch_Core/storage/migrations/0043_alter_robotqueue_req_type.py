# Generated by Django 4.1.9 on 2023-05-27 13:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0042_alter_storagetarget_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='robotqueue',
            name='req_type',
            field=models.IntegerField(choices=[(10, 'mount'), (20, 'unmount'), (30, 'unmount_force')]),
        ),
    ]
