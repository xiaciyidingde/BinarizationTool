"""
翻译管理器

管理应用程序的多语言翻译。
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional


class TranslationManager:
    """翻译管理器"""
    
    def __init__(self, locale: str = 'zh_CN'):
        """
        初始化翻译管理器
        
        Args:
            locale: 语言代码（zh_CN, en_US 等）
        """
        self.locale = locale
        self.translations: Dict[str, Any] = {}
        self.load_translations()
    
    def load_translations(self):
        """加载翻译文件"""
        locales_dir = self.get_locales_dir()
        translation_file = locales_dir / f"{self.locale}.json"
        
        if not translation_file.exists():
            print(f"警告：翻译文件不存在: {translation_file}，使用空翻译")
            self.translations = {}
            return
        
        try:
            with open(translation_file, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
        except Exception as e:
            print(f"加载翻译文件失败: {e}")
            self.translations = {}
    
    @staticmethod
    def get_locales_dir() -> Path:
        """获取翻译文件目录"""
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent
        locales_dir = project_root / 'locales'
        locales_dir.mkdir(parents=True, exist_ok=True)
        return locales_dir
    
    def tr(self, key: str, **kwargs) -> str:
        """
        翻译键
        
        Args:
            key: 翻译键（支持点号分隔的嵌套键，如 'menu.file.open'）
            **kwargs: 占位符替换参数
        
        Returns:
            翻译后的字符串
        
        Examples:
            tr('app.title')  # 返回 "BinarizationTool - 二值化图片编辑器"
            tr('message.loaded', filename='test.png')  # 返回 "已加载: test.png"
        """
        # 分割键
        keys = key.split('.')
        value = self.translations
        
        # 逐级查找
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    # 键不存在，返回原键
                    return key
            else:
                # 不是字典，无法继续查找
                return key
        
        # 如果最终值不是字符串，返回原键
        if not isinstance(value, str):
            return key
        
        # 替换占位符
        if kwargs:
            try:
                value = value.format(**kwargs)
            except KeyError:
                # 占位符不匹配，返回原字符串
                pass
        
        return value
    
    def set_language(self, locale: str):
        """
        切换语言
        
        Args:
            locale: 新的语言代码
        """
        self.locale = locale
        self.load_translations()
    
    def get_available_languages(self) -> list:
        """
        获取可用语言列表
        
        Returns:
            语言代码列表
        """
        locales_dir = self.get_locales_dir()
        languages = []
        
        for file in locales_dir.glob('*.json'):
            languages.append(file.stem)
        
        return sorted(languages)


# 全局翻译管理器实例
_translator: Optional[TranslationManager] = None


def get_translator() -> TranslationManager:
    """获取全局翻译管理器实例"""
    global _translator
    if _translator is None:
        # 从配置管理器获取语言设置
        from src.utils.config_manager import get_config_manager
        config = get_config_manager()
        locale = config.get('general', 'language', 'zh_CN')
        _translator = TranslationManager(locale)
    return _translator


def set_language(locale: str):
    """
    设置全局语言
    
    Args:
        locale: 语言代码
    """
    global _translator
    if _translator is None:
        _translator = TranslationManager(locale)
    else:
        _translator.set_language(locale)
