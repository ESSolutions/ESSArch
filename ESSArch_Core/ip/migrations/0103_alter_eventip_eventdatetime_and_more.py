# Generated by Django 5.0.1 on 2024-02-11 21:39

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ip', '0102_alter_informationpackage_end_date_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eventip',
            name='eventDateTime',
            field=models.DateTimeField(db_index=True, default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='eventip',
            name='linkingObjectIdentifierValue',
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
    ]
