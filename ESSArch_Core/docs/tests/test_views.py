from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class DocsViewTests(TestCase):
    def test_index(self):
        response = self.client.get(reverse('docs:index'))
        expected_url = reverse('docs:detail', kwargs={'lang': 'en', 'path': 'index.html'})
        self.assertRedirects(response, expected_url, fetch_redirect_response=False)
