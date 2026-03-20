"""
BinarizationTool - 应用程序入口

二值化图片编辑器主程序。
"""

import sys
from PySide6.QtWidgets import QApplication
from src.views.main_window import MainWindow
from src.__version__ import __version__, __app_name__


def main():
    """主函数"""
    # 创建应用程序
    app = QApplication(sys.argv)
    
    # 设置应用程序信息
    app.setApplicationName(__app_name__)
    app.setOrganizationName("ImageEditor")
    app.setApplicationVersion(__version__)
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
