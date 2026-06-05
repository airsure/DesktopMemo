"""桌面备忘录 v2 入口."""
import sys
import os

# 确保工作目录正确
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from app import App


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 关闭窗口不退出应用
    _ = App()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
