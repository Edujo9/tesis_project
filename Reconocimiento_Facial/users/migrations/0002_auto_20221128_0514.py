

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attendance',
            name='present',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='attendance',
            name='time_in',
            field=models.TimeField(
                default=django.utils.timezone.now, null=True),
        ),
        migrations.AlterField(
            model_name='attendance',
            name='time_out',
            field=models.TimeField(
                default=django.utils.timezone.now, null=True),
        ),
    ]
