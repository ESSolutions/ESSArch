# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2018-01-28 19:25
from django.db import migrations, models
import django.db.models.deletion
import jsonfield.fields
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('ip', '0064_informationpackage_appraisal_date'),
        ('maintenance', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConversionJob',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('RECEIVED', 'RECEIVED'), ('RETRY', 'RETRY'), ('REVOKED', 'REVOKED'), ('SUCCESS', 'SUCCESS'), ('STARTED', 'STARTED'), ('FAILURE', 'FAILURE'), ('PENDING', 'PENDING')], default='PENDING', max_length=50)),
                ('start_date', models.DateTimeField(null=True)),
                ('end_date', models.DateTimeField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='ConversionJobEntry',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('start_date', models.DateTimeField(null=True)),
                ('end_date', models.DateTimeField(null=True)),
                ('old_document', models.CharField(blank=True, max_length=255)),
                ('new_document', models.CharField(blank=True, max_length=255)),
                ('tool', models.CharField(blank=True, max_length=255)),
                ('ip', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='conversion_job_entries', to='ip.InformationPackage')),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entries', to='maintenance.ConversionJob')),
            ],
        ),
        migrations.CreateModel(
            name='ConversionRule',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('frequency', models.CharField(blank=True, default='', max_length=255)),
                ('specification', jsonfield.fields.JSONField(default=None, null=True)),
                ('information_packages', models.ManyToManyField(related_name='conversion_rules', to='ip.InformationPackage')),
            ],
        ),
        migrations.AddField(
            model_name='conversionjob',
            name='rule',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='jobs', to='maintenance.ConversionRule'),
        ),
    ]
