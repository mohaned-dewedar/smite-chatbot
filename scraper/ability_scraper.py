from playwright.async_api import async_playwright
import asyncio
import json
import csv
from typing import List, Dict
import requests
from bs4 import BeautifulSoup



class AbilityScraper:
    def __init__(self,base_url='https://wiki.smite2.com/'):
        self.base_url = base_url
        self.gods_abilities : List[Dict] = []
    def parse_god_abilities(self,god_url):
        website= requests.get(god_url)
        soup = BeautifulSoup(website.text,"html.parser")
        tables = soup.find_all("table",class_="wikitable")
        abilities = []

        for table in tables:
            ability  = 
            ability = {
                "name":"",
                "type":"",
                "description" :"",
                "stats":"",
                "notes":""
            }

            header = table.find('th')

            if header:
                text = header.get_text(strip=True)
                print(text)
AS = AbilityScraper()
AS.parse_god_abilities("https://wiki.smite2.com/w/Achilles")



                

