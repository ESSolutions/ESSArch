# Generated by Django 4.1.1 on 2022-09-23 12:59

from django.db import migrations
import django.db.models.deletion
import mptt.fields


class Migration(migrations.Migration):

    dependencies = [
        ('essauth', '0023_auto_20210416_1619'),
    ]

    operations = [
        migrations.AlterField(
            model_name='group',
            name='parent',
            field=mptt.fields.TreeForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sub_%(app_label)s_%(class)s_set', to='essauth.group', verbose_name='parent'),
        ),
    ]
