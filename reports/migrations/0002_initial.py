# Generated by Django 5.1.7 on 2025-07-26 18:37

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('reports', '0001_initial'),
        ('tankhah', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='financialreport',
            name='tankhah',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='tankhah.tankhah', verbose_name='تنخواه'),
        ),
    ]
