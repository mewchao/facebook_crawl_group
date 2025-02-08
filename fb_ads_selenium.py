import sys
import random
import time
import threading
import requests
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton, QCheckBox, QGroupBox, QGridLayout, QTextEdit
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from time import sleep
from PyQt5.QtWidgets import QScrollArea


class CommentPosterApp(QWidget):
    def __init__(self):
        super().__init__()  
        self.init_ui()

    def init_ui(self):
        """设置UI"""
        self.setWindowTitle("facebook引流评论工具")
        self.setGeometry(100, 100, 1200, 800)  # 设置适中的窗口大小

        # 设置图标为Facebook官方图标
        self.setWindowIcon(QIcon("facebook_icon.ico"))

        # 设置字体
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)

        # 创建主要水平布局来分隔左右两部分
        main_horizontal_layout = QHBoxLayout()
        
        # 左侧部分主布局
        left_main_layout = QVBoxLayout()

        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(500)  # 设置滚动区域的最小高度
        
        # 创建滚动区域的内容容器
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # 创建输入框和复选框的网格布局
        grid_layout = QGridLayout()
        grid_layout.setSpacing(6)

        self.inputs = []
        self.checkboxes = []

        # 为每个浏览器创建输入框
        for i in range(20):
            current_row = i * 3  # 每个浏览器占用3行
            
            # 第一行：复选框和ADS_ID
            checkbox = QCheckBox(f"浏览器 {i + 1}", self)
            grid_layout.addWidget(checkbox, current_row, 0)
            
            input_ads = QLineEdit(self)
            input_ads.setDisabled(True)
            input_ads.setMaximumWidth(80)
            grid_layout.addWidget(QLabel("ADS:"), current_row, 1)
            grid_layout.addWidget(input_ads, current_row, 2)
            
            # 创建10个GROUP_ID输入框，分两行显示
            inputs_group = []
            for j in range(10):
                input_group = QLineEdit(self)
                input_group.setDisabled(True)
                input_group.setMaximumWidth(80)
                inputs_group.append(input_group)
                
                if j < 5:  # 前5个放在第二行
                    grid_layout.addWidget(QLabel(f"G{j+1}:"), current_row + 1, j * 2 + 1)
                    grid_layout.addWidget(input_group, current_row + 1, j * 2 + 2)
                else:  # 后5个放在第三行
                    grid_layout.addWidget(QLabel(f"G{j+1}:"), current_row + 2, (j-5) * 2 + 1)
                    grid_layout.addWidget(input_group, current_row + 2, (j-5) * 2 + 2)

            self.inputs.append((input_ads, inputs_group))
            self.checkboxes.append(checkbox)
            checkbox.toggled.connect(self.toggle_input_fields)

            # 添加分隔空行
            if i < 19:
                grid_layout.setRowMinimumHeight(current_row + 3, 10)

        # 将网格布局添加到滚动区域的布局中
        scroll_layout.addLayout(grid_layout)
        scroll_layout.addStretch()  # 添加弹性空间
        
        # 设置滚动区域的内容
        scroll_content.setLayout(scroll_layout)
        scroll.setWidget(scroll_content)
        
        # 将滚动区域添加到左侧主布局
        left_main_layout.addWidget(scroll)

        # 创建自定义评论区域
        comment_group = QGroupBox("自定义评论")
        comment_group.setFont(font)
        comment_layout = QVBoxLayout()

        self.custom_comments = []
        for i in range(5):
            comment_input = QLineEdit(self)
            comment_input.setPlaceholderText(f"评论 {i + 1}")
            comment_layout.addWidget(comment_input)
            self.custom_comments.append(comment_input)

        comment_group.setLayout(comment_layout)
        left_main_layout.addWidget(comment_group)

        # 添加使用默认评论的复选框
        self.default_comment_checkbox = QCheckBox("使用默认评论?", self)
        self.default_comment_checkbox.setFont(font)
        left_main_layout.addWidget(self.default_comment_checkbox)

        # 创建"开始评论"按钮
        submit_btn = QPushButton("开始评论", self)
        submit_btn.setFont(font)
        submit_btn.setMinimumHeight(40)
        submit_btn.clicked.connect(self.submit)
        left_main_layout.addWidget(submit_btn)

        # 右侧部分布局
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignTop)

        # 创建批量导入群组ID的区域
        import_group = QGroupBox("批量导入")
        import_group.setFont(font)
        import_layout = QVBoxLayout()

        # 批量输入框
        self.batch_input = QTextEdit(self)
        self.batch_input.setPlaceholderText("将群组ID按行输入...")
        self.batch_input.setFont(font)
        self.batch_input.setMinimumWidth(250)
        self.batch_input.setMinimumHeight(500)  # 调整高度以匹配左侧滚动区域
        import_layout.addWidget(self.batch_input)

        # 创建"一键导入"按钮
        one_click_button = QPushButton("一键导入", self)
        one_click_button.setFont(font)
        one_click_button.setMinimumHeight(40)
        one_click_button.clicked.connect(self.auto_import_groups)
        import_layout.addWidget(one_click_button)

        import_group.setLayout(import_layout)
        right_layout.addWidget(import_group)

        # 将左右布局添加到主水平布局
        main_horizontal_layout.addLayout(left_main_layout, 75)
        main_horizontal_layout.addLayout(right_layout, 25)

        # 设置窗口的整体布局
        self.setLayout(main_horizontal_layout)

        # 初始化其他变量
        self.user_groups_commented = {}
        self.batch_groups = []

    def toggle_input_fields(self):
        """根据复选框状态启用或禁用输入框"""
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

        # 确保在切换复选框状态后，UI进行更新
        QApplication.processEvents()

    def auto_import_groups(self):
        """一键导入群组ID到各浏览器输入框"""
        # 获取批量输入框中的内容并清理
        self.batch_groups = self.batch_input.toPlainText().strip().split("\n")
        self.batch_groups = [group.strip() for group in self.batch_groups if group.strip()]

        if not self.batch_groups:
            print("没有输入群组ID")
            return

        # 记录当前要导入的群组索引
        current_group_index = 0
        
        # 遍历所有已启用的浏览器
        for i, checkbox in enumerate(self.checkboxes):
            if not checkbox.isChecked():
                continue
                
            # 获取当前浏览器的输入框组
            _, inputs_group = self.inputs[i]
            
            # 为当前浏览器的每个群组输入框填充数据
            for input_group in inputs_group:
                if current_group_index < len(self.batch_groups):
                    # 设置群组ID
                    input_group.setText(self.batch_groups[current_group_index])
                    # 移动到下一个群组ID
                    current_group_index += 1
                else:
                    # 如果没有更多群组ID可用，清空剩余输入框
                    input_group.setText("")
                
                # 强制每个输入框更新后立即刷新UI
                input_group.repaint()
                QApplication.processEvents()
                
            # 在每个浏览器处理完后添加小延迟，确保UI更新
            time.sleep(0.1)
        
        # 最后再次强制更新整个UI
        self.repaint()
        QApplication.processEvents()

    def submit(self):
        """处理“开始评论”按钮点击事件"""
        data = {}
        
        # 获取输入框中的群组ID
        for i, (input_ads, inputs_group) in enumerate(self.inputs):
            groups = []
            ads_id = input_ads.text().strip()
            if ads_id:  # 确保提供了ADS_ID
                for input_group in inputs_group:
                    group_id = input_group.text().strip()
                    if group_id:
                        groups.append(group_id)
                if groups:
                    data[f"浏览器 {i + 1}"] = (ads_id, groups)

        # 获取评论内容：选择默认评论或自定义评论
        if self.default_comment_checkbox.isChecked():
            comments = [
                "什么是大小和价格$$?",
                "+1",
                "你好，我想购买！",
                "什么是尺寸？？",
                "嗨，我想买"
            ]
        else:
            comments = [comment.text().strip() for comment in self.custom_comments if comment.text().strip()]

        if data:
            # 对每个浏览器调用自动化功能
            for browser, (ads_id, groups) in data.items():
                print(f"正在为 {browser} 执行自动化，ADS_ID: {ads_id}，群组：{groups}")
                threading.Thread(target=self.run_automation, args=(ads_id, groups, comments)).start()

    def run_automation(self, ads_id, groups, comments):
        """执行给定浏览器和群组的自动化任务"""
        COMMENT_TARGET = 30 + random.randint(0, 20)  # 每个群组每个浏览器30-50条评论
        COMMENT_DELAY = 5  # 每条评论之后的延迟

        def random_sleep(min_seconds=1, max_seconds=3):
            sleep(random.uniform(min_seconds, max_seconds))

        def human_typing_simulation(element, text, visited_comments):
            """模拟慢速打字以模仿人类行为"""
            if text not in visited_comments:
                element.clear()  # 清除输入框中的任何现有文本
                for char in text:
                    element.send_keys(char)
                    random_sleep(0.3, 0.7)  # 模拟慢速打字
                visited_comments.add(text)

        # 省略浏览器启动、评论发布等逻辑，保留原代码部分


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CommentPosterApp()
    window.show()
    sys.exit(app.exec_())
