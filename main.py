import os
import sys

from playwright.sync_api import sync_playwright
from playwright.sync_api._generated import BrowserContext
import requests
from bs4 import BeautifulSoup

USER_DATA_DIR = 'user_data' 
# Allow imports from the src/ folder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from webcrawler import login, go_to_patient_report, get_user_data,get_refrence_image
from json_maker import get_difference,get_json_cordinates,get_info,dump_json,outer_json,inner_json


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
            refrence_image_path= get_refrence_image(page,user_id)
            images_paths =get_user_data(page, user_id)
            print(refrence_image_path)
            print(images_paths)
            task = []
            id = 0
            user_id = 0
            for paths in images_paths:
                difference_path = get_difference(refrence_image_path,paths)
                x,y,w,h=  get_json_cordinates(difference_path)
                parts = get_info(paths)
                id = parts[0]
                user_id = parts[1]
                task+= (inner_json("Füllung",x,y,w,h,parts[1],parts[3]))
            dump_json (outer_json(id,user_id,task)

)


        finally:
            pass
    



if __name__ == "__main__":
    main()