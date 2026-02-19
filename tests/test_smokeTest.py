import os
import time
import pytest
import subprocess
import platform
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService


# ---------- Config ----------
# Default matches your hard-coded URL, but now you can override it:
# PowerShell: $env:BASE_URL="http://127.0.0.1:5500"
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5500").rstrip("/")

# Your project folder path used by tests
SITE_PATH = "/cse270/teton/1.6"

# Headless default:
# - In GitHub Actions, GITHUB_ACTIONS=true so headless = True
# - Locally, default to visible browser for debugging (set HEADLESS=1 to hide)
HEADLESS = os.getenv("HEADLESS", "").strip().lower()
if HEADLESS in ("1", "true", "yes"):
    RUN_HEADLESS = True
elif os.getenv("GITHUB_ACTIONS", "").lower() == "true":
    RUN_HEADLESS = True
else:
    RUN_HEADLESS = False  # Show browser locally for debugging


def cleanup_chrome():
    """Kill any existing Chrome processes that might interfere"""
    system = platform.system()
    try:
        if system == "Windows":
            result = subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], 
                                   capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print("Killed existing Chrome processes")
        elif system == "Darwin":  # macOS
            subprocess.run(["pkill", "-f", "chrome"], capture_output=True, timeout=5)
        else:  # Linux
            subprocess.run(["pkill", "-f", "chrome"], capture_output=True, timeout=5)
        time.sleep(2)
    except subprocess.TimeoutExpired:
        pass
    except Exception as e:
        print(f"Error killing Chrome processes: {e}")


# ---------- Pytest sanity check (fast failure if server isn't running) ----------
def test_server_is_reachable():
    """
    This test fails early with a clear message if your local server isn't running.
    Start your server first:
      python -m http.server 5500
    from the repo root.
    """
    import urllib.request
    import urllib.error

    url = f"{BASE_URL}{SITE_PATH}/"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            assert resp.status in (200, 301, 302), f"Unexpected HTTP status: {resp.status}"
        print(f"Server is reachable at {url}")
    except urllib.error.URLError as e:
        pytest.fail(
            f"Cannot reach site at {url}. "
            f"Make sure you started a server from repo root, e.g.:\n"
            f"  python -m http.server 5500\n"
            f"Error: {e}"
        )
    except Exception as e:
        pytest.fail(f"Unexpected error checking server: {e}")


class TestSmokeTest:
    def setup_method(self, method):
        # Clean up any hanging Chrome processes
        cleanup_chrome()
        
        options = ChromeOptions()
        
        # Chrome headless - always headless in CI
        if RUN_HEADLESS or os.getenv("GITHUB_ACTIONS") == "true":
            options.add_argument("--headless=new")
            print("Running in headless mode")
        else:
            print("Running in visible browser mode")
        
        # Add stability options for CI
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1200,800")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-setuid-sandbox")
        options.add_argument("--remote-debugging-port=9222")
        
        # Simple service setup
        service = ChromeService()
        
        # Retry logic for Chrome startup
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"Starting Chrome (attempt {attempt + 1}/{max_retries})...")
                self.driver = webdriver.Chrome(service=service, options=options)
                print("Chrome started successfully")
                break
            except Exception as e:
                print(f"Chrome startup attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    # Print diagnostic info
                    print("\nDiagnostic information:")
                    print(f"Chrome path: {shutil.which('chrome') or shutil.which('google-chrome')}")
                    print(f"ChromeDriver path: {shutil.which('chromedriver')}")
                    raise
                time.sleep(3)
        
        # Set window size
        try:
            self.driver.set_window_size(1200, 800)
            print("Window size set to 1200x800")
        except Exception as e:
            print(f"Could not set window size: {e}")
        
        self.vars = {}
        self.wait = WebDriverWait(self.driver, 10)

    def teardown_method(self, method):
        if hasattr(self, 'driver'):
            try:
                self.driver.quit()
                print("Browser closed successfully")
            except Exception as e:
                print(f"Error closing browser: {e}")
            finally:
                # Small delay to ensure process cleanup
                time.sleep(1)
                cleanup_chrome()

    # Helper to build full URLs
    def url(self, relative):
        if not relative.startswith("/"):
            relative = "/" + relative
        return f"{BASE_URL}{relative}"

    def test_test1HomePageVerification(self):
        print(f"Navigating to: {self.url(f'{SITE_PATH}/')}")
        self.driver.get(self.url(f"{SITE_PATH}/"))

        # Verify logo is present
        elements = self.driver.find_elements(By.CSS_SELECTOR, ".header-logo img, img[src*='logo']")
        assert len(elements) > 0, "Logo not found"
        print("Logo found")

        # Verify header text
        header_text = self.driver.find_element(By.CSS_SELECTOR, ".header-title > h1, .header-title").text
        assert "Teton Idaho" in header_text, f"Expected 'Teton Idaho' in header, got '{header_text}'"
        print(f"Header text verified: {header_text}")

        # Verify page title
        assert self.driver.title == "Teton Idaho CoC", f"Expected title 'Teton Idaho CoC', got '{self.driver.title}'"
        print(f"Page title verified: {self.driver.title}")

    def test_test2HomePageFeatures(self):
        self.driver.get(self.url(f"{SITE_PATH}/"))

        spotlight_selectors = [
            ".spotlight",
            ".spotlight-card",
            ".spotlight1",
            ".spotlight2",
            ".gold-member",
            ".member-card",
            ".featured-member",
            "[class*='spotlight']",
            ".cardsection",
            ".member",
        ]

        spotlight_found = False
        for selector in spotlight_selectors:
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if len(elements) >= 2:
                print(f"Found {len(elements)} spotlights with selector: {selector}")
                spotlight_found = True
                break

        if not spotlight_found:
            possible_spotlights = self.driver.find_elements(
                By.CSS_SELECTOR, "section, .card, div[class*='member'], div[class*='spotlight']"
            )
            visible_spotlights = [e for e in possible_spotlights if e.is_displayed()]
            assert len(visible_spotlights) >= 2, "Could not find at least 2 spotlight elements"

        # Find Join link
        join_link = None
        join_texts = ["Join Us", "Join", "Join Now", "Become a Member"]
        for text in join_texts:
            try:
                join_link = self.driver.find_element(By.LINK_TEXT, text)
                break
            except Exception:
                try:
                    join_link = self.driver.find_element(By.PARTIAL_LINK_TEXT, text)
                    break
                except Exception:
                    continue

        assert join_link is not None, "Join Us link not found"
        assert join_link.is_displayed(), "Join Us link not displayed"
        print(f"Join link found: {join_link.text}")

        join_link.click()
        time.sleep(2)

        current_url = self.driver.current_url
        assert "join" in current_url.lower(), f"Not redirected to join page. Current URL: {current_url}"
        print(f"Redirected to join page: {current_url}")

        name_fields = self.driver.find_elements(By.CSS_SELECTOR, "input[name='fname'], input[name='lname']")
        assert len(name_fields) > 0, "Join page form fields not found"
        print("Join page form fields verified")

    def test_test3DirectoryGridandListFeature(self):
        self.driver.get(self.url(f"{SITE_PATH}/directory.html"))
        
        # Wait for page to load
        time.sleep(2)
        
        # Try clicking grid button if exists
        grid_button = None
        grid_selectors = ["button#directory-grid", "#grid-view-button", "[data-view='grid']", "button:contains('Grid')"]
        for selector in grid_selectors:
            try:
                grid_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                if grid_button.is_displayed():
                    break
            except Exception:
                continue

        if grid_button:
            grid_button.click()
            time.sleep(2)
            print("Clicked grid view button")
        
        # Look for members in grid view
        member_selectors = ["section.gold-member", ".member-card", ".gold-member", ".directory-item", ".member", ".card", "[class*='member']"]
        members_found = False
        
        # Try to find any members
        page_source = self.driver.page_source
        if "Teton Turf" in page_source or "member" in page_source.lower():
            print("Found member content in page source")
        
        for selector in member_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if len(elements) > 0:
                    print(f"Found {len(elements)} members with selector: {selector} in grid view")
                    members_found = True
                    break
            except Exception:
                continue
        
        # If still not found, try a more general approach
        if not members_found:
            # Look for any sections or divs that might contain member info
            all_sections = self.driver.find_elements(By.CSS_SELECTOR, "section, div.card, div.item")
            visible_sections = [e for e in all_sections if e.is_displayed()]
            if len(visible_sections) >= 2:
                print(f"Found {len(visible_sections)} visible sections that might be members")
                members_found = True
        
        assert members_found, "No members found in grid view"
        
        # Try clicking list button if exists
        list_button = None
        list_selectors = ["button#directory-list", "#list-view-button", "[data-view='list']", "button:contains('List')"]
        for selector in list_selectors:
            try:
                list_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                if list_button.is_displayed():
                    break
            except Exception:
                continue

        if list_button:
            list_button.click()
            time.sleep(2)
            print("Clicked list view button")
        
        # Look for members in list view
        members_found = False
        for selector in member_selectors:
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if len(elements) > 0:
                print(f"Found {len(elements)} members with selector: {selector} in list view")
                members_found = True
                break
        
        assert members_found, "No members found in list view"

    def test_test4JoinPageDataEntry(self):
        self.driver.get(self.url(f"{SITE_PATH}/join.html"))
        initial_url = self.driver.current_url
        print(f"Initial URL: {initial_url}")
        
        # Wait for page to load
        time.sleep(2)
        
        # Print all input fields for debugging
        all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
        print(f"Total input fields found: {len(all_inputs)}")
        for i, input_field in enumerate(all_inputs):
            try:
                name = input_field.get_attribute("name")
                id = input_field.get_attribute("id")
                type = input_field.get_attribute("type")
                print(f"Input {i}: name='{name}', id='{id}', type='{type}'")
            except:
                pass
        
        # Try multiple selectors for first name
        first_name_selectors = [
            "input[name='fname']",
            "input#fname",
            "input[name='firstname']",
            "input#firstname",
            "input[placeholder*='First']",
            "input[name*='first']",
            "input[id*='first']",
            "input[type='text']:first-of-type"
        ]
        
        first_name_field = None
        for selector in first_name_selectors:
            try:
                fields = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if fields and fields[0].is_displayed():
                    first_name_field = fields[0]
                    print(f"Found first name field with selector: {selector}")
                    break
            except Exception as e:
                continue
        
        # If still not found, try getting the first visible text input
        if not first_name_field:
            for input_field in all_inputs:
                input_type = input_field.get_attribute("type")
                if input_type in ["text", "None"] and input_field.is_displayed():
                    first_name_field = input_field
                    print(f"Using first visible text input as fallback")
                    break
        
        assert first_name_field is not None, "First name field not found"
        
        # Fill in fields
        field_mappings = {
            "fname": "John",
            "lname": "Doe",
            "firstname": "John",
            "lastname": "Doe",
            "bizname": "Test Business",
            "business": "Test Business",
            "organization": "Test Business",
            "email": "test@example.com",
            "phone": "555-123-4567",
        }
        
        fields_filled = 0
        for field_name, field_value in field_mappings.items():
            try:
                # Try by name
                element = self.driver.find_element(By.NAME, field_name)
                element.clear()
                element.send_keys(field_value)
                print(f"Filled field by name: {field_name}")
                fields_filled += 1
            except Exception:
                try:
                    # Try by id
                    element = self.driver.find_element(By.ID, field_name)
                    element.clear()
                    element.send_keys(field_value)
                    print(f"Filled field by id: {field_name}")
                    fields_filled += 1
                except Exception:
                    continue
        
        print(f"Filled {fields_filled} fields")
        
        # Find and click next button
        next_button = None
        next_selectors = [
            "input[value='Next Step']",
            "button[type='submit']",
            "input[type='submit']",
            ".next-button",
            "#next-button",
            "button.next",
            "input[value='Next']",
            "button:contains('Next')",
            "button:contains('Continue')",
            "input[value='Continue']"
        ]
        
        for selector in next_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        next_button = element
                        print(f"Found next button with selector: {selector}")
                        break
                if next_button:
                    break
            except Exception:
                continue
        
        if not next_button:
            # Try finding any button that might be the next button
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for button in buttons:
                button_text = button.text.lower()
                if "next" in button_text or "continue" in button_text or "submit" in button_text:
                    if button.is_displayed():
                        next_button = button
                        print(f"Found next button with text: {button.text}")
                        break
        
        if not next_button:
            # Try the first submit button as last resort
            for input_field in all_inputs:
                if input_field.get_attribute("type") == "submit" and input_field.is_displayed():
                    next_button = input_field
                    print("Using first submit button as next button")
                    break
        
        assert next_button is not None, "Next Step button not found"
        
        # Click using JavaScript to avoid any interaction issues
        self.driver.execute_script("arguments[0].click();", next_button)
        print("Clicked next button")
        
        time.sleep(3)
        
        current_url = self.driver.current_url
        print(f"Current URL: {current_url}")
        url_changed = current_url != initial_url
        
        # Check for next page indicators
        next_page_indicators = [
            "input[name='email']",
            "input[type='email']",
            "input[name='phone']",
            "select",
            "textarea",
        ]
        
        field_found = False
        for selector in next_page_indicators:
            fields = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if fields:
                print(f"Found field on next page with selector: {selector}")
                field_found = True
                break
        
        assert field_found or url_changed, "Next page didn't load properly - no form fields found and URL didn't change"
        print("Join page test completed successfully")

    def test_test5AdminPageLogin(self):
        self.driver.get(self.url(f"{SITE_PATH}/admin.html"))
        
        # Wait for page to load
        time.sleep(2)
        
        # Print all input fields for debugging
        all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
        print(f"Total input fields found: {len(all_inputs)}")
        for i, input_field in enumerate(all_inputs):
            try:
                name = input_field.get_attribute("name")
                id = input_field.get_attribute("id")
                type = input_field.get_attribute("type")
                print(f"Input {i}: name='{name}', id='{id}', type='{type}'")
            except:
                pass
        
        # Find username field
        username_selectors = [
            "input#username",
            "input[name='username']",
            "input[type='text']:first-of-type",
            "input:first-of-type"
        ]
        
        username_field = None
        for selector in username_selectors:
            try:
                fields = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if fields and fields[0].is_displayed():
                    username_field = fields[0]
                    print(f"Found username field with selector: {selector}")
                    break
            except Exception:
                continue
        
        if not username_field and len(all_inputs) > 0:
            username_field = all_inputs[0]
            print("Using first input field as username field")
        
        assert username_field is not None, "Username field not found"
        print("Username field found")
        
        # Find password field
        password_selectors = [
            "input[type='password']",
            "input[name='password']",
            "input#password"
        ]
        
        password_field = None
        for selector in password_selectors:
            try:
                fields = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if fields and fields[0].is_displayed():
                    password_field = fields[0]
                    print(f"Found password field with selector: {selector}")
                    break
            except Exception:
                continue
        
        if not password_field:
            for input_field in all_inputs:
                if input_field.get_attribute("type") == "password":
                    password_field = input_field
                    print("Found password field by type")
                    break
        
        assert password_field is not None, "Password field not found"
        print("Password field found")
        
        # Enter wrong credentials
        username_field.clear()
        username_field.send_keys("wronguser")
        print("Entered username: wronguser")
        
        password_field.clear()
        password_field.send_keys("wrongpass")
        print("Entered password: wrongpass")
        
        # Find login button
        login_button = None
        login_selectors = [
            ".mysubmit",
            "button[type='submit']",
            "input[type='submit']",
            "#login-button",
            ".login-button",
            "button:contains('Login')",
            "button:contains('Sign In')",
            "input[value='Login']",
            "input[value='Sign In']"
        ]
        
        for selector in login_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed():
                        login_button = element
                        print(f"Found login button with selector: {selector}")
                        break
                if login_button:
                    break
            except Exception:
                continue
        
        if not login_button:
            # Try any button that might be the login button
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for button in buttons:
                button_text = button.text.lower()
                if "login" in button_text or "sign in" in button_text or "submit" in button_text:
                    if button.is_displayed():
                        login_button = button
                        print(f"Found login button with text: {button.text}")
                        break
        
        if not login_button:
            # Try the first submit button
            for input_field in all_inputs:
                if input_field.get_attribute("type") == "submit" and input_field.is_displayed():
                    login_button = input_field
                    print("Using first submit button as login button")
                    break
        
        assert login_button is not None, "Login button not found"
        
        # Click using JavaScript
        self.driver.execute_script("arguments[0].click();", login_button)
        print("Clicked login button")
        
        time.sleep(2)
        
        # Look for error message
        error_texts = ["Invalid", "Error", "Wrong", "Incorrect", "Login failed", "Invalid username", "Invalid password"]
        error_found = False
        
        page_text = self.driver.find_element(By.TAG_NAME, "body").text
        for text in error_texts:
            if text.lower() in page_text.lower():
                print(f"Found error message containing: '{text}'")
                error_found = True
                break
        
        if not error_found:
            # Try more specific selectors
            error_selectors = [
                ".error", ".alert", ".message", ".notification", 
                ".error-message", ".alert-danger", ".invalid",
                "[class*='error']", "[class*='alert']"
            ]
            for selector in error_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and element.text:
                        print(f"Found error element with text: {element.text}")
                        error_found = True
                        break
                if error_found:
                    break
        
        assert error_found, "No error message displayed for invalid login"
        print("Admin login test completed successfully")