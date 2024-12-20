import os
import shutil
import pyotp
import time
import requests
import traceback
import pyperclip
from time import sleep
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
import datetime


def initDriverProfile():
    CHROMEDRIVER_PATH = r"C:\chromedriver-win64\chromedriver-win64\chromedriver.exe"
    # WINDOW_SIZE = "1000,2000"
    chrome_options = Options()
    # chrome_options.add_argument("--headless")
    # chrome_options.add_argument("--window-size=%s" % WINDOW_SIZE)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("disable-infobars")
    (
        chrome_options.add_argument("--disable-gpu") if os.name == "nt" else None
    )  # Windows workaround
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
    chrome_options.add_argument(
        "--disable-dev-shm-usage"
    )  # overcome limited resource problems
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    # chrome_options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
    chrome_options.add_argument("disable-infobars")

    # 使用 Service 类传递 ChromeDriver 路径
    service = Service(CHROMEDRIVER_PATH)

    # 初始化 ChromeDriver
    driver = webdriver.Chrome(service=service, options=chrome_options)

    return driver


def checkLiveClone(driver):
    try:
        driver.get("https://mbasic.facebook.com/")
        time.sleep(2)
        # 使用 By.NAME 替代 find_elements_by_name
        elementLive = driver.find_elements(By.ID, "content")
        if len(elementLive) > 0:
            print("Live")
        else:
            print("unLive")
        return True
    except Exception as e:  # 捕获具体异常
        print("view fb err")
        print("Exception:", e)  # 打印异常信息
        traceback.print_exc()  # 打印完整的异常堆栈信息


def getCodeFrom2FA(code):
    totp = pyotp.TOTP(str(code).strip().replace(" ", "")[:32])
    time.sleep(2)
    return totp.now()


def loginBy2FA(driver, username, password, code):
    driver.get("https://mbasic.facebook.com/login/?next&ref=dbl&fl&refid=8")
    sleep(0.5)
    userNameElement = driver.find_elements(By.CSS_SELECTOR, "#email")
    userNameElement[0].send_keys(username)
    time.sleep(0.5)

    passwordElement = driver.find_elements(By.CSS_SELECTOR, "#pass")
    passwordElement[0].send_keys(password)
    time.sleep(0.5)

    btnSubmit = driver.find_elements(By.CSS_SELECTOR, "#loginbutton")
    print(btnSubmit[0])
    btnSubmit[0].click()
    time.sleep(0.5)

    faCodeElement = driver.find_elements(By.XPATH, "//*[contains(@id, 'r3')]")

    # faCodeElement = driver.find_elements_by_xpath('//*[@id=":r3:"]')
    faCodeElement[0].send_keys(str(getCodeFrom2FA(code)))
    time.sleep(0.5)

    btn2fa = driver.find_elements(By.CSS_SELECTOR, ".x3nfvp2.x1n2onr6.xh8yej3")

    btn2fa[0].click()
    time.sleep(0.5)

    btn2faContinue = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//span[text()='Trust this device']"))
    )

    # 检查是否找到元素
    if btn2faContinue:
        print("yes finde btn2faContinue...")
        btn2faContinue.click()
        print("yes click  btn2faContinue...")
    else:
        print("no finde btn2faContinue...")

    return True
    # end loginW


def save_to_file(filename, link):
    # 先检查文件中是否已经存在该链接
    if os.path.exists(filename):
        with open(filename, "r") as f:
            existing_links = f.readlines()  # 读取现有的所有链接
            existing_links = [line.strip() for line in existing_links]  # 去除换行符
        if link in existing_links:  # 如果链接已存在，则跳过
            print(f"Link already exists, skipping: {link}")
            return
    # 如果链接不在文件中，追加写入
    with open(filename, "a") as f:
        f.write(link + "\n")
        print(f"Link saved: {link}")


def click_with_retry(driver, button, retries=3, delay=1):
    for attempt in range(retries):
        try:
            button.click()
            return True
        except Exception as e:
            print(f"Click attempt {attempt + 1} failed: {e}")
            time.sleep(delay)
    return False


def getPostsGroup(driver, groupId, numberId):
    # 获取当前时间
    now = datetime.datetime.now()
    # 格式化时间，例如：2024-04-27 14:35:20
    formatted_time = now.strftime("%Y-%m-%d-%Hh-%Mmin")

    output_file = "copied_links"+formatted_time+".txt"  # 输出文件名

    save_to_file(output_file, formatted_time)  # 保存链接到文件

    try:
        driver.get(f"https://mbasic.facebook.com/groups/{groupId}")  # 打开群组页面
        wait = WebDriverWait(driver, 10)  # 设置显式等待

        collected_links = 0  # 已收集链接计数
        visited_links = set()  # 已访问链接集合
        visited_buttons = set()  # 已点击的按钮集合
        scroll_pause_time = 2  # 滚动等待时间
        scroll_increment = 800  # 每次滚动的像素值

        while collected_links < numberId:
            try:
                # 等待所有复制链接按钮加载完毕
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
                    break

                # 确保按钮没有被点击过
                if button in visited_buttons:
                    continue

                try:
                    # 确保按钮可点击

                    wait.until(EC.element_to_be_clickable(button))

                    # 使用ActionChains移动到元素
                    actions = ActionChains(driver)
                    actions.move_to_element(button).perform()
                    time.sleep(1)  # 等待滚动完成

                    try:
                        button.click()
                    except Exception as click_exception:
                        print(
                            "Regular click failed, trying JavaScript click:",
                            click_exception,
                        )

                    time.sleep(1)  # 等待剪贴板复制
                    print("click button ok")
                    clipboard_content = pyperclip.paste()  # 获取剪贴板内容

                    # 如果链接未被复制过，保存到文件
                    if clipboard_content and clipboard_content not in visited_links:
                        visited_links.add(clipboard_content)  # 添加到已访问链接集合
                        save_to_file(output_file, clipboard_content)  # 保存链接到文件
                        collected_links += 1  # 增加已收集链接计数
                        print(f"Link {collected_links} saved:", clipboard_content)

                    # 标记该按钮为已点击
                    visited_buttons.add(button)

                except Exception as e:
                    print("Error clicking button:", e)
                    continue

            # 逐步向下滚动页面
            driver.execute_script(f"window.scrollBy(0, {scroll_increment});")
            time.sleep(scroll_pause_time)  # 等待新内容加载
            print(f"Scrolled down by {scroll_increment} pixels.")
            current_scroll = driver.execute_script(
                "return window.pageYOffset + window.innerHeight;"
            )
            print(f"Current scroll position: {current_scroll}")

        print("Scrolling done.")

    except Exception as e:
        print("An error occurred:", e)  # 打印错误信息

    finally:
        print(f"Links saved to {output_file}")  # 打印保存文件信息


driver = initDriverProfile()
isLogin = checkLiveClone(driver)  # Check live
print(isLogin)
userName = "61552065756708"
passWord = "A@!ToiLaToi12"
twoFa = "Z64KOQI4FD3OETGO4VNWZFFWFJ4PUSAJ"

loginBy2FA(driver, userName, passWord, twoFa)

# value = input('Enter 1 to crawl id post of group, enter 2 to crawl content: ')
# if (int(value) == 1):

time.sleep(5)
getPostsGroup(driver, "gomabb", 1000)
# else:
#     postIds = readData(fileIds)
#     crawlPostData(driver, postIds, 'group')
