import asyncio
import json
from pathlib import Path

from typing import Literal

from controll import check_preview_image, find_duplaceted_info, find_duplicates_of
from get_info import get_patient_information
from helper_functions import make_path
from locators import Sel, Url
from patient_result import PatientResult
from screenshots import deactivated_show_buttons, get_refrence_image
from session import Session, ensure_page, remove_overlay
import time

from playwright.async_api import  Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError,BrowserContext, Page


async def find_page(context: BrowserContext, i:int, page_amount:int, output_dir:Path)->tuple[int, dict]:
    """Finds a page/user whose reference image has no duplicates left.

        Starting from index `i`, checks successive users by generating a
        reference image and searching `output_dir` for duplicates, skipping
        already-tested users, until no duplicates remain, an unrecoverable
        error occurs (e.g. missing canvas or timeout), or the search space
        is exhausted.

        Args:
            i: Starting index for the search.
            page_amount: Total number of available pages/users.
            output_dir: Directory to search for duplicate images.

        Returns:
            The resulting `user_id` (`page_amount - i - 1`).

        Raises:
            ValueError: If no users remain to check within `page_amount`,
                no reference image is found, or `user_id` becomes negative
                before duplicates are resolved.
            OSError: If navigating to a patient's report fails.
        """
    already_skipped: list[int] = [
    ]
    duplictas: list[Path] = [Path("")]
    duplictas_i = 0
    first_over: bool = False
    user_id = 0
    info: dict = {}
    while len(duplictas) > 0:
        user = i + duplictas_i
        duplictas_i += 1
        if user in already_skipped:
            print(f"User {user} already testet")
            continue
        print(f"USERID = {user}")

        user_id:int = page_amount - i - 1
        if page_amount - user < 0:
            if not first_over:
                duplictas_i = 0
                first_over = True
                continue
            user = 0 + duplictas_i


        try:
            if Session.user_page is not None:
                await Session.user_page.close()
            result  = await go_to_patient(context, user)
            Session.user_page = result.page
            if result.info is None:
                raise ValueError ("info is None")
            info = result.info
        except OSError as e:
            print(e)
            raise OSError(e)
        if find_duplaceted_info(info):
            print(f"found duplicates: {info}")
            continue

        try:
            await deactivated_show_buttons()
        except PlaywrightTimeoutError as e:
            print(f"couldn't find buttons: {e}")
            continue
        try:
            refrence_image_path = await get_refrence_image(
                make_path(user_id,info),  skip_if_exist=False,
            )
        except LookupError as e:
            print(f"Error:{e}")
            continue

        if refrence_image_path is None:

            raise ValueError("There is no Refrance Image")
        duplictas = find_duplicates_of(refrence_image_path, output_dir)
        print(f"Duplicated ID: {i} with {duplictas}")
        if len(duplictas) > 0:
            await asyncio.to_thread(refrence_image_path.unlink, missing_ok=True)
        #wy IS THERE NO RAISE OR RETURN here ????
        already_skipped.append(user)
        if user_id < 0:
            raise ValueError("couldn't find a other duplicate")
    return user_id, info
async def get_patient_amount(tries_unitl_retry: int = 3) -> int:
        """Gets the total patient count from Diagnocat.

           Tries to read the count directly from the active filter badge first.
           If that element isn't found (or raises a Playwright `Error`), falls
           back to scrolling the patient table until no new rows load for
           `max_stable_checks` consecutive polls, then returns the row count.
           Args:
               tries_unitl_retry (int): The number of times to retry before finding the amount with scrolling.

           Returns:
               int: The total number of patients.

           Raises:
               LookupError: If the filter badge amount is 0, or if the
                   filter badge element could not be located (this is caught
                   internally and triggers the scroll-based fallback).
           """
        try:
            page = Session.page
            amount_el = await page.wait_for_selector(
                "span.Filters-module_amount_zjpHX.Filters-module_amountActive_ysGOs"
            )
            if amount_el:
                amount_text = (await amount_el.inner_text()).strip()
                amount = int(amount_text)
                print(f"Active filter amount: {amount}")
                if amount == 0 :
                    if tries_unitl_retry > 0:
                        raise LookupError("amount of 0")
                    tries_unitl_retry -= 1
                    await page.wait_for_timeout(500)
                    return await get_patient_amount(tries_unitl_retry)


                return(amount)
            else:
                amount = None
                raise LookupError("No type found")
        except LookupError as e :

            page = Session.page
            print(f"{e}, tried to find amount out with scrooling " )

            row_selector = "tr.TableWithInfiniteScroll-module_tableRow_7Ru4e"

            _row = await page.wait_for_selector(row_selector)

            # Keep scrolling until no new rows appear
            previous_count = 0
            max_stable_checks = 200  # how many consecutive "no growth" checks before giving up
            poll_interval = 50  # ms between checks
            stable_checks = 0

            while True:
                rows = await page.query_selector_all(row_selector)
                current_count = len(rows)

                if current_count > previous_count:
                    # still growing — reset patience, keep going
                    previous_count = current_count
                    stable_checks = 0
                    await rows[-1].scroll_into_view_if_needed()
                else:
                    # no growth this check — don't give up immediately,
                    # could just be a slow network round-trip

                    stable_checks += 1
                    if stable_checks >= max_stable_checks:
                        break
                    # nudge scroll again in case loader needs re-triggering
                    if rows:
                        await rows[-1].scroll_into_view_if_needed()

                await page.wait_for_timeout(poll_interval)

            return previous_count
async def open_tooth_page(new_page: Page | None = None, retries: int = 3):
    if new_page is None:
        new_page = Session.page
    if new_page is None:
        raise ValueError("Page is None")

    # Precondition: we should be on the patient page
    if not Url.PATIENT_URL.match(new_page.url):
        raise ValueError(f"Unexpected starting URL: {new_page.url}")

    for attempt in range(1, retries + 1):
        try:
            button = await new_page.wait_for_selector(Sel.IMAGE_BUTTON, timeout=10_000)
            await button.click()
            # Postcondition: we landed on the pano report page
            await new_page.wait_for_url(Url.PANO_URL, timeout=15_000)
            await deactivated_show_buttons()
            return
        except PlaywrightTimeoutError as e:
            print(f"Attempt {attempt}/{retries} failed: {e}")
            if attempt == retries:
                raise
            await new_page.reload()



async def load_patients_list(page: Page, force_reload: bool = False) -> None:
    """Opens the patients list page and waits for the first row to be visible.

    If the page is already on the patients list, it is reused unless
    `force_reload` is True.

    Args:
        page: Page to navigate.
        force_reload: If True, reloads the page even when already on the list.

    Raises:
        PlaywrightTimeoutError: If navigation or the first row times out.
    """
    on_list = page.url.rstrip("/") == Url.PATIENTS.rstrip("/")
    if not on_list:
        await page.goto(Url.PATIENTS, wait_until="domcontentloaded", timeout=15000)
    elif force_reload:
        await page.reload(wait_until="domcontentloaded")
    await page.locator(Sel.PATIENT_ROW).first.wait_for(state="visible", timeout=15000)


async def _get_patient_id(page: Page, user_id: int) -> str | int:
    """Scrolls the infinite-scroll table to the given row and returns its patient ID.

    Keeps scrolling the last loaded row into view until the row at `user_id`
    exists. The ID is read from the row's React props.

    Args:
        page: Page showing the patients list.
        user_id: Index of the patient row.

    Returns:
        The patient ID stored in the row's data.

    Raises:
        IndexError: If scrolling stops loading new rows before `user_id` is
            reached (i.e. `user_id` is past the end of the table).
    """
    rows = page.locator(Sel.PATIENT_ROW)
    before, stale = 0, 0

    while True:
        count = await rows.count()
        if count > user_id:
            break
        await rows.nth(count - 1).scroll_into_view_if_needed(timeout=5000)
        await page.wait_for_timeout(500)  # Wait for new rows to load
        stale = stale + 1 if count == before else 0
        if stale >= 10:
            raise IndexError(f"row {user_id} not found (only {count} rows)")
        before = count

    row_json = await rows.nth(user_id).evaluate(Sel.GET_PROPS_JS, timeout=10000)
    return json.loads(row_json)["children"][0]["props"]["children"]["props"]["row"]["original"]["ID"]


async def go_to_patient(
    context: BrowserContext,
    user_id: int,
    mode: Literal["report", "upload","test"] = "report",
    max_retries: int = 20,
) -> PatientResult:
    """Opens a patient's page by row index in the patients table.

    Loads the patients list, scrolls the infinite-scroll table until the row at
    `user_id` is loaded, reads the patient ID from the row's React props, and
    navigates to that patient. Failures are handled in a retry loop:

    - Row not found (`IndexError`): restart from `user_id = 0`.
    - Report card missing (`ValueError`, report mode): move on to `user_id + 1`
      without consuming a retry.
    - Page/row timeouts and other Playwright errors: take a screenshot,
      recover the page, reload the list, and consume one retry. In report
      mode, a timeout also moves on to `user_id + 1`.
    - `user_id` beyond the patient count: restart from 0.

    Args:
        context: Browser context used to open a new page (report mode).
        user_id: Index of the patient row to open.
        mode: Behavior to use.
            "report": Opens the patient in a new page, fetches patient
                information, opens the tooth page, and removes the overlay.
            "upload": Opens the patient in the existing page and skips
                patients that already have a preview image.
            "test": just opens one of the images
        max_retries: Max retry attempts on page load/timeout errors.
            Defaults to 20.

    Returns:
        PatientResult containing the row index actually opened, the patient
        page, and (in report mode) the patient information.

    Raises:
        OSError: If the patients page/row can't be loaded after exhausting
            `max_retries`.
    """
    errors = 0
    force_reload = False

    while True:
        new_page: Page | None = None
        try:
            # Re-read each loop: ensure_page() may replace Session.page
            page: Page = Session.page
            await load_patients_list(page, force_reload=force_reload or mode == "upload")
            force_reload = False

            # Wrap around if the index is out of range
            if user_id >= await get_patient_amount():
                print("User ID exceeds patient amount, starting from the first patient")
                user_id = 0

            patient_id = await _get_patient_id(page, user_id)
            patient_url = f"{Url.PATIENTS}/{patient_id}"

            # ---------- upload mode ----------
            if mode == "upload":
                new_page = Session.user_page = await context.new_page()

                await new_page.goto(patient_url, wait_until="commit", timeout=60000)
                await new_page.wait_for_timeout(1500)

                if await check_preview_image(new_page):
                    print(f"skip user_id={user_id}: picture already there")
                    user_id += 1
                    continue
                info = await get_patient_information()

                return PatientResult(user_id, new_page,info)
            if mode == "test":
                new_page = Session.user_page = await context.new_page()
                await new_page.goto(patient_url, wait_until="commit", timeout=60000)
                await new_page.wait_for_timeout(1500)
                info = await get_patient_information()
                return PatientResult(user_id, new_page,info)


            # ---------- report mode ----------
            new_page = Session.user_page = await context.new_page()
            await new_page.goto(patient_url, wait_until="domcontentloaded", timeout=10000)

            info = await get_patient_information()
            await open_tooth_page(new_page)  # Raises ValueError if no report card
            await remove_overlay(new_page)
            print(f"Now on: {new_page.url}")
            return PatientResult(user_id, new_page, info)

        except IndexError as e:
            # Row doesn't exist: we ran past the end, so start over from 0
            print(f"user_id={user_id}: {e}. Restarting from 0")
            await _close_quietly(new_page)
            user_id = 0
            force_reload = True

        except ValueError as e:
            # No report card: move on to the next patient (no retry consumed)
            print(f"user_id={user_id}: report card missing: {e}")
            await _close_quietly(new_page)
            user_id += 1

        except (PlaywrightTimeoutError, PlaywrightError, KeyError, TypeError) as e:
            errors += 1
            print(f"error {errors}/{max_retries}: {type(e).__name__}: {e}")
            await _close_quietly(new_page)

            if not Session.page.is_closed():
                await Session.page.screenshot(path=f"fail_{int(time.time())}.png")
            await ensure_page(context)

            if errors > max_retries:
                raise OSError("Can't load patients page/row") from e
            force_reload = True
            if mode == "report" and isinstance(e, PlaywrightTimeoutError):
                user_id += 1  # Original behavior: skip to the next patient on timeout


async def _close_quietly(page: Page | None) -> None:
    """Closes a page if it exists and is still open, ignoring Playwright errors.

    Args:
        page: Page to close, or None (no-op).
    """
    if page is not None and not page.is_closed():
        try:
            await page.close()
        except PlaywrightError:
            pass
