# Generated by Django 3.0.4 on 2020-05-05 07:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tags', '0065_tag_appraisal_date'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='tag',
            options={'permissions': (('search', 'Can search'), ('create_archive', 'Can create new archives'), ('change_archive', 'Can change archives'), ('delete_archive', 'Can delete archives'), ('change_tag_location', 'Can change tag location'), ('security_level_1', 'Can see security level 1'), ('security_level_exists_1', 'Can see security level 1 exists'), ('security_level_2', 'Can see security level 2'), ('security_level_exists_2', 'Can see security level 2 exists'), ('security_level_3', 'Can see security level 3'), ('security_level_exists_3', 'Can see security level 3 exists'), ('security_level_4', 'Can see security level 4'), ('security_level_exists_4', 'Can see security level 4 exists'), ('security_level_5', 'Can see security level 5'), ('security_level_exists_5', 'Can see security level 5 exists'))},
        ),
    ]
