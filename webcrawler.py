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

def debug(page):
    '''A Empty function for Debug stuff'''
    buttons = page.query_selector_all("button.ConditionButton-module_container_Vda6L")
    buttons[0].hover()
    input("Press Enter to continue...")   

    # Print the full page HTML after hover so we can find the tooltip element
    html = page.inner_html("body")
    # Search for anything that appeared - look for the text you see in the tooltip
    if "Künstliche" in html or "Endodontisch" in html:
        print("Tooltip content found in DOM")
        print(html[html.find("Künstliche")-200:html.find("Künstliche")+500])

def get_user_Data(page):
    """Gets a single User Data"""
    # Gets the Buttons
    # Get all condition buttons
    buttons = page.query_selector_all("button.ConditionButton-module_container_Vda6L")

    for button in buttons:
        # Hover over each button
        button.hover()
        page.wait_for_timeout(500)  # Small pause to let hover effects render
        
        # Get the span text inside the button
        name = button.query_selector("span:first-child")
        percentage = button.query_selector("span.p3")
        if name and percentage:
            print(f"{name.inner_text()} - {percentage.inner_text()}")


def go_to_the_right_side(page):
    """Goes to the right page"""
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

    # Wait for the next page
    page.wait_for_selector("div.ReportCard-module_container_ONmLU", timeout=10000)
    page.query_selector("div.ReportCard-module_container_ONmLU").click()
    
    page.wait_for_timeout(3000)
    print(f"Now on: {page.url}")
    #get_user_Data(page)
    debug(page)
    

def main():
    with sync_playwright() as p:
        context: BrowserContext = p.chromium.launch_persistent_context(USER_DATA_DIR, headless=False)
        page = context.new_page()
        login(page)

        go_to_the_right_side(page)
        
    
main()