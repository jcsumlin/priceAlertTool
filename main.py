import datetime

import requests
from bestbuy import BestBuyAPI
import json
from configparser import ConfigParser
from pushover import init, Client
from loguru import logger

from utils.scraper import scrape
from utils.sms import SMS
from pushbullet import Pushbullet

config = ConfigParser()
config.read("auth.ini")
if "APIKeys" not in config.sections():
    logger.error("Missing APIKeys from auth.ini file. Exiting.")
    exit(1)

with open("./items.json") as file:
    items = json.load(file)
DAYS_BETWEEN_ALERTS = config.getint('Alerts', 'daysBetweenAlerts', fallback=1)


def update_items_file(data):
    with open("./items.json", 'w') as file:
        json.dump(data, file)


def send_alert(product_name, price, url=None, availability=None):
    message = f"Name: {product_name}\n" \
              f"Price: {price}"
    title = "PRODUCT ON SALE!"
    if availability:
        message = message + f"\nAvailability: {availability}"
    if "Alerts" not in config.sections():
        logger.info(f"{product_name} is priced at {price}")
        if url:
            logger.info(url)
        return
    if config.get('Alerts', 'pushoverToken', fallback=None) is not None and config.get('Alerts', 'pushoverUserKey', fallback=None) is not None:
        init(config.get('Alerts', 'pushoverToken'))
        pushover = Client(config.get('Alerts', 'pushoverUserKey'))
        if url:
            pushover.send_message(message, title=title, url_title="See Product", url=url)
        else:
            pushover.send_message(message, title=title)
    if config.get('Alerts', 'webhook', fallback=None) is not None:

        payload = {"name": product_name, "price": price, "url": url}
        r = requests.post(config.get('Alerts', 'webhook'), data=payload)
        if r.status_code != 200:
            logger.error("Webhook responded with non 200 code!")
    if config.get('Alerts', 'pushBulletKey', fallback=None) is not None:
        e2e_password = config.get('Alerts', 'pushBulletEncryptionPassword', fallback=None)
        pb = Pushbullet(config.get('Alerts', 'pushBulletKey'), encryption_password=e2e_password)
        if url:
            pb.push_link(title=title, body=message, url=url)
        else:
            pb.push_note(title, message)

    phone_number = config.get('Alerts', 'smsNumber', fallback=None)
    if phone_number is not None:
        gmail_username = config.get('APIKeys', 'gmailUsername', fallback=None)
        gmail_password = config.get('APIKeys', 'gmailUsername', fallback=None)
        if gmail_password is None or gmail_username is None:
            logger.error("Gmail username/password are not defined in auth.ini skipping SMS notification.")
        else:
            carrier = config.get('Alerts', 'smsCarrier', fallback="att")
            message = "ITEM ON SALE\n" + message
            if url:
                message = message + f"\nURL: {url}"
            sms = SMS(gmail_username, gmail_password)
            sms.send(message=message,
                     number=phone_number,
                     carrier=carrier)


for store in items:
    product_ids = items[store].keys()
    if store.lower() == "bestbuy":
        for sku in product_ids:
            bb = BestBuyAPI(config.get('APIKeys', 'BestBuyAPIKey'))
            product = bb.products.search_by_sku(sku=sku, format='json')
            if product['total'] >= 1:
                product_name = product['products'][0]['name']
                url = product['products'][0]['url']
                inStoreAvailability = product['products'][0]['inStoreAvailability']
                onlineAvailability = product['products'][0]['onlineAvailability']
                if product['products'][0]['onSale']:
                    price = product['products'][0]['salePrice']
                else:
                    price = product['products'][0]['regularPrice']
                if inStoreAvailability is False and onlineAvailability is False:
                    continue
                if price <= items[store][sku]['alert_price'] and 'notified_on' not in items[store][sku].keys():
                    send_alert(product_name, price, url=url)
                    items[store][sku]['notified_on'] = (datetime.datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
                    update_items_file(items)
                else:
                    if 'notified_on' in items[store][sku].keys():
                        insertion_date = datetime.datetime.strptime(items[store][sku]['notified_on'], '%Y-%m-%d %H:%M:%S')
                        time_between_insertion = datetime.datetime.now() - insertion_date
                        if time_between_insertion.days >= DAYS_BETWEEN_ALERTS:
                            del items[store][sku]['notified_on']
                            update_items_file(items)
    elif store.lower() == "amazon":
        for url in product_ids:
            product = scrape(url)
            if product is None:
                logger.error("Bad response from Amazon!")
            # Check if product has a price and is in stock
            if type(product['price']) is not float:
                continue
            if "in stock" not in product['availability'].lower():
                continue
            product_name = product['name']
            price = product['price']
            availability = product['availability']
            if price <= items[store][url]['alert_price'] and 'notified_on' not in items[store][url].keys():
                send_alert(product_name, price, url=url)
                items[store][url]['notified_on'] = (datetime.datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
                update_items_file(items)
            else:
                if 'notified_on' in items[store][url].keys():
                    insertion_date = datetime.datetime.strptime(items[store][url]['notified_on'], '%Y-%m-%d %H:%M:%S')
                    time_between_insertion = datetime.datetime.now() - insertion_date
                    if time_between_insertion.days >= DAYS_BETWEEN_ALERTS:
                        del items[store][url]['notified_on']
                        update_items_file(items)
