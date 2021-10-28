# Generated by Django 3.2.8 on 2021-10-28 18:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailcore', '0068_copy_userprofiles'),
    ]

    operations = [
        migrations.CreateModel(
            name='Admin',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'permissions': [('access_admin', 'Can access Wagtail admin')],
                'default_permissions': [],
            },
        ),
    ]
