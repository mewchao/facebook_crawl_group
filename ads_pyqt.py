import time
import random
import threading
import requests
import pyotp
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from time import sleep
from httpcore import TimeoutException

# Configuration
ADS_ID = "ks3wuby"  # AdsPower User ID

FACEBOOK_CREDENTIALS = {
    "username": "61550785360330",
    "password": "ooDKB3Ik",
    "2fa_secret": "PT7ETVPG2PR6V4PKLLP3KE6ET2V6WM4C"
}

GROUP_ID = "gomabb"  # Facebook Group ID

COMMENT_TARGET = 1000  # Target number of comments

# Default comments
default_comments = [
    "What is the size and price$$?",
    "+1",
    "Hello, I want to buy!",
    "What is the size??",
    "Hi, I want to buy"
]

def random_sleep(min_seconds=1, max_seconds=3):
    time.sleep(random.uniform(min_seconds, max_seconds))

def clear_cache():
    """Clear AdsPower cache"""
    try:
        response = requests.post("http://local.adspower.com:50325/api/v1/user/delete-cache")
        result = response.json()
        print(f"Cache clear result: {result['msg']}")
        return result["code"] == 0
    except Exception as e:
        print(f"Failed to clear cache: {str(e)}")
        return False

def update_environment(user_id):
    """Update AdsPower environment information"""
    url = "http://local.adspower.com:50325/api/v1/user/update"
    
    # Request data: setting open_urls as an empty list
    data = {
        "user_id": user_id,
        "open_urls": [],  # Set open_urls as an empty list
        "cookies":[] # 
    }
    
    try:
        # Send POST request to update environment information
        response = requests.post(url, json=data)
        result = response.json()
        
        if response.status_code == 200 and result.get("code") == 0:
            print(f"Environment {user_id} updated successfully.")
            return True
        else:
            print(f"Failed to update environment {user_id}: {result.get('msg')}")
            return False
    except Exception as e:
        print(f"Error updating environment: {str(e)}")
        return False

def start_browser():
    """Start AdsPower browser instance"""
    try:
        open_url = f"http://local.adspower.com:50325/api/v1/browser/start?user_id={ADS_ID}"
        response = requests.get(open_url).json()

        if response["code"] != 0:
            print(f"Failed to start browser: {response['msg']}")
            return None

        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", response["data"]["ws"]["selenium"])
        service = Service(executable_path=response["data"]["webdriver"])
        
        return webdriver.Chrome(service=service, options=chrome_options)
    
    except Exception as e:
        print(f"Browser initialization failed: {str(e)}")
        return None
    
def getCodeFrom2FA(code):
    totp = pyotp.TOTP(str(code).strip().replace(" ", "")[:32])
    random_sleep()
    return totp.now()
    
def facebook_login(driver):
    """Perform Facebook login with 2FA"""
    try:
        print("Accessing the login page.")
        driver.get("https://mbasic.facebook.com/login/?next&ref=dbl&fl&refid=8")
        random_sleep()

        print("Finding the username input field.")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#email"))
        ).send_keys(FACEBOOK_CREDENTIALS["username"])
        
        print(f"Entered username: {FACEBOOK_CREDENTIALS['username']}")
        random_sleep()

        print("Finding the password input field.")
        driver.find_element(By.CSS_SELECTOR, "#pass").send_keys(FACEBOOK_CREDENTIALS["password"])
        print("Entered password.")
        random_sleep()

        print("Finding and clicking the login button.")
        driver.find_element(By.CSS_SELECTOR, "#loginbutton").click()
        print("Clicked the login button.")
        random_sleep()

        wait = WebDriverWait(driver, 30)

        # Handle 2FA if present
        print("Checking if 2FA is required.")
        try:
            
            other_funs_continue_css_selector = "span.x1lliihq.x193iq5w.x6ikm8r.x10wlt62.xlyipyv.xuxw1ft"
            
            other_funs_continue = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, other_funs_continue_css_selector))
            )

            other_funs_continue.click()
            random_sleep()

            radio_button_xpath_expression = "//input[@type='radio' and @name='unused' and @value='1']"
            radio_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, radio_button_xpath_expression))
            )
            radio_button.click()

            time.sleep(10)

            fa_code_element = wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//input[contains(@class, 'x1a2a7pz') and contains(@class, 'xzsf02u')]")
                )
            )
            if fa_code_element:
                fa_code = str(getCodeFrom2FA(FACEBOOK_CREDENTIALS["2fa_secret"]))
                fa_code_element.send_keys(fa_code)
                print(f"Entered 2FA code: {fa_code}")
                time.sleep(0.5)

                print("Finding and clicking the 2FA confirmation button.")
                time.sleep(10)

        except TimeoutException:
            print("2FA not required or login failed.")
        
        print("Login successful.")
        return True

    except Exception as e:
        print(f"Login error: {str(e)}")
        traceback.print_exc()
        return False



def auto_scroll(driver, stop_event):
    """Automatically scroll the page"""
    while not stop_event.is_set():
        try:
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(random.uniform(2, 4))
        except:
            break

def post_comments(driver, comments):
    """Automate comment posting"""
    stop_event = threading.Event()
    scroll_thread = threading.Thread(target=auto_scroll, args=(driver, stop_event))
    scroll_thread.start()

    try:
        driver.get(f"https://mbasic.facebook.com/groups/{GROUP_ID}")
        visited = set()
        comment_count = 0

        while comment_count < COMMENT_TARGET:
            try:
                comment_boxes = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located(
                        (By.XPATH, "//*[@aria-label='Write an answer…' or @aria-label='Write a public comment…']")
                    )
                )

                for box in comment_boxes:
                    if comment_count >= COMMENT_TARGET:
                        break

                    if box in visited:
                        continue

                    try:
                        ActionChains(driver).move_to_element(box).perform()
                        time.sleep(random.uniform(0.5, 1.5))
                        
                        comment = random.choice(comments)
                        box.click()
                        box.send_keys(comment + Keys.ENTER)
                        
                        visited.add(box)
                        comment_count += 1
                        print(f"Comment posted [{comment_count}/{COMMENT_TARGET}]: {comment}")
                        
                        time.sleep(random.uniform(3, 6))
                        
                    except Exception as e:
                        print(f"Failed to post comment: {str(e)}")
                        continue

            except Exception as e:
                print(f"Failed to find comment box: {str(e)}")
                continue

    finally:
        stop_event.set()
        scroll_thread.join()

def main():
    clear_cache()
    update_environment(ADS_ID)

    driver = start_browser()
    if not driver:
        print("Failed to start browser, terminating program.")
        return

    try:
        if not facebook_login(driver):
            print("Login failed, terminating program.")
            return

        post_comments(driver, default_comments)
    
    finally:
        driver.quit()
        requests.get(f"http://local.adspower.com:50325/api/v1/browser/stop?user_id={ADS_ID}")
        print("Browser instance closed.")

if __name__ == "__main__":
    main()
