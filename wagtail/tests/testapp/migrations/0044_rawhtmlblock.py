# Generated by Django 3.0.4 on 2020-04-06 09:46

from django.db import migrations
import wagtail.core.blocks
import wagtail.core.fields
import wagtail.tests.testapp.models


class Migration(migrations.Migration):

    dependencies = [
        ('tests', '0043_customdocument_fancy_description'),
    ]

    operations = [
        migrations.AlterField(
            model_name='streampage',
            name='body',
            field=wagtail.core.fields.StreamField([('text', wagtail.core.blocks.CharBlock()), ('rich_text', wagtail.core.blocks.RichTextBlock()), ('image', wagtail.tests.testapp.models.ExtendedImageChooserBlock()), ('product', wagtail.core.blocks.StructBlock([('name', wagtail.core.blocks.CharBlock()), ('price', wagtail.core.blocks.CharBlock())])), ('raw_html', wagtail.core.blocks.RawHTMLBlock())]),
        ),
    ]
