# Generated by Django 5.0.14 on 2025-04-29 17:42

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('agents', '0017_alter_agent_id_alter_agentfunction_id_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='agent',
            options={'permissions': (('change_organization', 'Can change organization for agent'),)},
        ),
    ]
