import os
from locators import Url,Sel
from playwright.async_api import BrowserContext, TimeoutError as PlaywrightTimeoutError, Page
from dotenv import load_dotenv  # pip install python-dotenv

load_dotenv()  # loads variables from the .env file
EMAIL = os.environ["DIAGNOCAT_EMAIL"]
PASSWORD = os.environ["DIAGNOCAT_PASSWORD"]
from dataclasses import dataclass
@dataclass

class Session:
    context: BrowserContext
    page: Page                      # patient list page
    user_page: Page | None = None   # currently opened patient

    @classmethod
    def require_user_page(cls) -> Page:
        if cls.user_page is None:
            raise ValueError("user_page is not initialized")
        return cls.user_page


async def login(page: Page):
    """
       Ensure the browser session is logged in to Diagnocat.

       Navigates to the sign-in page. If the session is already
       authenticated (auto-redirect away from sign-in), skips the manual
       step. Otherwise, waits for manual login and for the browser to
       redirect to the patients page.

       Args:
           page (Page): Playwright page object used to navigate and check
               login status.
       """

    print("Checking login status...")
    Session.page = page
    await page.goto(Url.SIGN_IN, wait_until="domcontentloaded", timeout=60000)

    # If we are redirected away from sign-in, the session is still valid
    if "sign-in" not in page.url:
        print("Already logged in.")
        return

    print("Logging in automatically...")
    await page.fill('input[type="email"]', EMAIL)
    await page.fill('input[type="password"]', PASSWORD)
    await page.click('button[type="submit"]')

    try:
        await page.wait_for_url("**/patients**", timeout=60000)
        print("Login successful!")
    except PlaywrightTimeoutError:
        # Fallback: captcha or 2FA may require manual input
        print("Automatic login failed (captcha/2FA?). Please log in manually...")
        await page.wait_for_url("**/patients**", timeout=0)
async def reset_starting_page(page: Page):
    """Resets the global starting page after a failure, closing the old one.

        Called as a last resort when nothing else works and a fresh page has
        already been opened in `main`. Closes the current global `page` and
        replaces it with the newly opened `page1`.

        Args:
            page: The new page instance (already opened in `main`) that will
                replace the current global `page`.
                """
    await Session.page.close()
    Session.page = page

async def ensure_page(context: BrowserContext):
    """Reopens the patient list page if it has been closed.

        Checks whether `Session.page` is closed. If so, opens a new page in the
        given context and stores it as `Session.page`. Does nothing if the page
        is still open. Note that the new page is blank, so the caller must
        navigate and log in again if needed.

        Args:
            context: Browser context used to open the replacement page.
        """
    Session.page = await context.new_page()
    await login(Session.page)




async def remove_overlay(new_page:Page):
    """Removes the HubSpot overlay element from the page, if present.
    Args:
        new_page (Page): The page to remove the overlay from.
    """
    await new_page.evaluate(
            """
            selector => {
                const el = document.querySelector(selector);
                if (el) el.remove();
            }
            """,
            Sel.HUBSPOT_OVERLAY,
        )
