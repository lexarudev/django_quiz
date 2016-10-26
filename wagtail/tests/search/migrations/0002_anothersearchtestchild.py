# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-08-25 15:17
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('searchtests', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AnotherSearchTestChild',
            fields=[
                ('searchtest_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='searchtests.SearchTest')),
                ('subtitle', models.CharField(blank=True, max_length=255, null=True)),
            ],
            bases=('searchtests.searchtest',),
        ),
    ]
