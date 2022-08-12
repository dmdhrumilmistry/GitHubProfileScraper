from pprint import pprint
from bs4 import BeautifulSoup, ResultSet
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from urllib.parse import urljoin

import logging
logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] [%(levelname)s] - %(message)s')


class GithubProfileScraper:
    def __init__(self) -> None:
        # set options
        options = Options()
        options.headless = True
        options.add_argument(
            f'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36')
        options.add_argument("--window-size=1920,1080")
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument("--disable-extensions")
        options.add_argument("--proxy-server='direct://'")
        options.add_argument("--proxy-bypass-list=*")
        options.add_argument("--start-maximized")
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')

        # initialize headless firefox
        self.driver = webdriver.Firefox(options=options)
        logging.info("Headless Firefox Initialized")

    def __del__(self):
        self.driver.quit()
        logging.info("Headless Firefox Closed")

    def get_page_source_soup(self, url: str):
        '''loads page and returns BeautifulSoup object'''
        self.driver.get(url)
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        return soup

    def __find_value(self, source: BeautifulSoup, name: str, attrs: dict = None, find_all: bool = False):
        '''extracts data from the soup object'''
        if find_all:
            res = source.find_all(name, attrs)
            return res if len(res) > 0 else None

        res = source.find(name, attrs)
        return res.text.strip() if res else None

    def __get_data_tab_item_count(self, page_source: BeautifulSoup, tab_name: str):
        return self.__find_value(page_source.find('a', {'data-tab-item': tab_name}), 'span', {'class': 'Counter'})

    def get_pinned_items(self, page_source: BeautifulSoup):
        '''returns pinned card details as list of dictionary'''
        pinned_repos_list = self.__find_value(
            page_source, 'div', {'class': 'pinned-item-list-item-content'}, find_all=True)

        cards = list()
        for repo in pinned_repos_list:
            card = dict()

            # pinned card basic details
            url = repo.find('a').get('href')
            card['url'] = url if url else None
            card['name'] = self.__find_value(repo, 'span', {'class': 'repo'})
            card['desc'] = self.__find_value(
                repo, 'p', {'class': 'pinned-item-desc'})
            card['lang'] = self.__find_value(
                repo, 'span', {'itemprop': 'programmingLanguage'})

            # get repo meta data
            meta_data = self.__find_value(
                repo, 'a', {'class': 'pinned-item-meta'}, find_all=True)
            card['stars'] = None
            card['forks'] = None

            if meta_data:
                card['stars'] = meta_data[0].text.strip()
            if meta_data and len(meta_data) > 1:
                card['forks'] = meta_data[1].text.strip()

            cards.append(card)

        return cards

    def __get_contribution_graph(self, page_source: BeautifulSoup):
        graph_svg_data = page_source.find(
            'svg', {'class': 'js-calendar-graph-svg'}).find('g').find_all('g')
        commit_matrix_data = list()
        for g in graph_svg_data:
            rects = g.find_all('rect')
            for rect in rects:
                commit_data = {
                    'date': rect.get('data-date'),
                    'count': rect.get('data-count'),
                    'level': rect.get('data-level'),
                    'height': rect.get('height'),
                    'width': rect.get('width'),
                    'rx': rect.get('rx'),
                    'ry': rect.get('ry'),
                    'x': rect.get('x'),
                    'y': rect.get('y'),
                }
                commit_matrix_data.append(commit_data)
        return commit_matrix_data

    def scrape_user_data(self, username: str) -> dict:
        '''scrapes github user data and return data as dictionary'''
        # sanitize username
        username = username.strip()

        # start scraping info
        logging.info(f'Scraping data for GitHub username: {username}')
        page_source = self.get_page_source_soup(
            f'http://github.com/{username}')

        # get profile details
        details = dict()
        details['name'] = self.__find_value(page_source, 'span', {
            'class': 'p-name vcard-fullname d-block overflow-hidden', 'itemprop': 'name'})
        details['username'] = self.__find_value(page_source, 'span', {
            'class': 'p-nickname vcard-username d-block', 'itemprop': 'additionalName'})
        details['bio'] = self.__find_value(page_source, 'div', {
            'class': 'user-profile-bio'})
        details['location'] = self.__find_value(
            page_source, 'li', {'itemprop': 'homeLocation'})
        details['website'] = self.__find_value(
            page_source, 'a', {'rel': 'nofollow me'})

        # get follower and followings
        interaction_list = self.__find_value(page_source, 'a', {
                                             'class': 'Link--secondary no-underline no-wrap'}, find_all=True)
        details['followers'] = self.__find_value(
            interaction_list[0], 'span', {'class': 'text-bold'})
        details['following'] = self.__find_value(
            interaction_list[1], 'span', {'class': 'text-bold'})

        # get twitter acc
        twitter = self.__find_value(page_source, 'li', {'itemprop': 'twitter'})
        twitter = twitter.replace('Twitter\n@', '') if twitter else None
        details['twitter'] = twitter

        # get data tab items
        details['repos'] = self.__get_data_tab_item_count(
            page_source, 'repositories')
        details['projects'] = self.__get_data_tab_item_count(
            page_source, 'projects')
        details['packages'] = self.__get_data_tab_item_count(
            page_source, 'packages')
        details['starred_repos_count'] = self.__get_data_tab_item_count(
            page_source, 'stars')
        details['starred_repos_list'] = self.get_user_starred_repos_list(
            username)

        # contributions
        contributions = self.__find_value(
            page_source, 'div', {'class': 'js-yearly-contributions'})
        details['contribs'] = contributions.replace(
            '\n', '').split(' ')[0] if contributions else None
        details['contrib_matrix'] = self.__get_contribution_graph(
            page_source)

        # get repo details
        details['pinnedrepos'] = self.get_pinned_items(page_source)

        # followers list
        details['followers_list'] = self.get_user_followers_list(username)

        # following list
        details['following_list'] = self.get_user_following_list(username)

        return details

    def get_user_followers_list(self, username: str) -> list:
        '''returns followers list'''
        logging.info(f'Fetching {username} followers list')
        followers_list = list()
        page_no = 1

        while True:
            followers = self.___get_user_followers_list_per_page(
                username, page_no)
            if len(followers) == 0:
                break
            else:
                page_no += 1
                followers_list += followers
                # print(f'\r{page_no}\t{len(followers)}\t{len(followers_list)}', end='')

        return followers_list

    def ___get_user_followers_list_per_page(self, username: str, page_no: int = 1):
        '''returns followers list for the specified page'''
        page_source = self.get_page_source_soup(
            f'http://github.com/{username}?page={page_no}&tab=followers')
        users_card = page_source.find_all('a', {'data-hovercard-type': 'user'})
        # is_next_page = False if "That’s it. You’ve reached the end of\n" in page_source.text or "isn’t following anybody\n" in page_source.text else True

        followers_list = list()
        for user_card in users_card:
            username = user_card.get('href').removeprefix(
                '/').replace('https://github.com/', '')
            if username not in followers_list:
                followers_list.append(username)

        return followers_list

    def get_user_following_list(self, username: str) -> list:
        '''returns following list'''
        logging.info(f'Fetching {username} following list')
        following_list = list()
        page_no = 1

        while True:
            followings = self.___get_user_following_list_per_page(
                username, page_no)
            if len(followings) == 0:
                break
            else:
                page_no += 1
                following_list += followings
                # print(
                # f'\r{page_no}\t{len(followings)}\t{len(following_list)}', end='')

        return following_list

    def ___get_user_following_list_per_page(self, username: str, page_no: int = 1):
        '''returns following list for specified page'''
        page_source = self.get_page_source_soup(
            f'http://github.com/{username}?page={page_no}&tab=following')

        # check if page source indicates user isn't following anyone then return empty list
        if 'isn’t following anybody.\n' in page_source.text:
            return []

        users_card = page_source.find_all('a', {'data-hovercard-type': 'user'})

        following_list = list()
        for user_card in users_card:
            username = user_card.get('href').removeprefix(
                '/').replace('https://github.com/', '')
            if username not in following_list:
                following_list.append(username)
        return following_list

    def get_user_starred_repos_list(self, username: str):
        '''returns list of user starred repo list'''
        page_source = self.get_page_source_soup(
            f'http://github.com/{username}?tab=stars')

        starred_repos = list()
        next_btn_link = True
        while next_btn_link:
            repos, next_btn_link = self.__get_user_stars_repos_list(
                page_source)
            starred_repos += repos

            # visit new link if present
            if next_btn_link:
                page_source = self.get_page_source_soup(next_btn_link)

        return starred_repos

    def __get_user_stars_repos_list(self, page_source: BeautifulSoup) -> list:
        # get starred repo block
        stars_block = page_source.find(
            'turbo-frame', {'id': 'user-starred-repos'})

        # extract repo details
        repos_list = list()
        for repo_card in stars_block.find_all('h3'):
            repo_details = dict()

            # extract repo details and add it to the list
            url = urljoin('https://github.com/',
                          repo_card.find('a').get('href'))
            repo_details['url'] = url
            repo_details['name'] = url.split('/')[-1]
            repos_list.append(repo_details)

        # check
        btn_link = None
        btn_group = page_source.find(
            'div', {'class': 'BtnGroup', 'data-test-selector': 'pagination'})
        if btn_group:
            for btn in btn_group.find_all('a'):
                if btn.text == 'Next':
                    btn_link = btn.get('href')

        return (repos_list, btn_link)

    def get_user_repo_details(self, username: str) -> list:
        '''returns user repo details list'''
        logging.info(f'Fetching {username} repo details list')

        repo_details = list()
        page_no = 1

        while True:
            page_repos = self.___get_user_repo_details_list(username, page_no)
            if len(page_repos) == 0:
                break
            else:
                page_no += 1
                repo_details += page_repos

        return repo_details

    def ___get_user_repo_details_list(self, username: str, page_no: int = 1) -> list:
        '''returns user's repos list for specified page'''
        page_source = self.get_page_source_soup(
            f'http://github.com/{username}?page={page_no}&tab=repositories')

        # extract repos div block
        repos_block = page_source.find(id='user-repositories-list')

        # check if page source indicates there are no more repos then return empty list
        if 'doesn’t have any public repositories yet.\n' in page_source.text or not repos_block:
            return []

        repo_cards = repos_block.find_all('li')

        repos_list = list()
        for repo_card in repo_cards:
            repo_details = dict()

            # get name and url
            repo_name: ResultSet = repo_card.find(
                'a', {'itemprop': 'name codeRepository'})
            repo_details['name'] = repo_name.text.replace('\n', '').strip()
            repo_details['url'] = urljoin(
                'https://github.com/', repo_name.get('href'))

            # get latest updated time
            updated_block = repo_card.find('relative-time')
            repo_details['updated'] = None
            if updated_block:
                repo_details['updated'] = {
                    'datetime': updated_block.get('datetime'),
                    'string': updated_block.get('title')
                }

            # get topics
            topics_block = repo_card.find_all(
                'a', {'data-octo-click': 'topic_click'})
            repo_details['topics'] = [topic.text.replace(
                '\n', '').strip() for topic in topics_block]

            # get description and language
            repo_details['desc'] = self.__find_value(
                repo_card, 'p', {'itemprop': 'description'})
            repo_details['lang'] = self.__find_value(
                repo_card, 'span', {'itemprop': 'programmingLanguage'})

            # BUG: whenever it repeats it resets stars and forks to None, so only single value will be correct
            # get stars and forks
            stars = None
            forks = None
            for a_tag in repo_card.find_all('a'):
                url = a_tag.get('href')
                if url:
                    value = a_tag.text.replace('\n', '').strip()
                    keyword = url.split('/')[-1]
                    if keyword == 'stargazers':
                        stars = value
                    elif keyword == 'members':
                        forks = value

            repo_details['stars'] = stars
            repo_details['forks'] = forks

            # get license
            licen = None
            span_blocks = repo_card.find_all('span', {'class': 'mr-3'})

            for block in span_blocks:
                if 'License' in block.text:
                    licen = block.text.replace('\n', '').strip()

            repo_details['license'] = licen

            if repo_details not in repos_list:
                repos_list.append(repo_details)

        return repos_list
