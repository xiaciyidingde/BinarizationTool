"""
视图组件模块
"""

from .binarization_panel import BinarizationPanel
from .canvas import Canvas
from .main_window import MainWindow
from .shortcut_handler import ShortcutHandler

__all__ = [
    'Canvas',
    'BinarizationPanel',
    'MainWindow',
    'ShortcutHandler',
]
