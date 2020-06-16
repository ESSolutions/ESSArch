import time

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.webdriver import WebDriver


class FrontendTestCase(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        options = Options()
        options.headless = True
        try:
            print('setUpClass - WebDriver', flush=True)
            cls.selenium = WebDriver(options=options)
        except TimeoutException as e:
            print('setUpClass - TimeoutException - error: %s' % e, flush=True)
            print('sleep 60', flush=True)
            time.sleep(60)
            try:
                print('setUpClass - WebDriver', flush=True)
                cls.selenium = WebDriver(options=options)
            except TimeoutException as e:
                print('setUpClass - TimeoutException - error: %s' % e, flush=True)
                print('sleep 60', flush=True)
                time.sleep(60)
                print('setUpClass - WebDriver', flush=True)
                cls.selenium = WebDriver(options=options)

        print('setUpClass - implicitly_wait', flush=True)
        cls.selenium.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()
