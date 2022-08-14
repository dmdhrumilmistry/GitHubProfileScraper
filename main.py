from scraper import GithubProfileScraper
from utils import write_json

# REQURIEMENT: install firefox geckodriver and add it to path

# create obj
scraper = GithubProfileScraper()

# for complete user data
# data = dict()
# usernames = ['dmdhrumilmistry']
# for username in usernames:
#     user_details = scraper.scrape_user_data(username)
#     data[username] = user_details
#     print('-'*40)

data = dict()
repos = [
    'https://github.com/dmdhrumilmistry/pyhtools',
    'https://github.com/dmdhrumilmistry/PyTerminalColor', 
    'https://github.com/dmdhrumilmistry/PySafePass', 
]

for repo in repos:
    name = repo.split('/')[-1]
    data[name] = scraper.get_repo_details(repo)

# write data to a file
write_json('scraped_data.json', data)

# delete obj
del scraper
