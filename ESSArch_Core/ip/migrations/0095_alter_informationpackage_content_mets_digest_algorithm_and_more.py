# Generated by Django 4.0.8 on 2023-03-02 15:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ip', '0094_informationpackagegroupobjects'),
    ]

    operations = [
        migrations.AlterField(
            model_name='informationpackage',
            name='content_mets_digest_algorithm',
            field=models.IntegerField(choices=[(0, 'none'), (1, 'MD5'), (2, 'SHA-1'), (3, 'SHA-224'), (4, 'SHA-256'), (5, 'SHA-384'), (6, 'SHA-512')], null=True),
        ),
        migrations.AlterField(
            model_name='informationpackage',
            name='message_digest_algorithm',
            field=models.IntegerField(choices=[(0, 'none'), (1, 'MD5'), (2, 'SHA-1'), (3, 'SHA-224'), (4, 'SHA-256'), (5, 'SHA-384'), (6, 'SHA-512')], null=True),
        ),
        migrations.AlterField(
            model_name='informationpackage',
            name='package_mets_digest_algorithm',
            field=models.IntegerField(choices=[(0, 'none'), (1, 'MD5'), (2, 'SHA-1'), (3, 'SHA-224'), (4, 'SHA-256'), (5, 'SHA-384'), (6, 'SHA-512')], null=True),
        ),
        migrations.AlterField(
            model_name='informationpackagemetadata',
            name='message_digest_algorithm',
            field=models.IntegerField(choices=[(0, 'none'), (1, 'MD5'), (2, 'SHA-1'), (3, 'SHA-224'), (4, 'SHA-256'), (5, 'SHA-384'), (6, 'SHA-512')], null=True),
        ),
    ]