# Generated by Django 2.1.3 on 2018-11-20 21:00

from django.conf import settings
from django.db import migrations, models
import django.db.migrations.operations.special
import django.db.models.deletion
import wagtail.core.models
import wagtail.search.index


# Functions from wagtail.core.migrations.0001_initial


def set_page_path_collation(apps, schema_editor):
    """
    Treebeard's path comparison logic can fail on certain locales such as sk_SK, which
    sort numbers after letters. To avoid this, we explicitly set the collation for the
    'path' column to the (non-locale-specific) 'C' collation.

    See: https://groups.google.com/d/msg/wagtail/q0leyuCnYWI/I9uDvVlyBAAJ
    """
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute("""
            ALTER TABLE wagtailcore_page ALTER COLUMN path TYPE VARCHAR(255) COLLATE "C"
        """)


# Functions from wagtail.core.migrations.0002_initial_data


def initial_data(apps, schema_editor):
    ContentType = apps.get_model('contenttypes.ContentType')
    Group = apps.get_model('auth.Group')
    Page = apps.get_model('wagtailcore.Page')
    Site = apps.get_model('wagtailcore.Site')
    GroupPagePermission = apps.get_model('wagtailcore.GroupPagePermission')

    # Create page content type
    page_content_type, created = ContentType.objects.get_or_create(
        model='page',
        app_label='wagtailcore'
    )

    # Create root page
    root = Page.objects.create(
        title="Root",
        draft_title="Root",
        slug='root',
        content_type=page_content_type,
        path='0001',
        depth=1,
        numchild=1,
        url_path='/',
    )

    # Create homepage
    homepage = Page.objects.create(
        title="Welcome to your new Wagtail site!",
        draft_title="Welcome to your new Wagtail site!",
        slug='home',
        content_type=page_content_type,
        path='00010001',
        depth=2,
        numchild=0,
        url_path='/home/',
    )

    # Create default site
    Site.objects.create(
        hostname='localhost',
        root_page_id=homepage.id,
        is_default_site=True
    )

    # Create auth groups
    moderators_group = Group.objects.create(name='Moderators')
    editors_group = Group.objects.create(name='Editors')

    # Create group permissions
    GroupPagePermission.objects.create(
        group=moderators_group,
        page=root,
        permission_type='add',
    )
    GroupPagePermission.objects.create(
        group=moderators_group,
        page=root,
        permission_type='edit',
    )
    GroupPagePermission.objects.create(
        group=moderators_group,
        page=root,
        permission_type='publish',
    )

    GroupPagePermission.objects.create(
        group=editors_group,
        page=root,
        permission_type='add',
    )
    GroupPagePermission.objects.create(
        group=editors_group,
        page=root,
        permission_type='edit',
    )

    GroupPagePermission.objects.create(
        group=moderators_group,
        page=root,
        permission_type='lock',
    )


def remove_initial_data(apps, schema_editor):
    """This function does nothing. The below code is commented out together
    with an explanation of why we don't need to bother reversing any of the
    initial data"""
    pass
    # This does not need to be deleted, Django takes care of it.
    # page_content_type = ContentType.objects.get(
    #     model='page',
    #     app_label='wagtailcore',
    # )

    # Page objects: Do nothing, the table will be deleted when reversing 0001

    # Do not reverse Site creation since other models might depend on it

    # Remove auth groups -- is this safe? External objects might depend
    # on these groups... seems unsafe.
    # Group.objects.filter(
    #     name__in=('Moderators', 'Editors')
    # ).delete()
    #
    # Likewise, we're leaving all GroupPagePermission unchanged as users may
    # have been assigned such permissions and its harmless to leave them.


# Functions from wagtail.core.migrations.0025_collection_initial_data


def collection_initial_data(apps, schema_editor):
    Collection = apps.get_model('wagtailcore.Collection')

    # Create root page
    Collection.objects.create(
        name="Root",
        path='0001',
        depth=1,
        numchild=0,
    )


# Functions from wagtail.core.migrations.0027_fix_collection_path_collation


def set_collection_path_collation(apps, schema_editor):
    """
    Treebeard's path comparison logic can fail on certain locales such as sk_SK, which
    sort numbers after letters. To avoid this, we explicitly set the collation for the
    'path' column to the (non-locale-specific) 'C' collation.

    See: https://groups.google.com/d/msg/wagtail/q0leyuCnYWI/I9uDvVlyBAAJ
    """
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute("""
            ALTER TABLE wagtailcore_collection ALTER COLUMN path TYPE VARCHAR(255) COLLATE "C"
        """)


class Migration(migrations.Migration):

    replaces = [
        ('wagtailcore', '0001_initial'),
        ('wagtailcore', '0002_initial_data'),
        ('wagtailcore', '0003_add_uniqueness_constraint_on_group_page_permission'),
        ('wagtailcore', '0004_page_locked'),
        ('wagtailcore', '0005_add_page_lock_permission_to_moderators'),
        ('wagtailcore', '0006_add_lock_page_permission'),
        ('wagtailcore', '0007_page_latest_revision_created_at'),
        ('wagtailcore', '0008_populate_latest_revision_created_at'),
        ('wagtailcore', '0009_remove_auto_now_add_from_pagerevision_created_at'),
        ('wagtailcore', '0010_change_page_owner_to_null_on_delete'),
        ('wagtailcore', '0011_page_first_published_at'),
        ('wagtailcore', '0012_extend_page_slug_field'),
        ('wagtailcore', '0013_update_golive_expire_help_text'),
        ('wagtailcore', '0014_add_verbose_name'),
        ('wagtailcore', '0015_add_more_verbose_names'),
        ('wagtailcore', '0016_change_page_url_path_to_text_field'),
        ('wagtailcore', '0017_change_edit_page_permission_description'),
        ('wagtailcore', '0018_pagerevision_submitted_for_moderation_index'),
        ('wagtailcore', '0019_verbose_names_cleanup'),
        ('wagtailcore', '0020_add_index_on_page_first_published_at'),
        ('wagtailcore', '0021_capitalizeverbose'),
        ('wagtailcore', '0022_add_site_name'),
        ('wagtailcore', '0023_alter_page_revision_on_delete_behaviour'),
        ('wagtailcore', '0024_collection'),
        ('wagtailcore', '0025_collection_initial_data'),
        ('wagtailcore', '0026_group_collection_permission'),
        ('wagtailcore', '0027_fix_collection_path_collation'),
        ('wagtailcore', '0024_alter_page_content_type_on_delete_behaviour'),
        ('wagtailcore', '0028_merge'),
        ('wagtailcore', '0029_unicode_slugfield_dj19'),
        ('wagtailcore', '0030_index_on_pagerevision_created_at'),
        ('wagtailcore', '0031_add_page_view_restriction_types'),
        ('wagtailcore', '0032_add_bulk_delete_page_permission'),
        ('wagtailcore', '0033_remove_golive_expiry_help_text'),
        ('wagtailcore', '0034_page_live_revision'),
        ('wagtailcore', '0035_page_last_published_at'),
        ('wagtailcore', '0036_populate_page_last_published_at'),
        ('wagtailcore', '0037_set_page_owner_editable'),
        ('wagtailcore', '0038_make_first_published_at_editable'),
        ('wagtailcore', '0039_collectionviewrestriction'),
        ('wagtailcore', '0040_page_draft_title'),
        ('wagtailcore', '0041_group_collection_permissions_verbose_name_plural')
    ]

    dependencies = [
        ('auth', '0001_initial'),
        ('contenttypes', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Page',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('path', models.CharField(max_length=255, unique=True)),
                ('depth', models.PositiveIntegerField()),
                ('numchild', models.PositiveIntegerField(default=0)),
                ('title', models.CharField(help_text="The page title as you'd like it to be seen by the public", max_length=255, verbose_name='title')),
                ('slug', models.SlugField(allow_unicode=True, help_text='The name of the page as it will appear in URLs e.g http://domain.com/blog/[my-slug]/', max_length=255, verbose_name='slug')),
                ('live', models.BooleanField(default=True, editable=False, verbose_name='live')),
                ('has_unpublished_changes', models.BooleanField(default=False, editable=False, verbose_name='has unpublished changes')),
                ('url_path', models.TextField(blank=True, editable=False, verbose_name='URL path')),
                ('seo_title', models.CharField(blank=True, help_text="Optional. 'Search Engine Friendly' title. This will appear at the top of the browser window.", max_length=255, verbose_name='page title')),
                ('show_in_menus', models.BooleanField(default=False, help_text='Whether a link to this page will appear in automatically generated menus', verbose_name='show in menus')),
                ('search_description', models.TextField(blank=True, verbose_name='search description')),
                ('go_live_at', models.DateTimeField(blank=True, null=True, verbose_name='go live date/time')),
                ('expire_at', models.DateTimeField(blank=True, null=True, verbose_name='expiry date/time')),
                ('expired', models.BooleanField(default=False, editable=False, verbose_name='expired')),
                ('content_type', models.ForeignKey(on_delete=models.SET(wagtail.core.models.get_default_page_content_type), related_name='pages', to='contenttypes.ContentType', verbose_name='content type')),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='owned_pages', to=settings.AUTH_USER_MODEL, verbose_name='owner')),
                ('locked', models.BooleanField(default=False, editable=False, verbose_name='locked')),
                ('latest_revision_created_at', models.DateTimeField(editable=False, null=True, verbose_name='latest revision created at')),
                ('first_published_at', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='first published at')),
                ('draft_title', models.CharField(editable=False, max_length=255)),
                ('last_published_at', models.DateTimeField(editable=False, null=True, verbose_name='last published at')),
            ],
            options={
                'abstract': False,
                'verbose_name': 'page',
                'verbose_name_plural': 'pages',
            },
            bases=(wagtail.search.index.Indexed, models.Model),
        ),
        migrations.CreateModel(
            name='GroupPagePermission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('permission_type', models.CharField(choices=[('add', 'Add/edit pages you own'), ('edit', 'Edit any page'), ('publish', 'Publish any page'), ('bulk_delete', 'Delete pages with children'), ('lock', 'Lock/unlock any page')], max_length=20, verbose_name='permission type')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='page_permissions', to='auth.Group', verbose_name='group')),
                ('page', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='group_permissions', to='wagtailcore.Page', verbose_name='page')),
            ],
            options={
                'verbose_name': 'group page permission',
                'verbose_name_plural': 'group page permissions',
            },
        ),
        migrations.AlterUniqueTogether(
            name='grouppagepermission',
            unique_together={('group', 'page', 'permission_type')},
        ),
        migrations.CreateModel(
            name='PageRevision',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('submitted_for_moderation', models.BooleanField(db_index=True, default=False, verbose_name='submitted for moderation')),
                ('created_at', models.DateTimeField(db_index=True, verbose_name='created at')),
                ('content_json', models.TextField(verbose_name='content JSON')),
                ('approved_go_live_at', models.DateTimeField(blank=True, null=True, verbose_name='approved go live at')),
                ('page', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='revisions', to='wagtailcore.Page', verbose_name='page')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='user')),
            ],
            options={
                'verbose_name': 'page revision',
                'verbose_name_plural': 'page revisions',
            },
        ),
        migrations.AddField(
            model_name='page',
            name='live_revision',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailcore.PageRevision', verbose_name='live revision'),
        ),
        migrations.CreateModel(
            name='PageViewRestriction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(blank=True, max_length=255, verbose_name='password')),
                ('page', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='view_restrictions', to='wagtailcore.Page', verbose_name='page')),
                ('groups', models.ManyToManyField(blank=True, to='auth.Group', verbose_name='groups')),
                ('restriction_type', models.CharField(choices=[('none', 'Public'), ('login', 'Private, accessible to logged-in users'), ('password', 'Private, accessible with the following password'), ('groups', 'Private, accessible to users in specific groups')], max_length=20)),
            ],
            options={
                'verbose_name': 'page view restriction',
                'verbose_name_plural': 'page view restrictions',
            },
        ),
        migrations.CreateModel(
            name='Site',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hostname', models.CharField(db_index=True, max_length=255, verbose_name='hostname')),
                ('port', models.IntegerField(default=80, help_text='Set this to something other than 80 if you need a specific port number to appear in URLs (e.g. development on port 8000). Does not affect request handling (so port forwarding still works).', verbose_name='port')),
                ('is_default_site', models.BooleanField(default=False, help_text='If true, this site will handle requests for all other hostnames that do not have a site entry of their own', verbose_name='is default site')),
                ('root_page', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sites_rooted_here', to='wagtailcore.Page', verbose_name='root page')),
                ('site_name', models.CharField(blank=True, help_text='Human-readable name for the site.', max_length=255, null=True, verbose_name='site name')),
            ],
            options={
                'verbose_name': 'site',
                'verbose_name_plural': 'sites',
            },
        ),
        migrations.AlterUniqueTogether(
            name='site',
            unique_together={('hostname', 'port')},
        ),
        migrations.CreateModel(
            name='Collection',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('path', models.CharField(max_length=255, unique=True)),
                ('depth', models.PositiveIntegerField()),
                ('numchild', models.PositiveIntegerField(default=0)),
                ('name', models.CharField(max_length=255, verbose_name='name')),
            ],
            options={
                'verbose_name': 'collection',
                'verbose_name_plural': 'collections',
            },
        ),
        migrations.CreateModel(
            name='GroupCollectionPermission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('collection', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='group_permissions', to='wagtailcore.Collection', verbose_name='collection')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='collection_permissions', to='auth.Group', verbose_name='group')),
                ('permission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.Permission', verbose_name='permission')),
            ],
            options={
                'verbose_name': 'group collection permission',
            },
        ),
        migrations.AlterUniqueTogether(
            name='groupcollectionpermission',
            unique_together={('group', 'collection', 'permission')},
        ),
        migrations.CreateModel(
            name='CollectionViewRestriction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('restriction_type', models.CharField(choices=[('none', 'Public'), ('login', 'Private, accessible to logged-in users'), ('password', 'Private, accessible with the following password'), ('groups', 'Private, accessible to users in specific groups')], max_length=20)),
                ('password', models.CharField(blank=True, max_length=255, verbose_name='password')),
                ('collection', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='view_restrictions', to='wagtailcore.Collection', verbose_name='collection')),
                ('groups', models.ManyToManyField(blank=True, to='auth.Group', verbose_name='groups')),
            ],
            options={
                'verbose_name': 'collection view restriction',
                'verbose_name_plural': 'collection view restrictions',
            },
        ),
        migrations.AlterModelOptions(
            name='groupcollectionpermission',
            options={'verbose_name': 'group collection permission', 'verbose_name_plural': 'group collection permissions'},
        ),
        migrations.RunPython(set_page_path_collation, migrations.RunPython.noop),
        migrations.RunPython(initial_data, remove_initial_data),
        migrations.RunPython(collection_initial_data, migrations.RunPython.noop),
        migrations.RunPython(set_collection_path_collation, migrations.RunPython.noop),
    ]
