from pprint import pprint
from scraper import GithubProfileScraper
from utils import write_json

# install firefox geckodriver and add it to path
scraper = GithubProfileScraper()


usernames = ['dmdhrumilmistry']

data = dict()
# for username in usernames:
#     # user_details = scraper.scrape_user_data(username)
    
#     # data[username] = user_details
#     print('-'*40)


repos = ['https://github.com/dmdhrumilmistry/pyhtools', 'https://github.com/dmdhrumilmistry/PyTerminalColor']
for repo in repos:
    pprint(scraper.get_repo_details(repo))

# write_json('scraped_data.json', data)
del scraper
