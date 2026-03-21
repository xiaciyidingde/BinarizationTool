"""
BinarizationTool - 应用程序入口

二值化图片编辑器主程序。
"""

import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon, QPixmap
from src.views.main_window import MainWindow
from src.__version__ import __version__, __app_name__
from src.utils.theme_manager import ThemeManager
from src.utils.resources import APP_ICON_BYTES


def main():
    """主函数"""
    # 创建应用程序
    app = QApplication(sys.argv)
    
    # 设置应用程序信息
    app.setApplicationName(__app_name__)
    app.setOrganizationName("ImageEditor")
    app.setApplicationVersion(__version__)
    
    # 设置应用程序图标
    pixmap = QPixmap()
    pixmap.loadFromData(APP_ICON_BYTES)
    icon = QIcon(pixmap)
    app.setWindowIcon(icon)
    
    # Windows 特定：设置任务栏图标
    if sys.platform == 'win32':
        import ctypes
        # 设置应用程序 ID，使任务栏图标正确显示
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(__app_name__)
    
    # 应用主题
    theme_manager = ThemeManager()
    theme_manager.apply_theme(app, "light")
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    # 检查命令行参数（如果提供了图片路径）
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        # 检查文件是否存在且是支持的图片格式
        if os.path.exists(image_path):
            ext = os.path.splitext(image_path)[1].lower()
            if ext in ['.png', '.jpg', '.jpeg', '.bmp']:
                # 使用 QTimer 延迟加载，确保窗口已完全显示
                QTimer.singleShot(100, lambda: window._load_file_from_path(image_path))
            else:
                print(f"不支持的文件格式: {ext}")
                print("支持的格式: .png, .jpg, .jpeg, .bmp")
        else:
            print(f"文件不存在: {image_path}")
    
    # 运行应用程序
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
