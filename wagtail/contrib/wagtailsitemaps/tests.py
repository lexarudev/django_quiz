from django.test import TestCase
from django.core.urlresolvers import reverse
from django.core.cache import cache

from wagtail.wagtailcore.models import Page, Site
from wagtail.tests.models import SimplePage

from .sitemap_generator import Sitemap


class TestSitemapGenerator(TestCase):
    def setUp(self):
        self.home_page = Page.objects.get(id=2)

        self.child_page = self.home_page.add_child(instance=SimplePage(
            title="Hello world!",
            slug='hello-world',
            live=True,
        ))

        self.unpublished_child_page = self.home_page.add_child(instance=SimplePage(
            title="Unpublished",
            slug='unpublished',
            live=False,
        ))

        self.site = Site.objects.get(is_default_site=True)

    def test_get_pages(self):
        sitemap = Sitemap(self.site)
        pages = sitemap.get_pages()

        self.assertIn(self.child_page.page_ptr, pages)
        self.assertNotIn(self.unpublished_child_page.page_ptr, pages)

    def test_get_urls(self):
        sitemap = Sitemap(self.site)
        urls = [url['location'] for url in sitemap.get_urls()]

        self.assertIn('/', urls) # Homepage
        self.assertIn('/hello-world/', urls) # Child page

    def test_render(self):
        sitemap = Sitemap(self.site)
        xml = sitemap.render()

        # Check that a URL has made it into the xml
        self.assertIn('/hello-world/', xml)

        # Make sure the unpublished page didn't make it into the xml
        self.assertNotIn('/unpublished/', xml)


class TestSitemapView(TestCase):
    def test_sitemap_view(self):
        response = self.client.get('/sitemap.xml')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'wagtailsitemaps/sitemap.xml')
        self.assertEqual(response['Content-Type'], 'text/xml; charset=utf-8')

    def test_sitemap_view_cache(self):
        cache_key = 'wagtail-sitemap:%d' % Site.objects.get(is_default_site=True).id

        # Check that the key is not in the cache
        self.assertFalse(cache.has_key(cache_key))

        # Hit the view
        first_response = self.client.get('/sitemap.xml')

        self.assertEqual(first_response.status_code, 200)
        self.assertTemplateUsed(first_response, 'wagtailsitemaps/sitemap.xml')

        # Check that the key is in the cache
        self.assertTrue(cache.has_key(cache_key))

        # Hit the view again. Should come from the cache this time
        second_response = self.client.get('/sitemap.xml')

        self.assertEqual(second_response.status_code, 200)
        self.assertTemplateNotUsed(second_response, 'wagtailsitemaps/sitemap.xml') # Sitemap should not be re rendered

        # Check that the content is the same
        self.assertEqual(first_response.content, second_response.content)
