"""
主题管理器模块

管理应用程序的主题样式，支持动态切换主题。
"""

import os
import tempfile
from pathlib import Path

from .resources import THREE_BARS_BYTES


class ThemeManager:
    """
    主题管理器类

    负责加载和应用主题样式表。
    """

    # 主题文件路径
    THEMES_DIR = Path(__file__).parent.parent.parent / "themes"

    # 可用主题
    AVAILABLE_THEMES = {
        "light": "light_theme.qss",
        "dark": "dark_theme.qss",
    }

    def __init__(self):
        """初始化主题管理器"""
        self.current_theme = "light"
        self._stylesheet_cache = {}
        self._icon_temp_path = None
        self._setup_temp_icons()

    def _setup_temp_icons(self):
        """设置临时图标文件"""
        try:
            # 创建临时目录
            temp_dir = tempfile.gettempdir()
            icon_path = os.path.join(temp_dir, "kiro_three_bars_icon.png")

            # 写入图标数据
            with open(icon_path, 'wb') as f:
                f.write(THREE_BARS_BYTES)

            # 保存路径（使用 Path 对象转换为 URL 格式，跨平台兼容）
            from pathlib import Path
            self._icon_temp_path = Path(icon_path).as_posix()

        except Exception as e:
            print(f"设置临时图标失败: {e}")
            self._icon_temp_path = None

    def load_theme(self, theme_name: str) -> str | None:
        """
        加载主题样式表

        Args:
            theme_name: 主题名称

        Returns:
            样式表字符串，如果加载失败则返回 None
        """
        if theme_name not in self.AVAILABLE_THEMES:
            return None

        # 检查缓存
        if theme_name in self._stylesheet_cache:
            stylesheet = self._stylesheet_cache[theme_name]
        else:
            # 读取样式表文件
            theme_file = self.THEMES_DIR / self.AVAILABLE_THEMES[theme_name]

            try:
                with open(theme_file, encoding='utf-8') as f:
                    stylesheet = f.read()

                # 缓存样式表
                self._stylesheet_cache[theme_name] = stylesheet

            except Exception as e:
                print(f"加载主题失败: {e}")
                return None

        # 注入图标路径
        if self._icon_temp_path:
            stylesheet = stylesheet.replace(
                '{{THREE_BARS_ICON_PATH}}',
                self._icon_temp_path
            )

        return stylesheet

    def apply_theme(self, app, theme_name: str) -> bool:
        """
        应用主题到应用程序

        Args:
            app: QApplication 实例
            theme_name: 主题名称（light, dark, 或 system）

        Returns:
            True 如果应用成功，否则 False
        """
        # 如果是 system 主题，检测系统主题
        if theme_name == "system":
            theme_name = self._detect_system_theme()
        
        stylesheet = self.load_theme(theme_name)

        if stylesheet is None:
            return False

        app.setStyleSheet(stylesheet)
        self.current_theme = theme_name
        return True
    
    def _detect_system_theme(self) -> str:
        """
        检测系统主题
        
        Returns:
            'dark' 或 'light'
        """
        import sys
        
        if sys.platform == 'win32':
            try:
                import winreg
                # 读取 Windows 注册表中的主题设置
                registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
                key = winreg.OpenKey(registry, r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize')
                value, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
                winreg.CloseKey(key)
                # 0 = 深色, 1 = 浅色
                return 'light' if value == 1 else 'dark'
            except Exception:
                return 'light'  # 默认浅色
        else:
            # 其他系统暂时返回浅色
            return 'light'

    def get_current_theme(self) -> str:
        """
        获取当前主题名称

        Returns:
            当前主题名称
        """
        return self.current_theme

    def get_available_themes(self) -> list:
        """
        获取可用主题列表

        Returns:
            主题名称列表
        """
        return list(self.AVAILABLE_THEMES.keys())
