import functools
from typing import List
from django.contrib.auth.models import User

from tsetmc.client import Ticker
from utilities.email import EmailNotifier
from utilities.datetime import now


class Analysis:
    username = NotImplemented
    email = None

    @classmethod
    def run(cls, stocks: List[str], task) -> dict[str, bool]:
        conditions = dict()
        for stock in stocks:
            ticker = Ticker(symbol=stock)
            results = cls.analyze(ticker)
            condition = cls.conditioning(results)
            conditions[stock] = condition

        valid_stocks = [stock for stock, condition in conditions.items() if condition]
        if valid_stocks:
            cls.notification(", ".join(valid_stocks), task)

        return conditions

    @classmethod
    def analyze(cls, ticker: Ticker):
        raise NotImplemented

    @classmethod
    def conditioning(cls, analysis_results) -> bool:
        raise NotImplemented

    @classmethod
    def notification(cls, stocks: str, task):
        if cls.email is None:
            cls.email = cls.get_email()

        subject = f'Task [{task.task[task.task.rfind(".") + 1:]}] results from Stocker!'
        text = """Hello there. Your task result is up.
        Name: {name}
        Task: {task}
        Stock: {stock}
        Description:
        {description}
        Date-Time: {datetime}

        Cheers!""".format(
            name=task.name,
            task=task.task,
            stock=stocks,
            description="\n".join(map(lambda x: f'\t{x}', task.description.split('\n'))),
            datetime=now().strftime('%Y-%M-%d %H:%M')
        )
        html = """<html>
            <body>
                <p>
                    {text}
                </p>
            </body>
        </html>
        """.format(text=text.replace('\n', '<br>\n'))
        EmailNotifier.sendmail(cls.email, subject, text, html)

    @classmethod
    def get_email(cls):
        if cls.email is not None:
            return cls.email

        user = User.objects.filter(username=cls.username).first()
        if user is None:
            print('user not found')
            return

        if not user.email:
            print('user email not set')
            return

        cls.email = user.email
        return user.email


def metadata_wrapper(subclass):
    def decorator(func):
        @functools.wraps(func)
        def wrap(*args, **kwargs):
            func(*args, **kwargs)

        wrap.metadata = subclass
        return wrap

    return decorator
