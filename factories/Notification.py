from configparser import ConfigParser

import requests
from pushbullet import Pushbullet
from pushover import init, Client
from loguru import logger

from utils.sms import SMS

config = ConfigParser()
config.read("auth.ini")


class Payload(object):
    def __init__(self, name=None, price=None, url=None, availability=None):
        self.name = name
        self.url = url
        self.price = price
        self.availability = availability
    def generate_message(self):
        return f"Name: {self.name}\n" \
                  f"Price: {self.price}\n" \
                  f"Availability: {self.availability}\n" \
                  f"URL: {self.url}"


class Notification:
    def __init__(self):
        self.title = "PRODUCT ON SALE!"

    def send(self, payload: Payload, agent: str):
        if agent == "pushbullet":
            return self._send_pushbullet(payload)
        elif agent == "pushover":
            return self._send_pushover(payload)
        elif agent == "webhook":
            return self._send_webhook(payload)
        elif agent == "sms":
            return ValueError("SMS is not implemented at this time")

    def _send_pushbullet(self, payload):
        e2e_password = config.get('Alerts', 'pushBulletEncryptionPassword', fallback=None)
        pb = Pushbullet(config.get('Alerts', 'pushBulletKey'), encryption_password=e2e_password)
        if payload.url:
            pb.push_link(title=self.title, body=payload.generate_message(), url=payload.url)
        else:
            pb.push_note(self.title, payload.generate_message())

    def _send_pushover(self, payload):
        init(config.get('Alerts', 'pushoverToken'))
        pushover = Client(config.get('Alerts', 'pushoverUserKey'))
        if payload.url:
            pushover.send_message(payload.generate_message(), title=self.title, url_title="See Product", url=payload.url)
        else:
            pushover.send_message(payload.generate_message(), title=self.title)

    def _send_webhook(self, payload):
        payload = {"name": payload.name, "price": payload.price, "url": payload.url, "availability": payload.availability}
        r = requests.post(config.get('Alerts', 'webhook'), data=payload)
        if r.status_code != 200:
            logger.error("Webhook responded with non 200 code!")

    def _send_sms(self, payload):
        phone_number = config.get('Alerts', 'smsNumber', fallback=None)
        gmail_username = config.get('APIKeys', 'gmailUsername', fallback=None)
        gmail_password = config.get('APIKeys', 'gmailUsername', fallback=None)
        if gmail_password is None or gmail_username is None:
            logger.error("Gmail username/password are not defined in auth.ini skipping SMS notification.")
        else:
            carrier = config.get('Alerts', 'smsCarrier', fallback="att")
            message = f"{self.title}\n" + payload.generate_message
            sms = SMS(gmail_username, gmail_password)
            sms.send(message=message,
                     number=phone_number,
                     carrier=carrier)

