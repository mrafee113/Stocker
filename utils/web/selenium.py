import os
import functools
import validators

from typing import Union
from django.conf import settings
from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.common import exceptions as sexceptions
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.webdriver import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec


@functools.lru_cache(maxsize=100)
def get_driver_path() -> str:
    from webdriver_manager.core.constants import DEFAULT_USER_HOME_CACHE_PATH
    from webdriver_manager.core.utils import os_type

    root_dir = DEFAULT_USER_HOME_CACHE_PATH
    driver_name = 'geckodriver'
    os_type = os_type()

    from webdriver_manager.core.download_manager import WDMHttpClient
    latest_release_url = settings.GECKO_DRIVER_LATEST_RELEASE_URL
    auth_headers = None  # todo: github token needed.
    response = WDMHttpClient().get(url=latest_release_url, headers=auth_headers)
    version = response.json()['tag_name']
    return os.path.join(root_dir, 'drivers', driver_name, os_type, version, driver_name)


def web_driver(headless=True, data_dir=True, download_dir=True) -> WebDriver:
    driver_path = get_driver_path()
    if not os.path.isfile(driver_path):
        GeckoDriverManager().install()

    options = Options()
    options.headless = headless

    if data_dir:
        options.set_preference("browser.cache.disk.parent_directory", settings.FIREFOX_USER_DATA_DIR)

    if download_dir:
        options.set_preference("browser.download.folderList", 2)
        options.set_preference("browser.download.manager.showWhenStarting", False)
        options.set_preference("browser.download.dir", str(settings.FIREFOX_DOWNLOAD_DIR))
        options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/x-gzip")

    service = Service(executable_path=driver_path)
    driver = Firefox(service=service, options=options)
    driver.set_window_rect(311, 142, 1550, 797)
    return driver


def handler_decorator(func):
    """This only works for @classmethod"""

    @functools.wraps(func)
    def wrapper_handler(cls, el: Union[WebElement, WebDriver, None], repetitive: Union[bool, int] = 3,
                        raise_exception=False, **kwargs):
        if repetitive is False:
            repetitive = 1

        counter = 0
        response = None
        while counter < repetitive:
            response = func(cls, el, **kwargs)
            if response is not None:
                break

            counter += 1

        if raise_exception and (response is None or response is False):
            raise Exception("Operation Failed.")
        return response

    return wrapper_handler


class DriverHandler:
    """When a method is called, arguments from
    "handler_decorator.wrapper_handler" should be
    taken into account. Specially positional arguments.
    """

    @classmethod
    @handler_decorator
    def get_element(cls, el: Union[WebElement, WebDriver], xpath: str, many=False) \
            -> Union[WebElement, None, list[WebElement]]:
        try:
            if many:
                return el.find_elements(By.XPATH, xpath)
            return el.find_element(By.XPATH, xpath)
        except Exception:  # noqa
            pass

    @classmethod
    @handler_decorator
    def get_attr(cls, el: Union[WebElement, WebDriver, None], attr: str, prop=False) \
            -> Union[str, None]:
        try:
            if prop:
                return getattr(el, attr)
            else:
                return el.get_attribute(attr)
        except Exception:  # noqa
            pass

    @classmethod
    @handler_decorator
    def call_attr(cls, el: Union[WebElement, WebDriver, None], attr: str, **kwargs) -> bool:
        try:
            getattr(el, attr)(**kwargs)
            return True
        except Exception:  # noqa
            return False

    @classmethod
    @handler_decorator
    def get_url(cls, driver: WebDriver, url: str):
        if validators.url(url):
            try:
                if driver.current_url == url:
                    return True

                driver.get(url)
                return True
            except Exception:
                return
        else:
            raise ValueError(f'not a valid url... url={url}')

    @classmethod
    def validate(cls, value, none=True, tipe=None, value_exc=None, validation=None) -> bool:
        success = dict()

        if none and value is not None:
            success['none'] = True
        elif none and value is None:
            success['none'] = False

        if tipe is not None and isinstance(value, tipe):
            success['tipe'] = True
        elif tipe is not None:
            success['tipe'] = False

        if value_exc is not None and value == value_exc:
            success['value_exc'] = False
        elif value_exc is not None and value != value_exc:
            success['value_exc'] = True

        try:
            if validation is not None and validation(value) is True:
                success['validation'] = True
            elif validation is not None and validation(value) is not True:
                success['validation'] = False
        except Exception:
            success['validation'] = False

        end_success = True
        if none:
            end_success &= success['none']

        for k in ['tipe', 'value_exc', 'validation']:
            if locals()[k] is not None:
                end_success &= success[k]

        return end_success

    @classmethod
    def add_validated(cls, store: dict, key: str, value, post=None,
                      none=True, tipe=None, value_exc=None, validation=None) -> bool:
        validated = cls.validate(value, none=none, tipe=tipe, value_exc=value_exc, validation=validation)
        if validated:
            if post is not None:
                value = post(value)
            store[key] = value

        return validated

    @classmethod
    def wait_until(cls, driver: WebDriver, timeout: int, xpath: str):
        try:
            WebDriverWait(driver, timeout).until(ec.presence_of_element_located((By.XPATH, xpath)))
            return True
        except sexceptions.TimeoutException:
            return False

# todo: create timer decorator
# todo: add logging
# todo: add testing... maybe? maybe not?
