from playwright.sync_api._generated import BrowserContext
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright




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




def get_user_data(page,user_id):
    """Gets a single User Data"""
    # Gets the Buttons
    # Get all condition buttons
    buttons = page.query_selector_all("button.ConditionButton-module_container_Vda6L")
    canvas =  page.query_selector("canvas")
    page.wait_for_timeout(3000)  
    for i, button in enumerate(buttons):
        # Hover over each button
        button.hover()
        page.wait_for_timeout(300)  # Small pause to let hover effects render
        # Take a screenshot of just the canvas element
        
        # Get the span text inside the button
        name = button.query_selector("span:first-child")
        percentage = button.query_selector("span.p3")
        picture_path = f"output/{user_id}-{i}-{name.inner_text()}-{percentage.inner_text()}.png" 
        print(f"Saved {picture_path}")
        canvas.screenshot(path=picture_path)


def deactiveted_showButtons(page):

    buttons = page.query_selector("button.MaskFilterButton-module_container_EFNpE")

    for button in buttons:
        is_active = not button.is_enabled()  # disabled = active/pressed
        print(f"{button.text}: {'ACTIVE' if is_active else 'inactive'}")

def go_to_patient_report(page,user_id):
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

    rows[user_id].click()
    print("Clicked first patient row")

    # Wait for the patient detail page to load
    page.wait_for_timeout(3000)
    print(f"Now on: {page.url}")

    # Wait for the next page
    page.wait_for_selector("div.ReportCard-module_container_ONmLU", timeout=10000)
    page.query_selector("div.ReportCard-module_container_ONmLU").click()
    
    page.wait_for_timeout(3000)

    print(f"Now on: {page.url}")
    


def get_refrence_image(page,user_id):
    """gets a empty Image for refrence"""
    canvas =  page.query_selector("canvas")
    picture_path = f"output/{user_id}.png" 
    canvas.screenshot(path=picture_path)
    print(f"Saved {picture_path}")
    