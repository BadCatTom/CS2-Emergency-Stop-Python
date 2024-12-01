import sys
import keyboard
import threading
from queue import Queue, Empty
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit
from PyQt5.QtCore import QTimer, pyqtSignal, QObject
import time
import random

class Communicate(QObject):
    update_status_signal = pyqtSignal(str)
    update_timer_signal = pyqtSignal(str)

class KeyProcessor:
    """处理键盘事件和键的状态"""

    def __init__(self, press_threshold: float, emergency_press_time_range: tuple, long_press_time_range: tuple, get_time_func):
        self.current_keys = set()  # 当前按下的所有键
        self.lock = threading.Lock()
        self.key_queue = Queue()
        self.stop_event = threading.Event()
        self.get_time = get_time_func  # 获取当前时间的函数
        self.first_press_time = {}  # 记录每个键的第一次按下时间
        self.special_keys = {'w', 'a', 's', 'd'}  # 特定键集合

        # 反向键映射
        self.reverse_keys = {
            'w': 's',
            's': 'w',
            'a': 'd',
            'd': 'a',
            'a+w': 'd+s',
            's+a': 'w+d',
            's+d': 'w+a',
            'w+d': 'a+s',
            'a+s': 'd+w',
            'd+s': 'a+w',
            'd+w': 's+a',
        }

        self.press_threshold = press_threshold  # 自定义按下时间阈值（秒）
        self.emergency_press_time_range = emergency_press_time_range  # 急停按下时间范围（毫秒）
        self.long_press_time_range = long_press_time_range  # 长急停按下时间范围（毫秒）

    def press_key(self, key: str, duration: float):
        """按下并释放指定的键，持续指定的时间（毫秒）"""
        try:
            keyboard.press(key)
            time.sleep(duration / 1000.0)  # 将毫秒转换为秒
            keyboard.release(key)
        except Exception as e:
            print(f"按键处理时发生错误: {e}")

    def process_keys(self):
        """处理按键队列中的按键操作"""
        while not self.stop_event.is_set():
            try:
                key = self.key_queue.get(timeout=0.1)  # 使用超时防止持续阻塞
                duration = random.uniform(*self.long_press_time_range)  # 随机选择长急停时间
                self.press_key(key, duration)
                self.key_queue.task_done()
            except Empty:
                continue

    def on_key_event(self, event):
        """处理键盘事件，跟踪按下和释放的键"""
        if event.event_type == keyboard.KEY_DOWN:
            self.add_key(event.name)
        elif event.event_type == keyboard.KEY_UP:
            self.release_key(event.name)

    def add_key(self, key: str):
        """处理按键按下事件"""
        with self.lock:
            self.current_keys.add(key)  # 添加当前按下的键

            # 记录第一次按下的时间
            if key not in self.first_press_time:
                self.first_press_time[key] = self.get_time()  # 获取按下时的计时器时间

    def release_key(self, key: str):
        """处理按键松开事件"""
        with self.lock:
            if key in self.current_keys:  # 只处理当前按下的键
                self.current_keys.discard(key)  # 从当前按键集合中移除
                release_time = self.get_time()  # 获取释放时的计时器时间

                if key in self.first_press_time:
                    pressed_duration = release_time - self.first_press_time[key]  # 计算按键持续时间
                    del self.first_press_time[key]  # 清除记录的第一次按下时间

                    # 检查是否特定键（W, A, S, D）都已释放
                    if all(k not in self.current_keys for k in self.special_keys):
                        self.handle_key_duration(key, pressed_duration)  # 处理最后松开的键
                    else:
                        print("仍有特定按键按下，急停未触发。")

    def handle_key_duration(self, key: str, pressed_duration: float):
        """处理按键的持续时间"""
        print(f"{key} 按下持续时间: {pressed_duration:.3f} 秒")

        if pressed_duration < self.press_threshold:  # 如果按下时间小于自定义阈值，执行急停
            self.trigger_emergency_stop(key)
            print("执行短急停操作")
        else:  # 如果大于或等于自定义阈值，执行长急停
            self.trigger_changting_stop(key)
            print("执行长急停操作")

    def trigger_emergency_stop(self, key: str):
        """执行短急停操作，根据反向键逻辑决定按下的键"""
        if key in self.reverse_keys:  # 只按下反向键
            reverse_key = self.reverse_keys[key]  # 获取反向键
            press_duration = random.uniform(*self.emergency_press_time_range)  # 随机选择急停按下时间
            self.press_key(reverse_key, press_duration)  # 按下反向键
            print("成功执行操作")
            print(f"按下反向键: {reverse_key}, 按下时间: {press_duration:.2f} 毫秒")

    def trigger_changting_stop(self, key: str):
        """执行长急停操作，根据反向键逻辑决定按下的键"""
        if key in self.reverse_keys:  # 只按下反向键
            reverse_key = self.reverse_keys[key]  # 获取反向键
            press_duration = random.uniform(*self.long_press_time_range)  # 随机选择长急停按下时间
            self.press_key(reverse_key, press_duration)  # 按下反向键
            print("成功执行操作")
            print(f"按下反向键: {reverse_key}, 按下时间: {press_duration:.2f} 毫秒")


class MyApp(QWidget):
    """主应用程序类，用于创建界面和管理应用程序逻辑"""

    def __init__(self):
        super().__init__()
        self.process_thread = None
        self.initUI()  # 初始化用户界面
        self.start_status_timer()  # 启动状态定时器
        self.key_processor = None  # 初始化时没有创建 KeyProcessor 实例
        self.start_time = 0  # 用于计算运行时间
        self.timer = QTimer()  # 创建一个计时器
        self.c = Communicate()  # 实例化信号传递类

        # 连接信号与槽
        self.c.update_status_signal.connect(self.update_status_ui)
        self.c.update_timer_signal.connect(self.update_timer_ui)

        # 连接计时器的超时事件
        self.timer.timeout.connect(self.update_timer)

    def initUI(self):
        """初始化用户界面"""
        layout = QVBoxLayout()

        self.label = QLabel("点击 '启动' 开始自动急停，点击 '停止' 结束自动急停，点击 '关闭程序' 退出。")
        layout.addWidget(self.label)

        self.status_label = QLabel("状态: 未开启")
        layout.addWidget(self.status_label)

        self.timer_label = QLabel("计时器: 0.000 秒")
        layout.addWidget(self.timer_label)

        # 输入框设置
        self.min_delay_input = QLineEdit(self)
        self.min_delay_input.setPlaceholderText("输入最小急停延迟 (毫秒)")
        layout.addWidget(self.min_delay_input)

        self.max_delay_input = QLineEdit(self)
        self.max_delay_input.setPlaceholderText("输入最大急停延迟 (毫秒)")
        layout.addWidget(self.max_delay_input)

        # 长急停的输入框
        self.min_long_press_time_input = QLineEdit(self)
        self.min_long_press_time_input.setPlaceholderText("输入长急停最小按下时间 (毫秒)")
        layout.addWidget(self.min_long_press_time_input)

        self.max_long_press_time_input = QLineEdit(self)
        self.max_long_press_time_input.setPlaceholderText("输入长急停最大按下时间 (毫秒)")
        layout.addWidget(self.max_long_press_time_input)

        self.press_threshold_input = QLineEdit(self)
        self.press_threshold_input.setPlaceholderText("输入急停阈值时间 (毫秒)")
        layout.addWidget(self.press_threshold_input)

        self.emergency_press_time_min_input = QLineEdit(self)
        self.emergency_press_time_min_input.setPlaceholderText("输入短急停最小按下时间 (毫秒)")
        layout.addWidget(self.emergency_press_time_min_input)

        self.emergency_press_time_max_input = QLineEdit(self)
        self.emergency_press_time_max_input.setPlaceholderText("输入短急停最大按下时间 (毫秒)")
        layout.addWidget(self.emergency_press_time_max_input)

        # 按钮设置
        self.update_delay_button = QPushButton("更新设置")
        self.update_delay_button.clicked.connect(self.update_settings)
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
        self.setWindowTitle('自动急停2.0')
        self.show()

    def update_timer_ui(self, elapsed_time):
        """更新计时器显示"""
        self.timer_label.setText(elapsed_time)

    def update_status_ui(self, status):
        """更新状态显示"""
        self.status_label.setText(status)

    def update_timer(self):
        """更新计时器显示"""
        elapsed_time = time.perf_counter() - self.start_time
        self.c.update_timer_signal.emit(f"计时器: {elapsed_time:.3f} 秒")  # 显示到毫秒级别

    def start_status_timer(self):
        """启动状态更新定时器"""
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)  # 每秒更新一次状态

    def update_status(self):
        """更新状态显示"""
        if self.process_thread and self.process_thread.is_alive():
            self.c.update_status_signal.emit("状态: 运行中")
            if not self.timer.isActive():
                self.start_time = time.perf_counter()  # 记录程序启动时间
                self.timer.start(1)  # 启动计时器更新，每1毫秒更新一次
        else:
            self.c.update_status_signal.emit("状态: 停止")
            self.timer.stop()  # 停止计时器

    def update_settings(self):
        """更新按下时间和急停阈值设置"""
        try:
            min_delay_ms = int(self.min_delay_input.text())
            max_delay_ms = int(self.max_delay_input.text())

            # 使用新的变量名来存储长急停时间
            min_long_press_time_ms = int(self.min_long_press_time_input.text())
            max_long_press_time_ms = int(self.max_long_press_time_input.text())

            press_threshold = int(self.press_threshold_input.text()) / 1000  # 转换为秒
            emergency_min = int(self.emergency_press_time_min_input.text())
            emergency_max = int(self.emergency_press_time_max_input.text())

            if not (0 <= min_delay_ms <= max_delay_ms):
                raise ValueError("最小延迟必须小于等于最大延迟！")
            if not (0 <= min_long_press_time_ms <= max_long_press_time_ms):
                raise ValueError("长急停最小按下时间必须小于等于最大按下时间！")
            if emergency_min > emergency_max:
                raise ValueError("急停最小按下时间必须小于等于最大按下时间！")

            # 更新 KeyProcessor
            self.key_processor = KeyProcessor(press_threshold, (emergency_min, emergency_max),
                                               (min_long_press_time_ms, max_long_press_time_ms), self.get_timer_time)
            print(f"设置已更新：阈值 - {press_threshold}秒，急停按下时间范围 - {emergency_min} 到 {emergency_max} 毫秒，长急停按下时间范围 - {min_long_press_time_ms} 到 {max_long_press_time_ms} 毫秒")

        except ValueError as e:
            print(f"请输入有效的整数！{e}")
            self.update_settings_error_ui(str(e))

    def update_settings_error_ui(self, message):
        """更新设置错误状态显示"""
        self.status_label.setText(f"错误: {message}")

    def get_timer_time(self):
        """返回当前计时器的时间"""
        return time.perf_counter() - self.start_time  # 返回从程序开始到现在的时间

    def start_processing(self):
        """启动处理线程"""
        if self.process_thread is None or not self.process_thread.is_alive():
            self.key_processor.stop_event.clear()  # 清除停止事件
            self.process_thread = threading.Thread(target=self.key_processor.process_keys, daemon=True)
            self.process_thread.start()
            keyboard.hook(self.key_processor.on_key_event)

    def stop_processing(self):
        """停止处理线程"""
        if self.process_thread and self.process_thread.is_alive():
            self.key_processor.stop_event.set()
            keyboard.unhook(self.key_processor.on_key_event)

    def close_program(self):
        """关闭程序"""
        self.stop_processing()
        QApplication.quit()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyApp()
    sys.exit(app.exec_())
