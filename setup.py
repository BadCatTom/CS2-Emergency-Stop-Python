from setuptools import setup

setup(
    name='my_project',                  # 包的名称
    version='0.1',                     # 版本号
    description='A keyboard control application for emergency stop',  # 描述
    author='Your Name',                 # 作者
    author_email='your.email@example.com',  # 作者邮箱
    py_modules=['mina'],                # 你的主模块名，按需修改
    install_requires=['pynput'],        # 依赖包
    classifiers=[
        'Programming Language :: Python :: 3',  # 语言
        'License :: OSI Approved :: MIT License', # 许可证
        'Operating System :: OS Independent',    # 操作系统
    ],
    python_requires='>=3.6',           # Python 版本要求
)
