import warnings

from wagtail.utils.deprecation import RemovedInWagtail06Warning


warnings.warn(
    "The embed_filters tag library has been moved to wagtailembeds_tags. "
    "Use {% load wagtailembeds_tags %} instead.", RemovedInWagtail06Warning)


from wagtail.wagtailembeds.templatetags.wagtailembeds_tags import register, embed
