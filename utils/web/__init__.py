import os
from random import randint

import requests
from django.conf import settings
from requests.adapters import HTTPAdapter
from urllib3 import Retry


def requests_retry_session(
        retries=10, backoff_factor=0.3,
        status_forcelist=(500, 502, 504, 503),
        session=None) -> requests.Session:
    session = session or requests.Session()
    retry = Retry(
        total=retries, read=retries,
        connect=retries, backoff_factor=backoff_factor,
        status_forcelist=status_forcelist
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def get_random_user_agent() -> str:
    with open(os.path.join(settings.BASE_DIR, 'user-agents.txt')) as file:
        user_agents = file.read().split('\n')

    return user_agents[randint(0, len(user_agents) - 1)]
