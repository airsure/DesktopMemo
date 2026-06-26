"""桌面备忘录 v2 入口."""
import sys
import os

# 确保工作目录正确
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QMessageBox
from app import App

CONFIG_PATH = r"\\192.168.2.9\技术中心\技术部\参数化&智能化\2.智能化\config.ini"
MUTEX_NAME = "DesktopMemo_SingleInstance"


def check_single_instance() -> bool:
    """检查是否已有实例在运行（Windows 命名互斥体）."""
    import ctypes
    kernel32 = ctypes.windll.kernel32
    ERROR_ALREADY_EXISTS = 183
    handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        return False
    return True


def check_config() -> bool:
    """检查配置库是否可访问."""
    if os.path.exists(CONFIG_PATH):
        return True
    return False


def main():
    # 单实例检查（先于 QApplication，避免不必要的资源初始化）
    if not check_single_instance():
        app = QApplication(sys.argv)
        QMessageBox.warning(
            None, "提示", "程序已在运行",
            QMessageBox.Ok
        )
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    if not check_config():
        QMessageBox.critical(
            None, "连接失败", "无法连接配置库",
            QMessageBox.Ok
        )
        sys.exit(1)

    _ = App()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
