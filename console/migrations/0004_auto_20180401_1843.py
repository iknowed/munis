# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2018-04-01 18:43
from __future__ import unicode_literals

import django.contrib.gis.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0003_auto_20180401_1840'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vehicle',
            name='loc',
            field=django.contrib.gis.db.models.fields.GeometryField(blank=True, null=True, srid=100000),
        ),
    ]
