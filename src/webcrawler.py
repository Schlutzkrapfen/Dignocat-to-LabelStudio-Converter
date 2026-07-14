import os
from typing import cast

from playwright.async_api import ElementHandle, Locator, Page
from controll import find_duplicates_of


async def login(page: Page):
    """Handles the manual login and ensures the session is saved."""
    print("Checking login status...")
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


async def get_tooth_descriptions(page: Page) -> list[dict[str, str]]:
    """returns what all teeth have for a name"""
    divs = await page.locator("div.ConditionTitle-module_container_vpIP9").all()
    tooth_types: list[dict[str, str]] = []
    for div in divs:
        part = await div.inner_text()
        parts = part.split()
        tooth_types.append({"type": parts[0], "id": parts[1]})
    return tooth_types


async def get_theeh_picture(page: Page, teeth_id: str, user_id: str) -> str:
    picture_path = f"output/teeth-screenshoots/{user_id}-{teeth_id}.png"

    if os.path.exists(picture_path):
        return picture_path

    section = page.locator(f'section[id$="{teeth_id}"]')
    div = section.locator("div.ConditionTitle-module_container_vpIP9")
    await div.hover()

    canvas = page.locator("canvas").first
    await take_screenshot(page,canvas,picture_path)
    await page.evaluate("""
      () => new Promise(resolve => {
        requestAnimationFrame(() => requestAnimationFrame(resolve));
      })
    """)
    _screenshot = await canvas.screenshot(path=picture_path)

    return picture_path


async def get_thooth_id(page: Page, thoot_id: int)->str:
    thoot_id = int(thoot_id)
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
            print(id)
            section_id:str = cast(str, await section.evaluate("el => el.id"))
            return section_id[-4:]

    return "0000"


async def find_page(page: Page,i:int,page_amount:int,output_dir:str)->int:
    duplictas: list[str] = ["", "", ""]
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
        await go_to_patient_report(page, user)
        user_id:int = page_amount - i - 1
        await deactivated_showButtons(page)
        refrence_image_path = await get_refrence_image(
            page, user_id, skip_if_exist=False
        )
        if refrence_image_path is None:

            raise ValueError("There is no Refrance Image")
        duplictas = find_duplicates_of(refrence_image_path, output_dir)
        print(f"Duplicated ID: {i} with {duplictas}")
        already_skipped.append(user)
        if user_id < 0:
            raise ValueError("couldn't find a other duplicate")
    return user_id


async def get_user_data(page: Page, user_id:int) -> list[str]:
    """Gets a single User Data"""
    # Gets the Buttons
    # Get all condition buttons
    buttons = await page.query_selector_all(
        "button.ConditionButton-module_container_Vda6L"
    )
    canvas = await page.query_selector("canvas")

    saved_screenshoots: list[str] = []
    for i, button in enumerate(buttons):
        await button.hover()
        section_id:str = cast(str,await button.evaluate("el => el.closest('section').id"))
        last_4 = section_id[-4:]

        name = await button.query_selector("span:first-child")
        percentage = await button.query_selector("span.p3")
        if name is None or percentage is None or canvas is None:
            print("something went wrong while Fetching, lets try again.")
            return await get_user_data(page, user_id)

        picture_path = f"output/screenshots/{user_id}_{i}_{await name.inner_text()}_{await percentage.inner_text()}_{last_4}.png"
        if os.path.exists(picture_path):
            print(f"Skipping {picture_path}, already exists")
            saved_screenshoots.append(picture_path)
            continue
        print(f"Saved {picture_path}")
        saved_screenshoots.append(picture_path)
        await take_screenshot(page,canvas,picture_path)

    return saved_screenshoots


async def take_screenshot(page:Page,canvas:ElementHandle|Locator,path:str ):
    await page.evaluate("""
          () => new Promise(resolve => {
            requestAnimationFrame(() => requestAnimationFrame(resolve));
          })
        """)
    _screenshot = await canvas.screenshot(path=path)


async def deactivated_showButtons(page: Page):
    buttons = await page.query_selector_all(
        "button.MaskFilterButton-module_container_EFNpE"
    )
    for button in buttons:
        is_disabled =cast(bool, await page.evaluate("btn => btn.hasAttribute('disabled')", button))

        if is_disabled:
            continue

        classes =cast(list[str], await page.evaluate("btn => Array.from(btn.classList)", button))

        is_active = len(classes) > 2

        if is_active:
            await button.click()


async def get_patient_amount(page: Page):
    """Gets the Patient amount from Diagnocat page"""
    """TODO:Change this to read the page amount from the filter"""
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


async def go_to_patient_report(page: Page, user_id: int):
    """Goes to the right page"""
    print("Opening data page...")
    _website = await page.goto(
        "https://app.diagnocat.eu/patients",
        wait_until="domcontentloaded",
        timeout=10000,
    )
    _body = await page.wait_for_selector("body", timeout=15000)

    row_selector = "tr.TableWithInfiniteScroll-module_tableRow_7Ru4e"
    _row = await page.wait_for_selector(row_selector, timeout=10000)

    # Scroll until we have enough rows loaded to reach user_id
    while True:
        rows = await page.query_selector_all(row_selector)

        if len(rows) > user_id:
            break  # We have enough rows, stop scrolling

        # Not enough rows yet — scroll down to load more
        await rows[-1].scroll_into_view_if_needed()

    await rows[user_id].click()
    print("Clicked first patient row")

    print(f"Now on: {page.url}")

    # Wait for the next page
    try:
        _div = await page.wait_for_selector("div.ReportCard-module_container_ONmLU")

        button = await page.query_selector("div.ReportCard-module_container_ONmLU")
        if button is None:
            raise Exception("Picture Isn't here")
        await button.click()
    except Exception as e:
        print(f"the picture wasn't there: {e} ")
        # TODO: find a more efficent way to go true the loop if it failed
        await go_to_patient_report(page, user_id + 1)
        return

    await remove_overlay(page)
    print(f"Now on: {page.url}")


async def remove_overlay(page: Page):
    await page.evaluate("""
    const el = document.querySelector('#hs-web-interactives-top-anchor');
    if (el) el.remove();
""")


async def get_refrence_image(page: Page, user_id:int, skip_if_exist: bool = True):
    """gets a empty Image for refrence"""
    picture_path = f"output/{user_id}.png"

    if not os.path.exists(picture_path) or not skip_if_exist:
        await deactivated_showButtons(page)
        canvas = await page.query_selector("canvas")
        if canvas is None:
            print("ERROR")
            return
        await take_screenshot(page,canvas,picture_path)
        print(f"Saved {picture_path}")
    else:
        print(f"Screenshot already exists: {picture_path}")

    return picture_path
