import os
from pathlib import Path
from typing import cast
from playwright.async_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

from playwright.async_api import ElementHandle,   Page
from controll import find_duplicates_of


page:Page
async def login(page1: Page):
    """
       Ensure the browser session is logged in to Diagnocat.

       Navigates to the sign-in page. If the session is already
       authenticated (auto-redirect away from sign-in), skips the manual
       step. Otherwise, waits for manual login and for the browser to
       redirect to the patients page.

       Args:
           page1 (Page): Playwright page object used to navigate and check
               login status.
       """
    print("Checking login status...")
    global page
    page = page1
    _website = await page.goto("https://app.diagnocat.eu/sign-in")

    # If we are already logged in, the site might auto-redirect to /patients
    if "sign-in" not in page.url:
        print("Already logged in. Skipping manual step.")
    else:
        print("Please log in manually in the browser window...")
        # Wait for the URL to change to the patients page
        await page.wait_for_url("**/patients**", timeout=0)
        # Crucial: Wait a moment for cookies to sync to the 'user_data' folder
        print("Login successful!")


async def get_tooth_descriptions() -> list[dict[str, str]]:
    """Extracts tooth names and identifiers from the page.


        Returns:
            A list of dictionaries, where each dictionary contains the "type"
            and "id" of a tooth.
        """
    divs = await page.locator("div.ConditionTitle-module_container_vpIP9").all()
    tooth_types: list[dict[str, str]] = []
    for div in divs:
        part = await div.inner_text()
        parts = part.split()
        tooth_types.append({"type": parts[0], "id": parts[1]})
    return tooth_types


async def get_theeh_picture( teeth_id: str, user_id: int) -> Path:
    """Retrieves or generates a screenshot of a specific tooth's canvas.

        Checks if a screenshot for the given tooth and user already exists on
        disk. If so, returns the cached file path immediately. Otherwise,
        locates the corresponding section on the page, hovers over its title
        to trigger the canvas rendering, waits for the canvas element to
        appear, and captures a screenshot of it.

        Args:
            teeth_id: The identifier of the tooth, used to locate the
                corresponding section on the page and to build the output
                filename.
            user_id: The identifier of the user, used to build the output
                filename.

        Returns:
            The file path to the tooth's screenshot, either freshly captured
            or previously cached.

        Raises:
            ValueError: If no canvas element is found on the page after
                hovering over the tooth's title.
        """
    picture_path = Path(f"output/teeth-screenshoots/{user_id}-{teeth_id}.png")

    if picture_path.exists():
        return picture_path

    section = page.locator(f'section[id$="{teeth_id}"]')
    div = section.locator("div.ConditionTitle-module_container_vpIP9")
    await div.hover()

    canvas = await page.wait_for_selector("canvas")
    if canvas is None:
        raise ValueError("Got no Canvas")
    await take_screenshot(canvas,picture_path)
    return picture_path


async def get_thooth_id( thoot_id: int)->str:
    """Finds the trailing 4 characters of a section's ID matching the given tooth ID.

        This function searches through dental widget cards on the page, extracts
        the numeric identifier from their condition titles, and matches it against
        the requested tooth_id.

        Args:
            thoot_id: The numerical ID of the tooth to locate.

        Returns:
            The last 4 characters of the matching section's HTML id attribute,
            or raises a Valuerror if no match is found.
        Raises:
                   ValueError: If no section matching the given tooth ID is found.
         """
    sections = await page.locator("section.WidgetCard-module_container_1PPfu").all()
    for section in sections:
        div = section.locator("div.ConditionTitle-module_container_vpIP9")
        if await div.count() == 0:
            continue
        token = await div.inner_text()
        tokens = token.split()
        # check for just numbers
        numeric_tokens = [t for t in tokens if t.isdigit()]
        if not numeric_tokens:
            continue
        id = int(numeric_tokens[-1])
        if id == thoot_id:
            section_id:str = cast(str, await section.evaluate("el => el.id"))
            return section_id[-4:]

    raise ValueError(f"Couldn't find thooth {thoot_id}")


async def find_page(i:int,page_amount:int,output_dir:Path)->int:
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
    duplictas: list[Path] = [Path("")]
    already_skipped: list[int] = []
    duplictas_i = 0
    user_id = 0
    while len(duplictas) > 0:
        user = i + duplictas_i
        duplictas_i += 1

        if user in already_skipped:
            print(f"User {user} already testet")
            continue
        if page_amount - user < 0:
            raise ValueError("didn't find any doubles")
        print(f"USERID = {user}")

        user_id:int = page_amount - i - 1

        try:
            await go_to_patient_report( user)
        except OSError as e:
            print(e)
            raise OSError(e)
        try:
            await deactivated_show_buttons()
        except PlaywrightTimeoutError:
            continue
        try:
            refrence_image_path = await get_refrence_image(
                 user_id, skip_if_exist=False
            )
        except LookupError as e:
            print(f"Error:{e}")
            continue

        if refrence_image_path is None:

            raise ValueError("There is no Refrance Image")
        duplictas = find_duplicates_of(refrence_image_path, output_dir)
        print(f"Duplicated ID: {i} with {duplictas}")
        already_skipped.append(user)
        if user_id < 0:
            raise ValueError("couldn't find a other duplicate")
    return user_id


async def get_user_screenshoots( user_id: int) -> list[Path]:
    """
       Screenshot each condition button's canvas view for a user.
       For every condition button on the page: hovers it, reads its name,
       percentage, and enclosing section id, then screenshots the shared
       <canvas> to `output/screenshots/{user_id}_{i}_{name}_{percentage}_{section_suffix}.png`.
       Skips screenshots that already exist on disk.
       Args:
           user_id: Used to namespace output filenames.
       Returns:
           List of screenshot file paths, one per condition button.
       """
    # Gets the Buttons
    buttons = page.locator("button.ConditionButton-module_container_Vda6L")
    count = await buttons.count()
    canvas = await page.query_selector("canvas")

    if count == 0 or canvas is None:
        print("something went wrong while Fetching, lets try again.")
        return await get_user_screenshoots(user_id)

    saved_screenshoots: list[Path] = []
    for i in range(count):
        button = buttons.nth(i)
        await button.hover()

        section_id: str = cast(str, await button.evaluate("el => el.closest('section').id"))
        last_4 = section_id[-4:]

        name = button.locator("span:first-child")
        percentage = button.locator("span.p3")

        if await name.count() == 0 or await percentage.count() == 0:
            print("something went wrong while Fetching, lets try again.")
            return await get_user_screenshoots( user_id)

        picture_path =Path(f"output/screenshots/{user_id}_{i}_{await name.inner_text()}_{await percentage.inner_text()}_{last_4}.png")

        if os.path.exists(picture_path):
            print(f"Skipping {picture_path}, already exists")
            saved_screenshoots.append(picture_path)
            continue

        print(f"Saved {picture_path}")
        saved_screenshoots.append(picture_path)
        await take_screenshot( canvas, picture_path)

    return saved_screenshoots


async def take_screenshot(canvas:ElementHandle,path:Path,max_retries: int = 10 ):
    """Captures a screenshot of a canvas element and saves it to disk.

        Waits briefly for the page to settle and for two animation frames to
        pass (ensuring any pending rendering/paint operations have completed)
        before capturing the screenshot of the given canvas element. If the
        screenshot times out, the function retries up to `max_retries` times
        before giving up.

        Args:
            canvas: The ElementHandle representing the canvas element to
                capture.
            path: The file path where the screenshot will be saved.
            max_retries: Maximum number of retry attempts if the screenshot
                times out. Defaults to 10.
        Raises:
            TimeoutError: If the screenshot still fails after exhausting all
                retry attempts.
        """

    await page.evaluate("""
          () => new Promise(resolve => {
            requestAnimationFrame(() => requestAnimationFrame(resolve));
          })
        """)
    await page.wait_for_timeout(500)
    try:
        _screenshot = await canvas.screenshot(path=str(path))
    except (PlaywrightTimeoutError, PlaywrightError) as e:
        if max_retries <= 0:
                    print(f"Couldn't get screenshot, no retries left:{e}")
                    raise TimeoutError
        print(f"Couldn't get screenshot, trying again {e}")
        await take_screenshot( canvas, path, max_retries - 1)


async def deactivated_show_buttons() :
    """Waits for and clicks active, enabled filter buttons on the page.

    Raises:
        TimeoutError: if the selector can't be selected
    """
    selector = "button.MaskFilterButton-module_container_EFNpE"

    try:
        await page.wait_for_selector(selector, state="visible")
    except PlaywrightTimeoutError:
        raise PlaywrightTimeoutError("waitforselector didn't work")

    buttons = page.locator(selector)
    count = await buttons.count()

    for i in range(count):
        button = buttons.nth(i)

        if not await button.is_enabled():
            continue

        classes = cast(
            list[str],
            await button.evaluate("btn => Array.from(btn.classList)"),
        )

        if len(classes) > 2:
            await button.click()


async def get_patient_amount()->int:
    """Gets the total patient count from Diagnocat.

       Tries to read the count directly from the active filter badge first.
       If that element isn't found (or raises a Playwright `Error`), falls
       back to scrolling the patient table until no new rows load for
       `max_stable_checks` consecutive polls, then returns the row count.


       Returns:
           int: The total number of patients.

       Raises:
           LookupError: If the filter badge amount is 0, or if the
               filter badge element could not be located (this is caught
               internally and triggers the scroll-based fallback).
       """
    try:
        amount_el = await page.wait_for_selector(
            "span.Filters-module_amount_zjpHX.Filters-module_amountActive_ysGOs"
        )
        if amount_el:
            amount_text = (await amount_el.inner_text()).strip()
            amount = int(amount_text)  # 697
            print(f"Active filter amount: {amount}")
            if amount == 0:
                raise LookupError("amount of 0")
            return(amount)
        else:
            amount = None
            raise LookupError("No type found")
    except LookupError as e :
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


async def go_to_patient_report( user_id: int,max_retries:int=20):
    """Navigates to a specific patient's report page.

        Opens the patients list page, scrolls through the infinite-scroll
        table until the row for `user_id` is loaded, clicks it to open the
        patient, and then opens the report card. Retries on timeouts/errors
        (reloading the patients page) up to `max_retries` times, and on a
        missing report card, retries with the next `user_id`.

        Args:

            user_id (int): Index of the patient row to open in the table.
            max_retries (int): Maximum number of retry attempts on page
                load/timeout errors. Defaults to 20.


        Raises:
            OSError: If the page can't be loaded/seen after exhausting
                `max_retries`.
            ValueError: If no users are left to retry after exhausting
                `max_retries` on a report-card timeout.
        """
    print("Opening data page...")
    try:
        _website = await page.goto(
        "https://app.diagnocat.eu/patients",
        wait_until="domcontentloaded",
        timeout=10000,
        )
        row_selector = "tr.TableWithInfiniteScroll-module_tableRow_7Ru4e"

        _body = await page.wait_for_selector("body", timeout=15000)
        _row = await page.wait_for_selector(row_selector, timeout=15000)
    except (PlaywrightTimeoutError, PlaywrightError):
        if max_retries <= 0:
            raise OSError("Window is closed or can't be seen")
        await go_to_patient_report(user_id,max_retries -1)
        return
    # Scroll until we have enough rows loaded to reach user_id
    # Wait for the next page
    try:
        while True:
               rows = await page.query_selector_all(row_selector)

               if len(rows) > user_id:
                   break  # We have enough rows, stop scrolling

               # Not enough rows yet — scroll down to load more
               await rows[-1].scroll_into_view_if_needed()

        await rows[user_id].click()
        print("Clicked first patient row")

        print(f"Now on: {page.url}")
        _div = await page.wait_for_selector("div.ReportCard-module_container_ONmLU")

        button = await page.query_selector("div.ReportCard-module_container_ONmLU")
        if button is None:
            raise ValueError("Picture Isn't here")
        await button.click()
    except ValueError as e:
        print(f"the picture wasn't there: {e} ")
        # TODO: find a more efficent way to go true the loop if it failed
        await go_to_patient_report( user_id + 1)
        return
    except PlaywrightTimeoutError:
        if max_retries <= 0:
            raise ValueError("No Users Left")
        await go_to_patient_report(user_id,max_retries -1)
        return

    await remove_overlay()
    print(f"Now on: {page.url}")


async def remove_overlay():
    """Removes the HubSpot overlay element from the page, if present.

        Args:
        """
    await page.evaluate("""
    const el = document.querySelector('#hs-web-interactives-top-anchor');
    if (el) el.remove();
""")


async def get_refrence_image(user_id:int, skip_if_exist: bool = True)-> Path:
    """gets a empty Image for refrence
    Args:
            user_id (int): Identifier of the user, used to build the
                output file path.
            skip_if_exist (bool): If True, skips regenerating the
                screenshot when a file already exists at the target path.
                Defaults to True.
   Returns:
                       Path: Path to the reference screenshot, either newly created
                       or already existing.
    Raises:
        LookupError: Couldn't find the canvas
    """
    picture_path = Path(f"output/{user_id}.png")

    if not os.path.exists(picture_path) or not skip_if_exist:
        await deactivated_show_buttons()
        canvas = await page.wait_for_selector("canvas")
        if canvas is None:
            raise LookupError("Got no Canvas")
        await take_screenshot(canvas,picture_path)
        print(f"Saved {picture_path}")
    else:
        print(f"Screenshot already exists: {picture_path}")

    return picture_path
