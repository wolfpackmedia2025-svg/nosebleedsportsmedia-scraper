"""Thin wrapper so scrape_to_blob.py can import scrape_followers consistently."""
from .twitter import scrape_all_followers

def scrape_followers():
    return scrape_all_followers()
