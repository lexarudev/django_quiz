"""Helper classes for formatting data as tables"""

from collections import OrderedDict
from collections.abc import Mapping

from django.forms import MediaDefiningClass
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.text import capfirst

from wagtail.admin.ui.components import Component
from wagtail.core.utils import multigetattr


class Column(metaclass=MediaDefiningClass):

    class Header:
        # Helper object used for rendering column headers in templates -
        # behaves as a component (i.e. it has a render_html method) but delegates rendering
        # to Column.render_header_html
        def __init__(self, column):
            self.column = column

        def render_html(self, parent_context):
            return self.column.render_header_html(parent_context)

    class Cell:
        # Helper object used for rendering table cells in templates -
        # behaves as a component (i.e. it has a render_html method) but delegates rendering
        # to Column.render_cell_html
        def __init__(self, column, instance):
            self.column = column
            self.instance = instance

        def render_html(self, parent_context):
            return self.column.render_cell_html(self.instance, parent_context)

    header_template_name = "wagtailadmin/tables/column_header.html"
    cell_template_name = "wagtailadmin/tables/cell.html"

    def __init__(self, name, label=None, accessor=None, classname=None, sort_key=None):
        self.name = name
        self.accessor = accessor or name
        self.label = label or capfirst(name.replace('_', ' '))
        self.classname = classname
        self.sort_key = sort_key
        self.header = Column.Header(self)

    def get_header_context_data(self, parent_context):
        """
        Compiles the context dictionary to pass to the header template when rendering the column header
        """
        return {
            'column': self,
            'ordering': parent_context.get('ordering'),
            'request': parent_context.get('request'),
        }

    def render_header_html(self, parent_context):
        """
        Renders the column's header
        """
        context = self.get_header_context_data(parent_context)
        return render_to_string(self.header_template_name, context)

    def get_value(self, instance):
        """
        Given an instance (i.e. any object containing data), extract the field of data to be
        displayed in a cell of this column
        """
        if callable(self.accessor):
            return self.accessor(instance)
        else:
            return multigetattr(instance, self.accessor)

    def get_cell_context_data(self, instance, parent_context):
        """
        Compiles the context dictionary to pass to the cell template when rendering a table cell for
        the given instance
        """
        return {
            'instance': instance,
            'column': self,
            'value': self.get_value(instance),
            'request': parent_context.get('request'),
        }

    def render_cell_html(self, instance, parent_context):
        """
        Renders a table cell containing data for the given instance
        """
        context = self.get_cell_context_data(instance, parent_context)
        return render_to_string(self.cell_template_name, context)

    def get_cell(self, instance):
        """
        Return an object encapsulating this column and an item of data, which we can use for
        rendering a table cell into a template
        """
        return Column.Cell(self, instance)

    def __repr__(self):
        return "<%s.%s: %s>" % (self.__class__.__module__, self.__class__.__qualname__, self.name)


class TitleColumn(Column):
    """A column where data is styled as a title and wrapped in a link"""
    cell_template_name = "wagtailadmin/tables/title_cell.html"

    def __init__(self, name, url_name=None, **kwargs):
        super().__init__(name, **kwargs)
        self.url_name = url_name

    def get_cell_context_data(self, instance, parent_context):
        context = super().get_cell_context_data(instance, parent_context)
        context['link_url'] = self.get_link_url(instance, parent_context)
        return context

    def get_link_url(self, instance, parent_context):
        return reverse(self.url_name, args=(instance.pk,))


class StatusFlagColumn(Column):
    """Represents a boolean value as a status tag (or lack thereof, if the corresponding label is None)"""
    cell_template_name = "wagtailadmin/tables/status_flag_cell.html"

    def __init__(self, name, true_label=None, false_label=None, **kwargs):
        super().__init__(name, **kwargs)
        self.true_label = true_label
        self.false_label = false_label


class Table(Component):
    template_name = "wagtailadmin/tables/table.html"
    classname = 'listing'

    def __init__(self, columns, data, template_name=None):
        self.columns = OrderedDict([
            (column.name, column)
            for column in columns
        ])
        self.data = data
        if template_name:
            self.template_name = template_name

    def get_context_data(self, parent_context):
        context = super().get_context_data(parent_context)
        context['table'] = self
        return context

    @property
    def rows(self):
        for instance in self.data:
            yield Table.Row(self.columns, instance)

    class Row(Mapping):
        # behaves as an OrderedDict whose items are the rendered results of
        # the corresponding column's format_cell method applied to the instance
        def __init__(self, columns, instance):
            self.columns = columns
            self.instance = instance

        def __len__(self):
            return len(self.columns)

        def __getitem__(self, key):
            return self.columns[key].get_cell(self.instance)

        def __iter__(self):
            for name in self.columns:
                yield name

        def __repr__(self):
            return repr([col.get_cell(self.instance) for col in self.columns.values()])
