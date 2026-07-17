import json
import os

import numpy as np
from PIL import Image, ImageChops
from task_item import InnerAnnotation,  Prediction, TaskItem

from typing import cast

# Save the diff — black = same, white/colored = different


async def get_difference(refrence_path:str, image_path:str)-> str:
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

async def get_json_cordinates(difference_image:str)->tuple[float,float,float,float]:
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


def get_coordinates(difference_path:str)-> tuple[float,float,float,float]:
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


def get_info(filename: str)-> list[str]:
    """Gets the info out of the filename.

        Args:
            filename: Path to the image, expected format:
                      "Path/to/PatientId_PictureId_What-it-is_Prozent_SubId.png"

        Returns:
            list[str]: A list containing the split parts:
                       [PatientId, PictureId, What-it-is, Prozent, SubId]
        """

    filename = os.path.basename(filename)  # removes "output/"
    name, _ext = os.path.splitext(filename)
    parts = name.split("_")
    return parts


def get_image_size(imagePath: str)->tuple[int,int]:
    """Gets the image size of a path.

        Args:
            imagePath: Path to the image.

        Returns:
            tuple[int, int]: Image size in (width, height) format.
        """
    img = Image.open(imagePath)
    return img.size


def to_percent(value: float, dimension: float) -> float:
    """Normalizes a coordinate or size value to a percentage of an image dimension.

        Args:
            value: The coordinate or size in pixels (e.g., bounding box width or X coordinate).
            dimension: The corresponding image dimension in pixels (width or height).

        Returns:
            float: The value expressed as a percentage of the dimension (between 0.0 and 100.0).
        """
    return (value / dimension) * 100


def outer_json(user_id: int, id: str, inner_json: list[InnerAnnotation])->TaskItem:
    """Makes the outer JSON file that is needed once per person/X-ray.

        Args:
            user_id: ID for the User/X-ray.
            id: The ID for the prediction in str format.
            inner_json: All the predictions without ID and Model_version name.

        Returns:
            TaskItem: An item formatted for Label Studio.
        """
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
    """Converts a percentage string to a float value (e.g., "50%" -> 0.5).

        Args:
            value: The percentage string to convert (e.g., "96%").

        Returns:
            float: A value between 0.0 and 1.0, or 0.0 if the conversion fails.
    """

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
    """Creates an individual annotation object for a labeled bounding box.

        Args:
            label: The specific label text (e.g., "Füllung").
            x: The horizontal starting coordinate of the bounding box.
            y: The vertical starting coordinate of the bounding box.
            w: The width of the bounding box.
            h: The height of the bounding box.
            sub_index: A unique identifier index used to generate the annotation ID.
            prozent: The confidence score of the prediction as a percentage string (e.g., "96%").
            label_catorgie: The Category identifier

        Returns:
            InnerAnnotation: A dictionary representing a single formatted annotation
                ready for Label Studio.
        """
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
