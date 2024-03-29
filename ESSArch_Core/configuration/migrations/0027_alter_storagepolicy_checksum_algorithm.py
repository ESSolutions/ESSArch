# Generated by Django 4.0.8 on 2023-02-25 14:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('configuration', '0026_alter_storagepolicy_ingest_path'),
    ]

    operations = [
        migrations.AlterField(
            model_name='storagepolicy',
            name='checksum_algorithm',
            field=models.IntegerField(choices=[(0, 'MD5'), (1, 'SHA-1'), (2, 'SHA-224'), (3, 'SHA-256'), (4, 'SHA-384'), (5, 'SHA-512')], default=0, verbose_name='Checksum algorithm'),
        ),
    ]
