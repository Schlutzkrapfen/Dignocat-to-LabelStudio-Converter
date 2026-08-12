import json
import os
import logging
from sys import path

import numpy as np
from PIL import Image, ImageChops
from task_item import InnerAnnotation,  Prediction, TaskItem, Value
from playwright.async_api import Page

from helper_functions import get_info, strip_keys, to_percent,get_image_size,to_confidence
from add_options import    test_if_needs_combine
from typing import cast
from webcrawler import (
    get_refrence_image,
    get_theeh_picture,
    get_thooth_id,
    get_tooth_descriptions,
    get_user_screenshoots,
)
from label_converter import  map_label
logger = logging.getLogger(__name__)

ERROR_PROZENTAGE = 50


async def get_difference(refrence_path:str, image_path:str)-> str:
    """
        Compute the pixel-wise difference between a reference image and a
        comparison image, and save the result as a PNG file.

        Opens both images, converts them to RGB, and computes the absolute
        per-pixel difference between them using `ImageChops.difference`. The
        resulting difference image is saved to a fixed output directory
        (`../output/diff.png`, relative to this file's location) and the
        saved file path is returned.

        Args:
            refrence_path (str): Path to the reference (baseline) image.
            image_path (str): Path to the image to compare against the
                reference image.

        Returns:
            str: Absolute path to the saved difference image (`diff.png`).

        Raises:
            FileNotFoundError: If either `refrence_path` or `image_path`
                does not point to an existing file.
            OSError: If either file cannot be opened/identified as an image
                by Pillow.

        Warning:
            - The two images must have the same dimensions. Size mismatches
              are NOT currently handled.
              """

    try:
        img1 = Image.open(refrence_path).convert("RGB")
        img2 = Image.open(image_path).convert("RGB")
    except FileNotFoundError:
        raise FileNotFoundError("either `refrence_path` or `image_path` does not point to an existing file.")
    except OSError:
        raise OSError("either `refrence_path` or `image_path` cannot be opened/identified as an image by Pillow.")

   # if img1.size != img2.size:
   #     img2 = img2.resize(img1.size, Image.Resampling.LANCZOS)
    diff = ImageChops.difference(img1, img2)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, "../output")
    save_path = os.path.join(output_dir, "diff.png")

    diff.save(save_path)
    return save_path


async def get_json_cordinates(difference_image:str)->tuple[float,float,float,float]:
    """Converts pixel bounding box coordinates into Label Studio percentage values.

        Args:
            difference_image: Path to the image file to analyze.

        Returns:
            tuple[float, float, float, float]: Normalized coordinates as percentages:
                (x_percentage, y_percentage, width_percentage, height_percentage).

        Raises:
            ValueError: If the calculated width exceeds `Error_prozentage`.
        """
    img_width, img_height = get_image_size(difference_image)
    x_pixels, y_pixels, x2pixel, y2pixel = get_coordinates(difference_image)
    width_pixels = -x_pixels + x2pixel
    height_pixels = -y_pixels + y2pixel
    x_pct = to_percent(x_pixels, img_width)
    y_pct = to_percent(y_pixels, img_height)
    w_pct = to_percent(width_pixels, img_width)
    h_pct = to_percent(height_pixels, img_height)
    if w_pct > ERROR_PROZENTAGE:
        raise ValueError(
            "Something went wrong with getting a Thooth label is over 50 %"
        )
    return x_pct, y_pct, w_pct, h_pct



def get_coordinates(difference_path:str)-> tuple[float,float,float,float]:
    """
       Compute the bounding box of the non-black region in a difference image.

       Loads the image, converts it to grayscale, and finds the pixels
       brighter than a fixed threshold (i.e. pixels that differ from
       black). Returns the bounding box enclosing those pixels.

       Args:
           difference_path (str): Path to the difference image to analyze.

       Returns:
           tuple[float, float, float, float]: Bounding box as
               (x_min, y_min, x_max, y_max). Returns (0, 0, 0, 0) if no
               difference is found.
       """
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




def outer_json(user_id: int, id: str, inner_json: list[InnerAnnotation])->TaskItem:

    """Makes the outer JSON file that is needed once per person/X-ray.

        Args:
            user_id: ID for the User/X-ray.
            id: The ID for the prediction in str format.
            inner_json: All the predictions without ID and Model_version name.

        Returns:
            TaskItem: An item formatted for Label Studio.+Option settings
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


def inner_json(
    label: str,
    x: float,
    y: float,
    w: float,
    h: float,
    sub_index:int,
    prozent:str,
    label_catorgie:str,
    option:str,thoot_id:str
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
            option: Option which need to saved can be added
            thoot_id: needed for options

        Returns:
            InnerAnnotation: A dictionary representing a single formatted annotation
                ready for Label Studio.
        """
    task:InnerAnnotation
    values:Value = {
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
            "options":option,
            "thoot_id": thoot_id
        }
    )
    return task


def dump_json(task: list[TaskItem]):
    """Save the task list to a JSON file, excluding internal-only fields.

    Removes the "combine" and "thoot_id" keys (used only internally)
    before writing the output, since TypedDict has no built-in way to
    exclude fields at serialization time.

    Args:
        task: The list of TaskItem objects to save.
    """
    cleaned = strip_keys(task, {"combine", "thoot_id"})
    with open("output.json", "w") as f:
        json.dump(cleaned, f, indent=2)
    print("saved json to output.json")

async def get_task(page:Page,label_Data:dict[str, list[dict[str, str]]],user_id:int,refrence_image_path:str)->tuple[TaskItem, str]:

        not_conv_labels = await get_tooth_descriptions(page)

        inner_task:list[InnerAnnotation] = []
        id_addition:int = 0
        for i, non_conv_label in enumerate(not_conv_labels):
            labels:list[str]
            label_categories:list[str]
            try:
                labels, label_categories,options = map_label(
                non_conv_label["type"], label_Data
            )
            except ValueError:
                continue
            try:
                thooth_id = await get_thooth_id(page, int(non_conv_label["id"]))

                refrence_image_path = await get_refrence_image(page, user_id )
                paths = await get_theeh_picture(page, thooth_id, user_id)
            except ValueError:
                continue



            print(f"Saved {paths}")
            if refrence_image_path is None:
                print("Refrence Image is missing")
                continue
            try:

                difference_path = await get_difference(refrence_image_path, paths)
            except (FileNotFoundError,OSError)as e:
                print(e)
                continue
            try:
                x, y, w, h = await get_json_cordinates(difference_path)
            except ValueError:
                print("label wasn't found")
                continue

            for k, _ in enumerate(labels):
                inner_task.append( inner_json(
                    labels[k], x, y, w, h, i +id_addition , "100%", label_categories[k],options[k],thooth_id
                ))
                id_addition +=1
            if refrence_image_path == "":
                print("Refrence Image is none")
                continue
        images_paths = await get_user_screenshoots(page, user_id)

        return( await make_json(
                        images_paths, label_Data, refrence_image_path, inner_task, user_id, page
                ),refrence_image_path)



async def make_json(images_paths:list[str], label_Data: dict[str, list[dict[str, str]]], refrence_image_path:str, task :list[InnerAnnotation] , user_id:int, page:Page,)->TaskItem:
        """Diff each image against a reference image and append the resulting annotations to `task`.
        def add_option():
            :


            Args:
                images_paths: Paths to the tooth images to process.
                label_Data: Lookup table used to resolve a label key to a (label, category) pair.
                refrence_image_path: Path to the reference image each entry is diffed against.
                task: List of annotations to append to (mutated in place).
                user_id: Currently unused.
                page: Playwright page used to re-fetch a replacement image if a diff fails.

            Returns:
                TaskItem: `task` wrapped with the user_id/id of the last processed image.

            Raises:
                ValueError: If a resolved label has no category.
            """
        id = 0
        user_id = 0
        options = []
        thooth_leng = len(refrence_image_path)
        for paths in images_paths:
            parts = get_info(paths)
            try:
                label, label_categorie,options = map_label(parts[2], label_Data)
            except ValueError:
                continue


            user_id = int(parts[0])
            id = int(parts[1]) + thooth_leng
            try:
                difference_path = await get_difference(refrence_image_path, paths)
                x, y, w, h = await get_json_cordinates(difference_path)
            except (ValueError,FileNotFoundError,OSError) as e :
                print(f"Error: {e}")
                continue
            if w == 0 and h == 0:
                logger.warning(
                    f"Something went wrong with id= {id},user_id={user_id},label={label}/{parts[2]},thoot_id = {parts[4]}\n removed the broken Picture. "
                )
                os.remove(paths)
                paths = await get_theeh_picture(page, parts[4], id)
                difference_path = await  get_difference(refrence_image_path, paths)
                try:
                    x, y, w, h = await get_json_cordinates(difference_path)
                except ValueError:
                    continue
                if w == 0 and h == 0:
                    logger.error("Failed to get the  hole thoot Picture as replacement")
                    continue

            if label_categorie is None:
                raise ValueError("label Category doesen't exist")
            for i,_ in enumerate(label):
                task.append(inner_json(label[i], x, y, w, h, int(id)+i, parts[3], label_categorie[i],options[i],parts[4]))
            id += len(label)-1
        return outer_json(user_id, str(id), task)
