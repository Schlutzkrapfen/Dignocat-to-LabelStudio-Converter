import os
import sys

from playwright.sync_api import sync_playwright
from playwright.sync_api._generated import BrowserContext
import requests
from bs4 import BeautifulSoup

USER_DATA_DIR = 'user_data' 
# Allow imports from the src/ folder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from webcrawler import login, go_to_patient_report, get_user_data,get_refrence_image,get_theeh_picture,get_pationt_amount
from json_maker import get_difference,get_json_cordinates,get_info,dump_json,outer_json,inner_json
from label_converter import map_label,load_label_mapping 

def main():
    os.makedirs("output", exist_ok=True)
    label_Data = load_label_mapping()

    #Starts the browser
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(USER_DATA_DIR, headless=False)
        page = context.new_page()
        try:
            login(page)
            outer_task = []
            for i in range(get_pationt_amount(page)):
                user_id = i
                go_to_patient_report(page,user_id)
                refrence_image_path= get_refrence_image(page,user_id)
                images_paths =get_user_data(page, user_id)
                print(refrence_image_path)
                print(images_paths)
                id = 0
                task = []
                for paths in images_paths:
                    parts = get_info(paths)
                    label,label_categorie = map_label(parts[2],label_Data)
                    if label == None:
                        continue

                    id = parts[0]
                    user_id = parts[1]
                    difference_path = get_difference(refrence_image_path,paths)
                    x,y,w,h =  get_json_cordinates(difference_path)
                    if w == 0 and h == 0:
                        paths = get_theeh_picture(page, parts[4], id)
                        difference_path = get_difference(refrence_image_path,paths)
                        x,y,w,h = get_json_cordinates(difference_path)
                    
                    task += (inner_json(label,x,y,w,h,parts[1],parts[3],label_categorie))
                outer_task += outer_json(id,user_id,task)    
            dump_json (outer_task)
        finally:
            pass
    

if __name__ == "__main__":
    main()