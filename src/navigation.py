import asyncio
from pathlib import Path


from controll import check_preview_image, find_duplaceted_info, find_duplicates_of
from get_info import get_patient_information
from helper_functions import make_path
from locators import Sel, Url
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
            Session.user_page, info = await go_to_patient_report(context, user)
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
async def open_tooth_page(new_page: Page|None = None):
    if new_page is None:
        new_page = Session.page

    if new_page is None:
        raise ValueError("Page is None")
    _div = await new_page.wait_for_selector(Sel.IMAGE_BUTTON)

    button = await new_page.query_selector(Sel.IMAGE_BUTTON)
    if button is None:
        print("couldn't find button")
        raise ValueError("Button Isn't here")
    await button.click()

async def go_to_patient_report(context: BrowserContext, user_id: int,max_retries:int=20,locked:bool=False)-> tuple[Page, dict[str,str]]:
                """Navigates to a specific patient's report page.

                 Opens the patients list page (or reloads if `locked`), scrolls the
                 infinite-scroll table until `user_id`'s row loads, opens that patient
                 in a new page, and opens their report card. Retries recursively on
                 failure: page/row timeouts reload and retry (decrementing
                 `max_retries`); an out-of-range `user_id` restarts from 0; unresolved
                 row data restarts from 0; a missing report card retries with
                 `user_id + 1`; a report-card timeout reloads and retries from 0.

                 Args:
                     context: Browser context used to open the new patient page.
                     user_id: Index of the patient row to open in the table.
                     max_retries: Max retry attempts on page load/timeout errors.
                         Defaults to 20.
                     locked: If True, forces a reload of the patients page. Defaults
                         to False.

                 Returns:
                     Page: The new page, navigated to the patient's report.

                 Raises:
                     OSError: If the patients page/row can't be found after exhausting
                         `max_retries`.
                     ValueError: If the report card can't be loaded after exhausting
                         `max_retries`.

                 """
                page = Session.page
                try:
                    if page.url.rstrip("/") != Url.PATIENTS.rstrip("/") or locked == True:
                        print("Opening data page...")
                        _website = await page.goto(
                        Url.PATIENTS,
                        wait_until="domcontentloaded",
                        timeout=10000,
                        )
                    max_patiens = await get_patient_amount()
                    if user_id >= max_patiens:
                               print("User ID exceeds patient amount, starting from the first patient")
                               return await go_to_patient_report(context,0, max_retries, True)

                    row_selector =  Sel.PATIENT_ROW

                    _body = await page.wait_for_selector("body", timeout=15000)
                    _row = await page.wait_for_selector(row_selector, timeout=15000)
                except (PlaywrightTimeoutError, PlaywrightError) as e:
                    print(f"URL: {Session.page.url if not Session.page.is_closed() else 'Closed'}")
                    if not Session.page.is_closed():
                            await Session.page.screenshot(path=f"fail_{int(time.time())}.png")

                    print(f"couldn't find body/row,skipping page: {e}")
                    await ensure_page(context)


                    if max_retries <= 0:
                         raise OSError("Could not load the patients page after all retries")
                    return await go_to_patient_report(context,user_id ,max_retries -1, True)

                # Scroll until we have enough rows loaded to reach user_id
                # Wait for the next page
                Session.user_page = await context.new_page()
                new_page = Session.user_page
                if new_page is None:
                    raise ValueError("new_page is null")
                try:
                    while True:
                           rows = await page.query_selector_all(row_selector)

                           if len(rows) > user_id:
                               break  # We have enough rows, stop scrolling

                           # Not enough rows yet — scroll down to load more
                           await rows[-1].scroll_into_view_if_needed()


                    try:
                       # await rows[user_id].click()
                        row_data_json = await rows[user_id].evaluate("""
                        el => {
                            const key = Object.keys(el).find(k => k.startsWith('__reactProps$'));
                            if (!key) return null;
                            const props = el[key];
                            return JSON.stringify(props, (k, v) => typeof v === 'function' ? undefined : v);
                        }
                        """)

                        import json
                        row_data = json.loads(row_data_json)
                        patient_id = row_data["children"][0]["props"]["children"]["props"]["row"]["original"]["ID"]
                        patient_url = f"{Url.PATIENTS}/{patient_id}"

                        await Session.user_page.goto(patient_url, wait_until="domcontentloaded", timeout=10000)

                        # ... do your work on new_page ...

                       # #await new_page.close()

                    except IndexError as e:
                        print(f"User_id: {user_id} the picture wasn't there: {e} ")
                        await new_page.close()
                        return await go_to_patient_report(context, user_id + 1, max_retries)


                    print("Clicked first patient row")

                    print(f"Now on: {page.url}")
                    info = await get_patient_information()
                    await open_tooth_page(new_page)

                except ValueError as e:
                    print(f"User_id: {user_id} the picture wasn't there: {e} ")
                     #await new_page.close()
                    # TODO: find a more efficent way to go true the loop if it failed
                    await new_page.close()
                    return await go_to_patient_report(context, user_id + 1,max_retries )

                except PlaywrightTimeoutError as e:
                    print(f"Something went wrong, skipping: {e}")
                    if max_retries <= 0:
                        raise ValueError("Max retries exceeded")
                    await new_page.close()
                    return await go_to_patient_report(context, user_id + 1, max_retries - 1, True)


                await remove_overlay(new_page)
                print(f"Now on: {new_page.url}")
                return new_page, info

async def go_to_upload_patient_report(user_id: int,max_retries:int=20)-> int:
    """Opens a patient's page by row index in the patients table.

        Reloads the patients list, scrolls the infinite-scroll table until
        the row at `user_id` is loaded, extracts that patient's ID from the
        row's React props, and navigates to their patient page.

        Retries recursively on failure: a timeout waiting for the page/table
        reloads and retries with `max_retries` decremented; a preview image
        already present, or a missing row (`IndexError`), restarts from
        `user_id + 1` or `0` respectively.

        Args:
            user_id: Index of the patient row to open in the table.
            max_retries: Max retry attempts on page load/timeout errors.
                Defaults to 20.

        Raises:
            OSError: If the patients page/row can't be loaded after
                exhausting `max_retries`.
        """
    page = Session.page

    await page.reload()
    await page.wait_for_timeout(500)
    print("the start works right")

    try:
        if page.url.rstrip("/") != Url.PATIENTS.rstrip("/"):
            print("Opening data page...")
            _website = await page.goto(
            Url.PATIENTS,
            wait_until="domcontentloaded",
            timeout=10000,
            )
            Session.page = page

        row_selector =  Sel.PATIENT_ROW

        _body = await page.wait_for_selector("body", timeout=15000)
        _row = await page.wait_for_selector(row_selector, timeout=15000)
    except (TimeoutError, PlaywrightTimeoutError) as e:
        print(f"couldn't find body/row,skipping page: {e}")
        if max_retries <= 0:
            raise OSError("Window is closed or can't be seen")
        return await go_to_upload_patient_report(user_id ,max_retries -1)


    # Scroll until we have enough rows loaded to reach user_id
    # Wait for the next page
    print("I was here")
    stale_scrolls = 0
    before = 0


    while True:
            rows = await page.query_selector_all(row_selector)

            if len(rows) > user_id:
                break  # We have enough rows, stop scrolling

            # Not enough rows yet — scroll down to load more
            await rows[-1].scroll_into_view_if_needed()
            if len(rows) == before:
                stale_scrolls += 1
                if stale_scrolls >= 10:
                    return await go_to_upload_patient_report(0, max_retries-1)
                    break
            else:
                stale_scrolls = 0
            before = len(rows)


    try:
        # await rows[user_id].click()
        row_data_json = await rows[user_id].evaluate("""
        el => {
            const key = Object.keys(el).find(k => k.startsWith('__reactProps$'));
            if (!key) return null;
            const props = el[key];
            return JSON.stringify(props, (k, v) => typeof v === 'function' ? undefined : v);
        }
        """)
        import json
        row_data = json.loads(row_data_json)
        patient_id = row_data["children"][0]["props"]["children"]["props"]["row"]["original"]["ID"]
        patient_url = f"https://app.diagnocat.eu/patients/{patient_id}"


        retries = 0
        try:
            print("HELLO")
            await page.goto(patient_url, wait_until="commit", timeout=60000)
            await page.wait_for_timeout(1500)
        except PlaywrightTimeoutError as e:
            retries += 1
            print(f"Patient page timeout for {patient_url} ({retries}/{max_retries}): {e}")

            if retries > max_retries:
                raise OSError(f"Can't open {patient_url}")
            return await go_to_upload_patient_report(user_id,max_retries)

        if await check_preview_image(page):
            print("Something is wrong: the picture is already there")
            return await go_to_upload_patient_report(user_id+1,max_retries-1)



    except IndexError as e:
        print(f"User_id: {user_id} the picture wasn't there: {e} ")
        return await go_to_upload_patient_report(0,max_retries)
    return user_id
