import os

import json
import numpy as np
from PIL import Image, ImageChops



# Save the diff — black = same, white/colored = different

def get_difference(refrence_path,image_path):
    """Gets the Picutres that ware taken, on the null index is the refrence Image returns the savepath"""
    
    img1 = Image.open(refrence_path)
    img2 = Image.open(image_path)
    diff = ImageChops.difference(img1, img2)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, "../output")
    save_path = os.path.join(output_dir,"diff.png")
    diff.save(save_path)
    return(save_path)

def get_json_cordinates(difference_image):
    '''Converts the coordiantes to usfull Label Studio Values'''
    img_width, img_height = get_image_size(difference_image)  
    x_pixels,y_pixels ,x2pixel,y2pixel = get_coordinates(difference_image)
    width_pixels  = -x_pixels+x2pixel
    height_pixels = -y_pixels+y2pixel
    x_pct = to_percent(x_pixels, img_width)
    y_pct = to_percent(y_pixels, img_height)
    w_pct = to_percent(width_pixels, img_width)
    h_pct = to_percent(height_pixels, img_height)
    return x_pct,y_pct,w_pct,h_pct



def get_coordinates(difference_path):
    '''gets the coordinates for the Pixels'''
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, "../output")
    img = Image.open(difference_path)
    arr = np.array(img)

    # Find all pixels that are not black
    non_black = np.any(arr > 0, axis=2)  # True where any channel > 0
    coords = np.argwhere(non_black)  # Returns [row, col] pairs

    if len(coords) == 0:
        return 0,0,0,0
    else:
        top_left     = coords.min(axis=0)  # smallest row, smallest col
        bottom_right = coords.max(axis=0)  # largest row, largest col

        return top_left[1],top_left[0],bottom_right[1],bottom_right[0]

def get_info(filename):
    filename = os.path.basename(filename)  # removes "output/" 
    name, ext = os.path.splitext(filename)
    parts = name.split("_")
    return parts
    #user_id    = parts[0]   # "0"
    #sub_index  = parts[1]   # "0"
    #label      = parts[2]   # "Füllung"
    #confidence = parts[3]   # "96%"




def get_image_size(imagePath):
   img = Image.open(imagePath)
   return img.size

def to_percent(value, dimension):
    return (value / dimension) * 100

def outer_json(user_id,id, inner_json):
    '''Makes the outer Json file that is just needed onec per Person'''
    task = []
    predictions ={"id":id,"result":inner_json,"model_version":"Diagnocat"}
    task.append({"id":user_id,"data":{'image':f'/data/local-files/?d=/Dignocat-to-LabelStudio-Converter/output/{user_id}.png'},"predictions":[predictions], } )
    return task

def to_confidence(value):
    '''Converets a Prozent value to a Float value (ex. 50% ->0.5)'''
    if "%" not in value:
        print(f"Warning: '{value}' is not a percentage!")
        return 0.0
    cleaned = value.strip("%").strip()
    try:
        return int(cleaned) / 100
    except ValueError:
        print(f"Warning: '{value}' could not be converted!")
        return 0.0

def inner_json(label,x,y,w,h,sub_index,prozent,label_catorgie):
    '''Makes the inner Json everything that is used every Annotation'''
    task = []
    values ={"rotation":0,"rectanglelabels":[label],  "x": x, "y":y,"width":  w,"height": h }
    task.append({"from_name": label_catorgie,"to_name": "image", "type":"rectanglelabels","id":"ann"+sub_index,"value":values,"score":to_confidence(prozent)})
    return task

def dump_json(task):
    '''SAVE JSON'''
    with open('output.json', 'w') as f:
        json.dump(task, f, indent=2)
    print(f"saved json to output.json")
    