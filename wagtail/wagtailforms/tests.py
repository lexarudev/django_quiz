from django.test import TestCase
from django.core import mail

from wagtail.wagtailcore.models import Page
from wagtail.wagtailforms.models import FormSubmission


class TestFormSubmission(TestCase):
    fixtures = ['test.json']

    def test_get_form(self):
        response = self.client.get('/contact-us/')

        # Check response
        self.assertContains(response, """<label for="id_your-email">Your email</label>""")
        self.assertTemplateUsed(response, 'tests/form_page.html')
        self.assertTemplateNotUsed(response, 'tests/form_page_landing.html')

    def test_post_invalid_form(self):
        response = self.client.post('/contact-us/', {
            'your-email': 'bob', 'your-message': 'hello world'
        })

        # Check response
        self.assertContains(response, "Enter a valid email address.")
        self.assertTemplateUsed(response, 'tests/form_page.html')
        self.assertTemplateNotUsed(response, 'tests/form_page_landing.html')

    def test_post_valid_form(self):
        response = self.client.post('/contact-us/', {
            'your-email': 'bob@example.com', 'your-message': 'hello world'
        })

        # Check response
        self.assertContains(response, "Thank you for your feedback.")
        self.assertTemplateNotUsed(response, 'tests/form_page.html')
        self.assertTemplateUsed(response, 'tests/form_page_landing.html')

        # Check that an email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "The subject")
        self.assertTrue("Your message: hello world" in mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, ['to@email.com'])
        self.assertEqual(mail.outbox[0].from_email, 'from@email.com')

        # Check that form submission was saved correctly
        form_page = Page.objects.get(url_path='/home/contact-us/')
        self.assertTrue(FormSubmission.objects.filter(page=form_page, form_data__contains='hello world').exists())


class TestFormsBackend(TestCase):
    fixtures = ['test.json']

    def test_cannot_see_forms_without_permission(self):
        form_page = Page.objects.get(url_path='/home/contact-us/')

        self.client.login(username='eventeditor', password='password')
        response = self.client.get('/admin/forms/')
        self.assertFalse(form_page in response.context['form_pages'])

    def test_can_see_forms_with_permission(self):
        form_page = Page.objects.get(url_path='/home/contact-us/')

        self.client.login(username='siteeditor', password='password')
        response = self.client.get('/admin/forms/')
        self.assertTrue(form_page in response.context['form_pages'])

    def test_can_get_submissions(self):
        form_page = Page.objects.get(url_path='/home/contact-us/')

        self.client.login(username='siteeditor', password='password')

        response = self.client.get('/admin/forms/submissions/%d/' % form_page.id)
        self.assertEqual(len(response.context['data_rows']), 2)

        response = self.client.get('/admin/forms/submissions/%d/?date_from=01%%2F01%%2F2014' % form_page.id)
        self.assertEqual(len(response.context['data_rows']), 1)

        response = self.client.get('/admin/forms/submissions/%d/?date_from=01%%2F01%%2F2014&action=CSV' % form_page.id)
        data_line = response.content.split("\n")[1]
        self.assertTrue('new@example.com' in data_line)
