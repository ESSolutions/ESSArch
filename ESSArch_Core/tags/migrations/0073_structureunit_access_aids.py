# Generated by Django 3.1.2 on 2021-06-13 18:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('access', '0001_initial'),
        ('tags', '0072_auto_20201026_2154'),
    ]

    operations = [
        migrations.AddField(
            model_name='structureunit',
            name='access_aids',
            field=models.ManyToManyField(related_name='structure_units', to='access.AccessAid', verbose_name='access_aids'),
        ),
    ]
