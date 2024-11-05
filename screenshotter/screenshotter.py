from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import Select
import time
import os
import requests
import json
from contextlib import ExitStack
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.firefox.service import Service
from pyvirtualdisplay import Display

def setup_driver():
    """Set up Firefox WebDriver with virtual display for headless Linux"""
    from selenium.webdriver.firefox.service import Service
    from selenium.webdriver.firefox.options import Options
    
    # Start virtual display
    display = Display(visible=0, size=(1920, 1080))
    display.start()
    
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--width=1920')
    options.add_argument('--height=1080')
    
    service = Service('/usr/local/bin/geckodriver')
    
    try:
        driver = webdriver.Firefox(service=service, options=options)
        return driver
    except Exception as e:
        display.stop()
        raise e

def take_table_screenshot(driver, filename):
    """Take a screenshot of the trades table"""
    table = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "main")) # Can change this to table if needed, but this is a better view. 
    )
    # Scroll table into view
    driver.execute_script("arguments[0].scrollIntoView();", table)
    time.sleep(1)  # Allow time for any animations
    table.screenshot(f"screenshots/{filename}")

def change_status_to_open2(driver):
    """Change all closed statuses to open"""
    status_selector = Select(driver.find_element(By.CSS_SELECTOR, "select[name='status-selector']"))
    status_selector.select_by_visible_text("Open")

def wait_for_element(driver, by, selector, timeout=10, condition="presence"):
    """Generic wait function with different wait conditions"""
    try:
        if condition == "presence":
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
        elif condition == "clickable":
            element = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, selector))
            )
        elif condition == "visible":
            element = WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located((by, selector))
            )
        return element
    except TimeoutException:
        print(f"Timeout waiting for element: {selector}")
        driver.save_screenshot(f"screenshots/debug_timeout_{time.strftime('%Y%m%d_%H%M%S')}.png")
        raise


def change_status_to_open(driver):
    """Change status to open using the correct button selectors"""
    try:
        # Wait for page to be completely loaded
        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        # Wait for and find the status dropdown using the specific role and attributes
        dropdown = wait_for_element(
            driver,
            By.CSS_SELECTOR,
            "button[role='combobox'][aria-autocomplete='none']",
            timeout=20,
            condition="clickable"
        )
        
        # Scroll the dropdown into view
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", dropdown)
        time.sleep(1)
        
        # Click using JavaScript to avoid pointer-events issues
        driver.execute_script("arguments[0].click();", dropdown)
        time.sleep(1)
        
        # Find and click the "Open" option in the dropdown menu
        open_option = wait_for_element(
            driver,
            By.XPATH,
            "//div[@role='option' and text()='Open']",
            timeout=20,
            condition="clickable"
        )
        
        # Click using JavaScript
        driver.execute_script("arguments[0].click();", open_option)
        time.sleep(2)  # Wait for any updates

    except Exception as e:
        print(f"Error changing status to open: {str(e)}")
        driver.save_screenshot("screenshots/debug_status_change_error.png")
        raise

def select_trade_group(driver, group_name):
    """Select a specific trade group from the dropdown"""
    try:
        # Find and click the trade group dropdown
        group_dropdown = wait_for_element(
            driver,
            By.CSS_SELECTOR,
            "button[role='combobox'] span",
            timeout=20,
            condition="presence"
        )
        
        # Scroll into view and click using JavaScript
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", group_dropdown.find_element(By.XPATH, ".."))
        time.sleep(1)
        driver.execute_script("arguments[0].click();", group_dropdown.find_element(By.XPATH, ".."))
        
        # Wait for the dropdown content to appear
        content_wrapper = wait_for_element(
            driver,
            By.CSS_SELECTOR,
            "[data-radix-popper-content-wrapper]",
            timeout=10,
            condition="presence"
        )
        
        # Find and click the specific trade group option
        group_option = wait_for_element(
            driver,
            By.XPATH,
            f"//span[contains(text(), '{group_name}')]",
            timeout=10,
            condition="clickable"
        )
        group_option = wait_for_element(
            driver,
            By.XPATH,
            f"//div[data-radix-popper-content-wrapper]",
            timeout=10,
            condition="clickable"
        )
        print(group_option.get_attribute("innerHTML"))
        
        driver.execute_script("arguments[0].click();", group_option)
        time.sleep(1)  # Wait for UI update
        
    except Exception as e:
        print(f"Error selecting trade group {group_name}: {str(e)}")
        driver.save_screenshot(f"screenshots/debug_select_group_{group_name}.png")
        raise

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
        groups = ['swing_trader', 'day_trader', 'long_term_trader']
        
        for trader_group in groups:
            trader_group_name = trader_group.replace("_", " ").title()
            print(f"\nProcessing trade group: {trader_group_name}")
            # Find and click the trader group dropdown
            group_dropdown = wait_for_element(
                driver,
                By.CSS_SELECTOR,
                "button[role='combobox']",
                condition="clickable"
            )
            group_dropdown.click()
            
            # Select the trader group
            group_option = wait_for_element(
                driver,
                By.XPATH,
                f"//span[contains(text(), '{trader_group_name}')]",
                condition="clickable"
            )
            #group_option.find_element(By.XPATH, "..").click()
            driver.execute_script("arguments[0].click();", group_option)
            time.sleep(1)  # Wait for view to update
            
            # Take screenshot
            filename = f"{trader_group.lower().replace(' ', '_')}_portfolio.png"
            take_table_screenshot(driver, filename)

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

DEBUG_WEBHOOKS = {
    "day_trader": "https://discord.com/api/webhooks/1300084058507841577/85ZnFh1mR0cbuWqrwhWrSaFZfBiSpGS6KLg6Avg2am_sf8UyY8gkkA4VA1viKe7TAUiY",
    "swing_trader": "https://discord.com/api/webhooks/1300084058507841577/85ZnFh1mR0cbuWqrwhWrSaFZfBiSpGS6KLg6Avg2am_sf8UyY8gkkA4VA1viKe7TAUiY",
    "long_term_trader": "https://discord.com/api/webhooks/1300084058507841577/85ZnFh1mR0cbuWqrwhWrSaFZfBiSpGS6KLg6Avg2am_sf8UyY8gkkA4VA1viKe7TAUiY",
    "full_portfolio": "https://discord.com/api/webhooks/1300084058507841577/85ZnFh1mR0cbuWqrwhWrSaFZfBiSpGS6KLg6Avg2am_sf8UyY8gkkA4VA1viKe7TAUiY"
}

DISCORD_FILE_ORDER = ['day_trader_open.png', 'day_trader_portfolio.png', 'swing_trader_open.png', 'swing_trader_portfolio.png', 'long_term_trader_open.png', 'long_term_trader_portfolio.png']

DISCORD_FILE_GROUPS = {
    "day_trader": { "open": ["day_trader_regular_trades.png", "day_trader_options_trades.png", "day_trader_options_strategies.png"], "portfolio": ["day_trader_portfolio.png"] },
    "swing_trader": { "open": ["swing_trader_regular_trades.png", "swing_trader_options_trades.png", "swing_trader_options_strategies.png"], "portfolio": ["swing_trader_portfolio.png"] },
    "long_term_trader": { "open": ["long_term_trader_regular_trades.png", "long_term_trader_options_trades.png", "long_term_trader_options_strategies.png"], "portfolio": ["long_term_trader_portfolio.png"] }
}


def send_screenshot_to_discord(debug=False):
    """Send a screenshot to the Discord channel"""
    # For every screenshot in the screenshots directory, send it to the Discord channel
    # I want to order it as Open then portfolio for each group
    webhooks = DISCORD_WEBHOOKS if not debug else DEBUG_WEBHOOKS

    for group in DISCORD_FILE_GROUPS:
        message = f"# {group.replace('_', ' ').title()} Open Trades"
        send_discord_message(webhooks[group], message)
        for file in DISCORD_FILE_GROUPS[group]["open"]:
            send_discord_message(webhooks[group], "", f"screenshots/{file}")
        for file in DISCORD_FILE_GROUPS[group]["portfolio"]:
            message += f"# Realized Trades for {group.replace('_', ' ').title()}"
            send_discord_message(webhooks[group], message, f"screenshots/{file}")

#send_discord_message(webhooks["full_portfolio"], message, f"screenshots/{file}")

        

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

def capture_all_trade_views(driver):
    trade_types = ["Regular Trades", "Options Trades", "Options Strategies"]
    trader_groups = ["Day Trader", "Swing Trader", "Long Term Trader"]
    
    for trade_type in trade_types:
        # Click the trade type button
        trade_button = wait_for_element(
            driver,
            By.XPATH,
            f"//button[text()='{trade_type}']",
            condition="clickable"
        )
        trade_button.click()
        time.sleep(1)  # Wait for view to update

        for trader_group in trader_groups:
            # Find and click the trader group dropdown
            group_dropdown = wait_for_element(
                driver,
                By.CSS_SELECTOR,
                "button[role='combobox']",
                condition="clickable"
            )
            group_dropdown.click()
            
            # Select the trader group
            group_option = wait_for_element(
                driver,
                By.XPATH,
                f"//span[contains(text(), '{trader_group}')]",
                condition="clickable"
            )
            group_option.click()
            time.sleep(1)  # Wait for view to update
            
            # Take screenshot
            filename = f"{trader_group.lower().replace(' ', '_')}_{trade_type.lower().replace(' ', '_')}.png"
            take_table_screenshot(driver, filename)

def main():
    if not os.path.exists("screenshots"):
        os.makedirs("screenshots")

    driver = setup_driver()
    
    try:
        driver.get("http://localhost:3000")
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(2)

        # Change status to open
        #change_status_to_open(driver)
        time.sleep(1)

        # Capture all combinations
        capture_all_trade_views(driver)

        capture_portfolio_for_all_groups(driver)

        send_screenshot_to_discord(debug=True)

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        import traceback
        print(traceback.format_exc())
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
    