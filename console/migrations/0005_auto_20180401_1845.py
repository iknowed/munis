# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2018-04-01 18:45
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0004_auto_20180401_1843'),
    ]

    operations = [
        migrations.AlterField(
            model_name='run',
            name='speed',
            field=models.FloatField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name='speed',
            name='speed',
            field=models.FloatField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name='vehicle',
            name='speedkmhr',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
