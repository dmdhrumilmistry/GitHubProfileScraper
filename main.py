from scraper import GithubProfileScraper
from pprint import pprint

# install firefox geckodriver and add it to path
scraper = GithubProfileScraper()

usernames = ['dmdhrumilmistry']

for username in usernames:
    user_details = scraper.scrape_user_data(username)
    pprint(user_details)

    # user_followers = scraper.get_user_followers_list(username)
    # pprint(user_followers)

    # user_following = scraper.get_user_following_list(usernames)
    # pprint(user_following)
    # print(len(user_following))

    print('-'*40)

del scraper
