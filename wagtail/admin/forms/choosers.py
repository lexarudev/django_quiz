from django import forms
from django.core import validators
from django.forms.widgets import TextInput
from django.utils.translation import gettext_lazy as _

from wagtail.models import Locale


class URLOrAbsolutePathValidator(validators.URLValidator):
    @staticmethod
    def is_absolute_path(value):
        return value.startswith("/")

    def __call__(self, value):
        if URLOrAbsolutePathValidator.is_absolute_path(value):
            return None
        else:
            return super().__call__(value)


class URLOrAbsolutePathField(forms.URLField):
    widget = TextInput
    default_validators = [URLOrAbsolutePathValidator()]

    def to_python(self, value):
        if not URLOrAbsolutePathValidator.is_absolute_path(value):
            value = super().to_python(value)
        return value


class ExternalLinkChooserForm(forms.Form):
    url = URLOrAbsolutePathField(required=True, label=_("URL"))
    link_text = forms.CharField(required=False)


class AnchorLinkChooserForm(forms.Form):
    url = forms.CharField(required=True, label="#")
    link_text = forms.CharField(required=False)


class EmailLinkChooserForm(forms.Form):
    email_address = forms.EmailField(required=True)
    link_text = forms.CharField(required=False)


class PhoneLinkChooserForm(forms.Form):
    phone_number = forms.CharField(required=True)
    link_text = forms.CharField(required=False)


class SearchFilterMixin(forms.Form):
    """
    Mixin for a chooser listing filter form, to provide a search field
    """

    q = forms.CharField(
        label=_("Search term"),
        widget=forms.TextInput(attrs={"placeholder": _("Search")}),
        required=False,
    )


class CollectionFilterMixin(forms.Form):
    """
    Mixin for a chooser listing filter form, to provide a collection filter field.
    The view must pass a `collections` keyword argument when constructing the form
    """

    def __init__(self, *args, collections=None, **kwargs):
        super().__init__(*args, **kwargs)

        if collections:
            collection_choices = [
                ("", _("All collections"))
            ] + collections.get_indented_choices()
            self.fields["collection_id"] = forms.ChoiceField(
                label=_("Collection"),
                choices=collection_choices,
                required=False,
                widget=forms.Select(attrs={"data-chooser-modal-search-filter": True}),
            )


class LocaleFilterMixin(forms.Form):
    """
    Mixin for a chooser listing filter form, to provide a locale filter field.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        locales = Locale.objects.all()
        if locales:
            self.fields["locale"] = forms.ChoiceField(
                choices=[
                    (locale.language_code, locale.get_display_name())
                    for locale in locales
                ],
                required=False,
                widget=forms.Select(attrs={"data-chooser-modal-search-filter": True}),
            )
