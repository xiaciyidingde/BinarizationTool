"""
配置管理器

管理应用程序的配置文件读取、保存和默认值。
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigManager:
    """配置管理器"""
    
    # 默认配置
    DEFAULT_CONFIG = {
        "version": "1.0",
        "general": {
            "language": "zh_CN"  # zh_CN, en_US
        },
        "interface": {
            "theme": "light",  # light, dark, system
            "window_geometry": {
                "width": 1550,
                "height": 900,
                "x": 100,
                "y": 100,
                "maximized": False
            }
        },
        "editor": {
            "default_brush_size": 20,
            "default_selection_size": 50,
            "undo_history_limit": 50,
            "canvas_background": "white"  # white, gray, black
        },
        "performance": {
            "tile_cache_size": 1000,
            "debounce_delay": 150,
            "hardware_acceleration": True,
            "max_image_size": 20000
        },
        "file": {
            "default_save_format": "follow_original",  # follow_original, png, jpg, bmp, webp
            "filename_format": "timestamp",  # timestamp, copy, custom
            "custom_prefix": "",
            "custom_suffix": "",
            "recent_files": [],
            "last_open_directory": "",
            "last_save_directory": ""
        }
    }
    
    # 值映射：UI显示值 <-> 配置文件值
    VALUE_MAPPING = {
        # 语言
        "language": {
            "中文": "zh_CN",
            "English": "en_US"
        },
        # 主题
        "theme": {
            "浅色主题": "light",
            "深色主题": "dark",
            "跟随系统": "system"
        },
        # 画布背景
        "canvas_background": {
            "白色": "white",
            "灰色": "gray",
            "黑色": "black"
        },
        # 保存格式
        "save_format": {
            "跟随原文件": "follow_original",
            "PNG": "png",
            "JPG": "jpg",
            "BMP": "bmp",
            "WebP": "webp"
        },
        # 文件名格式
        "filename_format": {
            "原名_时间戳": "timestamp",
            "原名_副本": "copy",
            "自定义": "custom"
        }
    }
    
    def __init__(self):
        """初始化配置管理器"""
        self.config_file = self.get_config_file()
        self.config = self.load()
    
    @staticmethod
    def get_config_dir() -> Path:
        """获取配置目录（项目根目录的 data 文件夹）"""
        # 获取项目根目录
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent
        
        config_dir = project_root / 'data'
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir
    
    @staticmethod
    def get_config_file() -> Path:
        """获取配置文件路径"""
        return ConfigManager.get_config_dir() / 'config.json'
    
    def load(self) -> Dict[str, Any]:
        """加载配置"""
        import copy
        
        if not self.config_file.exists():
            # 配置文件不存在，创建默认配置
            self.config = copy.deepcopy(self.DEFAULT_CONFIG)
            self.save()
            return self.config
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 合并默认配置（处理新增的配置项）
            merged = self._merge_config(copy.deepcopy(self.DEFAULT_CONFIG), config)
            return merged
        except Exception as e:
            print(f"加载配置失败: {e}，使用默认配置")
            return copy.deepcopy(self.DEFAULT_CONFIG)
    
    def save(self):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
    
    def get(self, section: str, key: str, default=None) -> Any:
        """
        获取配置值
        
        Args:
            section: 配置节名称
            key: 配置键名称
            default: 默认值
        
        Returns:
            配置值
        """
        return self.config.get(section, {}).get(key, default)
    
    def set(self, section: str, key: str, value: Any):
        """
        设置配置值
        
        Args:
            section: 配置节名称
            key: 配置键名称
            value: 配置值
        """
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
    
    def get_all(self, section: str) -> Dict[str, Any]:
        """
        获取整个配置节
        
        Args:
            section: 配置节名称
        
        Returns:
            配置节字典
        """
        return self.config.get(section, {})
    
    def set_all(self, section: str, values: Dict[str, Any]):
        """
        设置整个配置节
        
        Args:
            section: 配置节名称
            values: 配置值字典
        """
        self.config[section] = values
    
    def reset_to_default(self):
        """重置为默认配置"""
        import copy
        self.config = copy.deepcopy(self.DEFAULT_CONFIG)
        self.save()
    
    def _merge_config(self, default: dict, user: dict) -> dict:
        """
        合并配置（用户配置覆盖默认配置）
        
        Args:
            default: 默认配置
            user: 用户配置
        
        Returns:
            合并后的配置
        """
        result = default.copy()
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result
    
    @classmethod
    def ui_to_config(cls, category: str, ui_value: str) -> str:
        """
        将 UI 显示值转换为配置文件值
        
        Args:
            category: 值类别（language, theme, canvas_background 等）
            ui_value: UI 显示值
        
        Returns:
            配置文件值
        """
        mapping = cls.VALUE_MAPPING.get(category, {})
        return mapping.get(ui_value, ui_value)
    
    @classmethod
    def config_to_ui(cls, category: str, config_value: str) -> str:
        """
        将配置文件值转换为 UI 显示值
        
        Args:
            category: 值类别
            config_value: 配置文件值
        
        Returns:
            UI 显示值
        """
        mapping = cls.VALUE_MAPPING.get(category, {})
        # 反向查找
        for ui_val, cfg_val in mapping.items():
            if cfg_val == config_value:
                return ui_val
        return config_value
    
    def add_recent_file(self, file_path: str, max_count: int = 10):
        """
        添加到最近文件列表
        
        Args:
            file_path: 文件路径
            max_count: 最大保留数量
        """
        recent = self.config['file']['recent_files']
        
        # 移除已存在的相同路径
        if file_path in recent:
            recent.remove(file_path)
        
        # 添加到列表开头
        recent.insert(0, file_path)
        
        # 限制数量
        self.config['file']['recent_files'] = recent[:max_count]
        self.save()
    
    def get_recent_files(self) -> list:
        """获取最近文件列表"""
        return self.config['file']['recent_files']
    
    def clear_recent_files(self):
        """清除最近文件列表"""
        self.config['file']['recent_files'] = []
        self.save()


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
