import argparse
import asyncio
import os
import logging
from pathlib import Path
import sys
from typing import cast

from playwright.async_api import BrowserContext, Page, async_playwright


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from upload_pictures import upload_pitcutres

from navigation import find_page, get_patient_amount
from session import login, reset_starting_page
from add_options import check_task_options
from json_maker import (
    delete_screenshot_folders,
    dump_json,
    get_task
)
from label_converter import load_label_mapping
from task_item import  TaskItem
logger = logging.getLogger(__name__)

USER_DATA_DIR = "user_data"

screenshot_quality_mulitplayer: float = 4
refrence_image_path = Path("")



def parse_id_range(total: int) ->str  | list[int]:
    """Parse "ids" CLI args into a flipped list of indices.

        Accepts: no args (all indices), "N+" (N..end), "N-" (0..N),
        "A B" (A..B, clamped), or "N" (single index). Invalid input logs
        an error instead of raising.

        Args:
            total: Size of the collection; bounds ranges and used for flipping (total - i - 1).

        Returns:
            list[int]: Indices, flipped relative to `total`, in generation order.
        """
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("ids", nargs="*", default=[])
    group.add_argument("--u", metavar="PATH", help="upload files from PATH")
    args = parser.parse_args()

    if args.u:
        print(f"upload files from {args.u}")
        return [(args.u)]

    raw_ids = cast(list[str], args.ids)
    raw_indices: list[int] = []

    try:
        match raw_ids:
            case []:
                raw_indices = list(range(total))
            case [s] if s.endswith("+"):
                start = int(s[:-1])
                if start >= total:
                    logger.error("The start number was too big")
                raw_indices = list(range(start, total))
            case [s] if s.endswith("-"):
                raw_indices = list(range(min(int(s[:-1]), total)))
            case [a, b]:
                start, end = int(a), min(int(b), total - 1)
                if start >= total:
                    logger.error("The start number was too big")
                raw_indices = list(range(start, end + 1))
            case [s]:
                n = int(s)
                if n >= total:
                    logger.error("The number was too big")
                raw_indices = [n]
            case _:
                logger.error("Invalid arguments")
    except ValueError:
        logger.error("Invalid number in arguments")

    return [total - i - 1 for i in raw_indices]

async def process_page_task(i:int, page_amount:int, context, output_dir, label_Data,max_tries=10):
    """Processes a single page's task and saves the result as JSON.

        Locates the page at index `i`, retrieves its associated task using
        `label_Data`, resolves any task options, and dumps the result(s) to
        JSON. If a RecursionError occurs, relaunches a fresh persistent
        browser context and retries, up to `max_tries` times.

        Args:
            i: Index of the page to process.
            page_amount: Total number of pages, used for locating the page.
            context: Active Playwright browser context.
            output_dir: Directory where output files are written.
            label_Data: Label data used to look up the task for this page.
            max_tries: Maximum number of retry attempts after a
                RecursionError before giving up. Defaults to 10.

        Returns:
            list[TaskItem]: The task(s) processed for this page.

        Raises:
            RecursionError: If `max_tries` is exhausted without success.
        """
    try:
        print(f"processing {i},page_amount={page_amount}")
        user_id,info = await find_page(context,i,page_amount,output_dir)
        task:list[TaskItem] = []
        refrence_image_path = Path()
        print(refrence_image_path)
        single_task  = await get_task(label_Data,user_id,info)
    except ValueError as e:
        print(f"Duplicate image found: {e}")
        return await process_page_task(i, page_amount, context, output_dir, label_Data,max_tries)

    except RecursionError as e:
        print(f"RecursionError:{e}")
        if max_tries <= 0:
            raise RecursionError

        page: Page = await context.new_page()
        await reset_starting_page(page)
        return await process_page_task(i, page_amount, context, output_dir, label_Data,max_tries-1)
    task.append(single_task)

    return task

async def main():
    """Runs the full pipeline: login, iterate patients, and extract task data.

        Raises:
            OSError: If a patient's page can't be found/loaded.
            RecursionError: If the maximum number of retries is exceeded.
            ValueError: If a patient's page is out of bounds.
        """
    output_dir = Path("output")
    os.makedirs(output_dir, exist_ok=True)
    label_Data = load_label_mapping()

    # Starts the browser
    async with async_playwright() as p:
        context: BrowserContext = await p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=False,
            # How good the quality of the Screenshots is
            device_scale_factor=screenshot_quality_mulitplayer,
        )

        page: Page = await context.new_page()
        task:list[TaskItem] = []


        try:
            await login(page)
            page_amount = await get_patient_amount()
            print(f"You have {page_amount} patience")

            for i in parse_id_range(page_amount):
                try:
                    i = int(i)
                    task.extend(await process_page_task(i, page_amount, context, output_dir, label_Data))
                except ValueError:
                    task.extend(await upload_pitcutres(i,page_amount))
        finally:
            task_dic: dict[str, list[TaskItem]] = {}
            try:
                task_dic = await check_task_options(task)
            except (OSError, RecursionError) as e:
                print(f"Error to get Task_options:{e}")
                dump_json(task)
            except ValueError as e:
                print(f"value error in taskitems:{e}")
                dump_json(task)
            for key,value in task_dic.items():
                if key =="main":
                    dump_json(value)
                else:
                    dump_json(value, Path(f"json/{key}.json"))
            #When debugging can be deaktivated for faster new runs and shows what screenshots were made
            delete_screenshot_folders()
            print("Finished")

if __name__ == "__main__":
    asyncio.run(main())
