# Generated by Django 5.0.6 on 2024-06-28 14:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ip', '0104_alter_eventip_eventidentifiervalue_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='informationpackage',
            name='information_class',
            field=models.IntegerField(choices=[(0, '0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], null=True),
        ),
    ]
