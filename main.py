from scraper import GithubProfileScraper
from utils import write_json

# install firefox geckodriver and add it to path
scraper = GithubProfileScraper()


usernames = ['dmdhrumilmistry']

data = dict()
for username in usernames:
    user_details = scraper.scrape_user_data(username)
    # pprint(user_details)

    # user_followers = scraper.get_user_followers_list(username)
    # pprint(user_followers)

    # user_following = scraper.get_user_following_list(username)
    # pprint(user_following)

    # user_starred_repos = scraper.get_user_starred_repos_list(username)
    # pprint(user_starred_repos)
    # print(len(user_starred_repos))

    # user_repo_details = scraper.get_user_repo_details(username)
    data[username] = user_details
    print('-'*40)

write_json('scraped_data.json', data)
del scraper
