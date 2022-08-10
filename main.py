from scraper import GithubProfileScraper
from pprint import pprint

# install firefox geckodriver and add it to path
scraper = GithubProfileScraper()

usernames = ['dmdhrumilmistry']

for username in usernames:
    details = scraper.scrape(username)
    pprint(details)
    print('-'*40)

del scraper
