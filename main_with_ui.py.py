import sys
import keyboard
import threading
from queue import Queue, Empty
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit
import time
import random

# 定义当前按键集合
current_keys = set()
lock = threading.Lock()
key_queue = Queue()
stop_event = threading.Event()

# 默认延迟（毫秒）
min_delay_ms = 0
max_delay_ms = 0
min_press_time_ms = 0  # 按下反向按键的最小时间
max_press_time_ms = 0  # 按下反向按键的最大时间
stop_key_combination = False  # 是否检测到组合键冲突的标志

# 记录按键按下与松开的时间
press_times = {}
release_times = {}

def press_key(key):
    """按下并释放指定的键"""
    try:
        keyboard.press(key)  # 按下
        time.sleep(random.uniform(min_press_time_ms / 1000.0, max_press_time_ms / 1000.0))  # 随机保持时间
        keyboard.release(key)  # 释放
    except Exception as e:
        print(f"按键处理时发生错误: {e}")

def process_keys():
    """处理按键队列中的按键操作"""
    while not stop_event.is_set():
        try:
            key = key_queue.get_nowait()  # 非阻塞获取
            press_key(key)  # 处理按键
            key_queue.task_done()  # 标记该任务完成
        except Empty:
            pass  # 如果队列为空，继续循环
        except Exception as e:
            print(f"处理按键时发生错误: {e}")

        time.sleep(0.001)  # 休眠1毫秒，以降低CPU占用

def on_key_event(event):
    """处理键盘事件，跟踪按下和释放的键"""
    global current_keys, press_times, release_times, stop_key_combination

    current_time = time.time() * 1000  # 当前时间（毫秒）

    if event.event_type == keyboard.KEY_DOWN and event.name in ['w', 'a', 's', 'd']:
        with lock:
            current_keys.add(event.name)
            press_times[event.name] = current_time  # 记录按下时间

            # 检测组合键情况
            if ('a' in current_keys and event.name in ['d', 's', 'w']) or \
               ('d' in current_keys and event.name in ['a', 's', 'w']) or \
               ('s' in current_keys and event.name in ['a', 'd', 'w']) or \
               ('w' in current_keys and event.name in ['a', 's', 'd']):
                stop_key_combination = True  # 强制不进行急停和反键操作
                print(f"组合键冲突，强制不进行急停和反向按键操作")

    elif event.event_type == keyboard.KEY_UP and event.name in ['w', 'a', 's', 'd']:
        with lock:
            current_keys.discard(event.name)
            release_times[event.name] = current_time  # 记录松开时间

            # 记录松开时间
            if event.name in press_times:
                pressed_duration = (current_time - press_times[event.name]) / 1000  # 转换为秒
                print(f"{event.name} 按下持续时间: {pressed_duration:.3f} 秒")

            if stop_key_combination:
                # 如果有组合键的按下，直接返回
                stop_key_combination = False  # 重置标志
                return

            # 在检查急停逻辑之前，确保执行急停逻辑
            if should_stop():
                print("执行急停操作")

            # 清除按下时间记录
            press_times.pop(event.name, None)

            reverse_keys = {
                'w': 's',
                's': 'w',
                'a': 'd',
                'd': 'a'
            }

            # 将反向按键放入队列
            if event.name in reverse_keys:
                key_queue.put(reverse_keys[event.name])

def should_stop():
    """判断是否需要执行急停"""
    global current_keys, stop_key_combination

    # 如果当前按下的键为空，则可以执行急停
    if not current_keys and not stop_key_combination:
        return True  # 执行急停

    # 如果有任何方向键（‘w’、‘a’、‘s’、‘d’）被按下，则不需要急停
    return False  # 不执行急停

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

        self.min_press_time_input = QLineEdit(self)
        self.min_press_time_input.setPlaceholderText("输入最小按下时间 (毫秒)")
        layout.addWidget(self.min_press_time_input)

        self.max_press_time_input = QLineEdit(self)
        self.max_press_time_input.setPlaceholderText("输入最大按下时间 (毫秒)")
        layout.addWidget(self.max_press_time_input)

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
        global min_delay_ms, max_delay_ms, min_press_time_ms, max_press_time_ms
        try:
            min_delay_ms = int(self.min_delay_input.text())
            max_delay_ms = int(self.max_delay_input.text())
            min_press_time_ms = int(self.min_press_time_input.text())
            max_press_time_ms = int(self.max_press_time_input.text())

            if (min_delay_ms < 0 or max_delay_ms < 0 or
                min_press_time_ms < 0 or max_press_time_ms < 0 or
                min_delay_ms > max_delay_ms or
                min_press_time_ms > max_press_time_ms):
                raise ValueError("请输入有效的延迟范围！")

            print(f"延迟范围已更新为: {min_delay_ms} 到 {max_delay_ms} 毫秒，按下时间范围已更新为: {min_press_time_ms} 到 {max_press_time_ms} 毫秒")
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
        keyboard.unhook(on_key_event)  # 解除钩子
        try:
            key_queue.join()  # 等待队列清空
        except Exception as e:
            print(f"停止过程中发生错误: {e}")

    def close_program(self):
        """关闭程序"""
        self.stop_processing()  # 首先停止处理
        QApplication.quit()  # 退出应用

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyApp()
    sys.exit(app.exec_())
