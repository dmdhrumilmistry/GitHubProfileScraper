# GithubProfileScraper

A python tool for scraping Github User Profiles and storing scraped data in json format

## Installation

- clone repo

  ```bash
  git clone https://github.com/dmdhrumilmistry/GitHubProfileScraper.git
  ```

- install requirements

  ```bash
  python3 -m pip install -r requirements.txt
  ```

## Using Proxies (Optional Step)

- Create `proxy.json` file in following format

  ```json
  {
    "login": "proxy_login",
    "password": "proxy_password",
    "proxies": ["ip1:port1", "ip2:port2"]
  }
  ```

## Usage

- create `usernames.txt` file containing GitHub usernames on each line

- run `main.py` file

  ```bash
  python3 main.py
  ```

- View currently visited page by loading `last_visited_page.html` in browser
