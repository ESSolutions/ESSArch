# Generated by Django 4.2.5 on 2023-10-15 21:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('WorkflowEngine', '0085_alter_processstep_options_and_more'),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='processtask',
            new_name='ProcessTask_retried_a85a5e_idx',
            old_fields=('retried', 'processstep', 'information_package'),
        ),
    ]