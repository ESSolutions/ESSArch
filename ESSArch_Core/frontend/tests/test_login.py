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
        print('test_login - login')
        username_input = self.selenium.find_element_by_name("username")
        username_input.send_keys('user')
        password_input = self.selenium.find_element_by_name("password")
        password_input.send_keys('pass')

        old_url = self.selenium.current_url
        self.selenium.find_element_by_xpath('//button[@type="submit"]').click()
        WebDriverWait(self.selenium, 300).until(EC.title_is('Info | ESSArch'))
        self.assertTrue(EC.url_changes(old_url))

        # logout
        print('test_login - logout')
        old_url = self.selenium.current_url
        self.selenium.find_element_by_class_name('dropdown-toggle').click()
        self.selenium.find_element_by_xpath('//*[contains(text(), "Logout")]').click()
        WebDriverWait(self.selenium, 300).until(EC.title_is('Login | ESSArch'))
        self.assertTrue(EC.url_changes(old_url))
