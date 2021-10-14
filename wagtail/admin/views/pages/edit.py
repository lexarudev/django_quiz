import json

from urllib.parse import quote

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models import Prefetch, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.views.generic.base import ContextMixin, TemplateResponseMixin, View

from wagtail.admin import messages
from wagtail.admin.action_menu import PageActionMenu
from wagtail.admin.mail import send_notification
from wagtail.admin.views.generic import HookResponseMixin
from wagtail.admin.views.pages.utils import get_valid_next_url_from_request
from wagtail.core.exceptions import PageClassNotFoundError
from wagtail.core.models import (
    COMMENTS_RELATION_NAME, Comment, CommentReply, Page, PageSubscription, UserPagePermissionsProxy,
    WorkflowState)


class EditView(TemplateResponseMixin, ContextMixin, HookResponseMixin, View):
    def get_template_names(self):
        if self.page.alias_of_id:
            return ['wagtailadmin/pages/edit_alias.html']

        else:
            return ['wagtailadmin/pages/edit.html']

    def add_legacy_moderation_warning(self):
        # Check for revisions still undergoing moderation and warn - this is for the old moderation system
        if self.latest_revision and self.latest_revision.submitted_for_moderation:
            buttons = []

            if self.page.live:
                buttons.append(self.get_compare_with_live_message_button())

            messages.warning(self.request, _("This page is currently awaiting moderation"), buttons=buttons)

    def add_save_confirmation_message(self):
        if self.is_reverting:
            message = _(
                "Page '{0}' has been replaced with version from {1}."
            ).format(
                self.page.get_admin_display_title(),
                self.previous_revision.created_at.strftime("%d %b %Y %H:%M")
            )
        else:
            message = _(
                "Page '{0}' has been updated."
            ).format(
                self.page.get_admin_display_title()
            )

        messages.success(self.request, message)

    def get_commenting_changes(self):
        """
        Finds comments that have been changed during this request.

        Returns a tuple of 5 lists:
         - New comments
         - Deleted comments
         - Resolved comments
         - Edited comments
         - Replied comments (dict containing the instance and list of replies)
        """
        # Get changes
        comments_formset = self.form.formsets['comments']
        new_comments = comments_formset.new_objects
        deleted_comments = comments_formset.deleted_objects

        # Assume any changed comments that are resolved were only just resolved
        resolved_comments = []
        edited_comments = []
        for changed_comment, changed_fields in comments_formset.changed_objects:
            if changed_comment.resolved_at and 'resolved' in changed_fields:
                resolved_comments.append(changed_comment)

            if 'text' in changed_fields:
                edited_comments.append(changed_comment)

        new_replies = []
        deleted_replies = []
        edited_replies = []
        for comment_form in comments_formset.forms:
            # New
            replies = getattr(comment_form.formsets['replies'], 'new_objects', [])
            if replies:
                new_replies.append((comment_form.instance, replies))

            # Deleted
            replies = getattr(comment_form.formsets['replies'], 'deleted_objects', [])
            if replies:
                deleted_replies.append((comment_form.instance, replies))

            # Edited
            replies = getattr(comment_form.formsets['replies'], 'changed_objects', [])
            replies = [reply for reply, changed_fields in replies if 'text' in changed_fields]
            if replies:
                edited_replies.append((comment_form.instance, replies))

        return {
            'new_comments': new_comments,
            'deleted_comments': deleted_comments,
            'resolved_comments': resolved_comments,
            'edited_comments': edited_comments,
            'new_replies': new_replies,
            'deleted_replies': deleted_replies,
            'edited_replies': edited_replies,
        }

    def send_commenting_notifications(self, changes):
        """
        Sends notifications about any changes to comments to anyone who is subscribed.
        """
        relevant_comment_ids = []
        relevant_comment_ids.extend(comment.pk for comment in changes['resolved_comments'])
        relevant_comment_ids.extend(comment.pk for comment, replies in changes['new_replies'])

        # Skip if no changes were made
        # Note: We don't email about edited comments so ignore those here
        if (not changes['new_comments']
                and not changes['deleted_comments']
                and not changes['resolved_comments']
                and not changes['new_replies']):
            return

        # Get global page comment subscribers
        subscribers = PageSubscription.objects.filter(page=self.page, comment_notifications=True).select_related('user')
        global_recipient_users = [subscriber.user for subscriber in subscribers if subscriber.user != self.request.user]

        # Get subscribers to individual threads
        replies = CommentReply.objects.filter(comment_id__in=relevant_comment_ids)
        comments = Comment.objects.filter(id__in=relevant_comment_ids)
        thread_users = get_user_model().objects.exclude(pk=self.request.user.pk).exclude(pk__in=subscribers.values_list('user_id', flat=True)).prefetch_related(
            Prefetch('comment_replies', queryset=replies),
            Prefetch(COMMENTS_RELATION_NAME, queryset=comments)
        ).exclude(
            Q(comment_replies__isnull=True) & Q(**{('%s__isnull' % COMMENTS_RELATION_NAME): True})
        )

        # Skip if no recipients
        if not (global_recipient_users or thread_users):
            return
        thread_users = [(user, set(list(user.comment_replies.values_list('comment_id', flat=True)) + list(getattr(user, COMMENTS_RELATION_NAME).values_list('pk', flat=True)))) for user in thread_users]
        mailed_users = set()

        for current_user, current_threads in thread_users:
            # We are trying to avoid calling send_notification for each user for performance reasons
            # so group the users receiving the same thread notifications together here
            if current_user in mailed_users:
                continue
            users = [current_user]
            mailed_users.add(current_user)
            for user, threads in thread_users:
                if user not in mailed_users and threads == current_threads:
                    users.append(user)
                    mailed_users.add(user)
            send_notification(users, 'updated_comments', {
                'page': self.page,
                'editor': self.request.user,
                'new_comments': [comment for comment in changes['new_comments'] if comment.pk in threads],
                'resolved_comments': [comment for comment in changes['resolved_comments'] if comment.pk in threads],
                'deleted_comments': [],
                'replied_comments': [
                    {
                        'comment': comment,
                        'replies': replies,
                    }
                    for comment, replies in changes['new_replies']
                    if comment.pk in threads
                ]
            })

        return send_notification(global_recipient_users, 'updated_comments', {
            'page': self.page,
            'editor': self.request.user,
            'new_comments': changes['new_comments'],
            'resolved_comments': changes['resolved_comments'],
            'deleted_comments': changes['deleted_comments'],
            'replied_comments': [
                {
                    'comment': comment,
                    'replies': replies,
                }
                for comment, replies in changes['new_replies']
            ]
        })

    def log_commenting_changes(self, changes, revision):
        """
        Generates log entries for any changes made to comments or replies.
        """
        for comment in changes['new_comments']:
            comment.log_create(
                page_revision=revision,
                user=self.request.user
            )

        for comment in changes['edited_comments']:
            comment.log_edit(
                page_revision=revision,
                user=self.request.user
            )

        for comment in changes['resolved_comments']:
            comment.log_resolve(
                page_revision=revision,
                user=self.request.user
            )

        for comment in changes['deleted_comments']:
            comment.log_delete(
                page_revision=revision,
                user=self.request.user
            )

        for comment, replies in changes['new_replies']:
            for reply in replies:
                reply.log_create(
                    page_revision=revision,
                    user=self.request.user
                )

        for comment, replies in changes['edited_replies']:
            for reply in replies:
                reply.log_edit(
                    page_revision=revision,
                    user=self.request.user
                )

        for comment, replies in changes['deleted_replies']:
            for reply in replies:
                reply.log_delete(
                    page_revision=revision,
                    user=self.request.user
                )

    def get_edit_message_button(self):
        return messages.button(
            reverse('wagtailadmin_pages:edit', args=(self.page.id,)),
            _('Edit')
        )

    def get_view_draft_message_button(self):
        return messages.button(
            reverse('wagtailadmin_pages:view_draft', args=(self.page.id,)),
            _('View draft'),
            new_window=False
        )

    def get_view_live_message_button(self):
        return messages.button(self.page.url, _('View live'), new_window=False)

    def get_compare_with_live_message_button(self):
        return messages.button(
            reverse('wagtailadmin_pages:revisions_compare', args=(self.page.id, 'live', self.latest_revision.id)),
            _('Compare with live version')
        )

    def get_page_for_status(self):
        if self.page.live and self.page.has_unpublished_changes:
            # Page status needs to present the version of the page containing the correct live URL
            return self.real_page_record.specific
        else:
            return self.page

    def dispatch(self, request, page_id):
        self.real_page_record = get_object_or_404(Page, id=page_id)
        self.latest_revision = self.real_page_record.get_latest_revision()
        self.page_content_type = self.real_page_record.cached_content_type
        self.page_class = self.real_page_record.specific_class

        if self.page_class is None:
            raise PageClassNotFoundError(
                f"The page '{self.real_page_record}' cannot be edited because the "
                f"model class used to create it ({self.page_content_type.app_label}."
                f"{self.page_content_type.model}) can no longer be found in the codebase. "
                "This usually happens as a result of switching between git "
                "branches without running migrations to trigger the removal of "
                "unused ContentTypes. To edit the page, you will need to switch "
                "back to a branch where the model class is still present."
            )

        self.page = self.real_page_record.get_latest_revision_as_page()
        self.parent = self.page.get_parent()

        self.page_perms = self.page.permissions_for_user(self.request.user)

        if not self.page_perms.can_edit():
            raise PermissionDenied

        self.next_url = get_valid_next_url_from_request(self.request)

        response = self.run_hook('before_edit_page', self.request, self.page)
        if response:
            return response

        try:
            self.subscription = PageSubscription.objects.get(page=self.page, user=self.request.user)
        except PageSubscription.DoesNotExist:
            self.subscription = PageSubscription(page=self.page, user=self.request.user, comment_notifications=False)

        self.edit_handler = self.page_class.get_edit_handler()
        self.edit_handler = self.edit_handler.bind_to(instance=self.page, request=self.request)
        self.form_class = self.edit_handler.get_form_class()

        if getattr(settings, 'WAGTAIL_WORKFLOW_ENABLED', True):
            # Retrieve current workflow state if set, default to last workflow state
            self.workflow_state = self.page.current_workflow_state or self.page.workflow_states.order_by('created_at').last()
        else:
            self.workflow_state = None

        if self.workflow_state:
            self.workflow_tasks = self.workflow_state.all_tasks_with_status()
        else:
            self.workflow_tasks = []

        self.errors_debug = None

        return super().dispatch(request)

    def get(self, request):
        if self.page_perms.user_has_lock():
            if self.page.locked_at:
                lock_message = format_html(_("<b>Page '{}' was locked</b> by <b>you</b> on <b>{}</b>."), self.page.get_admin_display_title(), self.page.locked_at.strftime("%d %b %Y %H:%M"))
            else:
                lock_message = format_html(_("<b>Page '{}' is locked</b> by <b>you</b>."), self.page.get_admin_display_title())

            lock_message += format_html(
                '<span class="buttons"><button class="button button-small button-secondary" data-locking-action="{}">{}</button></span>',
                reverse('wagtailadmin_pages:unlock', args=(self.page.id,)),
                _("Unlock")
            )
            messages.warning(self.request, lock_message, extra_tags='lock')

        elif self.page.locked and self.page_perms.page_locked():
            # the page can also be locked at a permissions level if in a workflow, on a task the user is not a reviewer for
            # this should be indicated separately
            if self.page.locked_by and self.page.locked_at:
                lock_message = format_html(_("<b>Page '{}' was locked</b> by <b>{}</b> on <b>{}</b>."), self.page.get_admin_display_title(), str(self.page.locked_by), self.page.locked_at.strftime("%d %b %Y %H:%M"))
            else:
                # Page was probably locked with an old version of Wagtail, or a script
                lock_message = format_html(_("<b>Page '{}' is locked</b>."), self.page.get_admin_display_title())

            if self.page_perms.can_unlock():
                lock_message += format_html(
                    '<span class="buttons"><button class="button button-small button-secondary" data-locking-action="{}">{}</button></span>',
                    reverse('wagtailadmin_pages:unlock', args=(self.page.id,)),
                    _("Unlock")
                )
            messages.error(self.request, lock_message, extra_tags='lock')

        if self.page.current_workflow_state:
            workflow = self.workflow_state.workflow
            task = self.workflow_state.current_task_state.task
            if (
                self.workflow_state.status != WorkflowState.STATUS_NEEDS_CHANGES
                and task.specific.page_locked_for_user(self.page, self.request.user)
            ):
                # Check for revisions still undergoing moderation and warn
                if len(self.workflow_tasks) == 1:
                    # If only one task in workflow, show simple message
                    workflow_info = _("This page is currently awaiting moderation.")
                else:
                    workflow_info = format_html(
                        _("This page is awaiting <b>'{}'</b> in the <b>'{}'</b> workflow."),
                        task.name, workflow.name
                    )
                messages.error(
                    self.request, mark_safe(workflow_info + " " + _("Only reviewers for this task can edit the page.")),
                    extra_tags="lock"
                )

        self.form = self.form_class(instance=self.page, subscription=self.subscription, parent_page=self.parent)
        self.has_unsaved_changes = False
        self.edit_handler = self.edit_handler.bind_to(form=self.form)
        self.add_legacy_moderation_warning()
        self.page_for_status = self.get_page_for_status()

        return self.render_to_response(self.get_context_data())

    def add_cancel_workflow_confirmation_message(self):
        message = _(
            "Workflow on page '{0}' has been cancelled."
        ).format(
            self.page.get_admin_display_title()
        )

        messages.success(self.request, message, buttons=[
            self.get_view_draft_message_button(),
            self.get_edit_message_button(),
        ])

    def post(self, request):
        # Don't allow POST requests if the page is an alias
        if self.page.alias_of_id:
            # Return 405 "Method Not Allowed" response
            return HttpResponse(status=405)

        self.form = self.form_class(
            self.request.POST, self.request.FILES, instance=self.page, subscription=self.subscription, parent_page=self.parent
        )

        self.is_cancelling_workflow = bool(self.request.POST.get('action-cancel-workflow')) and self.workflow_state and self.workflow_state.user_can_cancel(self.request.user)

        if self.form.is_valid() and not self.page_perms.page_locked():
            return self.form_valid(self.form)
        else:
            return self.form_invalid(self.form)

    def workflow_action_is_valid(self):
        self.workflow_action = self.request.POST['workflow-action-name']
        available_actions = self.page.current_workflow_task.get_actions(self.page, self.request.user)
        available_action_names = [name for name, verbose_name, modal in available_actions]
        return (self.workflow_action in available_action_names)

    def form_valid(self, form):
        self.is_reverting = bool(self.request.POST.get('revision'))
        # If a revision ID was passed in the form, get that revision so its
        # date can be referenced in notification messages
        if self.is_reverting:
            self.previous_revision = get_object_or_404(self.page.revisions, id=self.request.POST.get('revision'))

        self.has_content_changes = self.form.has_changed()

        if self.request.POST.get('action-publish') and self.page_perms.can_publish():
            return self.publish_action()
        elif self.request.POST.get('action-submit') and self.page_perms.can_submit_for_moderation():
            return self.submit_action()
        elif self.request.POST.get('action-restart-workflow') and self.page_perms.can_submit_for_moderation() and self.workflow_state and self.workflow_state.user_can_cancel(self.request.user):
            return self.restart_workflow_action()
        elif self.request.POST.get('action-workflow-action') and self.workflow_action_is_valid():
            return self.perform_workflow_action()
        elif self.is_cancelling_workflow:
            return self.cancel_workflow_action()
        else:
            return self.save_action()

    def save_action(self):
        self.page = self.form.save(commit=False)
        self.subscription.save()

        # Save revision
        revision = self.page.save_revision(
            user=self.request.user,
            log_action=True,  # Always log the new revision on edit
            previous_revision=(self.previous_revision if self.is_reverting else None)
        )

        self.add_save_confirmation_message()

        if self.has_content_changes and 'comments' in self.form.formsets:
            changes = self.get_commenting_changes()
            self.log_commenting_changes(changes, revision)
            self.send_commenting_notifications(changes)

        response = self.run_hook('after_edit_page', self.request, self.page)
        if response:
            return response

        # Just saving - remain on edit page for further edits
        return self.redirect_and_remain()

    def publish_action(self):
        self.page = self.form.save(commit=False)
        self.subscription.save()

        # Save revision
        revision = self.page.save_revision(
            user=self.request.user,
            log_action=True,  # Always log the new revision on edit
            previous_revision=(self.previous_revision if self.is_reverting else None)
        )

        # store submitted go_live_at for messaging below
        go_live_at = self.page.go_live_at

        response = self.run_hook('before_publish_page', self.request, self.page)
        if response:
            return response

        revision.publish(
            user=self.request.user,
            changed=self.has_content_changes,
            previous_revision=(self.previous_revision if self.is_reverting else None)
        )

        if self.has_content_changes and 'comments' in self.form.formsets:
            changes = self.get_commenting_changes()
            self.log_commenting_changes(changes, revision)
            self.send_commenting_notifications(changes)

        # Need to reload the page because the URL may have changed, and we
        # need the up-to-date URL for the "View Live" button.
        self.page = self.page.specific_class.objects.get(pk=self.page.pk)

        response = self.run_hook('after_publish_page', self.request, self.page)
        if response:
            return response

        # Notifications
        if go_live_at and go_live_at > timezone.now():
            # Page has been scheduled for publishing in the future

            if self.is_reverting:
                message = _(
                    "Version from {0} of page '{1}' has been scheduled for publishing."
                ).format(
                    self.previous_revision.created_at.strftime("%d %b %Y %H:%M"),
                    self.page.get_admin_display_title()
                )
            else:
                if self.page.live:
                    message = _(
                        "Page '{0}' is live and this version has been scheduled for publishing."
                    ).format(
                        self.page.get_admin_display_title()
                    )

                else:
                    message = _(
                        "Page '{0}' has been scheduled for publishing."
                    ).format(
                        self.page.get_admin_display_title()
                    )

            messages.success(self.request, message, buttons=[self.get_edit_message_button()])

        else:
            # Page is being published now

            if self.is_reverting:
                message = _(
                    "Version from {0} of page '{1}' has been published."
                ).format(
                    self.previous_revision.created_at.strftime("%d %b %Y %H:%M"),
                    self.page.get_admin_display_title()
                )
            else:
                message = _(
                    "Page '{0}' has been published."
                ).format(
                    self.page.get_admin_display_title()
                )

            buttons = []
            if self.page.url is not None:
                buttons.append(self.get_view_live_message_button())
            buttons.append(self.get_edit_message_button())
            messages.success(self.request, message, buttons=buttons)

        response = self.run_hook('after_edit_page', self.request, self.page)
        if response:
            return response

        # we're done here - redirect back to the explorer
        return self.redirect_away()

    def submit_action(self):
        self.page = self.form.save(commit=False)
        self.subscription.save()

        # Save revision
        revision = self.page.save_revision(
            user=self.request.user,
            log_action=True,  # Always log the new revision on edit
            previous_revision=(self.previous_revision if self.is_reverting else None)
        )

        if self.has_content_changes and 'comments' in self.form.formsets:
            changes = self.get_commenting_changes()
            self.log_commenting_changes(changes, revision)
            self.send_commenting_notifications(changes)

        if self.workflow_state and self.workflow_state.status == WorkflowState.STATUS_NEEDS_CHANGES:
            # If the workflow was in the needs changes state, resume the existing workflow on submission
            self.workflow_state.resume(self.request.user)
        else:
            # Otherwise start a new workflow
            workflow = self.page.get_workflow()
            workflow.start(self.page, self.request.user)

        message = _(
            "Page '{0}' has been submitted for moderation."
        ).format(
            self.page.get_admin_display_title()
        )

        messages.success(self.request, message, buttons=[
            self.get_view_draft_message_button(),
            self.get_edit_message_button(),
        ])

        response = self.run_hook('after_edit_page', self.request, self.page)
        if response:
            return response

        # we're done here - redirect back to the explorer
        return self.redirect_away()

    def restart_workflow_action(self):
        self.page = self.form.save(commit=False)
        self.subscription.save()

        # save revision
        revision = self.page.save_revision(
            user=self.request.user,
            log_action=True,  # Always log the new revision on edit
            previous_revision=(self.previous_revision if self.is_reverting else None)
        )

        if self.has_content_changes and 'comments' in self.form.formsets:
            changes = self.get_commenting_changes()
            self.log_commenting_changes(changes, revision)
            self.send_commenting_notifications(changes)

        # cancel workflow
        self.workflow_state.cancel(user=self.request.user)
        # start new workflow
        workflow = self.page.get_workflow()
        workflow.start(self.page, self.request.user)

        message = _(
            "Workflow on page '{0}' has been restarted."
        ).format(
            self.page.get_admin_display_title()
        )

        messages.success(self.request, message, buttons=[
            self.get_view_draft_message_button(),
            self.get_edit_message_button(),
        ])

        response = self.run_hook('after_edit_page', self.request, self.page)
        if response:
            return response

        # we're done here - redirect back to the explorer
        return self.redirect_away()

    def perform_workflow_action(self):
        self.page = self.form.save(commit=False)
        self.subscription.save()

        if self.has_content_changes:
            # Save revision
            revision = self.page.save_revision(
                user=self.request.user,
                log_action=True,  # Always log the new revision on edit
                previous_revision=(self.previous_revision if self.is_reverting else None)
            )

            if 'comments' in self.form.formsets:
                changes = self.get_commenting_changes()
                self.log_commenting_changes(changes, revision)
                self.send_commenting_notifications(changes)

        extra_workflow_data_json = self.request.POST.get('workflow-action-extra-data', '{}')
        extra_workflow_data = json.loads(extra_workflow_data_json)
        self.page.current_workflow_task.on_action(self.page.current_workflow_task_state, self.request.user, self.workflow_action, **extra_workflow_data)

        self.add_save_confirmation_message()

        response = self.run_hook('after_edit_page', self.request, self.page)
        if response:
            return response

        # we're done here - redirect back to the explorer
        return self.redirect_away()

    def cancel_workflow_action(self):
        self.workflow_state.cancel(user=self.request.user)
        self.page = self.form.save(commit=False)
        self.subscription.save()

        # Save revision
        revision = self.page.save_revision(
            user=self.request.user,
            log_action=True,  # Always log the new revision on edit
            previous_revision=(self.previous_revision if self.is_reverting else None)
        )

        if self.has_content_changes and 'comments' in self.form.formsets:
            changes = self.get_commenting_changes()
            self.log_commenting_changes(changes, revision)
            self.send_commenting_notifications(changes)

        # Notifications
        self.add_cancel_workflow_confirmation_message()

        response = self.run_hook('after_edit_page', self.request, self.page)
        if response:
            return response

        # Just saving - remain on edit page for further edits
        return self.redirect_and_remain()

    def redirect_away(self):
        if self.next_url:
            # redirect back to 'next' url if present
            return redirect(self.next_url)
        else:
            # redirect back to the explorer
            return redirect('wagtailadmin_explore', self.page.get_parent().id)

    def redirect_and_remain(self):
        target_url = reverse('wagtailadmin_pages:edit', args=[self.page.id])
        if self.next_url:
            # Ensure the 'next' url is passed through again if present
            target_url += '?next=%s' % quote(self.next_url)
        return redirect(target_url)

    def form_invalid(self, form):
        # even if the page is locked due to not having permissions, the original submitter can still cancel the workflow
        if self.is_cancelling_workflow:
            self.workflow_state.cancel(user=self.request.user)
            self.add_cancel_workflow_confirmation_message()

        if self.page_perms.page_locked():
            messages.error(self.request, _("The page could not be saved as it is locked"))
        else:
            messages.validation_error(
                self.request, _("The page could not be saved due to validation errors"), self.form
            )
        self.errors_debug = (
            repr(self.form.errors)
            + repr([
                (name, formset.errors)
                for (name, formset) in self.form.formsets.items()
                if formset.errors
            ])
        )
        self.has_unsaved_changes = True

        self.edit_handler = self.edit_handler.bind_to(form=self.form)
        self.add_legacy_moderation_warning()
        self.page_for_status = self.get_page_for_status()

        return self.render_to_response(self.get_context_data())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page': self.page,
            'page_for_status': self.page_for_status,
            'content_type': self.page_content_type,
            'edit_handler': self.edit_handler,
            'errors_debug': self.errors_debug,
            'action_menu': PageActionMenu(self.request, view='edit', page=self.page),
            'preview_modes': self.page.preview_modes,
            'form': self.form,
            'next': self.next_url,
            'has_unsaved_changes': self.has_unsaved_changes,
            'page_locked': self.page_perms.page_locked(),
            'workflow_state': self.workflow_state if self.workflow_state and self.workflow_state.is_active else None,
            'current_task_state': self.page.current_workflow_task_state,
            'publishing_will_cancel_workflow': self.workflow_tasks and getattr(settings, 'WAGTAIL_WORKFLOW_CANCEL_ON_PUBLISH', True),
            'locale': None,
            'translations': [],
        })

        if getattr(settings, 'WAGTAIL_I18N_ENABLED', False):
            user_perms = UserPagePermissionsProxy(self.request.user)

            context.update({
                'locale': self.page.locale,
                'translations': [
                    {
                        'locale': translation.locale,
                        'url': reverse('wagtailadmin_pages:edit', args=[translation.id]),
                    }
                    for translation in self.page.get_translations().only('id', 'locale', 'depth').select_related('locale')
                    if user_perms.for_page(translation).can_edit()
                ],
            })

        return context
