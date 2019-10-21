from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('configuration', '0019_auto_20190619_1620'),
    ]

    operations = [
        migrations.AddField(
            model_name='eventtype',
            name='category',
            field=models.IntegerField(choices=[(0, 'Information package'), (1, 'Delivery')], default=0),
            preserve_default=False,
        ),
    ]
