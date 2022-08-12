from scraper import GithubProfileScraper
from pprint import pprint

# install firefox geckodriver and add it to path
scraper = GithubProfileScraper()

usernames = ['dmdhrumilmistry']

for username in usernames:
    user_details = scraper.scrape_user_data(username)
    pprint(user_details['starred_repos_list'])

    # user_followers = scraper.get_user_followers_list(username)
    # pprint(user_followers)

    # user_following = scraper.get_user_following_list(username)
    # pprint(user_following)

    # user_starred_repos = scraper.get_user_starred_repos_list(username)
    # pprint(user_starred_repos)
    # print(len(user_starred_repos))

    print('-'*40)

del scraper
