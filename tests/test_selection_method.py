"""
选择方式下拉框的回归测试

覆盖：
1. 默认方式为涂抹，下拉项 userData 为 paint/rect/smart
2. 变更信号发出方式字符串
3. set_selection_method 编程式设置
4. SelectionTool.method 单一事实源
"""

import sys

import pytest


class TestPropertiesPanelSelectionMethod:
    """属性面板选择方式下拉框"""

    @pytest.fixture
    def panel(self):
        from PySide6.QtWidgets import QApplication

        from src.views.properties_panel import PropertiesPanel

        _app = QApplication.instance() or QApplication(sys.argv)
        return PropertiesPanel()

    def test_default_is_paint(self, panel):
        """默认方式为涂抹"""
        assert panel.selection_method_combo.currentText() == panel.tr.tr("properties_panel.method_paint")
        assert panel.current_selection_method() == "paint"

    def test_all_methods_present(self, panel):
        """三个下拉项及其 userData"""
        data = [panel.selection_method_combo.itemData(i) for i in range(panel.selection_method_combo.count())]
        assert data == ["paint", "rect", "smart"]

    def test_change_emits_method_string(self, panel):
        """手动变更发出方式字符串信号"""
        received = []
        panel.selection_method_changed.connect(received.append)

        panel.selection_method_combo.setCurrentIndex(1)
        panel.selection_method_combo.setCurrentIndex(2)

        assert received == ["rect", "smart"]

    def test_set_selection_method_programmatic(self, panel):
        """编程式设置生效并发出信号（智能选择按钮依赖此路径）"""
        received = []
        panel.selection_method_changed.connect(received.append)

        panel.set_selection_method("smart")

        assert panel.current_selection_method() == "smart"
        assert received == ["smart"]

    def test_set_unknown_method_ignored(self, panel):
        """未知方式不改变当前值也不发信号"""
        received = []
        panel.selection_method_changed.connect(received.append)

        panel.set_selection_method("nonexistent")

        assert panel.current_selection_method() == "paint"
        assert received == []


class TestSelectionToolMethod:
    """SelectionTool 的方式字段"""

    def test_default_method_paint(self):
        """默认方式为涂抹"""
        from src.models.selection_tool import SelectionTool

        tool = SelectionTool()
        assert tool.method == "paint"

    def test_method_replaces_rect_flag(self):
        """rect_select_mode 已被 method 字段取代"""
        from src.models.selection_tool import SelectionTool

        tool = SelectionTool()
        assert not hasattr(tool, "rect_select_mode")

        tool.method = "rect"
        assert tool.method == "rect"
