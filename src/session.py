from locators import Url,Sel
from playwright.async_api import BrowserContext
from playwright.async_api import Page

from dataclasses import dataclass

@dataclass
class Session:
    context: BrowserContext
    page: Page                      # patient list page
    user_page: Page | None = None   # currently opened patient

    def require_user_page(self) -> Page:
        if self.user_page is None:
            raise ValueError("user_page is not initialized")
        return self.user_page


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
    _website = await Session.page.goto(Url.SIGN_IN)

    # If we are already logged in, the site might auto-redirect to /patients
    if "sign-in" not in Session.page.url:
        print("Already logged in. Skipping manual step.")
    else:
        print("Please log in manually in the browser window...")
        # Wait for the URL to change to the patients page
        await Session.page.wait_for_url("**/patients**", timeout=0)
        # Crucial: Wait a moment for cookies to sync to the 'user_data' folder
        print("Login successful!")

async def reset_starting_page(page: Page):
    """Resets the global starting page after a failure, closing the old one.

        Called as a last resort when nothing else works and a fresh page has
        already been opened in `main`. Closes the current global `page` and
        replaces it with the newly opened `page1`.

        Args:
            page: The new page instance (already opened in `main`) that will
                replace the current global `page`.
                """
    await page.close()
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
    if Session.page.is_closed():
        Session.page = await context.new_page()




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
