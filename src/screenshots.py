
import asyncio
import os
from pathlib import Path
from typing import cast

from playwright.async_api import ElementHandle, Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

from session import Session


async def get_anatomie(user_id: int) -> list[Path]:
    """Captures a screenshot of the canvas for each anatomy mask filter button.

        Waits for the mask filter buttons to become visible, then iterates over
        them. For each button, it toggles the mask on, screenshots the canvas,
        and toggles the mask off again. Buttons that time out on click are
        skipped.

        Args:
            user_id: The user ID, used as the first part of each screenshot
                filename.

        Returns:
            list[Path]: Paths of the saved screenshots, one per processed button.
                Filenames follow the pattern
                `output/{user_id}_{110000 + index}_{button_text}_100%_0000.png`.

        Raises:
            ValueError: If the global `user_page` is None, or if no canvas
                element is found after clicking a button.
            TimeoutError: If the mask filter buttons do not become
                visible in time.
        """
    selector = "button.MaskFilterButton-module_container_EFNpE"
    try:
        user_page = Session.require_user_page()

        await user_page.wait_for_selector(selector, state="visible")
    except PlaywrightTimeoutError:
        raise PlaywrightTimeoutError("waitforselector didn't work")

    buttons =  user_page.locator(selector)
    count = await buttons.count()
    paths:list[Path] = []
    names = []
    for i in range(count):
        btn = buttons.nth(i)
        text = (await btn.inner_text()).strip()
        names.append(text)
        try:
            await buttons.nth(i).click()
            canvas = await user_page.query_selector("canvas")
        except PlaywrightTimeoutError:
            continue
        if canvas is None:
            raise ValueError("canvas is None")
        #TODO: MAKE BETTER FIX
        input  = i+  110000

        path :Path = Path(f"output/teeth-screenshots/{user_id}_{input}_{text}_{"100%"}_{"0000"}.png")
        await take_screenshot(canvas=canvas, path=path)
        paths.append(path)
        try:
            await buttons.nth(i).click()
        except PlaywrightTimeoutError:
            continue
        print(f"Saved the picture: {path}")
    return paths

async def get_user_screenshoots( user_id: int) -> list[Path]:
    """Screenshots each condition button's canvas view for a user.

        For every condition button: hovers it, reads its name, percentage,
        and section id, then screenshots the shared <canvas> to
        `output/screenshots/{user_id}_{i}_{name}_{percentage}_{section_suffix}.png`.
        Existing screenshots are skipped. Retries recursively if no buttons/canvas
        are found, or if a button lacks name/percentage text.

        Args:
            user_id: Used to namespace output filenames.

        Returns:
            List of screenshot file paths, one per condition button.

        """
    # Gets the Buttons
    user_page = Session.require_user_page()
    buttons = user_page.locator("button.ConditionButton-module_container_Vda6L")
    count = await buttons.count()
    canvas = await user_page.query_selector("canvas")

    if count == 0 or canvas is None:
        print("No Buttons or Canvas found, lets try again.")

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
            print("No name or percentage found, lets try again.")
            return await get_user_screenshoots(user_id)

        picture_path =Path(f"output/screenshots/{user_id}_{i}_{await name.inner_text()}_{await percentage.inner_text()}_{last_4}.png")

        if await asyncio.to_thread(os.path.exists, picture_path):
            print(f"Skipping {picture_path}, already exists")
            saved_screenshoots.append(picture_path)
            continue

        print(f"Saved {picture_path}")
        saved_screenshoots.append(picture_path)
        await take_screenshot(canvas, picture_path)

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
    user_page = Session.require_user_page()
    await user_page.evaluate("""
          () => new Promise(resolve => {
            requestAnimationFrame(() => requestAnimationFrame(resolve));
          })
        """)
    await user_page.wait_for_timeout(500)
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
            user_page = Session.require_user_page()
            await user_page.wait_for_selector(selector, state="visible")
        except PlaywrightTimeoutError:
            raise PlaywrightTimeoutError("waitforselector didn't work")

        buttons =  user_page.locator(selector)
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

async def get_refrence_image(picture_path: Path, skip_if_exist: bool = True,)-> Path:
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
    if skip_if_exist and await asyncio.to_thread(os.path.exists, picture_path):
        print(f"Screenshot already exists: {picture_path}")
        return picture_path
    else:
        user_page = Session.require_user_page()
        await user_page.mouse.move(0, 0)
        try:
            await deactivated_show_buttons()
        except PlaywrightTimeoutError as e:
            raise LookupError(f"couldn't find buttons: {e}")
        canvas = await user_page.wait_for_selector("canvas")
        if canvas is None:
            raise LookupError("Got no Canvas")
        await take_screenshot(canvas,picture_path)
        print(f"Saved {picture_path}")
        return picture_path


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

    if await asyncio.to_thread(picture_path.exists):
        return picture_path

    user_page = Session.require_user_page()

    section = user_page.locator(f'section[id$="{teeth_id}"]')
    div = section.locator("div.ConditionTitle-module_container_vpIP9")
    await div.hover()

    canvas = await user_page.wait_for_selector("canvas")
    if canvas is None:
        raise ValueError("Got no Canvas")
    await take_screenshot(canvas,picture_path)
    return picture_path
