# Generated by Django 2.2.5 on 2019-09-30 13:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ip', '0081_auto_20190930_1112'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConsignMethod',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True, verbose_name='name')),
            ],
            options={
                'verbose_name': 'consign method',
                'verbose_name_plural': 'consign methods',
            },
        ),
        migrations.AddField(
            model_name='order',
            name='consign_method',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='ip.ConsignMethod', verbose_name='consign method'),
        ),
    ]
