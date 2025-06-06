"""
Global variables for the dictionnaire-academie.fr scraper.
Created on: 2025-06-02 14:01:45 HKT
Created by: Jacob Shing
"""

# Global variables
HEADER_ACCEPT = "application/json, text/javascript, */*; q=0.01"
HEADER_ACCEPT_ENCODING = "gzip, deflate, br"
HEADER_ACCEPT_LANGUAGE = "en-GB,en;q=0.9"
HEADER_CONTENT_TYPE = "application/x-www-form-urlencoded; charset=UTF-8"
HEADER_MISC_COOKIES = "acceptCookies=1; accessibilitySettings=wordNavigationLink=false&openDyslexic=false"
HEADER_SEC_FETCH_SITE = "same-origin"
HEADER_SEC_FETCH_MODE = "cors"
HEADER_SEC_FETCH_DEST = "empty"
COOKIE_JSESSION_ID = None # Obtained from the website during runtime
URL_ROOT = "https://dictionnaire-academie.fr/"
URL_CONJUGATION_TABLE = f"{URL_ROOT}conjuguer/"
URL_SEARCH = f"{URL_ROOT}search"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15"

CONFIG_IGNORE_CACHE = False
CONFIG_MAX_RETRY = 5
CONFIG_REQUESTS_DELAY = 500 # in ms; set to higher if blocked by the server
CONFIG_VERBOSE = False

EXTENSION_GEN_SQLITE3 = False
EXTENSION_GEN_INFINITIVES = False

EXT_GEN_INFS_URL = f"{URL_ROOT}advsearch/"
EXT_GEN_INFS_HEADER_ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
EXT_GEN_INFS_HEADER_DATA = "txt_fullsearch=&chk_allform=1&lst_section=&checked_domain=&txt_entry={% ALPHABET %}.*&chk_noaccent=1&checked_grammcat=27%2C28%2C29%2C30%2C31%2C32%2C33%2C&chk_grpcat=on&chk_gramcat=v.&chk_gramcat=v.+tr.&chk_gramcat=v.+intr.&chk_gramcat=v.+pron.&chk_gramcat=v.+r%C3%A9cipr.&chk_gramcat=v.+impers.&checked_lang=&lst_datation=&lst_editions=9&btRechercher="