"""
配置文件损坏回退行为的单元测试

覆盖：损坏的配置加载时自动备份为 .bak、回退默认配置、
合法配置正常加载不受影响。
"""

import json
import shutil
import tempfile
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


def load_with_config_file(config_path: Path) -> ConfigManager:
    """在指定配置文件路径下创建 ConfigManager"""
    with patch.object(ConfigManager, "get_config_file", return_value=config_path):
        return ConfigManager()


class TestCorruptConfigBackup:
    """配置损坏备份测试类"""

    def test_corrupt_json_backed_up_and_default_used(self, temp_config_dir):
        """损坏的 JSON：原文件备份为 .bak，内存配置回退默认值"""
        config_path = temp_config_dir / "config.json"
        broken_content = '{"interface": {"theme": "dark"  # 缺少收尾'
        config_path.write_text(broken_content, encoding="utf-8")

        manager = load_with_config_file(config_path)

        # 回退默认配置
        assert manager.config == ConfigManager.DEFAULT_CONFIG
        # 原文件已备份且内容完整保留
        backup_path = temp_config_dir / "config.json.bak"
        assert backup_path.exists()
        assert backup_path.read_text(encoding="utf-8") == broken_content

    def test_unreadable_bytes_backed_up(self, temp_config_dir):
        """非法字节内容：同样触发备份与回退"""
        config_path = temp_config_dir / "config.json"
        config_path.write_bytes(b"\xff\xfe\x00broken")

        manager = load_with_config_file(config_path)

        assert manager.config == ConfigManager.DEFAULT_CONFIG
        assert (temp_config_dir / "config.json.bak").exists()

    def test_valid_config_not_touched(self, temp_config_dir):
        """合法配置：正常加载，不产生备份文件"""
        config_path = temp_config_dir / "config.json"
        config_path.write_text(
            json.dumps({"interface": {"theme": "dark"}}),
            encoding="utf-8",
        )

        manager = load_with_config_file(config_path)

        # 用户配置生效（并与默认配置合并）
        assert manager.get("interface", "theme") == "dark"
        assert manager.get("interface", "animations_enabled") is True
        assert not (temp_config_dir / "config.json.bak").exists()

    def test_save_after_corrupt_load_writes_default_merge(self, temp_config_dir):
        """损坏回退后保存：写入的是默认合并配置，且 .bak 仍保留损坏原件"""
        config_path = temp_config_dir / "config.json"
        config_path.write_text("not-json-at-all", encoding="utf-8")

        manager = load_with_config_file(config_path)
        manager.set("editor", "default_brush_size", 33)
        manager.save()

        saved = json.loads(config_path.read_text(encoding="utf-8"))
        assert saved["editor"]["default_brush_size"] == 33
        assert saved["interface"]["theme"] == ConfigManager.DEFAULT_CONFIG["interface"]["theme"]
        assert (temp_config_dir / "config.json.bak").read_text(encoding="utf-8") == "not-json-at-all"
