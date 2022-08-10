from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

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

    def get_page_source_soup(self, url: str):
        '''loads page and returns BeautifulSoup object'''
        self.driver.get(url)
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        return soup

    def __find_value(self, source: BeautifulSoup, name: str, attrs: dict, find_all: bool = False):
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

    def scrape(self, username: str) -> dict:
        '''scrapes github user data and return data as dictionary'''

        page_source = self.get_page_source_soup(
            f'http://github.com/{username.strip()}')

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
        details['starred'] = self.__get_data_tab_item_count(
            page_source, 'stars')

        # get repo details
        details['pinnedrepos'] = self.get_pinned_items(page_source)

        return details

    def __del__(self):
        self.driver.quit()
        logging.info("Headless Firefox Closed")
