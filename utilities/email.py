import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from django.conf import settings


class EmailNotifier:
    @classmethod
    def sendmail(cls, receiver_mail: str, subject: str, text: str, html: str):
        sender_mail = settings.GMAIL_USERNAME
        password = settings.GMAIL_PASSWORD

        message = MIMEMultipart('alternative')
        message['Subject'] = subject
        message['FROM'] = sender_mail
        message['TO'] = receiver_mail

        message.attach(MIMEText(text, 'plain'))
        message.attach(MIMEText(html, 'html'))

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
            server.login(sender_mail, password)
            server.sendmail(sender_mail, receiver_mail, message.as_string())
