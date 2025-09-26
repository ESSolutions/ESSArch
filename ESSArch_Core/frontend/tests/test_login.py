from time import sleep

from django.contrib.auth import get_user_model
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from ESSArch_Core.frontend.tests import FrontendTestCase

User = get_user_model()


class LoginTests(FrontendTestCase):
    def setUp(self):
        User.objects.create_user(username='user', password='pass')

    def test_login(self):
        max_attempts = 5
        for _ in range(max_attempts):
            try:
                self.selenium.get('%s' % (self.live_server_url))

                # Wait for the username field to appear
                WebDriverWait(self.selenium, 15).until(
                    EC.presence_of_element_located((By.NAME, "username"))
                )

                # login
                username_input = self.selenium.find_element(By.NAME, "username")
                username_input.send_keys('user')
                password_input = self.selenium.find_element(By.NAME, "password")
                password_input.send_keys('pass')

                old_url = self.selenium.current_url
                self.selenium.find_element("xpath", '//button[@type="submit"]').click()
                WebDriverWait(self.selenium, 15).until(EC.title_is('Info | ESSArch'))
                break  # Exit the loop if successful
            except TimeoutException:
                self.selenium.delete_all_cookies()
                sleep(1)
                continue  # Retry if a timeout occurs

        self.assertTrue(EC.url_changes(old_url))

        # logout
        old_url = self.selenium.current_url
        self.selenium.find_element("class name", 'dropdown-toggle').click()
        self.selenium.find_element("xpath", '//*[contains(text(), "Logout")]').click()
        WebDriverWait(self.selenium, 15).until(EC.title_is('Login | ESSArch'))
        self.assertTrue(EC.url_changes(old_url))
