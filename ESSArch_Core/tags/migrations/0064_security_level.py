# Generated by Django 2.2.5 on 2019-09-30 08:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tags', '0063_tagversiontype_custom_fields_template'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='tag',
            options={'permissions': (('search', 'Can search'), ('create_archive', 'Can create new archives'), ('change_archive', 'Can change archives'), ('delete_archive', 'Can delete archives'), ('change_tag_location', 'Can change tag location'), ('security_level_1', 'Can see security level 1'), ('security_level_2', 'Can see security level 2'), ('security_level_3', 'Can see security level 3'), ('security_level_4', 'Can see security level 4'), ('security_level_5', 'Can see security level 5'))},
        ),
        migrations.AddField(
            model_name='tagversion',
            name='security_level',
            field=models.IntegerField(null=True, verbose_name='security level'),
        ),
    ]