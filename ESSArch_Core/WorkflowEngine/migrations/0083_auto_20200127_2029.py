# Generated by Django 3.0.2 on 2020-01-27 19:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('WorkflowEngine', '0082_auto_20200127_1902'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name='processstep',
            index_together={('tree_id', 'lft', 'rght'), ('tree_id', 'lft')},
        ),
    ]
