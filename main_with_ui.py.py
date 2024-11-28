import sys
import keyboard
import threading
from queue import Queue, Empty
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit
import time
import random  # 导入随机模块

# 定义 current_keys 变量
current_keys = set()
lock = threading.Lock()
key_queue = Queue()
stop_event = threading.Event()

# 默认延迟（毫秒）
min_delay_ms = 0
max_delay_ms = 0

def press_key(key):
    """按下并释放指定的键"""
    keyboard.press_and_release(key)

def process_keys():
    """处理按键队列中的按键操作，应用延迟"""
    while not stop_event.is_set():
        try:
            key = key_queue.get(timeout=0.1)  # 取出一个键
            press_key(key)  # 处理按键
            key_queue.task_done()  # 标记该任务完成
        except Empty:
            continue
        except Exception as e:
            print(f"Error processing keys: {e}")

def on_key_event(event):
    """处理键盘事件，跟踪按下和释放的键"""
    global current_keys

    if event.event_type == keyboard.KEY_DOWN and event.name in ['w', 'a', 's', 'd']:
        with lock:
            current_keys.add(event.name)

    elif event.event_type == keyboard.KEY_UP and event.name in ['w', 'a', 's', 'd']:
        with lock:
            current_keys.discard(event.name)  # 使用 discard 以避免 KeyError
            reverse_keys = {
                'w': 's',
                's': 'w',
                'a': 'd',
                'd': 'a'
            }

            # 处理反向按键
            if event.name in reverse_keys:
                delay = random.uniform(min_delay_ms / 1000.0, max_delay_ms / 1000.0)  # 获取随机延迟
                threading.Timer(delay, lambda: key_queue.put(reverse_keys[event.name])).start()

            # 处理同时松开的多个方向键
            if len(current_keys) == 0:  # 检查是否所有键都松开
                threading.Timer(random.uniform(min_delay_ms / 1000.0, max_delay_ms / 1000.0), add_reverse_keys).start()

def add_reverse_keys():
    """在延迟后添加所有反向键并输出"""
    with lock:
        if 'w' in current_keys:
            key_queue.put('s')
        if 's' in current_keys:
            key_queue.put('w')
        if 'a' in current_keys:
            key_queue.put('d')
        if 'd' in current_keys:
            key_queue.put('a')

class MyApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.process_thread = None

    def initUI(self):
        layout = QVBoxLayout()

        self.label = QLabel("点击 '启动' 开始自动急停，点击 '停止' 结束自动急停，点击 '关闭程序' 退出。")
        layout.addWidget(self.label)

        self.min_delay_input = QLineEdit(self)
        self.min_delay_input.setPlaceholderText("输入最小延迟 (毫秒)")
        layout.addWidget(self.min_delay_input)

        self.max_delay_input = QLineEdit(self)
        self.max_delay_input.setPlaceholderText("输入最大延迟 (毫秒)")
        layout.addWidget(self.max_delay_input)

        self.update_delay_button = QPushButton("更新延迟")
        self.update_delay_button.clicked.connect(self.update_delay)
        layout.addWidget(self.update_delay_button)

        self.start_button = QPushButton("启动")
        self.start_button.clicked.connect(self.start_processing)
        layout.addWidget(self.start_button)

        self.stop_button = QPushButton("停止")
        self.stop_button.clicked.connect(self.stop_processing)
        layout.addWidget(self.stop_button)

        self.close_button = QPushButton("关闭程序")
        self.close_button.clicked.connect(self.close_program)
        layout.addWidget(self.close_button)

        self.setLayout(layout)
        self.setWindowTitle('自动急停1.0')
        self.show()

    def update_delay(self):
        """更新延迟值"""
        global min_delay_ms, max_delay_ms
        try:
            min_delay_ms = int(self.min_delay_input.text())
            max_delay_ms = int(self.max_delay_input.text())
            if min_delay_ms < 0 or max_delay_ms < 0 or min_delay_ms > max_delay_ms:
                raise ValueError("请输入有效的延迟范围！")
            print(f"延迟范围已更新为: {min_delay_ms} 到 {max_delay_ms} 毫秒")
        except ValueError as e:
            print(f"请输入有效的整数！{e}")

    def start_processing(self):
        """启动处理线程"""
        if not self.process_thread or not self.process_thread.is_alive():
            global stop_event
            stop_event.clear()  # 清除停止事件
            self.process_thread = threading.Thread(target=process_keys, daemon=True)
            self.process_thread.start()
            keyboard.hook(on_key_event)

    def stop_processing(self):
        """停止处理线程"""
        global stop_event
        stop_event.set()  # 设置停止事件
        key_queue.join()  # 等待队列清空
        keyboard.unhook(on_key_event)  # 解除钩子

    def close_program(self):
        """关闭程序"""
        self.stop_processing()  # 首先停止处理
        QApplication.quit()  # 退出应用

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyApp()
    sys.exit(app.exec_())
