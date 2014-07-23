# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Embed',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('url', models.URLField()),
                ('max_width', models.SmallIntegerField(null=True, blank=True)),
                ('type', models.CharField(max_length=10, choices=[(b'video', b'Video'), (b'photo', b'Photo'), (b'link', b'Link'), (b'rich', b'Rich')])),
                ('html', models.TextField(blank=True)),
                ('title', models.TextField(blank=True)),
                ('author_name', models.TextField(blank=True)),
                ('provider_name', models.TextField(blank=True)),
                ('thumbnail_url', models.URLField(null=True, blank=True)),
                ('width', models.IntegerField(null=True, blank=True)),
                ('height', models.IntegerField(null=True, blank=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='embed',
            unique_together=set([(b'url', b'max_width')]),
        ),
    ]
