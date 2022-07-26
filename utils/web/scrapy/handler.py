import functools
import urllib.parse
from functools import partial
from typing import Union

import termcolor
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement


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


class ScrapyHandler:
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
    def extract_from_list(cls, value: list, raise_exception=False):
        valid = True
        reason = str()
        if isinstance(value, list):
            if len(value) < 1:
                valid = False
                reason = 'iterable has length < 1'
            elif len(value) > 1:
                valid = False
                reason = 'iterable has length > 1'
                print(termcolor.colored(f'SelectorList had more than one element. invalidated. {value}'))
            else:
                value = value[0]
        else:
            valid = False
            reason = f'type of value was not of type list. type(value)={type(value)}'

        if not valid:
            if raise_exception:
                raise TypeError(f'invalidated. reason="{reason}" value={value}')
            else:
                return None
        return value

    @classmethod
    def validate(cls, value, none=True, tipe=None, value_exc=None, validation=None, post=None):
        from utils.web.selenium import DriverHandler
        valid = DriverHandler.validate(value, none=none, tipe=tipe, value_exc=value_exc, validation=validation)
        if valid:
            if post is not None:
                value = post(value)
            return value

        return None

    @classmethod
    def pvalidate(cls, none=True, tipe=None, value_exc=None, validation=None, post=None):
        kw = {"none": none, 'tipe': tipe, "value_exc": value_exc, "validation": validation, "post": post}
        kw = {k: v for k, v in kw.items() if v is not None}
        if kw:
            return partial(cls.validate, **kw)

    @classmethod
    def add_validated(cls, store: dict, key: str, value, post=None,
                      none=True, tipe=None, value_exc=None, validation=None) -> bool:
        from utils.web.selenium import DriverHandler
        return DriverHandler.add_validated(store, key, value, post=post, none=none, tipe=tipe, value_exc=value_exc,
                                           validation=validation)

    @classmethod
    def urlify(cls, scheme=str(), netloc=str(), path=str(), params=str(), query=str(), fragment=str()) -> str:
        return urllib.parse.urlunparse((scheme, netloc, path, params, query, fragment))
