import functools

from typing import Union
from playwright.sync_api._generated import Locator as SyncLocator
from playwright.async_api._generated import Locator as AsyncLocator


def handler_decorator(func):
    """This only works for @classmethod"""

    @functools.wraps(func)
    def wrapper_handler(cls, loc: Union[SyncLocator, AsyncLocator], repetitive: Union[bool, int] = 1,
                        raise_exception=False, **kwargs):
        if repetitive is False:
            repetitive = 1

        exception = None
        counter = 0
        response = None
        while counter < repetitive:
            try:
                response = func(cls, loc, **kwargs)
            except Exception as e:
                exception = e
                response = None

            if response is not None:
                break

            counter += 1

        if raise_exception and (response is None or response is False):
            raise exception if exception is not None else Exception("Operation Failed.")
        return response

    return wrapper_handler


class PWrightHandler:
    @classmethod
    def get_attr(cls, loc: Union[SyncLocator, AsyncLocator], attr: str, timeout=3000, prop=False):
        if prop:
            return getattr(loc, attr)

        if attr == 'inner_html':
            return loc.inner_html(timeout=timeout)

        match attr:
            case 'inner_html':
                return loc.inner_html(timeout=timeout)
            case 'inner_text':
                return loc.inner_text()
            case 'all_inner_texts':
                return loc.all_inner_texts()
            case 'text_content':
                return loc.text_content()
            case 'all_text_contents':
                return loc.all_text_contents()

        return loc.get_attribute(attr)
