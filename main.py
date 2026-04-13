import os
import sys

from playwright.sync_api import sync_playwright
from playwright.sync_api._generated import BrowserContext
import requests
from bs4 import BeautifulSoup

USER_DATA_DIR = 'user_data' 
# Allow imports from the src/ folder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from webcrawler import login, go_to_patient_report, get_user_data
#from json_maker import make_json
        

def main():
    os.makedirs("output", exist_ok=True)
    
    #Starts the browser
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(USER_DATA_DIR, headless=False)
        page = context.new_page()

        try:
            login(page)
            user_id = 0
            go_to_patient_report(page,user_id)

            get_user_data(page, user_id)
        finally:
            pass
    



if __name__ == "__main__":
    main()