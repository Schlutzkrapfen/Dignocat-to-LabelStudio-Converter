import json
import os

import numpy as np
from PIL import Image, ImageChops
from task_item import InnerAnnotation,  Prediction, TaskItem

from typing import cast

# Save the diff — black = same, white/colored = different


async def get_difference(refrence_path:str, image_path:str):
    """Gets the Picutres that ware taken, on the null index is the refrence Image returns the savepath"""
    print(refrence_path)
    print(image_path)
    img1 = Image.open(refrence_path).convert("RGB")
    img2 = Image.open(image_path).convert("RGB")

   # if img1.size != img2.size:
   #     img2 = img2.resize(img1.size, Image.Resampling.LANCZOS)
    diff = ImageChops.difference(img1, img2)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, "../output")
    save_path = os.path.join(output_dir, "diff.png")

    diff.save(save_path)
    return save_path

Error_prozentage = 50

async def get_json_cordinates(difference_image:str):
    """Converts the coordiantes to usfull Label Studio Values"""
    img_width, img_height = get_image_size(difference_image)
    x_pixels, y_pixels, x2pixel, y2pixel = get_coordinates(difference_image)
    width_pixels = -x_pixels + x2pixel
    height_pixels = -y_pixels + y2pixel
    x_pct = to_percent(x_pixels, img_width)
    y_pct = to_percent(y_pixels, img_height)
    w_pct = to_percent(width_pixels, img_width)
    h_pct = to_percent(height_pixels, img_height)
    if w_pct > Error_prozentage:
        raise ValueError(
            "Something went wrong with getting a Thooth label is over 50 %"
        )
    return x_pct, y_pct, w_pct, h_pct


def get_coordinates(difference_path:str):
    """gets the coordinates for the Pixels"""
    img = Image.open(difference_path).convert("L")  # grayscale
    arr = np.array(img)
    non_black = arr > 10
    coords = np.argwhere(non_black)  # Returns [row, col] pairs

    if len(coords) == 0:
        return 0, 0, 0, 0
    else:
        top_left = cast(list[float] ,coords.min(axis=0))  # smallest row, smallest col
        bottom_right = cast(list[float],coords.max(axis=0))  # largest row, largest col

        return top_left[1], top_left[0], bottom_right[1], bottom_right[0]


def get_info(filename: str):
    filename = os.path.basename(filename)  # removes "output/"
    name, _ext = os.path.splitext(filename)
    parts = name.split("_")
    return parts
    # user_id    = parts[0]   # "0"
    # sub_index  = parts[1]   # "0"
    # label      = parts[2]   # "Füllung"
    # confidence = parts[3]   # "96%"


def get_image_size(imagePath: str):
    img = Image.open(imagePath)
    return img.size


def to_percent(value: float, dimension: float) -> float:
    return (value / dimension) * 100


def outer_json(user_id: int, id: str, inner_json: list[InnerAnnotation])->TaskItem:
    """Makes the outer Json file that is just needed onec per Person"""
    predictions:Prediction = {"id": id, "result": inner_json, "model_version": "Diagnocat"}
    task:TaskItem = {
            "id": user_id,
            "data": {
                "image": f"/data/local-files/?d=/Dignocat-to-LabelStudio-Converter/output/{user_id}.png"
            },
            "predictions": [predictions],
        }

    return task


def to_confidence(value: str)->float:
    """Converets a Prozent value to a Float value (ex. 50% ->0.5)"""
    if "%" not in value:
        print(f"Warning: '{value}' is not a percentage!")
        return 0.0
    cleaned: str = value.strip("%").strip()
    try:
        return float(cleaned) / 100
    except ValueError:
        print(f"Warning: '{value}' could not be converted!")
        return 0.0


def inner_json(
    label: str,
    x: float,
    y: float,
    w: float,
    h: float,
    sub_index:str,
    prozent:str,
    label_catorgie:str,
)->InnerAnnotation:
    """Makes the inner Json everything that is used every Annotation"""
    task:InnerAnnotation
    values = {
        "rotation": 0,
        "rectanglelabels": [label],
        "x": x,
        "y": y,
        "width": w,
        "height": h,
    }
    task =  (
        {
            "from_name": str(label_catorgie),
            "to_name": "image",
            "type": "rectanglelabels",
            "id": "ann" + str(sub_index),
            "value": values,
            "score": to_confidence(prozent),
        }
    )
    return task


def dump_json(task:list[TaskItem]):
    """SAVE JSON"""
    with open("output.json", "w") as f:
        json.dump(task, f, indent=2)
    print("saved json to output.json")
