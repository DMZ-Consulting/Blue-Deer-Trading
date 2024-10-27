from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import time
import os

def setup_driver():
    """Set up Chrome WebDriver with appropriate options"""
    options = webdriver.ChromeOptions()
    options.add_argument('--start-maximized')
    options.add_argument('--disable-infobars')
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

def capture_day_trader_groups(driver):
    """Take screenshots for each trade group in the Day Trader selector"""
    day_trader_select = Select(driver.find_element(By.CSS_SELECTOR, "select[id='trade-group-selector']"))
    groups = [option.text for option in day_trader_select.options]
    
    for group in groups:
        day_trader_select.select_by_visible_text(group)
        time.sleep(1)  # Allow time for table to update
        take_table_screenshot(driver, f"day_trader_group_{group}.png")

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
                take_portfolio_screenshot(driver, f"portfolio_view_{group}.png")
            else:
                print(f"Skipping screenshot for {group} due to selection failure")

    except Exception as e:
        print(f"Error in capture_portfolio_for_all_groups: {str(e)}")
        raise e

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
        #change_status_to_open(driver)

        # Take screenshot after status change
        #take_table_screenshot(driver, "table_status_open.png")

        # Capture screenshots for each Day Trader group
        #capture_day_trader_groups(driver)

        # Capture portfolio view for each trade group
        capture_portfolio_for_all_groups(driver)

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        import traceback
        print(traceback.format_exc())
    finally:
        driver.quit()

if __name__ == "__main__":
    main()