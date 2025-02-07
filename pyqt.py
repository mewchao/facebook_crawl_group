import sys
import os
import time
import datetime
import traceback
import pyperclip
import pyotp
import random

from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
    QCheckBox,  # 导入QCheckBox
)
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, QObject

# ========= 下面是从题主给出的爬虫代码中复制的相关函数，可以根据需要精简/拆分 =========
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
from fake_useragent import UserAgent

def get_random_user_agent():
    ua = UserAgent()
    return ua.random


def random_sleep(min_seconds=1, max_seconds=3):
    time.sleep(random.uniform(min_seconds, max_seconds))


def initDriverProfile():
    CHROMEDRIVER_PATH = r"C:\chromedriver-win64\chromedriver-win64\chromedriver.exe"
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("disable-infobars")
    chrome_options.add_argument("--disable-gpu")  # Windows workaround
    chrome_options.add_argument("--verbose")
    chrome_options.add_argument("--no-default-browser-check")
    chrome_options.add_argument("--ignore-ssl-errors")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-feature=IsolateOrigins,site-per-process")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-translate")
    chrome_options.add_argument("--ignore-certificate-error-spki-list")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("useAutomationExtension", False)
    prefs = {"profile.default_content_setting_values.notifications": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument("--start-maximized")  # 最大化浏览器窗口
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument("disable-infobars")
    chrome_options.add_argument(f"user-agent={get_random_user_agent()}")

    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver


def checkLiveClone(driver):
    """检查账号是否能登录成功"""
    try:
        driver.get("https://mbasic.facebook.com/")
        time.sleep(2)
        elementLive = driver.find_elements(By.ID, "content")
        if len(elementLive) > 0:
            print("Live")
        else:
            print("unLive")
        return True
    except Exception as e:
        print("view fb err")
        print("Exception:", e)
        traceback.print_exc()


def getCodeFrom2FA(code):
    totp = pyotp.TOTP(str(code).strip().replace(" ", "")[:32])
    time.sleep(2)
    return totp.now()


def loginBy2FA(driver, username, password, code):
    """登录 Facebook，支持二次验证"""
    driver.get("https://mbasic.facebook.com/login/?next&ref=dbl&fl&refid=8")
    random_sleep()

    userNameElement = driver.find_elements(By.CSS_SELECTOR, "#email")
    userNameElement[0].send_keys(username)
    random_sleep()

    passwordElement = driver.find_elements(By.CSS_SELECTOR, "#pass")
    passwordElement[0].send_keys(password)
    random_sleep()

    btnSubmit = driver.find_elements(By.CSS_SELECTOR, "#loginbutton")
    btnSubmit[0].click()
    random_sleep()

    faCodeElement = driver.find_elements(By.XPATH, "//*[contains(@id, 'r3')]")
    faCodeElement[0].send_keys(str(getCodeFrom2FA(code)))
    random_sleep()

    btn2fa = driver.find_elements(By.CSS_SELECTOR, ".x3nfvp2.x1n2onr6.xh8yej3")
    btn2fa[0].click()
    random_sleep()

    # 点击 "Trust this device" 按钮
    try:
        xpath = "//span[text()='Trust this device' or text()='信任这台设备' or text()='信任此裝置']"
        btn2faContinue = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        if btn2faContinue:
            btn2faContinue.click()
    except:
        print("no find 'Trust this device' button")

    return True


def save_to_file(filename, link):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            existing_links = f.readlines()
            existing_links = [line.strip() for line in existing_links]
        if link in existing_links:
            print(f"Link already exists, skipping: {link}")
            return
    with open(filename, "a") as f:
        line_number = sum(1 for _ in open(filename)) + 1
        f.write(link + "\n")
        print(f"{line_number} Link saved: {link}")


def smooth_scroll_to_fixed_distance(driver, distance):
    driver.execute_script(f"""
        window.scrollBy({{ top: {distance}, behavior: 'smooth' }});
    """)


def getPostsGroup(driver, groupId, numberId):
    """核心爬虫函数，给定groupId，收集一定数量的复制链接"""
    now = datetime.datetime.now()
    formatted_time = now.strftime("%Y-%m-%d-%Hh-%Mmin")
    output_file = groupId + "time" + formatted_time + ".txt"
    pyperclip.copy("")

    try:
        driver.get(f"https://mbasic.facebook.com/groups/{groupId}")
        wait = WebDriverWait(driver, 10)
        collected_links = 0
        visited_links = set()
        visited_buttons = set()
        scroll_pause_time = 2
        scroll_increment = 400

        while collected_links < numberId:
            try:
                copy_buttons = wait.until(
                    EC.presence_of_all_elements_located(
                        (By.XPATH, "//*[@aria-label='Copy link']")
                    )
                )
            except Exception as e:
                print("Error locating copy buttons:", e)
                break

            for button in copy_buttons:
                if collected_links >= numberId:
                    print("Number of collected links reached the limit.")
                    break

                if button in visited_buttons:
                    continue

                try:
                    wait.until(EC.element_to_be_clickable(button))
                    smooth_scroll_to_fixed_distance(driver, 650)
                    random_sleep()
                    actions = ActionChains(driver)
                    actions.move_to_element(button).perform()
                    random_sleep()

                    try:
                        button.click()
                    except Exception as click_exception:
                        print("Regular click failed:", click_exception)

                    random_sleep()
                    clipboard_content = pyperclip.paste()

                    if clipboard_content and clipboard_content not in visited_links:
                        visited_links.add(clipboard_content)
                        save_to_file(output_file, clipboard_content)
                        collected_links += 1
                        print(f"Link {collected_links} copyed: {clipboard_content}")

                    visited_buttons.add(button)
                    random_sleep()

                except Exception as e:
                    print("Error clicking button:", e)
                    random_sleep()
                    smooth_scroll_to_fixed_distance(driver, 650)
                    continue

            driver.execute_script(f"window.scrollBy(0, {scroll_increment});")
            time.sleep(scroll_pause_time)
            current_scroll = driver.execute_script(
                "return window.pageYOffset + window.innerHeight;"
            )
            print(f"Current scroll position: {current_scroll}")

        print("Scrolling done.")

    except Exception as e:
        print("An error occurred:", e)
    finally:
        print(f"Links saved to {output_file}")


# =========================== 线程 Worker 对象 ================================
class CrawlerWorker(QObject):
    """用于在后台线程执行爬虫工作的类"""
    finished = pyqtSignal(str)  # 爬虫结束信号
    progress = pyqtSignal(str)  # 过程更新信号

    def __init__(self, group_id, username=None, password=None, two_fa_code=None, parent=None):
        super().__init__(parent)
        self.group_id = group_id
        self._running = True

        # 默认账号信息
        self.default_username = "100093652996566"
        self.default_password = "GaoGaoPhuongNamPhim_L4Hn31"
        self.default_two_fa_code = "OFQOASXSK6TYNS22NLA5UIAZINTF43IS"

        # 如果提供了账号信息，则使用用户提供的
        self.username = username if username else self.default_username
        self.password = password if password else self.default_password
        self.two_fa_code = two_fa_code if two_fa_code else self.default_two_fa_code

        # 打印接收到的参数（为安全起见，部分信息进行了掩码处理）
        print(f"[CrawlerWorker] 初始化: group_id={self.group_id}, username={self.username}, "
              f"password={'*' * len(self.password)}, two_fa_code={'*' * len(self.two_fa_code)}")

    @pyqtSlot()
    def run(self):
        """在子线程中执行爬虫逻辑"""
        try:
            # 输出实际使用的账号信息
            print("=== 登录信息 ===")
            print(f"用户名: {self.username}")
            print(f"密码: {self.password}")
            print(f"2FA代码: {self.two_fa_code}")
            print("================\n")

            self.progress.emit("初始化浏览器...")
            driver = initDriverProfile()

            # 登录
            self.progress.emit("开始登录...")
            checkLiveClone(driver)
            loginBy2FA(driver, self.username, self.password, self.two_fa_code)
            self.progress.emit("登录完成，准备爬虫...")

            # 开始爬虫
            self.progress.emit(f"开始爬取 GroupID = {self.group_id}")
            getPostsGroup(driver, self.group_id, 1000)  # 采集数量可根据需要修改

            # 完成
            self.progress.emit("爬虫完成！")
            self.finished.emit("爬虫已完成。")
        except Exception as e:
            self.finished.emit(f"爬虫异常结束: {str(e)}")
        finally:
            self._running = False

    def stop(self):
        """停止爬虫的接口（示例中仅设置标志，实际中可根据需要完善退出逻辑）"""
        self._running = False
        self.finished.emit("爬虫被手动停止。")


# =========================== 主界面 ================================
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

        self.thread = None
        self.worker = None

    def initUI(self):
        self.setWindowTitle("PyQt 爬虫示例")
        self.resize(400, 400)  # 增加高度以容纳更多输入框

        # Group ID 输入
        self.label_input = QLabel("请输入Group ID:")
        self.lineEdit_group_id = QLineEdit()
        self.lineEdit_group_id.setPlaceholderText("例如：1003349513083986")

        # 账号输入
        self.label_username = QLabel("账号(前提加入该群组):")
        self.lineEdit_username = QLineEdit()
        self.lineEdit_username.setPlaceholderText("请输入账号")

        # 密码输入
        self.label_password = QLabel("密码:")
        self.lineEdit_password = QLineEdit()
        self.lineEdit_password.setEchoMode(QLineEdit.Password)
        self.lineEdit_password.setPlaceholderText("请输入密码")

        # 2FA 输入
        self.label_2fa = QLabel("2FA代码:")
        self.lineEdit_2fa = QLineEdit()
        self.lineEdit_2fa.setPlaceholderText("请输入2FA代码")

        # 使用默认账号复选框
        self.checkbox_default = QCheckBox("使用默认账号")
        self.checkbox_default.setChecked(True)
        self.checkbox_default.stateChanged.connect(self.toggle_default_account)

        # 状态显示
        self.label_status = QLabel("状态：等待开始")

        # 按钮
        self.btn_start = QPushButton("开始爬虫")
        self.btn_stop = QPushButton("结束爬虫")

        self.btn_start.clicked.connect(self.start_crawling)
        self.btn_stop.clicked.connect(self.stop_crawling)

        # 布局
        layout_input = QVBoxLayout()
        layout_input.addWidget(self.label_input)
        layout_input.addWidget(self.lineEdit_group_id)

        layout_account = QVBoxLayout()
        layout_account.addWidget(self.checkbox_default)
        layout_account.addWidget(self.label_username)
        layout_account.addWidget(self.lineEdit_username)
        layout_account.addWidget(self.label_password)
        layout_account.addWidget(self.lineEdit_password)
        layout_account.addWidget(self.label_2fa)
        layout_account.addWidget(self.lineEdit_2fa)

        layout_buttons = QHBoxLayout()
        layout_buttons.addWidget(self.btn_start)
        layout_buttons.addWidget(self.btn_stop)

        main_layout = QVBoxLayout()
        main_layout.addLayout(layout_input)
        main_layout.addLayout(layout_account)
        main_layout.addWidget(self.label_status)
        main_layout.addLayout(layout_buttons)

        self.setLayout(main_layout)

        # 初始时禁用自定义账号输入框
        self.toggle_default_account()

    def toggle_default_account(self):
        """切换是否使用默认账号，禁用或启用输入框"""
        use_default = self.checkbox_default.isChecked()
        self.lineEdit_username.setEnabled(not use_default)
        self.lineEdit_password.setEnabled(not use_default)
        self.lineEdit_2fa.setEnabled(not use_default)

    def start_crawling(self):
        group_id = self.lineEdit_group_id.text().strip()
        if not group_id:
            QMessageBox.warning(self, "提示", "请先输入Group ID！")
            return

        use_default = self.checkbox_default.isChecked()

        if not use_default:
            username = self.lineEdit_username.text().strip()
            password = self.lineEdit_password.text().strip()
            two_fa_code = self.lineEdit_2fa.text().strip()

            if not username or not password or not two_fa_code:
                QMessageBox.warning(self, "提示", "请填写完整的账号、密码和2FA代码！")
                return
            print(f"使用自定义账号信息: 用户名={username}, 密码={password}, 2FA={two_fa_code}")
        else:
            username = None
            password = None
            two_fa_code = None
            print("使用默认账号信息")

        # 创建线程和worker
        self.thread = QThread()
        self.worker = CrawlerWorker(group_id, username, password, two_fa_code)
        self.worker.moveToThread(self.thread)

        # 连接信号
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_crawler_finished)
        self.worker.progress.connect(self.on_crawler_progress)
        self.worker.finished.connect(self.thread.quit)      # 完成后退出线程
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        # 启动线程
        self.label_status.setText("状态：正在爬虫中...")
        self.thread.start()

    @pyqtSlot(str)
    def on_crawler_progress(self, msg):
        """更新爬虫进度到界面"""
        self.label_status.setText(f"状态：{msg}")

    @pyqtSlot(str)
    def on_crawler_finished(self, msg):
        """爬虫结束后的处理"""
        self.label_status.setText(f"状态：{msg}")
        self.thread = None
        self.worker = None

    def stop_crawling(self):
        """终止爬虫"""
        if self.worker is not None:
            self.worker.stop()
            self.label_status.setText("状态：请求停止爬虫...")

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()