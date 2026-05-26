import os
import sys
import logging
import argparse

from playwright.sync_api import sync_playwright

USER_DATA_DIR = 'user_data' 
Error_prozentage = 50
screenshot_quality_mulitplayer = 4
# Allow imports from the src/ folder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from webcrawler import login, go_to_patient_report, get_user_data,get_refrence_image,get_theeh_picture,get_patient_amount,get_tooth_descriptions,get_thooth_id,deactivated_showButtons
from json_maker import get_difference,get_json_cordinates,get_info,dump_json,outer_json,inner_json
from label_converter import map_label,load_label_mapping 
from controll import find_duplicates_of


def parse_id_range(total: int):
    parser = argparse.ArgumentParser()
    parser.add_argument("ids", nargs="*")
    args = parser.parse_args()


    raw_indices = []
    match args.ids:
        case []:                        
            raw_indices = list(range(total))
            
        case [s] if s.endswith("+"):    
            raw_indices = list(range(int(s[:-1]), total ))    
            if int(s[:-1])>= total:
                logging.error("The start number was to big")
        case [s] if s.endswith("-"):    
            raw_indices = list(0, range(int(s[:-1]))) 
        case [a, b]:                    
            if int(b)+1 > total:
                b = total -1
            raw_indices = list(range(int(a), int(b) + 1))
            if int(a)>= total:
                logging.error("The start number was to big")
        case [s]:                       
            raw_indices = [int(s)]
            if int(s)>= total:
                logging.error("The number was to big")
    

    def flip(i): return total  - i -1 
    return [flip(i) for i in raw_indices]


def main():
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    label_Data = load_label_mapping()

    #Starts the browser
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            USER_DATA_DIR, 
            headless=False,
            #How good the quality of the Screenshots is
            device_scale_factor=screenshot_quality_mulitplayer,  
            )
        page = context.new_page()
        try:
            login(page)
            outer_task = []
            page_amount = get_patient_amount(page)
            print(f"You have {page_amount} patience")
            
            already_skipped = []

            for i in parse_id_range(page_amount):
                user_id = i  
                if user_id < 0:
                    continue
                print(f"USERID = {user_id}")
                go_to_patient_report(page,user_id)

                user_id = page_amount  - i -1  
                deactivated_showButtons(page)
                refrence_image_path= get_refrence_image(page,user_id)
                duplictas = find_duplicates_of(refrence_image_path,output_dir )
                if len(duplictas)  > 1:
                    print(f"Duplicated ID: {i} with {duplictas}")
                    already_skipped.append(i)

                    continue
                not_conv_labels = get_tooth_descriptions(page)
                task= []

                for i,non_conv_label in enumerate(not_conv_labels):
                    label,label_categorie = map_label(non_conv_label["type"],label_Data)
                    if label == None:
                        continue
                    thooth_id = get_thooth_id(page,non_conv_label["id"])
                    if thooth_id == "0000":
                        continue
                    
                    paths = get_theeh_picture(page, thooth_id, user_id)
                    print(thooth_id)
                    print(f"Saved {paths}")
                    difference_path = get_difference(refrence_image_path,paths)
                    x,y,w,h = get_json_cordinates(difference_path)
                    if w > Error_prozentage:
                        logging.error("Something went wrong with getting a thooth picture")
                    task += (inner_json(label,x,y,w,h,str(i),"100%",label_categorie))
                thooth_leng = len(refrence_image_path)
                images_paths =get_user_data(page, user_id)
                id = 0
                for paths in images_paths:
                    parts = get_info(paths)
                    label,label_categorie = map_label(parts[2],label_Data)
                    if label == None:
                        continue
                    user_id = parts[0]
                    id = str(int(parts[1]) +thooth_leng)
                    difference_path = get_difference(refrence_image_path,paths)
                    x,y,w,h =  get_json_cordinates(difference_path)
                    if w == 0 and h == 0:
                        logging.warning(f"Something went wrong with id= {id},user_id={user_id},label={label}/{parts[2]},thoot_id = {parts[4]}\n removed the broken Picture. ")
                        os.remove(paths)
                        paths = get_theeh_picture(page, parts[4], id)
                        difference_path = get_difference(refrence_image_path,paths)
                        x,y,w,h = get_json_cordinates(difference_path)
                        if w == 0 and h == 0:
                            logging.error("Failed to get the  hole thoot Picture as replacement")
                            continue
                    task += (inner_json(label,x,y,w,h,id,parts[3],label_categorie))
                outer_task += outer_json(user_id,id,task)    
            dump_json (outer_task)
        finally:
            pass
    

if __name__ == "__main__":
    main()