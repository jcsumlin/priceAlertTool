from selectorlib import Extractor
import requests
from loguru import logger


class WebScraper:
    def __init__(self, site="amazon"):
        self.template = Extractor.from_yaml_file(f'./utils/{site}.yml')
        self.headers = {
            'authority': f'www.{site}.com',
            'pragma': 'no-cache',
            'cache-control': 'no-cache',
            'dnt': '1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.64 Safari/537.36',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'sec-fetch-site': 'none',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-dest': 'document',
            'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        }

    def scrape(self, url):
        r = requests.get(url, headers=self.headers)
        if r.status_code > 500:
            if "To discuss automated access to Amazon data please contact" in r.text:
                logger.debug("Page %s was blocked by Amazon. Please try using better proxies\n" % url)
            else:
                logger.debug(
                    "Page %s must have been blocked by Amazon as the status code was %d" % (url, r.status_code))
            return None
        # Pass the HTML of the page and create
        results = self.template.extract(r.text)
        if results["price"] is not None:
            results["price"] = float(results['price'].replace("$", ""))
        if "dealprice" in results:
            if results["dealprice"] is not None:
                results["price"] = float(results['dealprice'].replace("$", ""))
        return results
