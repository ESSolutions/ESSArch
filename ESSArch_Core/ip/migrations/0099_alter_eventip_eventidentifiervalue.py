# Generated by Django 4.1.10 on 2023-09-26 09:09

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('ip', '0098_alter_informationpackage_label_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eventip',
            name='eventIdentifierValue',
            field=models.UUIDField(default=uuid.uuid4, unique=True),
        ),
    ]
