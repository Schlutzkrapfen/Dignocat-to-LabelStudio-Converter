from playwright.sync_api._generated import BrowserContext
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


from playwright.sync_api import sync_playwright

USER_DATA_DIR = 'user_data' 

def login(page):    
    """Handles the manual login and ensures the session is saved."""
    print("Checking login status...")
    
    page.goto('https://app.diagnocat.eu/sign-in')

    # If we are already logged in, the site might auto-redirect to /patients
    if "sign-in" not in page.url:
        print("Already logged in. Skipping manual step.")
    else:
        print("Please log in manually in the browser window...")
        # Wait for the URL to change to the patients page
        page.wait_for_url("**/patients**", timeout=0) 
        # Crucial: Wait a moment for cookies to sync to the 'user_data' folder
        page.wait_for_timeout(2000)
        print("Login successful!")


def get_patient_data(page):
    """Opens the saved session and extracts text."""
    print("Opening data page...")
    page.goto('https://app.diagnocat.eu/patients', wait_until="domcontentloaded", timeout=60000)
    page.wait_for_selector("body", timeout=15000)
    page.wait_for_timeout(3000)

    # --- Click the first patient row ---
    row_selector = "tr.TableWithInfiniteScroll-module_tableRow_7Ru4e"
    page.wait_for_selector(row_selector, timeout=10000)
    
    rows = page.query_selector_all(row_selector)
    print(f"Found {len(rows)} patient rows")

    # Click the first row (index 0), second would be index 1, third index 2
    rows[0].click()
    print("Clicked first patient row")

    # Wait for the patient detail page to load
    page.wait_for_timeout(3000)
    print(f"Now on: {page.url}")

    # Extract text from the detail page
    all_text = page.inner_text('body')
    print(all_text[:1000])

def main():
    with sync_playwright() as p:
        context: BrowserContext = p.chromium.launch_persistent_context(USER_DATA_DIR, headless=False)
        page = context.new_page()
        login(page)
        get_patient_data(page)
    
main()