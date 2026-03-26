"""
配置管理器单元测试
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
import pytest
from src.utils.config_manager import ConfigManager


@pytest.fixture
def temp_config_dir():
    """创建临时配置目录"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def config_manager(temp_config_dir):
    """创建配置管理器实例（使用临时目录）"""
    # Mock 配置文件路径到临时目录
    config_path = temp_config_dir / f'test_{id(temp_config_dir)}.json'
    with patch.object(ConfigManager, 'get_config_file', return_value=config_path):
        manager = ConfigManager()
        # 确保每个测试都从干净的状态开始
        import copy
        manager.config = copy.deepcopy(manager.DEFAULT_CONFIG)
        yield manager


class TestConfigManager:
    """配置管理器测试类"""
    
    def test_init_creates_default_config(self, config_manager):
        """测试初始化时创建默认配置"""
        assert config_manager.config is not None
        assert 'general' in config_manager.config
        assert 'interface' in config_manager.config
        assert 'editor' in config_manager.config
        assert 'performance' in config_manager.config
        assert 'file' in config_manager.config
    
    def test_get_default_values(self, config_manager):
        """测试获取默认值"""
        assert config_manager.get('general', 'language') == 'zh_CN'
        assert config_manager.get('interface', 'theme') == 'light'
        assert config_manager.get('editor', 'default_brush_size') == 20
        assert config_manager.get('performance', 'tile_cache_size') == 1000
        assert config_manager.get('file', 'default_save_format') == 'follow_original'
    
    def test_get_with_custom_default(self, config_manager):
        """测试使用自定义默认值"""
        value = config_manager.get('general', 'nonexistent_key', 'custom_default')
        assert value == 'custom_default'
    
    def test_set_and_get(self, config_manager):
        """测试设置和获取配置"""
        config_manager.set('general', 'language', 'en_US')
        assert config_manager.get('general', 'language') == 'en_US'
        
        config_manager.set('editor', 'default_brush_size', 50)
        assert config_manager.get('editor', 'default_brush_size') == 50
    
    def test_save_and_load(self, temp_config_dir):
        """测试保存和加载配置"""
        config_path = temp_config_dir / 'config.json'
        
        # 创建第一个实例并修改配置
        with patch.object(ConfigManager, 'get_config_file', return_value=config_path):
            manager1 = ConfigManager()
            manager1.set('general', 'language', 'en_US')
            manager1.set('editor', 'default_brush_size', 100)
            assert manager1.save() is True
        
        # 创建新实例加载
        with patch.object(ConfigManager, 'get_config_file', return_value=config_path):
            manager2 = ConfigManager()
            # 验证加载的值
            assert manager2.get('general', 'language') == 'en_US'
            assert manager2.get('editor', 'default_brush_size') == 100
    
    def test_reset_to_default(self, temp_config_dir):
        """测试重置为默认值"""
        config_path = temp_config_dir / 'reset_test' / 'config.json'
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with patch.object(ConfigManager, 'get_config_file', return_value=config_path):
            manager = ConfigManager()
            # 修改配置
            manager.set('general', 'language', 'en_US')
            manager.set('editor', 'default_brush_size', 100)
            manager.save()
            
            # 重置
            manager.reset_to_default()
            
            # 验证已重置
            assert manager.get('general', 'language') == 'zh_CN'
            assert manager.get('editor', 'default_brush_size') == 20
    
    def test_ui_to_config_mapping(self, config_manager):
        """测试 UI 值到配置值的映射"""
        assert config_manager.ui_to_config('language', '中文') == 'zh_CN'
        assert config_manager.ui_to_config('language', 'English') == 'en_US'
        assert config_manager.ui_to_config('save_format', '跟随原文件') == 'follow_original'
        assert config_manager.ui_to_config('save_format', 'PNG') == 'png'
        
        # 测试未映射的值直接返回
        assert config_manager.ui_to_config('unknown_key', 'value') == 'value'
    
    def test_config_to_ui_mapping(self, config_manager):
        """测试配置值到 UI 值的映射"""
        assert config_manager.config_to_ui('language', 'zh_CN') == '中文'
        assert config_manager.config_to_ui('language', 'en_US') == 'English'
        assert config_manager.config_to_ui('save_format', 'follow_original') == '跟随原文件'
        assert config_manager.config_to_ui('save_format', 'png') == 'PNG'
        
        # 测试未映射的值直接返回
        assert config_manager.config_to_ui('unknown_key', 'value') == 'value'
    
    def test_add_recent_file(self, config_manager):
        """测试添加最近文件"""
        config_manager.add_recent_file('/path/to/file1.png')
        config_manager.add_recent_file('/path/to/file2.png')
        
        recent = config_manager.get_recent_files()
        assert len(recent) == 2
        assert recent[0] == '/path/to/file2.png'  # 最新的在前
        assert recent[1] == '/path/to/file1.png'
    
    def test_add_recent_file_duplicate(self, config_manager):
        """测试添加重复的最近文件"""
        config_manager.add_recent_file('/path/to/file1.png')
        config_manager.add_recent_file('/path/to/file2.png')
        config_manager.add_recent_file('/path/to/file1.png')  # 重复
        
        recent = config_manager.get_recent_files()
        assert len(recent) == 2
        assert recent[0] == '/path/to/file1.png'  # 移到最前
        assert recent[1] == '/path/to/file2.png'
    
    def test_add_recent_file_max_limit(self, config_manager):
        """测试最近文件数量限制"""
        # 添加超过限制的文件
        for i in range(15):
            config_manager.add_recent_file(f'/path/to/file{i}.png')
        
        recent = config_manager.get_recent_files()
        assert len(recent) == 10  # 最多保留 10 个
        assert recent[0] == '/path/to/file14.png'  # 最新的
        assert recent[-1] == '/path/to/file5.png'  # 最旧的
    
    def test_clear_recent_files(self, config_manager):
        """测试清空最近文件"""
        config_manager.add_recent_file('/path/to/file1.png')
        config_manager.add_recent_file('/path/to/file2.png')
        
        config_manager.clear_recent_files()
        
        recent = config_manager.get_recent_files()
        assert len(recent) == 0
    
    def test_get_recent_files_empty(self, config_manager):
        """测试获取空的最近文件列表"""
        recent = config_manager.get_recent_files()
        assert recent == []
    
    def test_config_file_creation(self, temp_config_dir):
        """测试配置文件创建"""
        config_path = temp_config_dir / 'config.json'
        
        with patch.object(ConfigManager, 'get_config_file', return_value=config_path):
            manager = ConfigManager()
            # 保存配置
            manager.save()
        
        # 验证文件存在
        assert config_path.exists()
        
        # 验证文件内容
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert 'general' in data
        assert 'interface' in data
        assert 'editor' in data
        assert 'performance' in data
        assert 'file' in data
    
    def test_load_partial_config(self, temp_config_dir):
        """测试加载部分配置（缺少某些键）"""
        # 使用不同的临时目录避免冲突
        config_path = temp_config_dir / 'partial' / 'config.json'
        
        # 创建部分配置文件
        partial_config = {
            'general': {
                'language': 'en_US'
            }
        }
        
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(partial_config, f)
        
        # 加载配置（使用新的 patch 上下文）
        with patch.object(ConfigManager, 'get_config_file', return_value=config_path):
            manager = ConfigManager()
            # 强制重新加载
            manager.config_file = config_path
            manager.config = manager.load()
        
        # 验证已加载的值
        assert manager.get('general', 'language') == 'en_US'
        
        # 验证缺失的值使用默认值
        assert manager.get('interface', 'theme') == 'light'
        assert manager.get('editor', 'default_brush_size') == 20
    
    def test_invalid_config_file(self, temp_config_dir):
        """测试加载无效的配置文件"""
        # 使用不同的临时目录避免冲突
        config_path = temp_config_dir / 'invalid' / 'config.json'
        
        # 创建无效的 JSON 文件
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write('invalid json content')
        
        # 加载配置应该使用默认值（使用新的 patch 上下文）
        with patch.object(ConfigManager, 'get_config_file', return_value=config_path):
            manager = ConfigManager()
            # 强制重新加载
            manager.config_file = config_path
            manager.config = manager.load()
        
        # 验证使用默认值
        assert manager.get('general', 'language') == 'zh_CN'
        assert manager.get('editor', 'default_brush_size') == 20
    
    def test_set_creates_section(self, config_manager):
        """测试设置值时自动创建节"""
        config_manager.set('new_section', 'new_key', 'new_value')
        assert config_manager.get('new_section', 'new_key') == 'new_value'
    
    def test_save_creates_directory(self, temp_config_dir):
        """测试保存时自动创建目录"""
        config_path = temp_config_dir / 'subdir' / 'config.json'
        
        with patch.object(ConfigManager, 'get_config_file', return_value=config_path):
            # 确保父目录存在
            config_path.parent.mkdir(parents=True, exist_ok=True)
            manager = ConfigManager()
            
            # 保存配置
            assert manager.save() is True
        
        # 验证目录和文件都已创建
        assert config_path.parent.exists()
        assert config_path.exists()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
