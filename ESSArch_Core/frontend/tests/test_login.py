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
        print('test_login - login', flush=True)
        username_input = self.selenium.find_element_by_name("username")
        print('test_login - send user', flush=True)
        username_input.send_keys('user')
        password_input = self.selenium.find_element_by_name("password")
        print('test_login - send pass', flush=True)
        password_input.send_keys('pass')

        old_url = self.selenium.current_url
        print('test_login - before click', flush=True)
        self.selenium.find_element_by_xpath('//button[@type="submit"]').click()
        print('test_login - after click', flush=True)
        WebDriverWait(self.selenium, 10).until(EC.title_is('Info | ESSArch'))
        self.assertTrue(EC.url_changes(old_url))

        # logout
        print('test_login - logout', flush=True)
        old_url = self.selenium.current_url
        self.selenium.find_element_by_class_name('dropdown-toggle').click()
        self.selenium.find_element_by_xpath('//*[contains(text(), "Logout")]').click()
        WebDriverWait(self.selenium, 10).until(EC.title_is('Login | ESSArch'))
        self.assertTrue(EC.url_changes(old_url))
