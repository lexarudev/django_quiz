from __future__ import absolute_import, unicode_literals

import django

from wagtail.wagtailcore.models import Site
from wagtail.wagtailcore.request_cache import RequestCache


if django.VERSION >= (1, 10):
    from django.utils.deprecation import MiddlewareMixin
else:
    MiddlewareMixin = object



class SiteMiddleware(MiddlewareMixin):
    def process_request(self, request):
        """
        Set request.site to contain the Site object responsible for handling this request,
        according to hostname matching rules
        """
        try:
            request.site = Site.find_for_request(request)
        except Site.DoesNotExist:
            request.site = None


class RequestCacheMiddleware(MiddlewareMixin):
    """
    Creates a fresh cache instance as request.cache. The cache instance lives only as long as request does.
    """

    def process_request(self, request):
        request.cache = RequestCache()
