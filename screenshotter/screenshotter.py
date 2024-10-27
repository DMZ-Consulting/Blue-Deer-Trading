from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import time
import os
import requests
import json
from contextlib import ExitStack
from selenium.webdriver.chrome.options import Options

def setup_driver():
    """Set up Chrome WebDriver with headless mode and VPS-friendly options"""
    options = Options()
    options.add_argument('--headless=new')  # Enable new headless mode
    options.add_argument('--no-sandbox')  # Required for running as root on VPS
    options.add_argument('--disable-dev-shm-usage')  # Handle limited shared memory on VPS
    options.add_argument('--disable-gpu')  # Disable GPU hardware acceleration
    options.add_argument('--window-size=1920,1080')  # Set a standard resolution
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-extensions')
    options.add_argument('--remote-debugging-port=9222')

    return webdriver.Chrome(options=options)

def take_table_screenshot(driver, filename):
    """Take a screenshot of the trades table"""
    table = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
    )
    # Scroll table into view
    driver.execute_script("arguments[0].scrollIntoView();", table)
    time.sleep(1)  # Allow time for any animations
    table.screenshot(f"screenshots/{filename}")

def change_status_to_open2(driver):
    """Change all closed statuses to open"""
    status_selector = Select(driver.find_element(By.CSS_SELECTOR, "select[name='status-selector']"))
    status_selector.select_by_visible_text("Open")

def change_status_to_open(driver):
    """Change all closed statuses to open"""
    # Locate the button and click it to open the combo box
    button = driver.find_element(By.CSS_SELECTOR, "button[role='combobox']")
    button.click()
    
    # Wait for the options to be visible and select the "Open" option
    open_option = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//span[text()='Open']"))
    )
    open_option.click()

def select_trade_group(driver, group_value):
    """Safely select a trade group with retry logic"""
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            # Wait for and get fresh reference to select element
            trade_group_select = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "trade-group-selector"))
            )
            select = Select(trade_group_select)
            
            # Get current selection
            current_value = select.first_selected_option.get_attribute('value')
            if current_value == group_value:
                print(f"Already on {group_value}")
                return True
                
            select.select_by_value(group_value)
            print(f"Selected trade group: {group_value}")
            time.sleep(2)  # Wait for page update
            return True
            
        except Exception as e:
            if attempt == max_attempts - 1:
                print(f"Failed to select trade group {group_value}: {str(e)}")
                return False
            time.sleep(1)
            continue

def capture_trade_groups(driver):
    """Take screenshots for each trade group in the Day Trader selector"""
    day_trader_select = Select(driver.find_element(By.CSS_SELECTOR, "select[id='trade-group-selector']"))
    groups = [option.text for option in day_trader_select.options]
    
    for group in groups:
        day_trader_select.select_by_visible_text(group)
        time.sleep(1)  # Allow time for table to update
        group_str = group.lower().replace(" ", "_")
        take_table_screenshot(driver, f"{group_str}_open.png")

def take_portfolio_screenshot(driver, filename):
    """Take a screenshot of the portfolio and reports sections"""
    try:
        # Wait for page to stabilize
        time.sleep(2)
        
        # Find the main container that holds both portfolio and reports
        main_content = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "portfolio-page"))
        )
        
        # Take full page screenshot
        driver.execute_script("arguments[0].scrollIntoView();", main_content)
        main_content.screenshot(f"screenshots/{filename}")
        print(f"Screenshot saved: {filename}")
        
    except Exception as e:
        print(f"Error taking screenshot: {str(e)}")
        raise e
    
def navigate_to_portfolio(driver):
    """Navigate to portfolio view with retry logic"""
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            # Find and click Portfolio View link
            portfolio_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Portfolio View"))
            )
            portfolio_link.click()
            print("Navigated to Portfolio View")
            time.sleep(2)  # Wait for navigation
            return True
        except Exception as e:
            if attempt == max_attempts - 1:
                print(f"Failed to navigate to Portfolio View: {str(e)}")
                return False
            time.sleep(1)

def capture_portfolio_for_all_groups(driver):
    """Capture portfolio view for each trade group"""
    try:
        # Navigate to Portfolio View
        if not navigate_to_portfolio(driver):
            raise Exception("Failed to navigate to Portfolio View")
        
        # List of trade groups
        groups = ['day_trader', 'swing_trader', 'long_term_trader']
        
        # Take screenshot for each group
        for group in groups:
            print(f"\nProcessing trade group: {group}")
            if select_trade_group(driver, group):
                take_portfolio_screenshot(driver, f"{group}_portfolio.png")
            else:
                print(f"Skipping screenshot for {group} due to selection failure")

    except Exception as e:
        print(f"Error in capture_portfolio_for_all_groups: {str(e)}")
        raise e
    
#"avatar_url": "https://cdn.discordapp.com/app-icons/1284994761211772928/e632e899e42157ced313d77b7aa5d3d7.png"
DISCORD_WEBHOOKS = {
    "day_trader": "https://discord.com/api/webhooks/1300088111665123378/ufkdui9ywzRhJO69_nxojxJya3FpcuG5WAezvq3K7OixfATHhNWZw61DXg5HsdSqoruS",
    "swing_trader": "https://discord.com/api/webhooks/1300088535046422538/oYG32QQrGf0ikR238UeKs0H8kZZdx9mmM0-KOMQN1iasTe5BZ1X1KoTML7S8Lu_1_UZP",
    "long_term_trader": "https://discord.com/api/webhooks/1300088644702310451/NFQ7UzgNYQ4pO-qxKA-0LZd53V3VM4C2toNwvJ_ak4g-P0_uERQlVE7NcipXi5WSNj08",
    "full_portfolio": "https://discord.com/api/webhooks/1300088766354165820/dDOy-rbyWXHlwZbQ2TbJRDdtGNuauRN5cQHzqkj_6lBtrcE6Oo4ZQWQbcslIZSLH_rj8"
}

DISCORD_FILE_ORDER = ['day_trader_open.png', 'day_trader_portfolio.png', 'swing_trader_open.png', 'swing_trader_portfolio.png', 'long_term_trader_open.png', 'long_term_trader_portfolio.png']


def send_screenshot_to_discord():
    """Send a screenshot to the Discord channel"""
    # For every screenshot in the screenshots directory, send it to the Discord channel
    # I want to order it as Open then portfolio for each group
    for file in DISCORD_FILE_ORDER:
        message = "ERROR"
        if file.endswith("open.png"):
            message = f"# Open Trades for {file.split('_')[0].capitalize()} Trader"
        elif file.endswith("portfolio.png"):
            message = f"# {file.split('_')[0].capitalize()} Trader Portfolio"
        
        if file.startswith("day_trader"):
            send_discord_message(DISCORD_WEBHOOKS["day_trader"], message, f"screenshots/{file}")
        elif file.startswith("swing_trader"):
            send_discord_message(DISCORD_WEBHOOKS["swing_trader"], message, f"screenshots/{file}")
        elif file.startswith("long_term_trader"):
            send_discord_message(DISCORD_WEBHOOKS["long_term_trader"], message, f"screenshots/{file}")
        else:
            print(f"Unknown file: {file}")

        send_discord_message(DISCORD_WEBHOOKS["full_portfolio"], message, f"screenshots/{file}")

def send_discord_message(webhook_url, message, image_path=None, avatar_path=None):
    """
    Send a message to Discord with optional local image and avatar files
    
    Parameters:
    webhook_url (str): The Discord webhook URL
    message (str): The message to send
    image_path (str): Path to message image file (optional)
    avatar_path (str): Path to avatar image file (optional)
    """
    
    # Use ExitStack to manage multiple file contexts
    with ExitStack() as stack:
        files = {}
        
        # Basic payload with message
        payload = {
            "content": message,
            "username": "Task Updates Bot",
        }
        
        # If avatar file is provided, add it to the files
        if avatar_path:
            try:
                avatar = stack.enter_context(open(avatar_path, 'rb'))
                files['avatar'] = ('avatar.png', avatar, 'image/png')
                payload["avatar_url"] = "attachment://avatar.png"
            except FileNotFoundError:
                print(f"Error: Avatar file '{avatar_path}' not found")
                return
            except Exception as e:
                print(f"Error opening avatar file: {str(e)}")
                return

        # If message image is provided, add it to the files
        if image_path:
            try:
                image = stack.enter_context(open(image_path, 'rb'))
                files['file'] = ('image.png', image, 'image/png')
            except FileNotFoundError:
                print(f"Error: Image file '{image_path}' not found")
                return
            except Exception as e:
                print(f"Error opening image file: {str(e)}")
                return

        try:
            # Send the message with files
            response = requests.post(
                webhook_url,
                data={'payload_json': json.dumps(payload)},
                files=files
            )
            
            if response.status_code == 204:
                print("Message sent successfully!")
            else:
                print(f"Failed to send message. Status code: {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"Error sending message: {str(e)}")

def main2():
    send_screenshot_to_discord()

def main():
    # Create screenshots directory if it doesn't exist
    if not os.path.exists("screenshots"):
        os.makedirs("screenshots")

    driver = setup_driver()
    
    try:
        # Load the webpage (replace with actual URL)
        driver.get("http://localhost:3000")

        # Take initial screenshot of table
        #take_table_screenshot(driver, "initial_table.png")

        # Change status from closed to open
        change_status_to_open(driver)

        # Take screenshot after status change
        ##take_table_screenshot(driver, "table_status_open.png")

        # Capture screenshots for each Day Trader group
        capture_trade_groups(driver)

        # Capture portfolio view for each trade group
        capture_portfolio_for_all_groups(driver)

        send_screenshot_to_discord()

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        import traceback
        print(traceback.format_exc())
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
    