import argparse
import asyncio
import logging
import os
import sys
from typing import cast

from playwright.async_api import Page, async_playwright


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from json_maker import (
    dump_json,
    get_difference,
    get_info,
    get_json_cordinates,
    inner_json,
    outer_json,
)
from task_item import InnerAnnotation, TaskItem
from label_converter import load_label_mapping, map_label
from webcrawler import (
    get_patient_amount,
    get_refrence_image,
    get_theeh_picture,
    get_thooth_id,
    get_tooth_descriptions,
    get_user_data,
    login,
    find_page
)

USER_DATA_DIR = "user_data"
Error_prozentage = 50
screenshot_quality_mulitplayer: float = 4


def parse_id_range(total: int):
    parser:argparse.ArgumentParser = argparse.ArgumentParser()
    _action:argparse.Action = parser.add_argument("ids", nargs="*")
    args:argparse.Namespace = parser.parse_args()

    raw_indices = []
    raw_ids: list[str] = cast(list[str], args.ids)
    match raw_ids:
        case []:
            raw_indices = list(range(total))

        case [s] if s.endswith("+"):
            raw_indices = list(range(int(s[:-1]), total))
            if int(s[:-1]) >= total:
                logging.error("The start number was to big")
        case [s] if s.endswith("-"):
            raw_indices = list(range(0, int(s[:-1])))
        case [a, b]:
            if int(b) + 1 > total:
                b = total - 1
            raw_indices = list(range(int(a), int(b) + 1))
            if int(a) >= total:
                logging.error("The start number was to big")
        case [s]:
            raw_indices = [int(s)]
            if int(s) >= total:
                logging.error("The number was to big")
        case[_]:
            logging.error("Value wasn't detecter or not a right value")

        case _:
            logging.error("Value wasn't detecter or not a right value")

    def flip(i: int):
        return total - i - 1

    return [flip(i) for i in raw_indices]


async def main():
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    label_Data = load_label_mapping()

    # Starts the browser
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=False,
            # How good the quality of the Screenshots is
            device_scale_factor=screenshot_quality_mulitplayer,
        )

        page: Page = await context.new_page()
        try:
            await login(page)
            page_amount = await get_patient_amount(page)
            print(f"You have {page_amount} patience")

            task:list[TaskItem] = []
            refrence_image_path = ""

            for i in parse_id_range(page_amount):

                user_id = await find_page(page,i,page_amount,output_dir)
                not_conv_labels = await get_tooth_descriptions(page)

                inner_task:list[InnerAnnotation] = []
                for i, non_conv_label in enumerate(not_conv_labels):
                    label, label_categorie = map_label(
                        non_conv_label["type"], label_Data
                    )
                    if label is None:
                        continue
                    thooth_id = await get_thooth_id(page, int(non_conv_label["id"]))
                    if thooth_id == "0000":
                        continue

                    refrence_image_path = await get_refrence_image(page, user_id )

                    paths = await get_theeh_picture(page, thooth_id, str(user_id))
                    print(thooth_id)
                    print(f"Saved {paths}")
                    if refrence_image_path is None:
                        raise ValueError("Refrence Image is missing")
                    difference_path = get_difference(refrence_image_path, paths)
                    x, y, w, h = get_json_cordinates(difference_path)
                    if w > Error_prozentage:
                        logging.error(
                            "Something went wrong with getting a thooth picture"
                        )
                    if label_categorie is None:
                        raise ValueError("label Category doesen't exist")

                    inner_task.append( inner_json(
                        label, x, y, w, h, str(i), "100%", label_categorie
                    ))
                if refrence_image_path == "":
                    print("Refrence Image is none")
                    continue
                images_paths = await get_user_data(page, user_id)
                task.append( await make_json(
                    images_paths, label_Data, refrence_image_path, inner_task, user_id, page
                ))

            dump_json(task)
        finally:
            pass


async def make_json(images_paths:list[str], label_Data: dict[str, dict[str, str]], refrence_image_path:str, task :list[InnerAnnotation] , user_id, page:Page):
    id = 0
    user_id = 0
    thooth_leng = len(refrence_image_path)
    for paths in images_paths:
        parts = get_info(paths)
        label, label_categorie = map_label(parts[2], label_Data)
        if label is None:
            continue
        user_id = int(parts[0])
        id = str(int(parts[1]) + thooth_leng)
        difference_path = get_difference(refrence_image_path, paths)
        x, y, w, h = get_json_cordinates(difference_path)
        if w == 0 and h == 0:
            logging.warning(
                f"Something went wrong with id= {id},user_id={user_id},label={label}/{parts[2]},thoot_id = {parts[4]}\n removed the broken Picture. "
            )
            os.remove(paths)
            paths = await get_theeh_picture(page, parts[4], id)
            difference_path = get_difference(refrence_image_path, paths)
            x, y, w, h = get_json_cordinates(difference_path)
            if w == 0 and h == 0:
                logging.error("Failed to get the  hole thoot Picture as replacement")
                continue

        if label_categorie is None:
            raise ValueError("label Category doesen't exist")
        task.append(inner_json(label, x, y, w, h, id, parts[3], label_categorie))
    return outer_json(user_id, str(id), task)


if __name__ == "__main__":
    asyncio.run(main())
