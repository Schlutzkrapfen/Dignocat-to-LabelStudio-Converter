import os

import numpy as np
from PIL import Image, ImageChops



# Save the diff — black = same, white/colored = different

def get_difference():
    """Gets the Picutres that ware taken, on the null index is the refrence Image returns the savepath"""

    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, "../output")
    
    img1 = Image.open(os.path.join(output_dir, "0.png"))
    img2 = Image.open(os.path.join(output_dir, "0-0-Füllung-96%.png"))
    diff = ImageChops.difference(img1, img2)
    save_path = os.path.join(output_dir,"diff.png")
    diff.save(save_path)
    return(save_path)

def get_json_cordinates(difference_image):
    img_width, img_height = get_image_size(difference_image)  
    x_pixels,y_pixels ,x2pixel,y2pixel = get_coordinates(difference_image)
    width_pixels = x_pixels -x2pixel
    height_pixels = y_pixels -y2pixel
    x_pct = to_percent(x_pixels, img_width)
    y_pct = to_percent(y_pixels, img_height)
    w_pct = to_percent(width_pixels, img_width)
    h_pct = to_percent(height_pixels, img_height)
    return x_pct,y_pct,w_pct,h_pct



def get_coordinates():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, "../output")
    img = Image.open("output/diff.png")
    arr = np.array(img)

    # Find all pixels that are not black
    non_black = np.any(arr > 0, axis=2)  # True where any channel > 0
    coords = np.argwhere(non_black)  # Returns [row, col] pairs

    if len(coords) == 0:
        return False
        print("No differences found!")
    else:
        top_left     = coords.min(axis=0)  # smallest row, smallest col
        bottom_right = coords.max(axis=0)  # largest row, largest col

        print(f"Top-left:     x={top_left[1]},  y={top_left[0]}")
        print(f"Bottom-right: x={bottom_right[1]}, y={bottom_right[0]}")
        return top_left,bottom_right

def get_info(filename):
    name, ext = os.path.splitext(filename)  
    parts = name.split("-")                 

    index      = parts[0]   # "0"
    sub_index  = parts[1]   # "0"
    label      = parts[2]   # "Füllung"
    confidence = parts[3]   # "96%"

    print(index, sub_index, label, confidence)


def get_image_size(imagePath):
   img = Image.open(imagePath)
   return img.size

def to_percent(value, dimension):
    return (value / dimension) * 100

def main():
    difference = get_difference()
    x,y,x1,y2=  get_json_cordinates(difference)
    get_info("0-0-Füllung-96%.png")


main()