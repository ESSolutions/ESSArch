# Generated by Django 3.0.2 on 2020-01-27 17:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('WorkflowEngine', '0080_auto_20200127_1846'),
    ]

    operations = [
        migrations.AlterField(
            model_name='processtask',
            name='undo_type',
            field=models.BooleanField(db_index=True, default=False, editable=False),
        ),
    ]
