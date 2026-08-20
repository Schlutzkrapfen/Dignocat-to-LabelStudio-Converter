import argparse
import asyncio
import os
import logging
from pathlib import Path
import sys
from typing import cast

from playwright.async_api import Page, async_playwright

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from add_options import check_task_options
from json_maker import (
    dump_json,
    get_task


)
from label_converter import load_label_mapping
from task_item import  TaskItem
from webcrawler import (
    find_page,
    get_patient_amount,
    login,
)
logger = logging.getLogger(__name__)

USER_DATA_DIR = "user_data"
screenshot_quality_mulitplayer: float = 4
refrence_image_path = Path("")



def parse_id_range(total: int) -> list[int]:
    """Parse "ids" CLI args into a flipped list of indices.

        Accepts: no args (all indices), "N+" (N..end), "N-" (0..N),
        "A B" (A..B, clamped), or "N" (single index). Invalid input logs
        an error instead of raising.

        Args:
            total: Size of the collection; bounds ranges and used for flipping (total - i - 1).

        Returns:
            list[int]: Indices, flipped relative to `total`, in generation order.
        """
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
                logger.error("The start number was to big")
        case [s] if s.endswith("-"):
            raw_indices = list(range(int(s[:-1])))
        case [a, b]:
            if int(b) + 1 > total:
                b = total - 1
            raw_indices = list(range(int(a), int(b) + 1))
            if int(a) >= total:
                logger.error("The start number was to big")
        case [s]:
            raw_indices = [int(s)]
            if int(s) >= total:
                logger.error("The number was to big")

    def flip(i: int):
        return total - i - 1

    return [flip(i) for i in raw_indices]


async def main():
    """Runs the full pipeline: login, iterate patients, and extract task data.

        Raises:
            OSError: If a patient's page can't be found/loaded.
        """
    output_dir = Path("output")
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
        task:list[TaskItem] = []

        refrence_image_path:Path = Path()
        try:
            await login(page)
            page_amount = await get_patient_amount()
            print(f"You have {page_amount} patience")


            for i in parse_id_range(page_amount):
                try:
                    user_id = await find_page(i,page_amount,output_dir)
                except (ValueError,OSError)as e:
                    print(f"complete failure:{e}")
                    raise OSError
                print(refrence_image_path)
                single_task  = await get_task(label_Data,user_id)
                task.append(single_task)
                task = await check_task_options(task)
                dump_json(task)
                #When debugging can be deaktivated for faster new runs and shows what screenshots were made
                #delete_screenshot_folders()

        finally:
            print("Finished")

if __name__ == "__main__":
    asyncio.run(main())
