# Generated by Django 4.0.8 on 2023-02-08 17:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('essauth', '0024_alter_group_parent'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='groupgenericobjects',
            unique_together={('group', 'object_id')},
        ),
    ]