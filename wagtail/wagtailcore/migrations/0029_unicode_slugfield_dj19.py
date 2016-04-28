# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-04-27 22:39
from __future__ import unicode_literals

from django.db import migrations, models
from django import VERSION as DJANGO_VERSION


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailcore', '0028_merge'),
    ]

    operations = []
    if DJANGO_VERSION >= (1, 9):
        operations += [
            migrations.AlterField(
                model_name='page',
                name='slug',
                field=models.SlugField(allow_unicode=True, help_text='The name of the page as it will appear in URLs e.g http://domain.com/blog/[my-slug]/', max_length=255, verbose_name='slug'),
            ),
        ]
