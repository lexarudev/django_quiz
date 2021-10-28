# Generated by Django 3.1.8 on 2021-04-22 16:50

from django.db import migrations, models
import django.db.models.deletion
import wagtail.fields
import wagtail.test.testapp.models


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailcore', '0062_comment_models_and_pagesubscription'),
        ('tests', '0058_blockcountsstreammodel_minmaxcountstreammodel'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeadlyStreamPage',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.page')),
                ('body', wagtail.fields.StreamField([('title', wagtail.test.testapp.models.DeadlyCharBlock())])),
            ],
            options={
                'abstract': False,
            },
            bases=('wagtailcore.page',),
        ),
    ]
