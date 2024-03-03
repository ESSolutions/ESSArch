from django.contrib.auth import get_user_model
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from ESSArch_Core.frontend.tests import FrontendTestCase

User = get_user_model()


class LoginTests(FrontendTestCase):
    def setUp(self):
        User.objects.create_user(username='user', password='pass')

    def test_login(self):
        self.selenium.get('%s' % (self.live_server_url))

        # login
        username_input = self.selenium.find_element("name", "username")
        username_input.send_keys('user')
        password_input = self.selenium.find_element("name", "password")
        password_input.send_keys('pass')

        old_url = self.selenium.current_url
        self.selenium.find_element("xpath", '//button[@type="submit"]').click()
        WebDriverWait(self.selenium, 25).until(EC.title_is('Info | ESSArch'))
        self.assertTrue(EC.url_changes(old_url))

        # logout
        old_url = self.selenium.current_url
        self.selenium.find_element("class name", 'dropdown-toggle').click()
        self.selenium.find_element("xpath", '//*[contains(text(), "Logout")]').click()
        WebDriverWait(self.selenium, 25).until(EC.title_is('Login | ESSArch'))
        self.assertTrue(EC.url_changes(old_url))
