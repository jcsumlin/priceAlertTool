import datetime

import requests
from bestbuy import BestBuyAPI
import json
from configparser import ConfigParser
from loguru import logger

from factories.Notification import Notification, Payload
from utils.scraper import scrape
from utils.sms import SMS
from pushbullet import Pushbullet

config = ConfigParser()
config.read("auth.ini")
disable_bestbuy = False
if "APIKeys" not in config.sections():
    disable_bestbuy = True

with open("./items.json") as file:
    items = json.load(file)
DAYS_BETWEEN_ALERTS = config.getint('Alerts', 'daysBetweenAlerts', fallback=1)


def update_items_file(data):
    with open("./items.json", 'w') as file:
        json.dump(data, file)


def send_alert(product_name, price, url=None, availability=None):
    payload = Payload(name=product_name,
                      price=price,
                      url=url,
                      availability=availability)
    if "Alerts" not in config.sections():
        logger.info(payload.generate_message())
        return
    if config.get('Alerts', 'pushoverToken', fallback=None) is not None and config.get('Alerts', 'pushoverUserKey', fallback=None) is not None:
        Notification().send(payload, 'pushover')
    if config.get('Alerts', 'webhook', fallback=None) is not None:
        Notification().send(payload, agent="webhook")

    if config.get('Alerts', 'pushBulletKey', fallback=None) is not None:
        Notification().send(payload, agent="pushbullet")

    if config.get('Alerts', 'smsNumber', fallback=None) is not None:
        Notification().send(payload, agent="sms")


for store in items:
    product_ids = items[store].keys()
    if store.lower() == "bestbuy" and not disable_bestbuy:
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
                    availability = ""
                    if inStoreAvailability:
                        availability += "Available in Store"
                    if onlineAvailability:
                        if inStoreAvailability:
                            availability += " and "
                        availability += "Available Online"
                    send_alert(product_name, price, url=url, availability=availability)
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
