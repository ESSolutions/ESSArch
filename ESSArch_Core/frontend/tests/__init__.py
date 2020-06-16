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
            cls.selenium = WebDriver(options=options)
        except TimeoutException as e:
            print('FrontendTestCase - setUpClass - TimeoutException - error: %s' % e, flush=True)
            print('FrontendTestCase - sleep 15', flush=True)
            time.sleep(15)
            try:
                print('FrontendTestCase - setUpClass - WebDriver', flush=True)
                cls.selenium = WebDriver(options=options)
            except TimeoutException as e:
                print('FrontendTestCase - setUpClass - TimeoutException - error: %s' % e, flush=True)
                print('FrontendTestCase - sleep 60', flush=True)
                time.sleep(60)
                print('FrontendTestCase - setUpClass - WebDriver', flush=True)
                cls.selenium = WebDriver(options=options)
        cls.selenium.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()
