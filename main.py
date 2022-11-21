from scraper import GithubProfileScraper
from utils import write_json
from os.path import isfile
from random import randint

# path to file containing username with each
username_file = 'usernames.txt'
proxy_file = 'proxy.json'

# read usernames file containting GitHub usernames on each line
assert isfile(username_file)
usernames = []
with open(username_file, 'r') as f:
    usernames = f.read().split('\n')

# scrape data for 5-10 random users
# base_num = randint(1, 2860)
# offset = randint(5, 10)
# usernames = usernames[base_num:base_num+offset]

# create obj
scraper = GithubProfileScraper(
    max_threads=5,
    proxy_json_file=proxy_file
)

# scrape data
data = dict()
for username in usernames:
    user_details = scraper.scrape_user_data(username)
    data[username] = user_details
    print('-'*40)

    # write data to a file
    write_json('scraped_data.json', data)

print(f'data scraped for {len(usernames)} users')
