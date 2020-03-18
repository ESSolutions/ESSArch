import os
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, override_settings
from django.urls import reverse

User = get_user_model()


class DocsViewTests(SimpleTestCase):
    def setUp(self):
        self.datadir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.datadir)

    def test_index(self):
        response = self.client.get(reverse('docs:index'))
        expected_url = reverse('docs:detail', kwargs={'lang': 'en', 'path': 'index.html'})
        self.assertRedirects(response, expected_url, fetch_redirect_response=False)

    def test_search(self):
        open(os.path.join(self.datadir, 'example.css'), 'a').close()
        open(os.path.join(self.datadir, 'example.js'), 'a').close()

        with override_settings(DOCS_ROOT=self.datadir):
            with self.subTest('css'):
                response = self.client.get(reverse('docs:detail', kwargs={'lang': 'en', 'path': 'example.css'}))
                self.assertEqual(response['Content-Type'], 'text/css')
                response.close()

            with self.subTest('js'):
                response = self.client.get(reverse('docs:detail', kwargs={'lang': 'en', 'path': 'example.js'}))
                self.assertEqual(response['Content-Type'], 'application/javascript')
                response.close()
