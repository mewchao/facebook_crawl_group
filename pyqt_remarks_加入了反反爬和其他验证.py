import os
import threading

import pyotp
import random  # 导入 random 模块
import time
import traceback
from httpcore import TimeoutException
from selenium import webdriver
from selenium.common import ElementClickInterceptedException, ElementNotInteractableException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
import datetime  # 或者 from datetime import datetime
import undetected_chromedriver as uc


from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QHBoxLayout, QTextEdit, QRadioButton, QButtonGroup, QMessageBox, QGroupBox, QCheckBox, QFileDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# 定义默认账号信息
DEFAULT_USERNAME = "61550785360330"
DEFAULT_PASSWORD = "ooDKB3Ik"
DEFAULT_TWOFA = "PT7ETVPG2PR6V4PKLLP3KE6ET2V6WM4C"

# 定义默认 Chromedriver 路径
DEFAULT_CHROMEDRIVER_PATH = r"C:\chromedriver-win64\chromedriver-win64\chromedriver.exe"

# 定义评论库，包含五个不同的评论内容
default_comments = [
    "请问尺寸价格$$?",
    "+1",
    "你好，我要购买！",
    "请问size??",
    "你好～我要购買"
]

def random_sleep(min_seconds=1, max_seconds=3):
    time.sleep(random.uniform(min_seconds, max_seconds))

def override_permissions(driver, log_signal):
    """ 注入 JavaScript 覆盖 Permissions API """
    js_script = """
    (function() {
        const originalQuery = navigator.permissions.query;
        navigator.permissions.query = function(parameters) {
            if (parameters.name === 'geolocation') {
                return Promise.resolve({ state: 'prompt' });
            }
            if (parameters.name === 'notifications') {
                return Promise.resolve({ state: 'prompt' });
            }
            if (parameters.name === 'camera') {
                return Promise.resolve({ state: 'prompt' });
            }
            if (parameters.name === 'microphone') {
                return Promise.resolve({ state: 'prompt' });
            }
            return originalQuery(parameters);
        };
    })();
    """
    try:
        driver.execute_script(js_script)
        log_signal.emit("成功覆盖 navigator.permissions.query。")
    except Exception as e:
        log_signal.emit(f"覆盖 navigator.permissions.query 时发生错误: {str(e)}")


def modify_webgl(driver, log_signal):
    """ 修改 WebGL Vendor 和 Renderer """
    js_script = """
    Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === this.VENDOR) {
            return 'Google Inc. (AMD)';
        }
        if (parameter === this.RENDERER) {
            return 'ANGLE (AMD, AMD Radeon(TM) Graphics (0x00001681) Direct3D11 vs_5_0 ps_5_0, D3D11)';
        }
        return getParameter(parameter);
    };
    """
    try:
        driver.execute_script(js_script)
        log_signal.emit("成功修改 WebGL 信息。")
    except Exception as e:
        log_signal.emit(f"修改 WebGL 信息时发生错误: {str(e)}")


def hide_webdriver(driver, log_signal):
    """ 隐藏 WebDriver 和相关标志 """
    try:
        # 隐藏 navigator.webdriver
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        log_signal.emit("成功隐藏 navigator.webdriver。")

        # 覆盖 plugins 和 languages
        driver.execute_script("""
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3],
        });
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'zh-CN'],
        });
        """)
        log_signal.emit("成功覆盖 navigator.plugins 和 navigator.languages。")
    except Exception as e:
        log_signal.emit(f"隐藏 WebDriver 时发生错误: {str(e)}")

def random_sleep(min_seconds=1, max_seconds=3):
    time.sleep(random.uniform(min_seconds, max_seconds))


class Worker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, use_default, username, password, twofa, comments, group_id, number_id, chromedriver_path):
        super().__init__()
        self.use_default = use_default
        self.username = username if not use_default else DEFAULT_USERNAME
        self.password = password if not use_default else DEFAULT_PASSWORD
        self.twofa = twofa if not use_default else DEFAULT_TWOFA
        self.comments = comments
        self.group_id = group_id
        self.number_id = number_id
        self.chromedriver_path = chromedriver_path
        self.stop_requested = False

    def run(self):
        try:
            driver = self.initDriverProfile()
            self.log_signal.emit("初始化浏览器驱动成功。")
            is_live = self.checkLiveClone(driver)
            self.log_signal.emit(f"登录状态: {'Live' if is_live else 'unLive'}")
            if not is_live:
                self.log_signal.emit("未能检测到 Facebook 登录状态。")
                driver.quit()
                self.finished_signal.emit()
                return

            login_success = self.loginBy2FA(driver, self.username, self.password, self.twofa)
            if login_success:
                self.log_signal.emit("登录成功。")
            else:
                self.log_signal.emit("登录失败。")
                driver.quit()
                self.finished_signal.emit()
                return

            time.sleep(5)
            # 开始爬取 启动滚动线程
            self.getPostsGroup(driver, self.group_id, self.number_id)
            driver.quit()
            self.log_signal.emit("任务完成。")
        except Exception as e:
            self.log_signal.emit(f"发生错误: {str(e)}")
            traceback_str = ''.join(traceback.format_tb(e.__traceback__))
            self.log_signal.emit(traceback_str)
        finally:
            self.finished_signal.emit()


    def initDriverProfile(self):
        try:
            # 使用 undetected-chromedriver
            desired_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0"
            prefs = {
                "profile.default_content_setting_values.notifications": 1,    # 1: prompt, 2: block
                "profile.default_content_setting_values.geolocation": 1,
                "profile.default_content_setting_values.media_stream": 1,      # 摄像头和麦克风
                "profile.default_content_setting_values.automatic_downloads": 1,
                "profile.default_content_setting_values.popups": 1,
            }

            chrome_options = uc.ChromeOptions()
            chrome_options.add_argument(f"user-agent={desired_user_agent}")
            chrome_options.add_argument("--lang=en-US,zh-CN")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-feature=IsolateOrigins,site-per-process")
            chrome_options.add_argument("--no-first-run")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-translate")
            chrome_options.add_argument("--ignore-certificate-error-spki-list")
            chrome_options.add_argument("--ignore-certificate-errors")

            chrome_options.add_experimental_option("prefs", prefs)
            # 移除以下两行以避免冲突
            # chrome_options.add_experimental_option("useAutomationExtension", False)
            # chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])

            # 初始化 undetected-chromedriver
            driver = uc.Chrome(options=chrome_options)
            self.log_signal.emit("初始化 undetected-chromedriver 成功。")

            # 隐藏 WebDriver 和相关标志
            hide_webdriver(driver, self.log_signal)

            # 修改 WebGL 信息
            modify_webgl(driver, self.log_signal)

            # 覆盖 Permissions API
            override_permissions(driver, self.log_signal)

            # 加载 stealth.min.js
            try:
                stealth_js_path = resource_path('stealth.min.js')
                if not os.path.exists(stealth_js_path):
                    self.log_signal.emit("未找到 stealth.min.js 文件。")
                else:
                    with open(stealth_js_path, 'r', encoding='utf-8') as f:
                        js = f.read()
                    try:
                        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': js})
                        self.log_signal.emit("成功加载 stealth.min.js。")
                    except Exception as e:
                        self.log_signal.emit(f"加载 stealth.min.js 时发生错误: {str(e)}")
            except Exception as e:
                self.log_signal.emit(f"加载 stealth.min.js 时发生错误: {str(e)}")

            return driver
        except Exception as e:
            self.log_signal.emit(f"初始化浏览器驱动时发生错误: {str(e)}")
            traceback_str = ''.join(traceback.format_tb(e.__traceback__))
            self.log_signal.emit(traceback_str)
            raise

    def checkLiveClone(self, driver):
        try:
            driver.get("https://mbasic.facebook.com/")
            random_sleep()
            element_live = driver.find_elements(By.ID, "content")
            return len(element_live) > 0
        except Exception as e:
            self.log_signal.emit("查看 Facebook 状态时发生错误。")
            self.log_signal.emit(str(e))
            traceback.print_exc()
            return False

    def getCodeFrom2FA(self, code):
        totp = pyotp.TOTP(str(code).strip().replace(" ", "")[:32])
        random_sleep()
        return totp.now()

    def loginBy2FA(self, driver, username, password, code):
        try:
            self.log_signal.emit("访问登录页面。")
            driver.get("https://mbasic.facebook.com/login/?next&ref=dbl&fl&refid=8")
            random_sleep()

            self.log_signal.emit("查找用户名输入框。")
            user_name_element = driver.find_elements(By.CSS_SELECTOR, "#email")
            if not user_name_element:
                self.log_signal.emit("未找到用户名输入框。")
                return False
            user_name_element[0].send_keys(username)
            self.log_signal.emit(f"输入用户名: {username}")
            random_sleep()

            self.log_signal.emit("查找密码输入框。")
            password_element = driver.find_elements(By.CSS_SELECTOR, "#pass")
            if not password_element:
                self.log_signal.emit("未找到密码输入框。")
                return False
            password_element[0].send_keys(password)
            self.log_signal.emit("输入密码。")
            random_sleep()

            self.log_signal.emit("查找并点击登录按钮。")
            btn_submit = driver.find_elements(By.CSS_SELECTOR, "#loginbutton")
            if not btn_submit:
                self.log_signal.emit("未找到登录按钮。")
                return False
            btn_submit[0].click()
            self.log_signal.emit("点击登录按钮。")
            random_sleep()

            wait = WebDriverWait(driver, 30)

            self.log_signal.emit("等待并点击 '其他方式继续' 按钮。")

            other_funs_continue_css_selector = "span.x1lliihq.x193iq5w.x6ikm8r.x10wlt62.xlyipyv.xuxw1ft"
            try:
                other_funs_continue = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, other_funs_continue_css_selector))
                )
                if other_funs_continue:
                    other_funs_continue.click()
                    self.log_signal.emit("点击 '其他方式继续' 按钮。")
                    random_sleep()

                    self.log_signal.emit("等待并点击单选按钮。")
                    radio_button_xpath_expression = "//input[@type='radio' and @name='unused' and @value='1']"
                    radio_button = wait.until(
                        EC.element_to_be_clickable((By.XPATH, radio_button_xpath_expression))
                    )
                    radio_button.click()
                    self.log_signal.emit("点击单选按钮。")
                    random_sleep()

                    self.log_signal.emit("等待并点击 '繼續' 按钮。")
                    try:
                        self.log_signal.emit("等待 '繼續' 按钮可点击。")

                        continue_button = WebDriverWait(driver, 20).until(
                            EC.element_to_be_clickable(
                                (By.XPATH, "//div[@role='button' and .//span[text()='繼續']]")
                            )
                        )
                        # 滚动到按钮以确保其可见
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", continue_button)
                        time.sleep(1)  # 等待滚动完成

                        self.log_signal.emit("'繼續' 按钮找到，准备点击。")

                        actions = ActionChains(driver)
                        actions.move_to_element(continue_button).click().perform()

                        # 滚动到元素
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", continue_button)
                        random_sleep()

                        # 尝试直接点击
                        try:
                            continue_button.click()
                            self.log_signal.emit("直接点击 '繼續' 按钮成功。")
                        except (ElementClickInterceptedException, ElementNotInteractableException) as e:
                            self.log_signal.emit("直接点击失败，尝试使用 ActionChains。")
                            actions = ActionChains(driver)
                            actions.move_to_element(continue_button).click().perform()
                            self.log_signal.emit("通过 ActionChains 点击 '繼續' 按钮成功。")

                        # 最后使用 JavaScript 点击
                        driver.execute_script("arguments[0].click();", continue_button)
                        self.log_signal.emit("通过 JavaScript 点击 '繼續' 按钮成功。")

                        # 尝试截图（可选）
                        # driver.save_screenshot("after_click_continue.png")

                    except TimeoutException:
                        self.log_signal.emit("等待 '繼續' 按钮超时。")
                        # driver.save_screenshot("timeout_click_continue.png")
                        raise
                    except Exception as e:
                        self.log_signal.emit(f"点击 '繼續' 按钮时发生错误: {str(e)}")
                        # driver.save_screenshot("error_click_continue.png")
                        raise
                    random_sleep()

            except TimeoutException:
                self.log_signal.emit("未找到 '其他方式继续' 按钮。")
                return False

            self.log_signal.emit("查找2FA代码输入框。")

            fa_code_element = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//input[contains(@class, 'x1a2a7pz') and contains(@class, 'xzsf02u')]")
                )
            )
            if fa_code_element:
                fa_code = str(self.getCodeFrom2FA(code))
                fa_code_element.send_keys(fa_code)
                self.log_signal.emit(f"输入2FA代码: {fa_code}")
                time.sleep(0.5)

                self.log_signal.emit("查找并点击2FA确认按钮。")
                btn_2fa = driver.find_elements(By.CSS_SELECTOR, ".x3nfvp2.x1n2onr6.xh8yej3")
                if btn_2fa:
                    btn_2fa[0].click()
                    self.log_signal.emit("点击2FA确认按钮。")
                    time.sleep(0.5)

                    try:
                        self.log_signal.emit("等待并点击 '信任此设备' 按钮。")
                        xpath = ".x1lliihq.x193iq5w.x6ikm8r.x10wlt62.xlyipyv.xuxw1ft"
                        btn_2fa_continue = WebDriverWait(driver, 20).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, xpath))
                        )

                        if btn_2fa_continue:
                            btn_2fa_continue.click()
                            self.log_signal.emit("2FA 设备信任成功。")
                    except TimeoutException:
                        self.log_signal.emit("未找到 'Trust this device' 按钮。")
            return True
        except Exception as e:
            self.log_signal.emit(f"登录过程中发生错误: {str(e)}")
            traceback.print_exc()
            return False

    def smooth_scroll_to_fixed_distance(self, driver, distance):
        driver.execute_script(f"""
            window.scrollBy({{ top: {distance}, behavior: 'smooth' }});
        """)

    def auto_scroll(self, driver, stop_event, pixels=200, interval=20):
        """
        自动滚动页面的函数，每隔 `interval` 秒滚动 `pixels` 像素。
        直到 `stop_event` 被设置为 True。
        """
        while not stop_event.is_set():
            try:
                driver.execute_script(f"window.scrollBy(0, {pixels});")
                # 你可以根据需要调整滚动距离和频率
                time.sleep(interval)
            except Exception as e:
                self.log_signal.emit(f"滚动线程遇到错误: {str(e)}")
                break

    def getPostsGroup(self, driver, groupId, numberId):
        stop_event = threading.Event()
        # 启动平滑滚动线程
        scroll_thread = threading.Thread(target=self.auto_scroll, args=(driver, stop_event))
        scroll_thread.start()  # 启动自动滚动线程
        self.log_signal.emit("自动滚动线程已启动。")

        try:
            driver.get(f"https://mbasic.facebook.com/groups/{groupId}")
            wait = WebDriverWait(driver, 6)

            collected_links = 0
            visited_buttons = set()

            while collected_links < numberId and not self.stop_requested:
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

                    try:
                        copy_buttons = wait.until(
                            EC.presence_of_all_elements_located(
                                (By.XPATH, xpath)
                            )
                        )
                        self.log_signal.emit(f"找到 {len(copy_buttons)} 个评论按钮。")
                    except TimeoutException:
                        self.smooth_scroll_to_fixed_distance(driver, 650)
                        self.log_signal.emit("未在6秒内找到指定的复制按钮，继续执行其他操作。")
                        continue

                    for button in copy_buttons:
                        if collected_links >= numberId or self.stop_requested:
                            break

                        if button in visited_buttons:
                            continue

                        try:
                            wait.until(EC.element_to_be_clickable(button))

                            self.smooth_scroll_to_fixed_distance(driver, 650)
                            time.sleep(0.8)
                            actions = ActionChains(driver)
                            actions.move_to_element(button).perform()
                            time.sleep(0.6)

                            try:
                                selected_comment = random.choice(self.comments)
                                button.click()
                                time.sleep(0.5)
                                button.send_keys(selected_comment)
                                self.smooth_scroll_to_fixed_distance(driver, 100)
                                time.sleep(0.8)

                                button.send_keys(Keys.ENTER)
                                time.sleep(3)
                                self.log_signal.emit(f"已发布评论: {selected_comment}")
                                collected_links += 1
                            except Exception as click_exception:
                                self.log_signal.emit(f"常规点击失败，尝试 JavaScript 点击: {str(click_exception)}")

                            time.sleep(0.5)
                            visited_buttons.add(button)
                            time.sleep(0.5)

                        except Exception as e:
                            self.log_signal.emit(f"点击按钮时发生错误: {str(e)}")
                            self.smooth_scroll_to_fixed_distance(driver, 650)
                            break
                        # 慢速版本 防止封号
                        time.sleep(60)

                except Exception as e:
                    self.log_signal.emit(f"Error: {str(e)}")
                    continue

        except Exception as e:
            self.log_signal.emit(f"An error occurred: {str(e)}")
        finally:
            stop_event.set()
            scroll_thread.join()
            self.log_signal.emit("自动滚动线程已停止。")

    def stop(self):
        self.stop_requested = True


class FacebookAutoCommenter(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.worker = None

    def initUI(self):
        self.setWindowTitle("Facebook 自动评论工具")
        self.setGeometry(100, 100, 600, 800)

        layout = QVBoxLayout()

        # 账号信息组
        account_group = QGroupBox("账号信息")
        account_layout = QVBoxLayout()

        # 添加复选框以使用默认账号
        self.use_default_checkbox = QCheckBox("使用默认账号")
        self.use_default_checkbox.stateChanged.connect(self.toggle_default_account)
        account_layout.addWidget(self.use_default_checkbox)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("用户名(已关注该群组)")
        account_layout.addWidget(QLabel("用户名:"))
        account_layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("密码")
        account_layout.addWidget(QLabel("密码:"))
        account_layout.addWidget(self.password_input)

        self.twofa_input = QLineEdit()
        self.twofa_input.setPlaceholderText("2FA 密钥")
        account_layout.addWidget(QLabel("2FA 密钥:"))
        account_layout.addWidget(self.twofa_input)

        account_group.setLayout(account_layout)
        layout.addWidget(account_group)

        # 评论设置组
        comment_group = QGroupBox("评论设置")
        comment_layout = QVBoxLayout()

        self.radio_default = QRadioButton("使用默认评论")
        self.radio_custom = QRadioButton("使用自定义评论")
        self.radio_default.setChecked(True)

        self.button_group = QButtonGroup()
        self.button_group.addButton(self.radio_default)
        self.button_group.addButton(self.radio_custom)
        self.button_group.buttonClicked.connect(self.toggle_comment_mode)

        comment_layout.addWidget(self.radio_default)
        comment_layout.addWidget(self.radio_custom)

        # 自定义评论输入
        self.custom_comments_group = QGroupBox("自定义评论内容")
        self.custom_comments_layout = QVBoxLayout()
        self.custom_comments = []
        for i in range(5):
            comment_input = QLineEdit()
            comment_input.setPlaceholderText(f"自定义评论 {i + 1}")
            self.custom_comments.append(comment_input)
            self.custom_comments_layout.addWidget(comment_input)
        self.custom_comments_group.setLayout(self.custom_comments_layout)
        comment_layout.addWidget(self.custom_comments_group)
        self.custom_comments_group.setVisible(False)  # 默认隐藏

        comment_group.setLayout(comment_layout)
        layout.addWidget(comment_group)

        # 群组和数量设置
        group_layout = QHBoxLayout()
        self.group_id_input = QLineEdit()
        self.group_id_input.setPlaceholderText("群组 ID")
        self.number_id_input = QLineEdit()
        self.number_id_input.setPlaceholderText("评论数量")
        group_layout.addWidget(QLabel("群组 ID:"))
        group_layout.addWidget(self.group_id_input)
        group_layout.addWidget(QLabel("评论数量:"))
        group_layout.addWidget(self.number_id_input)
        layout.addLayout(group_layout)

        # Chromedriver 路径
        chromedriver_layout = QHBoxLayout()
        self.chromedriver_input = QLineEdit()
        self.chromedriver_input.setPlaceholderText("Chromedriver 路径")
        chromedriver_layout.addWidget(QLabel("Chromedriver 路径:"))
        chromedriver_layout.addWidget(self.chromedriver_input)

        # 添加“浏览”按钮
        self.browse_button = QPushButton("浏览")
        self.browse_button.clicked.connect(self.browse_chromedriver)
        chromedriver_layout.addWidget(self.browse_button)

        layout.addLayout(chromedriver_layout)

        # 设置默认 Chromedriver 路径
        if os.path.exists(DEFAULT_CHROMEDRIVER_PATH):
            self.chromedriver_input.setText(DEFAULT_CHROMEDRIVER_PATH)

        # 启动按钮
        self.start_button = QPushButton("开始")
        self.start_button.clicked.connect(self.start_process)
        layout.addWidget(self.start_button)

        # 停止按钮
        self.stop_button = QPushButton("停止")
        self.stop_button.clicked.connect(self.stop_process)
        self.stop_button.setEnabled(False)
        layout.addWidget(self.stop_button)

        # 日志显示
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(QLabel("日志:"))
        layout.addWidget(self.log_text)

        self.setLayout(layout)

    def browse_chromedriver(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择 Chromedriver", "", "Executables (*.exe);;All Files (*)", options=options
        )
        if file_path:
            self.chromedriver_input.setText(file_path)

    def toggle_default_account(self, state):
        if state == Qt.Checked:
            self.username_input.setDisabled(True)
            self.password_input.setDisabled(True)
            self.twofa_input.setDisabled(True)
            self.log_text.append("已选择使用默认账号。")
        else:
            self.username_input.setDisabled(False)
            self.password_input.setDisabled(False)
            self.twofa_input.setDisabled(False)
            self.log_text.append("已选择使用自定义账号。")

    def toggle_comment_mode(self):
        if self.radio_custom.isChecked():
            self.custom_comments_group.setVisible(True)
            self.log_text.append("已选择使用自定义评论。")
        else:
            self.custom_comments_group.setVisible(False)
            self.log_text.append("已选择使用默认评论。")

    def start_process(self):
        use_default = self.use_default_checkbox.isChecked()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        twofa = self.twofa_input.text().strip()
        group_id = self.group_id_input.text().strip()
        number_id = self.number_id_input.text().strip()
        chromedriver_path = self.chromedriver_input.text().strip()

        # 验证输入
        if not use_default:
            if not all([username, password, twofa]):
                QMessageBox.warning(self, "输入错误", "请填写所有账号信息字段，或选择使用默认账号。")
                return
        if not all([group_id, number_id, chromedriver_path]):
            QMessageBox.warning(self, "输入错误", "请填写所有必填字段。")
            return

        try:
            number_id = int(number_id)
            if number_id <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "输入错误", "评论数量必须是一个正整数。")
            return

        if self.radio_default.isChecked():
            comments = default_comments.copy()
        else:
            comments = []
            for comment_input in self.custom_comments:
                comment = comment_input.text().strip()
                if comment:
                    comments.append(comment)
            if not comments:
                QMessageBox.warning(self, "输入错误", "请至少输入一个自定义评论。")
                return

        if not os.path.exists(chromedriver_path):
            QMessageBox.warning(self, "路径错误", "Chromedriver 路径不存在。")
            return

        # 启动 Worker 线程
        self.worker = Worker(
            use_default=use_default,
            username=username,
            password=password,
            twofa=twofa,
            comments=comments,
            group_id=group_id,
            number_id=number_id,
            chromedriver_path=chromedriver_path
        )
        self.worker.log_signal.connect(self.append_log)
        self.worker.finished_signal.connect(self.process_finished)
        self.worker.start()

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.log_text.append("任务已启动。")

    def stop_process(self):
        if self.worker:
            self.worker.stop()
            self.log_text.append("停止任务请求已发送。")
            self.stop_button.setEnabled(False)

    def append_log(self, message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    def process_finished(self):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.log_text.append("任务已结束。")


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = FacebookAutoCommenter()
    window.show()
    sys.exit(app.exec_())
