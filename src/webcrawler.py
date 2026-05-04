import os
import logging


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

def get_tooth_descriptions(page):
    '''returns what all teeth have for a name'''
    divs = page.locator('div.ConditionTitle-module_container_vpIP9').all()
    tooth_types = []
    for div in divs:
        parts = div.inner_text().split()
        tooth_types.append({
            "type": parts[0],
            "id": parts[1]
        })
    return tooth_types

    
def get_theeh_picture(page, teeth_id, user_id):
    picture_path = f"output/teeth-screenshoots/{user_id}-{teeth_id}.png"
    
    if os.path.exists(picture_path):
        return picture_path
    
    section = page.locator(f'section[id$="{teeth_id}"]')
    div = section.locator('div.ConditionTitle-module_container_vpIP9')
    div.hover()
    
    page.wait_for_timeout(300)  # Small pause to let hover effects render
    
    canvas = page.locator("canvas").first  
    canvas.screenshot(path=picture_path)
    
    return picture_path

def get_thooth_id(page, thoot_id):
    thoot_id = int(thoot_id)
    sections = page.locator('section.WidgetCard-module_container_1PPfu').all()
    for section in sections:
        div = section.locator('div.ConditionTitle-module_container_vpIP9')
        if div.count() == 0:
            continue
        tokens = div.inner_text().split()
        numeric_tokens = [t for t in tokens if t.isdigit()]
        if not numeric_tokens:
            continue
        id = int(div.inner_text().split()[-1])
        if id == thoot_id:
            print(id)
            section_id = section.evaluate("el => el.id")
            return section_id[-4:]

    
    
    return "0000"

def get_user_data(page,user_id):
    """Gets a single User Data"""
    # Gets the Buttons
    # Get all condition buttons
    buttons = page.query_selector_all("button.ConditionButton-module_container_Vda6L")
    canvas =  page.query_selector("canvas")

    saved_screenshoots = []
    for i, button in enumerate(buttons):
        button.hover()
        section_id =  button.evaluate("el => el.closest('section').id")
        last_4 = section_id[-4:]

        name = button.query_selector("span:first-child")
        percentage = button.query_selector("span.p3")
        picture_path = f"output/screenshots/{user_id}_{i}_{name.inner_text()}_{percentage.inner_text()}_{last_4}.png" 
        if os.path.exists(picture_path):
            print(f"Skipping {picture_path}, already exists")
            saved_screenshoots.append(picture_path)
            continue
        page.wait_for_timeout(300)  # Small pause to let hover effects render
        print(f"Saved {picture_path}")
        saved_screenshoots.append(picture_path)
        canvas.screenshot(path=picture_path)
    
    return saved_screenshoots

def deactivated_showButtons(page):
    page.wait_for_timeout(3000)  
    buttons = page.query_selector_all("button.MaskFilterButton-module_container_EFNpE")
    for button in buttons:
        is_disabled = page.evaluate("btn => btn.hasAttribute('disabled')", button)
        
        if is_disabled:
            continue
        
        classes = page.evaluate("btn => Array.from(btn.classList)", button)
        is_active = len(classes) > 2
        
        if  is_active:
            button.click()


def get_patient_amount(page):
    '''Gets the Patient amount from Diagnocat page'''
    row_selector = "tr.TableWithInfiniteScroll-module_tableRow_7Ru4e"
    
    page.wait_for_selector(row_selector, timeout=10000)
    
    # Keep scrolling until no new rows appear
    previous_count = 0
    while True:
        rows = page.query_selector_all(row_selector)
        current_count = len(rows)
        
        if current_count == previous_count:
            break  # No new rows loaded, we're done
        
        previous_count = current_count
        
        # Scroll the last row into view to trigger loading
        rows[-1].scroll_into_view_if_needed()
        page.wait_for_timeout(1500)  # Wait for new rows to load
    
    return current_count

def go_to_patient_report(page,user_id):
    """Goes to the right page"""
    print("Opening data page...")
    page.goto('https://app.diagnocat.eu/patients', wait_until="domcontentloaded", timeout=60000)
    page.wait_for_selector("body", timeout=15000)

    row_selector = "tr.TableWithInfiniteScroll-module_tableRow_7Ru4e"
    page.wait_for_selector(row_selector, timeout=10000)
    
     # Scroll until we have enough rows loaded to reach user_id
    while True:
        rows = page.query_selector_all(row_selector)
        
        if len(rows) > user_id:
            break  # We have enough rows, stop scrolling
        
        # Not enough rows yet — scroll down to load more
        rows[-1].scroll_into_view_if_needed()
        page.wait_for_timeout(1500)

    rows[user_id].click()
    print("Clicked first patient row")

    print(f"Now on: {page.url}")

    # Wait for the next page
    page.wait_for_selector("div.ReportCard-module_container_ONmLU", timeout=10000)
    page.query_selector("div.ReportCard-module_container_ONmLU").click()
    

    remove_overlay(page)
    print(f"Now on: {page.url}")
    

def remove_overlay(page):
    page.evaluate("""
    const el = document.querySelector('#hs-web-interactives-top-anchor');
    if (el) el.remove();
""")

def get_refrence_image(page, user_id):
    """gets a empty Image for refrence"""
    picture_path = f"output/{user_id}.png"
    
    if not os.path.exists(picture_path):
        deactivated_showButtons(page)
        canvas = page.query_selector("canvas")
        canvas.screenshot(path=picture_path)
        print(f"Saved {picture_path}")
    else:
        print(f"Screenshot already exists: {picture_path}")
    
    return picture_path