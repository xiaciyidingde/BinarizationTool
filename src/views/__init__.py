"""
视图组件模块
"""

from .canvas import Canvas
from .binarization_panel import BinarizationPanel
from .main_window import MainWindow
from .shortcut_handler import ShortcutHandler

__all__ = [
    'Canvas',
    'BinarizationPanel',
    'MainWindow',
    'ShortcutHandler',
]
