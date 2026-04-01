"""
窗口工具函数

提供窗口相关的通用功能。
"""

import ctypes
import sys


def apply_dark_titlebar(widget):
    """
    为窗口应用深色标题栏（Windows 11）
    
    Args:
        widget: QWidget 或其子类实例（QDialog, QMainWindow 等）
    """
    if sys.platform != 'win32':
        return
    
    try:
        # 获取配置管理器
        from .config_manager import ConfigManager
        config_manager = ConfigManager()
        theme = config_manager.get('interface', 'theme', 'light')
        
        # 如果是跟随系统，检测系统主题
        if theme == 'system':
            from .theme_manager import ThemeManager
            theme_manager = ThemeManager()
            theme = theme_manager._detect_system_theme()
        
        # 确保窗口已经创建窗口句柄
        if not widget.isVisible():
            widget.show()
            widget.hide()
        
        hwnd = int(widget.winId())
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        
        # 根据主题设置标题栏颜色：1 = 深色, 0 = 浅色
        value = ctypes.c_int(1 if theme == 'dark' else 0)
        
        try:
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(value),
                ctypes.sizeof(value)
            )
        except Exception as e:
            print(f"设置深色标题栏失败: {e}")
    
    except Exception as e:
        print(f"应用深色标题栏失败: {e}")


def apply_dark_titlebar_after_show(widget):
    """
    在窗口显示后应用深色标题栏（用于 QMessageBox 等系统对话框）
    
    这个函数会在事件循环中延迟应用标题栏样式，确保窗口句柄已创建。
    
    Args:
        widget: QWidget 或其子类实例
    """
    if sys.platform != 'win32':
        return
    
    try:
        from PySide6.QtCore import QTimer
        
        def apply():
            try:
                # 获取配置管理器
                from .config_manager import ConfigManager
                config_manager = ConfigManager()
                theme = config_manager.get('interface', 'theme', 'light')
                
                # 如果是跟随系统，检测系统主题
                if theme == 'system':
                    from .theme_manager import ThemeManager
                    theme_manager = ThemeManager()
                    theme = theme_manager._detect_system_theme()
                
                hwnd = int(widget.winId())
                DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                
                # 根据主题设置标题栏颜色：1 = 深色, 0 = 浅色
                value = ctypes.c_int(1 if theme == 'dark' else 0)
                
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_USE_IMMERSIVE_DARK_MODE,
                    ctypes.byref(value),
                    ctypes.sizeof(value)
                )
            except Exception:
                pass
        
        # 延迟 10ms 执行，确保窗口已完全创建
        QTimer.singleShot(10, apply)
    
    except Exception:
        pass



# QMessageBox 包装函数，自动应用深色标题栏
def message_box_warning(parent, title, text):
    """显示警告消息框（自动应用深色标题栏）"""
    from PySide6.QtWidgets import QMessageBox
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Warning)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    msg_box.setStandardButtons(QMessageBox.Ok)
    apply_dark_titlebar_after_show(msg_box)
    return msg_box.exec()


def message_box_critical(parent, title, text):
    """显示错误消息框（自动应用深色标题栏）"""
    from PySide6.QtWidgets import QMessageBox
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    msg_box.setStandardButtons(QMessageBox.Ok)
    apply_dark_titlebar_after_show(msg_box)
    return msg_box.exec()


def message_box_information(parent, title, text):
    """显示信息消息框（自动应用深色标题栏）"""
    from PySide6.QtWidgets import QMessageBox
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Information)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    msg_box.setStandardButtons(QMessageBox.Ok)
    apply_dark_titlebar_after_show(msg_box)
    return msg_box.exec()


def message_box_question(parent, title, text, buttons=None, default_button=None):
    """显示询问消息框（自动应用深色标题栏）"""
    from PySide6.QtWidgets import QMessageBox
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Question)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    
    if buttons is None:
        from PySide6.QtWidgets import QMessageBox
        buttons = QMessageBox.Yes | QMessageBox.No
    msg_box.setStandardButtons(buttons)
    
    if default_button is not None:
        msg_box.setDefaultButton(default_button)
    
    apply_dark_titlebar_after_show(msg_box)
    return msg_box.exec()
