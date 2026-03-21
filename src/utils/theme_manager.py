"""
主题管理器模块

管理应用程序的主题样式，支持动态切换主题。
"""

from typing import Optional
from pathlib import Path


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
    }
    
    def __init__(self):
        """初始化主题管理器"""
        self.current_theme = "light"
        self._stylesheet_cache = {}
    
    def load_theme(self, theme_name: str) -> Optional[str]:
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
            return self._stylesheet_cache[theme_name]
        
        # 读取样式表文件
        theme_file = self.THEMES_DIR / self.AVAILABLE_THEMES[theme_name]
        
        try:
            with open(theme_file, 'r', encoding='utf-8') as f:
                stylesheet = f.read()
            
            # 缓存样式表
            self._stylesheet_cache[theme_name] = stylesheet
            return stylesheet
            
        except Exception as e:
            print(f"加载主题失败: {e}")
            return None
    
    def apply_theme(self, app, theme_name: str) -> bool:
        """
        应用主题到应用程序
        
        Args:
            app: QApplication 实例
            theme_name: 主题名称
            
        Returns:
            True 如果应用成功，否则 False
        """
        stylesheet = self.load_theme(theme_name)
        
        if stylesheet is None:
            return False
        
        app.setStyleSheet(stylesheet)
        self.current_theme = theme_name
        return True
    
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
