import sys
import random
import time
import threading
import requests
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton, QCheckBox, QGroupBox, QGridLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from time import sleep

class CommentPosterApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """Set up the UI"""
        self.setWindowTitle("Comment Poster")
        self.setGeometry(0, 0, 1920, 1080)  # Make the window full-screen

        # Set the font for the labels and buttons
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)

        # Main layout for the window
        main_layout = QVBoxLayout()

        # Create a grid layout for input fields and checkboxes
        grid_layout = QGridLayout()

        self.inputs = []
        self.checkboxes = []

        # Create input fields for up to 10 groups per browser
        for i in range(20):
            checkbox = QCheckBox(f"Enable for Browser {i + 1}", self)
            inputs_group = []
            input_ads = QLineEdit(self)  # For each browser, add a field for ADS_ID
            input_ads.setDisabled(True)
            grid_layout.addWidget(QLabel(f"ADS_ID {i + 1}:"), i, 1)  # Adjust column for ADS_ID label
            grid_layout.addWidget(input_ads, i, 2)  # Adjust column for ADS_ID input field

            for j in range(10):
                input_group = QLineEdit(self)
                input_group.setDisabled(True)
                inputs_group.append(input_group)
                grid_layout.addWidget(QLabel(f"GROUP_ID {i * 10 + j + 1}:"), i, j * 2 + 3)  # Adjust column for GROUP_ID label
                grid_layout.addWidget(input_group, i, j * 2 + 4)  # Adjust column for GROUP_ID input fields

            # Place checkbox in the first column
            grid_layout.addWidget(checkbox, i, 0, 1, 1)  # Checkbox in the first column, occupying one row and one column

            self.inputs.append((input_ads, inputs_group))
            self.checkboxes.append(checkbox)

            # Connect the checkbox state change to toggle_input_fields
            checkbox.toggled.connect(self.toggle_input_fields)

        # Add the grid layout to the main layout
        main_layout.addLayout(grid_layout)

        # Create a group box for custom comments
        comment_group = QGroupBox("Custom Comments")
        comment_group.setFont(font)
        comment_layout = QVBoxLayout()

        self.custom_comments = []
        for i in range(5):
            comment_input = QLineEdit(self)
            comment_input.setPlaceholderText(f"Comment {i + 1}")
            comment_layout.addWidget(comment_input)
            self.custom_comments.append(comment_input)

        comment_group.setLayout(comment_layout)
        main_layout.addWidget(comment_group)

        # Add a checkbox to select default comments or custom
        self.default_comment_checkbox = QCheckBox("Use default comments?", self)
        self.default_comment_checkbox.setFont(font)
        main_layout.addWidget(self.default_comment_checkbox)

        # Add submit button
        submit_btn = QPushButton("Submit", self)
        submit_btn.setFont(font)
        submit_btn.clicked.connect(self.submit)
        main_layout.addWidget(submit_btn)

        # Set the layout of the window
        self.setLayout(main_layout)

        # Keep track of which group each user has commented on
        self.user_groups_commented = {}

    def toggle_input_fields(self):
        """Enable or disable input fields based on checkbox status"""
        for i, checkbox in enumerate(self.checkboxes):
            input_ads, inputs_group = self.inputs[i]
            if checkbox.isChecked():
                input_ads.setEnabled(True)
                for input_group in inputs_group:
                    input_group.setEnabled(True)
            else:
                input_ads.setDisabled(True)
                for input_group in inputs_group:
                    input_group.setDisabled(True)

        # Ensure UI updates after toggling checkbox state
        QApplication.processEvents()

    def submit(self):
        """Handle submit button click"""
        data = {}
        for i, (input_ads, inputs_group) in enumerate(self.inputs):
            groups = []
            ads_id = input_ads.text().strip()
            if ads_id:  # Ensure ADS_ID is provided
                for input_group in inputs_group:
                    group_id = input_group.text().strip()
                    if group_id:
                        groups.append(group_id)
                if groups:
                    data[f"Browser {i + 1}"] = (ads_id, groups)

        # Get comments to use: either default or custom
        if self.default_comment_checkbox.isChecked():
            comments = [
                "What is the size and price$$?",
                "+1",
                "Hello, I want to buy!",
                "What is the size??",
                "Hi, I want to buy"
            ]
        else:
            comments = [comment.text().strip() for comment in self.custom_comments if comment.text().strip()]

        if data:
            # Call the automation function for each browser
            for browser, (ads_id, groups) in data.items():
                print(f"Running automation for {browser} with ADS_ID: {ads_id} and groups {groups}")
                threading.Thread(target=self.run_automation, args=(ads_id, groups, comments)).start()

    def run_automation(self, ads_id, groups, comments):
        """Run the automation for the given browser and groups"""
        COMMENT_TARGET = 30 + random.randint(0, 20)  # 30-50 comments per group per browser
        # COMMENT_TARGET = 2 
        COMMENT_DELAY = 5  # Delay after posting each comment

        def random_sleep(min_seconds=1, max_seconds=3):
            sleep(random.uniform(min_seconds, max_seconds))

        def human_typing_simulation(element, text):
            """Simulate slow typing to mimic human behavior"""
            for char in text:
                element.send_keys(char)
                random_sleep(0.3, 0.7)  # Slow typing speed

        def start_browser(ads_id):
            """Start the browser with a delay to prevent frequent API calls"""
            time.sleep(3)  # Add delay to prevent frequent API calls

            try:
                open_url = f"http://local.adspower.com:50325/api/v1/browser/start?user_id={ads_id}"
                response = requests.get(open_url).json()

                if response["code"] != 0:
                    print(f"Failed to start browser for {ads_id}: {response['msg']}")
                    return None

                chrome_options = Options()
                chrome_options.add_experimental_option("debuggerAddress", response["data"]["ws"]["selenium"])
                service = Service(executable_path=response["data"]["webdriver"])

                return webdriver.Chrome(service=service, options=chrome_options)
            except Exception as e:
                print(f"Browser initialization failed for {ads_id}: {str(e)}")
                return None

        def post_comments(driver, comments, groups):
            stop_event = threading.Event()
            scroll_thread = threading.Thread(target=auto_scroll, args=(driver, stop_event))
            scroll_thread.start()

            # Track which groups the current browser has commented on
            user_commented_groups = self.user_groups_commented.get(ads_id, set())

            try:
                while len(user_commented_groups) < len(groups):
                    # Select the next group that has not been commented yet
                    group_to_comment = None
                    for group in groups:
                        if group not in user_commented_groups:
                            group_to_comment = group
                            break
                    
                    if not group_to_comment:
                        break

                    # Start commenting in the selected group
                    driver.get(f"https://mbasic.facebook.com/groups/{group_to_comment}")
                    visited = set()
                    comment_count = 0

                    while comment_count < COMMENT_TARGET:
                        try:
                            xpath_expression = (
                                "//*[@aria-label='Write an answer…'] | "
                                "//*[@aria-label='Write a public comment…'] | "
                                "//*[@aria-label='输入回答…'] | "
                                "//*[@aria-label='发表公开评论…'] | "
                                "//*[@aria-label='公開留言……'] | "
                                "//*[@aria-label='撰寫回答……']"
                            )

                            xpath = "//*[contains(@class, 'xzsf02u') and contains(@class, 'x1a2a7pz') and contains(@class, 'x1n2onr6') and contains(@class, 'x14wi4xw')]"                   
                            comment_boxes = WebDriverWait(driver, 10).until(
                                EC.presence_of_all_elements_located(
                                    (By.XPATH, xpath)
                                )
                            )

                            for box in comment_boxes:
                                if comment_count >= COMMENT_TARGET:
                                    break

                                if box in visited:
                                    continue

                                try:
                                    ActionChains(driver).move_to_element(box).perform()
                                    random_sleep(1, 2)  # Pause before interacting with the box

                                    # Stop scrolling while typing the comment
                                    stop_event.set()

                                    comment = random.choice(comments)
                                    box.click()
                                    human_typing_simulation(box, comment + Keys.ENTER)

                                    visited.add(box)
                                    comment_count += 1
                                    print(f"Comment posted [{comment_count}/{COMMENT_TARGET}]: {comment}")

                                    # After posting the comment, start scrolling again
                                    stop_event.clear()  # Resume scrolling after posting the comment
                                    random_sleep(COMMENT_DELAY, COMMENT_DELAY + 5)  # Simulate break between comments

                                except Exception as e:
                                    print(f"Failed to post comment: {str(e)}")
                                    continue

                        except Exception as e:
                            print(f"Failed to find comment box: {str(e)}")
                            continue

                    user_commented_groups.add(group_to_comment)  # Mark this group as commented

                    # Update the record for this user
                    self.user_groups_commented[ads_id] = user_commented_groups

            finally:
                stop_event.set()
                scroll_thread.join()

        def auto_scroll(driver, stop_event):
            """Automatically scroll the page, but paused during typing"""
            while not stop_event.is_set():
                try:
                    driver.execute_script("window.scrollBy(0, 500);")
                    random_sleep(3, 7)  # Longer pauses to simulate natural scrolling
                except:
                    break

        # Start the browser in a new thread with a delay
        driver = start_browser(ads_id)
        if not driver:
            print(f"Failed to start browser for {ads_id}.")
            return

        try:
            post_comments(driver, comments, groups)  # List of groups to comment on
        finally:
            driver.quit()
            requests.get(f"http://local.adspower.com:50325/api/v1/browser/stop?user_id={ads_id}")
            print(f"Browser instance closed for {ads_id}.")

    def center(self):
        """Center the window on the screen but move it up a little"""
        screen_geometry = self.screen().geometry()
        window_geometry = self.geometry()
        x = (screen_geometry.width() - window_geometry.width()) // 2
        y = (screen_geometry.height() - window_geometry.height()) // 4  # Move window up to the top quarter
        self.move(x, y)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CommentPosterApp()
    window.show()
    sys.exit(app.exec_())
