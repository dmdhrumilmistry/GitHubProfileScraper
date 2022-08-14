from scraper import GithubProfileScraper
from utils import write_json

# create obj
scraper = GithubProfileScraper()

# for complete user data uncomment below lines
data = dict()
usernames = ['dmdhrumilmistry']
for username in usernames:
    # user_details = scraper.scrape_user_data(username)
    user_details = scraper.get_user_following_list(username)
    data[username] = user_details
    
    print(len(user_details))
    print('-'*40)
# end

# for repo data uncomment below lines
# data = dict()
# repos = [
#     # 'https://github.com/dmdhrumilmistry/pyhtools', # normal repo
#     # 'https://github.com/kgryte/abstract-ndarray' # empty repo
# ]

# for repo in repos:
#     name = repo.split('/')[-1]
#     data[name] = scraper.get_repo_details(repo)
# end

# write data to a file
write_json('scraped_data.json', data)
