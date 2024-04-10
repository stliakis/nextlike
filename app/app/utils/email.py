import requests
from app.utils.logging import log

from app.core.config import settings


class EmailClient(object):
    def __init__(self):
        pass

    def send(self, to_address, subject, body):
        raise NotImplementedError


class SendGridEmailClient(object):
    TEMPLATE_VERIFY_EMAIL_AFTER_REGISTRATION = "d-316546705aa44d69824f7be23c8431ce"

    def __init__(self):
        self.sendgrid_api_key = settings.SENDGRID.api_key
        if not self.sendgrid_api_key:
            raise Exception("Missing sendgrid api key")

    def send_templated_email(self, template, to_address, from_address="info@nexly.io", data: dict = None):
        response = requests.post("https://api.sendgrid.com/v3/mail/send", headers={
            "Authorization": "Bearer {api_key}".format(api_key=self.sendgrid_api_key)
        }, json={
            "from": {
                "email": from_address
            },
            "personalizations": [
                {
                    "to": [
                        {
                            "email": to_address
                        }
                    ],
                    "dynamic_template_data": data or {}
                }
            ],
            "template_id": template
        })
        log("info", "sendgrid response: {} {}".format(response.status_code, response.content))
