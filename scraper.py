from bs4 import BeautifulSoup
from random import randint
from requests import get as req_get
from time import sleep
from urllib.parse import urljoin
from utils import sanitize_html_text, ThreadHandler
from os.path import isfile
from json import JSONDecodeError, loads as load_json

import logging
logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] [%(levelname)s] - %(message)s')


class GithubProfileScraper:
    '''class to scrape github user profile'''

    def __init__(self, max_threads: int, proxy_json_file:str = None) -> None:
        assert isinstance(max_threads, int)
        self.max_threads = max_threads

        # load proxy config file if present
        self.proxy_list = None
        self.proxy_login = None
        self.proxy_passwd = None
        if proxy_json_file and isfile(proxy_json_file):
            logging.info(f'Loading proxy config from {proxy_json_file}')
            try:
                with open(proxy_json_file, 'r') as f:
                    proxy_config = load_json(f.read())
                    self.proxy_login = proxy_config.get('login', None)
                    self.proxy_passwd = proxy_config.get('password', None)
                    self.proxy_list = proxy_config.get('proxies', None)
                    logging.info(f'Proxies: {self.proxy_list}')
            except JSONDecodeError:
                logging.warning('Not using proxies. Config file should be in JSON format')

    def rotating_proxy_request(self, url: str, **kwargs):
        '''sends request using random proxy from the chain'''

        while True:
            try:
                proxy_index = randint(0, len(self.proxy_list) - 1)
                proxies = {
                    'http': f'http://{self.proxy_login}:{self.proxy_passwd}@{self.proxy_list[proxy_index]}',
                    'https': f'http://{self.proxy_login}:{self.proxy_passwd}@{self.proxy_list[proxy_index]}',
                }
                res = req_get(url, proxies=proxies, )
                break
            except Exception as e:
                logging.warning('Request Failed! Choosing another proxy')
        return res

    def get_page_source_soup(self, url: str):
        '''loads page and returns BeautifulSoup object'''
        headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.5',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'DNT': '1',
            'Host': 'github.com',
            'Origin': 'https://github.com',
            'Pragma': 'no-cache',
            'Referer': 'https://github.com/',
            'Sec-Fetch-Dest': 'script',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
            'TE': 'trailers',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0 Win64 x64 rv: 103.0) Gecko/20100101 Firefox/103.0',
        }
        if self.proxy_list and self.proxy_login and self.proxy_passwd:
            res = self.rotating_proxy_request(url, headers=headers)
        else:
            res = req_get(url, headers=headers)

        # if error occurred or url doesn't exist then return None
        if res.status_code in [404, 500, 501, 502]:
            logging.info(f'{url} URL Not Found on the server')
            return None

        soup = BeautifulSoup(res.text, 'html.parser')

        # write html page to file for debugging purpose
        with open('last_visited_page.html', 'w', encoding='utf-8') as f:
            f.write(url + res.text)

        # detect abuse detection page
        # if detected try after waiting random amount of time
        if 'Whoa there!' in soup.text:
            waiting_time = randint(10, 120)
            logging.warn(
                f'Abuse detection system triggered, trying after {waiting_time}s')
            sleep(waiting_time)
            soup = self.get_page_source_soup(url)

        return soup

    def __find_value(self, source: BeautifulSoup, name: str, attrs: dict = None, find_all: bool = False):
        '''extracts data from the soup object'''
        if not source:
            return None

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
        if pinned_repos_list:
            for repo in pinned_repos_list:
                card = dict()

                # pinned card basic details
                url = repo.find('a').get('href')
                card['url'] = url if url else None
                card['name'] = self.__find_value(
                    repo, 'span', {'class': 'repo'})
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

        if not page_source:
            return dict({'message': 'user not found'})

        # get profile details
        details = dict()
        logging.info(f'Fetching {username} user profile details')
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

        # get twitter acc
        twitter = self.__find_value(page_source, 'li', {'itemprop': 'twitter'})
        twitter = twitter.replace('Twitter\n@', '') if twitter else None
        details['twitter'] = twitter

        # get repo details
        details['pinnedrepos'] = self.get_pinned_items(page_source)

        # get follower and followings
        logging.info(
            f'Fetching {username} user followers and followings count')

        interaction_list = self.__find_value(page_source, 'a', {
                                             'class': 'Link--secondary no-underline no-wrap'}, find_all=True)
        followers = None
        followings = None
        if interaction_list:
            followers = self.__find_value(
                interaction_list[0], 'span', {'class': 'text-bold'})
            followings = self.__find_value(
                interaction_list[1], 'span', {'class': 'text-bold'})
        details['followers'] = followers
        details['following'] = followings

        # followers list
        # details['followers_list'] = self.get_user_followers_list(username)

        # following list
        # details['following_list'] = self.get_user_following_list(username)

        # get data tab items
        logging.info(
            f'Fetching {username} user repo, project, and package details')

        details['repos_count'] = self.__get_data_tab_item_count(
            page_source, 'repositories')
        details['repos'] = self.get_user_repos_list(username)
        details['projects_count'] = self.__get_data_tab_item_count(
            page_source, 'projects')
        details['packages'] = self.__get_data_tab_item_count(
            page_source, 'packages')
        details['starred_repos_count'] = self.__get_data_tab_item_count(
            page_source, 'stars')
        details['starred_repos_list'] = self.get_user_starred_repos_list(
            username)

        # contributions
        logging.info(f'Fetching {username} user contribution details')

        contributions = self.__find_value(
            page_source, 'div', {'class': 'js-yearly-contributions'})
        details['contribs'] = contributions.replace(
            '\n', '').split(' ')[0] if contributions else None
        details['contrib_matrix'] = self.__get_contribution_graph(
            page_source)

        return details

    def get_user_followers_list(self, username: str) -> list:
        '''returns followers list'''
        logging.info(f'Fetching {username} followers list')
        followers_list = list()

        # for data extration
        page_no = 1
        running_status = True

        def handle_thread():
            '''handles threading for retrieving user followers list'''
            nonlocal page_no
            nonlocal followers_list
            nonlocal running_status

            followers = self.___get_user_followers_list_per_page(
                username, page_no)
            page_no += 1

            if len(followers) == 0:
                running_status = False
            else:
                for follower in followers:
                    if follower not in followers_list:
                        followers_list.append(follower)

            # print(f'page_no:{page_no}\trunning:{running_status}\tfollowers on page:{len(followers)}\ttot followers:{len(followers_list)}')

        # handle threads
        threads = list()
        while running_status:
            if len(threads) < self.max_threads:
                thread = ThreadHandler(target=handle_thread)
                thread.start()
                threads.append(thread)
            else:
                # wait until all threads are terminated
                for thread in threads:
                    thread.join()
                    threads.remove(thread)
                sleep(0.3)
            sleep(0.1)

        return followers_list

    def ___get_user_followers_list_per_page(self, username: str, page_no: int = 1):
        '''returns followers list for the specified page'''
        page_source = self.get_page_source_soup(
            f'http://github.com/{username}?page={page_no}&tab=followers')

        # page not found then return empty list
        if not page_source:
            return list()

        users_card = page_source.find_all('a', {'data-hovercard-type': 'user'})
        # is_next_page = False if "That???s it. You???ve reached the end of\n" in page_source.text or "isn???t following anybody\n" in page_source.text else True

        # create list to store followers
        followers_list = list()

        # if there are followers then add them to the list
        if 'That???s it. You???ve reached the end of' not in page_source.text:
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

        # for data extration
        page_no = 1
        running_status = True

        def handle_thread(username: str, page_no: int):
            '''handles threading for retrieving user following list'''
            nonlocal following_list
            nonlocal running_status

            followings = self.___get_user_following_list_per_page(
                username, page_no)
            page_no += 1

            if len(followings) == 0:
                running_status = False
            else:
                for following in followings:
                    if following not in following_list:
                        following_list.append(following)
            # print(f'page_no:{page_no}\trunning:{running_status}\tfollowers on page:{len(followings)}\ttot followers:{len(following_list)}')

        # handle threads
        threads = list()
        while running_status:
            if len(threads) < self.max_threads:
                thread = ThreadHandler(
                    target=handle_thread, args=(username, page_no,))
                thread.start()
                threads.append(thread)
                page_no += 1
            else:
                # wait until all threads are terminated
                for thread in threads:
                    thread.join()
                    threads.remove(thread)
                sleep(0.3)
            sleep(0.2)

         # wait until all threads are terminated
        for thread in threads:
            thread.join()

        return following_list

    def ___get_user_following_list_per_page(self, username: str, page_no: int = 1):
        '''returns following list for specified page'''
        page_source = self.get_page_source_soup(
            f'http://github.com/{username}?page={page_no}&tab=following')

        # page not found then return empty list
        if not page_source:
            return list()

        # check if page source indicates user isn't following anyone then return empty list
        if 'isn???t following anybody.\n' in page_source.text:
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

        # page not found then return empty list
        if not page_source:
            return list()

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
            url = repo_card.find('a') if repo_card else None
            url = urljoin('https://github.com/',
                          url.get('href')) if url else None

            # if url is absent continue to next iteration
            if not url:
                continue

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

    def get_user_repos_list(self, username: str) -> list:
        '''returns user's repos list'''
        logging.info(f'Fetching repos list for {username}')

        repos_list = list()
        page_no = 1
        running_status = True

        def handle_repo_thread(username: str, page_no: int):
            '''handles threading for retrieving user repos list'''
            nonlocal repos_list
            nonlocal running_status

            repos = self.___get_user_repos_list(username, page_no)

            if len(repos) == 0:
                running_status = False
            else:
                for repo in repos:
                    if repo not in repos_list:
                        repos_list.append(repo)

            # print(
                # f'page_no:{page_no}\trunning:{running_status}\trepos on page:{len(repos)}\ttot repos:{len(repos_list)}')

        # handle threads
        threads = list()
        while running_status:
            # print(len(threads))
            if len(threads) < self.max_threads:
                # print('create thread')
                thread = ThreadHandler(
                    target=handle_repo_thread, args=(username, page_no,))
                thread.start()
                threads.append(thread)
                page_no += 1
            else:
                # print('joining all threads')
                # wait until all threads are terminated
                for thread in threads:
                    thread.join()
                    threads.remove(thread)
                sleep(0.3)
            sleep(0.2)

        # fetch details for user repos
        repo_details_list = list()
        threads = list()

        def get_repo_details(repo_url):
            repo_details = self.get_repo_details(repo_url)

            if repo_details not in repo_details_list:
                repo_details_list.append(repo_details)

        while repos_list:
            if len(threads) < self.max_threads:
                repo_url = repos_list.pop(0)
                thread = ThreadHandler(
                    target=get_repo_details, args=(repo_url,))
                thread.start()
                threads.append(thread)

            else:
                for thread in threads:
                    thread.join()
                    threads.remove(thread)
                sleep(0.3)
            sleep(0.2)

        return repo_details_list

    def ___get_user_repos_list(self, username: str, page_no: int = 1) -> list:
        '''returns user's repos list for specified page'''
        page_source = self.get_page_source_soup(
            f'http://github.com/{username}?page={page_no}&tab=repositories')

        # page not found then return empty list
        if not page_source:
            return list()

        # extract repos div block
        repos_block = page_source.find(id='user-repositories-list')

        # check if page source indicates there are no more repos then return empty list
        if 'doesn???t have any public repositories yet.\n' in page_source.text or not repos_block:
            return []

        repo_cards = repos_block.find_all('li')

        repos_list = list()
        for repo_card in repo_cards:
            repo_url = urljoin('https://github.com/', repo_card.find('a',
                               {'itemprop': 'name codeRepository'}).get('href'))

            # TODO: uncomment below line
            # repo_details = self.get_repo_details(repo_url)
            repo_details = repo_url
            if repo_details not in repos_list:
                repos_list.append(repo_details)

        return repos_list

    def get_repo_details(self, repo_url: str) -> dict:
        '''returns repo details using repo url as dict, if empty returns None'''
        assert isinstance(repo_url, str)

        page_source = self.get_page_source_soup(repo_url)

        # page not found then return empty list
        if not page_source:
            return list()

        # if repo is empty return None
        if 'This repository is empty' in page_source.text:
            return None

        # create dict to store repo details
        details = dict()

        # add url
        details['url'] = repo_url

        # get name
        name_block = page_source.find('strong', {'itemprop': 'name'})
        name = name_block.find('a') if name_block else None
        name = sanitize_html_text(name.text) if name else None
        details['name'] = name

        # get author
        author_block = page_source.find('span', {'itemprop': 'author'})
        author = author_block.find('a') if author_block else None
        author = sanitize_html_text(author.text) if author else None
        details['author'] = author

        # get about block
        detail_blocks = page_source.find_all(
            'div', {'class': 'BorderGrid-cell'})
        about_block = detail_blocks[0]

        # for about
        details['desc'] = self.__find_value(
            about_block, 'p', {'class': 'f4 my-3'})

        # get topics
        topics = []
        for topic in about_block.find_all('a', {'class': 'topic-tag'}):
            topic_name = sanitize_html_text(topic.text)
            if topic_name not in topics:
                topics.append(topic_name)

        details['topics'] = topics

        # get stars
        stars = page_source.find(id='repo-stars-counter-star')
        stars = sanitize_html_text(stars.text) if stars else None
        details['stars'] = stars

        # get forks
        forks = page_source.find('span', id='repo-network-counter')
        forks = sanitize_html_text(forks.text) if forks else None
        details['forks'] = forks

        # for license
        lic = None
        watchers = None
        for a_tag in about_block.find_all('a', {'class': 'Link--muted'}):
            a_tag_text = a_tag.text.lower()

            if 'license' in a_tag_text:
                lic = sanitize_html_text(a_tag.text)
            if 'watching' in a_tag_text:
                watchers = a_tag.find('strong')
                watchers = sanitize_html_text(
                    watchers.text) if watchers else None

        details['license'] = lic
        details['watchers'] = watchers

        # get file navigation block to get branch count
        branches = None
        file_nav_block = page_source.find('div', {'class': 'file-navigation'})
        branches_tag = file_nav_block.find(
            'a', {'data-turbo-frame': 'repo-content-turbo-frame', 'class': 'Link--primary no-underline'})
        if branches_tag and branches_tag.get('href').split('/')[-1] == 'branches':
            branches = sanitize_html_text(branches_tag.find('strong').text)
        details['branches'] = branches

        # get releases and languages
        releases = None
        languages = None
        for detail_block in detail_blocks:
            # for releases
            a_tag = detail_block.find('a')
            if a_tag and 'Releases' in a_tag.text:
                releases = a_tag.find(
                    'span', {'class': 'Counter'})
                releases = releases.get('title') if releases else None

            # for languages and their pcs
            h2_tag = detail_block.find('h2')
            if h2_tag and 'Languages' in h2_tag.text:
                languages = list()
                for lang_a_tag in detail_block.find_all('li', {'class': 'd-inline'}):
                    span_tags = lang_a_tag.find_all('span')

                    lang = None
                    percent = None
                    if len(span_tags) == 2:
                        lang = sanitize_html_text(span_tags[0].text)
                        percent = sanitize_html_text(span_tags[1].text)
                    elif len(span_tags) == 3:
                        lang = sanitize_html_text(span_tags[1].text)
                        percent = sanitize_html_text(span_tags[2].text)

                    if lang and percent:
                        languages.append({'lang': lang, 'percent': percent})

        details['releases'] = releases
        details['languages'] = languages

        # for commits
        commits = None
        box_div = page_source.find('div', {'class': 'Box-header'})
        if box_div:
            for li_tag in box_div.find_all('li'):
                a_tag = li_tag.find('a')
                if 'commits' in a_tag.get('href').split('/'):
                    commit_data = li_tag.find('strong')
                    commits = sanitize_html_text(
                        commit_data.text) if commit_data.text else None

        details['commits'] = commits

        # for last commit time
        updated_block = page_source.find('relative-time')
        updated = None
        if updated_block:
            updated = {
                'datetime': updated_block.get('datetime'),
                'string': updated_block.get('title')
            }
        details['updated'] = updated

        return details
