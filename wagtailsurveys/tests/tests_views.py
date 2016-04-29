# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.core.urlresolvers import reverse
from django.test import TestCase

from wagtail.tests.utils import WagtailTestUtils
from wagtail.wagtailcore.models import Page

from wagtailsurveys.models import FormSubmission
from wagtailsurveys.tests.testapp.models import SurveyPage
from wagtailsurveys.tests.utils import make_survey_page


class TestSurveysIndex(TestCase):
    fixtures = ['test.json']

    def setUp(self):
        self.assertTrue(self.client.login(username='siteeditor', password='password'))
        self.survey_page = Page.objects.get(url_path='/home/let-us-know/')

    def make_survey_pages(self):
        """
        This makes 100 survey pages and adds them as children to 'let-us-know'
        This is used to test pagination on the survey index
        """
        for i in range(100):
            self.survey_page.add_child(instance=SurveyPage(
                title="Survey " + str(i),
                slug='survey-' + str(i),
                live=True
            ))

    def test_survey_index(self):
        response = self.client.get(reverse('wagtailsurveys:index'))

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'wagtailsurveys/index.html')

    def test_survey_index_pagination(self):
        # Create some more survey pages to make pagination kick in
        self.make_survey_pages()

        # Get page two
        response = self.client.get(reverse('wagtailsurveys:index'), {'p': 2})

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'wagtailsurveys/index.html')

        # Check that we got the correct page
        self.assertEqual(response.context['survey_pages'].number, 2)

    def test_survey_index_pagination_invalid(self):
        # Create some more survey pages to make pagination kick in
        self.make_survey_pages()

        # Get page two
        response = self.client.get(reverse('wagtailsurveys:index'), {'p': 'Hello world!'})

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'wagtailsurveys/index.html')

        # Check that it got page one
        self.assertEqual(response.context['survey_pages'].number, 1)

    def test_survey_index_pagination_out_of_range(self):
        # Create some more survey pages to make pagination kick in
        self.make_survey_pages()

        response = self.client.get(reverse('wagtailsurveys:index'), {'p': 99999})

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'wagtailsurveys/index.html')

        # Check that it got the last page
        self.assertEqual(response.context['survey_pages'].number, response.context['survey_pages'].paginator.num_pages)

    def test_cannot_see_survey_without_permission(self):
        # Login with as a user without permission to see surveys
        self.assertTrue(self.client.login(username='eventeditor', password='password'))

        response = self.client.get(reverse('wagtailsurveys:index'))

        # Check that the user cannot see the survey page
        self.assertFalse(self.survey_page in response.context['survey_pages'])

    def test_can_see_survey_with_permission(self):
        response = self.client.get(reverse('wagtailsurveys:index'))

        # Check that the user can see the survey page
        self.assertIn(self.survey_page, response.context['survey_pages'])


class TestFormsSubmissionsList(TestCase, WagtailTestUtils):
    def setUp(self):
        # Create a survey page
        self.survey_page = make_survey_page()

        # Add a couple of form submissions
        old_form_submission = FormSubmission.objects.create(
            page=self.survey_page,
            form_data=json.dumps({
                'your-name': "John",
                'your-biography': "I'm a lazy person",
            }),
        )
        old_form_submission.submit_time = '2013-01-01T12:00:00.000Z'
        old_form_submission.save()

        new_form_submission = FormSubmission.objects.create(
            page=self.survey_page,
            form_data=json.dumps({
                'your-name': "Mikalai",
                'your-biography': "You don't want to know",
            }),
        )
        new_form_submission.submit_time = '2014-01-01T12:00:00.000Z'
        new_form_submission.save()

        # Login
        self.login()

    def make_list_submissions(self):
        """
        This makes 100 submissions to test pagination on the forms submissions page
        """
        for i in range(100):
            submission = FormSubmission(
                page=self.survey_page,
                form_data=json.dumps({
                    'hello': 'world'
                })
            )
            submission.save()

    def test_list_submissions(self):
        response = self.client.get(reverse('wagtailsurveys:list_submissions', args=(self.survey_page.id,)))

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'wagtailsurveys/index_submissions.html')
        self.assertEqual(len(response.context['data_rows']), 2)

    def test_list_submissions_pagination(self):
        self.make_list_submissions()

        response = self.client.get(reverse('wagtailsurveys:list_submissions', args=(self.survey_page.id,)), {'p': 2})

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'wagtailsurveys/index_submissions.html')

        # Check that we got the correct page
        self.assertEqual(response.context['submissions'].number, 2)

    def test_list_submissions_pagination_invalid(self):
        self.make_list_submissions()

        response = self.client.get(
            reverse('wagtailsurveys:list_submissions', args=(self.survey_page.id,)), {'p': 'Hello World!'}
        )

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'wagtailsurveys/index_submissions.html')

        # Check that we got page one
        self.assertEqual(response.context['submissions'].number, 1)

    def test_list_submissions_pagination_out_of_range(self):
        self.make_list_submissions()

        response = self.client.get(
            reverse('wagtailsurveys:list_submissions', args=(self.survey_page.id,)),
            {'p': 99999}
        )

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'wagtailsurveys/index_submissions.html')

        # Check that we got the last page
        self.assertEqual(response.context['submissions'].number, response.context['submissions'].paginator.num_pages)


class TestFormsSubmissionsExport(TestCase, WagtailTestUtils):
    fixtures = ['test.json']

    def setUp(self):
        self.survey_page = Page.objects.get(url_path='/home/let-us-know/')

        self.login()

    def test_list_submissions_csv_export(self):
        response = self.client.get(
            reverse('wagtailsurveys:list_submissions', args=(self.survey_page.id,)),
            {'action': 'CSV'}
        )

        # Check response
        self.assertEqual(response.status_code, 200)
        data_lines = response.content.decode().split("\n")

        self.assertEqual(data_lines[0], 'Submission Date,Your name,Your biography,Your choices\r')
        self.assertEqual(data_lines[1], "2013-01-01 12:00:00+00:00,Mikalai,Airhead :),bar :)\r")
        self.assertEqual(data_lines[2], "2014-01-01 12:00:00+00:00,John,Genius,None\r")

    def test_list_submissions_csv_export_with_unicode(self):
        unicode_form_submission = FormSubmission.objects.create(
            page=self.survey_page,
            form_data=json.dumps({
                'your-name': "Unicode boy",
                'your-biography': 'こんにちは、世界',
            }),
        )
        unicode_form_submission.submit_time = '2014-01-02T12:00:00.000Z'
        unicode_form_submission.save()

        response = self.client.get(
            reverse('wagtailsurveys:list_submissions', args=(self.survey_page.id,)),
            {'action': 'CSV'}
        )

        # Check response
        self.assertEqual(response.status_code, 200)
        data_line = response.content.decode('utf-8').split("\n")[3]
        self.assertIn('こんにちは、世界', data_line)


class TestDeleteFormSubmission(TestCase):
    fixtures = ['test.json']

    def setUp(self):
        self.assertTrue(self.client.login(username='siteeditor', password='password'))
        self.survey_page = Page.objects.get(url_path='/home/let-us-know/')

    def test_delete_submission_show_cofirmation(self):
        response = self.client.get(reverse(
            'wagtailsurveys:delete_submission',
            args=(self.survey_page.id, FormSubmission.objects.first().id)
        ))
        # Check show confirm page when HTTP method is GET
        self.assertTemplateUsed(response, 'wagtailsurveys/confirm_delete.html')

        # Check that the deletion has not happened with GET request
        self.assertEqual(FormSubmission.objects.count(), 2)

    def test_delete_submission_with_permissions(self):
        response = self.client.post(reverse(
            'wagtailsurveys:delete_submission',
            args=(self.survey_page.id, FormSubmission.objects.first().id)
        ))

        # Check that the submission is gone
        self.assertEqual(FormSubmission.objects.count(), 1)
        # Should be redirected to list of submissions
        self.assertRedirects(response, reverse("wagtailsurveys:list_submissions", args=(self.survey_page.id,)))

    def test_delete_submission_bad_permissions(self):
        self.assertTrue(self.client.login(username="eventeditor", password="password"))

        response = self.client.post(reverse(
            'wagtailsurveys:delete_submission',
            args=(self.survey_page.id, FormSubmission.objects.first().id)
        ))

        # Check that the user recieved a 403 response
        self.assertEqual(response.status_code, 403)

        # Check that the deletion has not happened
        self.assertEqual(FormSubmission.objects.count(), 2)
