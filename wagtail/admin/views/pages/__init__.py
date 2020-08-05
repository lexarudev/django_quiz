from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _

from wagtail.admin import messages
from wagtail.admin.auth import user_has_any_page_permission, user_passes_test
from wagtail.admin.filters import PageHistoryReportFilterSet
from wagtail.admin.views.pages.utils import get_valid_next_url_from_request
from wagtail.admin.views.reports import ReportView
from wagtail.core import hooks
from wagtail.core.models import (
    Page, PageLogEntry, PageRevision, TaskState, UserPagePermissionsProxy, WorkflowState)

from wagtail.admin.views.pages.copy import *  # noqa
from wagtail.admin.views.pages.create import *  # noqa
from wagtail.admin.views.pages.edit import *  # noqa
from wagtail.admin.views.pages.listing import *  # noqa
from wagtail.admin.views.pages.lock import *  # noqa
from wagtail.admin.views.pages.moderation import *  # noqa
from wagtail.admin.views.pages.move import *  # noqa
from wagtail.admin.views.pages.preview import *  # noqa
from wagtail.admin.views.pages.revisions import *  # noqa
from wagtail.admin.views.pages.search import *  # noqa
from wagtail.admin.views.pages.workflow import *  # noqa


def content_type_use(request, content_type_app_name, content_type_model_name):
    try:
        content_type = ContentType.objects.get_by_natural_key(content_type_app_name, content_type_model_name)
    except ContentType.DoesNotExist:
        raise Http404

    page_class = content_type.model_class()

    # page_class must be a Page type and not some other random model
    if not issubclass(page_class, Page):
        raise Http404

    pages = page_class.objects.all()

    paginator = Paginator(pages, per_page=10)
    pages = paginator.get_page(request.GET.get('p'))

    return TemplateResponse(request, 'wagtailadmin/pages/content_type_use.html', {
        'pages': pages,
        'app_name': content_type_app_name,
        'content_type': content_type,
        'page_class': page_class,
    })


def delete(request, page_id):
    page = get_object_or_404(Page, id=page_id).specific
    if not page.permissions_for_user(request.user).can_delete():
        raise PermissionDenied

    with transaction.atomic():
        for fn in hooks.get_hooks('before_delete_page'):
            result = fn(request, page)
            if hasattr(result, 'status_code'):
                return result

        next_url = get_valid_next_url_from_request(request)

        if request.method == 'POST':
            parent_id = page.get_parent().id
            page.delete(user=request.user)

            messages.success(request, _("Page '{0}' deleted.").format(page.get_admin_display_title()))

            for fn in hooks.get_hooks('after_delete_page'):
                result = fn(request, page)
                if hasattr(result, 'status_code'):
                    return result

            if next_url:
                return redirect(next_url)
            return redirect('wagtailadmin_explore', parent_id)

    return TemplateResponse(request, 'wagtailadmin/pages/confirm_delete.html', {
        'page': page,
        'descendant_count': page.get_descendant_count(),
        'next': next_url,
    })


def unpublish(request, page_id):
    page = get_object_or_404(Page, id=page_id).specific

    user_perms = UserPagePermissionsProxy(request.user)
    if not user_perms.for_page(page).can_unpublish():
        raise PermissionDenied

    next_url = get_valid_next_url_from_request(request)

    if request.method == 'POST':
        include_descendants = request.POST.get("include_descendants", False)

        for fn in hooks.get_hooks('before_unpublish_page'):
            result = fn(request, page)
            if hasattr(result, 'status_code'):
                return result

        page.unpublish(user=request.user)

        if include_descendants:
            live_descendant_pages = page.get_descendants().live().specific()
            for live_descendant_page in live_descendant_pages:
                if user_perms.for_page(live_descendant_page).can_unpublish():
                    live_descendant_page.unpublish()

        for fn in hooks.get_hooks('after_unpublish_page'):
            result = fn(request, page)
            if hasattr(result, 'status_code'):
                return result

        messages.success(request, _("Page '{0}' unpublished.").format(page.get_admin_display_title()), buttons=[
            messages.button(reverse('wagtailadmin_pages:edit', args=(page.id,)), _('Edit'))
        ])

        if next_url:
            return redirect(next_url)
        return redirect('wagtailadmin_explore', page.get_parent().id)

    return TemplateResponse(request, 'wagtailadmin/pages/confirm_unpublish.html', {
        'page': page,
        'next': next_url,
        'live_descendant_count': page.get_descendants().live().count(),
    })


def set_page_position(request, page_to_move_id):
    page_to_move = get_object_or_404(Page, id=page_to_move_id)
    parent_page = page_to_move.get_parent()

    if not parent_page.permissions_for_user(request.user).can_reorder_children():
        raise PermissionDenied

    if request.method == 'POST':
        # Get position parameter
        position = request.GET.get('position', None)

        # Find page thats already in this position
        position_page = None
        if position is not None:
            try:
                position_page = parent_page.get_children()[int(position)]
            except IndexError:
                pass  # No page in this position

        # Move page

        # any invalid moves *should* be caught by the permission check above,
        # so don't bother to catch InvalidMoveToDescendant

        if position_page:
            # If the page has been moved to the right, insert it to the
            # right. If left, then left.
            old_position = list(parent_page.get_children()).index(page_to_move)
            if int(position) < old_position:
                page_to_move.move(position_page, pos='left')
            elif int(position) > old_position:
                page_to_move.move(position_page, pos='right')
        else:
            # Move page to end
            page_to_move.move(parent_page, pos='last-child')

    return HttpResponse('')


def workflow_history(request, page_id):
    page = get_object_or_404(Page, id=page_id)

    user_perms = UserPagePermissionsProxy(request.user)
    if not user_perms.for_page(page).can_edit():
        raise PermissionDenied

    workflow_states = WorkflowState.objects.filter(page=page).order_by('-created_at')

    paginator = Paginator(workflow_states, per_page=20)
    workflow_states = paginator.get_page(request.GET.get('p'))

    return TemplateResponse(request, 'wagtailadmin/pages/workflow_history/index.html', {
        'page': page,
        'workflow_states': workflow_states,
    })


def workflow_history_detail(request, page_id, workflow_state_id):
    page = get_object_or_404(Page, id=page_id)

    user_perms = UserPagePermissionsProxy(request.user)
    if not user_perms.for_page(page).can_edit():
        raise PermissionDenied

    workflow_state = get_object_or_404(WorkflowState, page=page, id=workflow_state_id)

    # Get QuerySet of all revisions that have existed during this workflow state
    # It's possible that the page is edited while the workflow is running, so some
    # tasks may be repeated. All tasks that have been completed no matter what
    # revision needs to be displayed on this page.
    page_revisions = PageRevision.objects.filter(
        page=page,
        id__in=TaskState.objects.filter(workflow_state=workflow_state).values_list('page_revision_id', flat=True)
    ).order_by('-created_at')

    # Now get QuerySet of tasks completed for each revision
    task_states_by_revision_task = [
        (page_revision, {
            task_state.task: task_state
            for task_state in TaskState.objects.filter(workflow_state=workflow_state, page_revision=page_revision)
        })
        for page_revision in page_revisions
    ]

    # Make sure task states are always in a consistent order
    # In some cases, they can be completed in a different order to what they are defined
    tasks = workflow_state.workflow.tasks.all()
    task_states_by_revision = [
        (
            page_revision,
            [
                task_states_by_task.get(task, None)
                for task in tasks
            ]
        )
        for page_revision, task_states_by_task in task_states_by_revision_task
    ]

    # Generate timeline
    completed_task_states = TaskState.objects.filter(
        workflow_state=workflow_state
    ).exclude(
        finished_at__isnull=True
    ).exclude(
        status=TaskState.STATUS_CANCELLED
    )

    timeline = [
        {
            'time': workflow_state.created_at,
            'action': 'workflow_started',
            'workflow_state': workflow_state,
        }
    ]

    if workflow_state.status not in (WorkflowState.STATUS_IN_PROGRESS, WorkflowState.STATUS_NEEDS_CHANGES):
        last_task = completed_task_states.order_by('finished_at').last()
        if last_task:
            timeline.append({
                'time': last_task.finished_at + timedelta(milliseconds=1),
                'action': 'workflow_completed',
                'workflow_state': workflow_state,
            })

    for page_revision in page_revisions:
        timeline.append({
            'time': page_revision.created_at,
            'action': 'page_edited',
            'revision': page_revision,
        })

    for task_state in completed_task_states:
        timeline.append({
            'time': task_state.finished_at,
            'action': 'task_completed',
            'task_state': task_state,
        })

    timeline.sort(key=lambda t: t['time'])
    timeline.reverse()

    return TemplateResponse(request, 'wagtailadmin/pages/workflow_history/detail.html', {
        'page': page,
        'workflow_state': workflow_state,
        'tasks': tasks,
        'task_states_by_revision': task_states_by_revision,
        'timeline': timeline,
    })


class PageHistoryView(ReportView):
    template_name = 'wagtailadmin/pages/history.html'
    title = _('Page history')
    header_icon = 'history'
    paginate_by = 20
    filterset_class = PageHistoryReportFilterSet

    @method_decorator(user_passes_test(user_has_any_page_permission))
    def dispatch(self, request, *args, **kwargs):
        self.page = get_object_or_404(Page, id=kwargs.pop('page_id')).specific

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, object_list=None, **kwargs):
        context = super().get_context_data(*args, object_list=object_list, **kwargs)
        context['page'] = self.page
        context['subtitle'] = self.page.get_admin_display_title()

        return context

    def get_queryset(self):
        return PageLogEntry.objects.filter(page=self.page)
