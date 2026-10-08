"""
图层面板行序与画布图层叠放层级映射的单元测试

锁定面板约定：面板顶行 = 画布最顶层，根图层（画布最底层）固定在最后一行。
覆盖：
1. add_layer 的追加与置顶插入
2. 拖放后根图层强制回最后一行，信号按顶→底发出
3. order_layers_by_panel 的面板顺序 → 数据列表顺序反转映射
4. 模拟 _sync_layers_panel 的重建顺序
"""

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from src.models.user_layer import UserLayer
from src.views.main_window import order_layers_by_panel
from src.widgets.layers_panel import LayersPanel


def make_panel():
    _app = QApplication.instance() or QApplication(sys.argv)
    return LayersPanel()


def panel_rows(panel) -> list:
    """按顶→底返回面板中的图层 ID"""
    return [panel.layers_list.item(i).data(Qt.UserRole) for i in range(panel.layers_list.count())]


class TestAddLayerPosition:
    """add_layer 插入位置测试"""

    def test_plain_append_order(self):
        """普通追加按调用顺序向下排列"""
        panel = make_panel()
        panel.add_layer("layer1", "图层 1")
        panel.add_layer("layer2", "图层 2")

        assert panel_rows(panel) == ["layer1", "layer2"]

    def test_on_top_inserts_above_root(self):
        """on_top=True 时插入到面板顶部（根图层之上）"""
        panel = make_panel()
        panel.add_layer("root", "🖼️ test.png", is_root=True)
        panel.add_layer("layer1", "图层 1", on_top=True)

        assert panel_rows(panel) == ["layer1", "root"]

    def test_on_top_with_existing_layers(self):
        """连续保存多个图层：最新图层始终在面板顶部"""
        panel = make_panel()
        panel.add_layer("root", "🖼️ test.png", is_root=True)
        panel.add_layer("layer1", "图层 1", on_top=True)
        panel.add_layer("layer2", "图层 2", on_top=True)

        # 最新保存的 layer2 是画布最顶层，应在面板顶行
        assert panel_rows(panel) == ["layer2", "layer1", "root"]

    def test_root_always_bottom_after_live_adds(self):
        """无论添加多少图层，根图层始终在最后一行"""
        panel = make_panel()
        panel.add_layer("layer1", "图层 1", on_top=True)
        panel.add_layer("root", "🖼️ test.png", is_root=True)
        panel.add_layer("layer2", "图层 2", on_top=True)

        assert panel_rows(panel)[-1] == "root"
        assert panel_rows(panel) == ["layer2", "layer1", "root"]


class TestRowsMovedRootReposition:
    """拖放后根图层位置保护测试"""

    def test_root_moved_to_top_snaps_back_to_bottom(self, qtbot=None):
        """拖放导致根图层离开最后一行时，自动移回最后一行"""
        panel = make_panel()
        panel.add_layer("layer1", "图层 1")
        panel.add_layer("layer2", "图层 2")
        panel.add_layer("root", "🖼️ test.png", is_root=True)

        # 模拟一次把根图层拖到顶部的内部移动
        root_item = panel.layers_list.takeItem(2)
        panel.layers_list.insertItem(0, root_item)
        assert panel_rows(panel) == ["root", "layer1", "layer2"]

        emitted = []
        panel.layer_order_changed.connect(lambda ids: emitted.append(list(ids)))
        panel._on_rows_moved(None, 0, 0, None, 0)

        # 根图层回到最后一行，信号按顶→底发出（根在末尾）
        assert panel_rows(panel) == ["layer1", "layer2", "root"]
        assert emitted == [["layer1", "layer2", "root"]]

    def test_signal_emits_top_to_bottom(self):
        """顺序改变信号按面板顶→底发出，根图层在末尾"""
        panel = make_panel()
        panel.add_layer("layer1", "图层 1")
        panel.add_layer("layer2", "图层 2")
        panel.add_layer("root", "🖼️ test.png", is_root=True)

        emitted = []
        panel.layer_order_changed.connect(lambda ids: emitted.append(list(ids)))
        panel._on_rows_moved(None, 0, 0, None, 0)

        assert emitted == [["layer1", "layer2", "root"]]


class TestOrderLayersByPanel:
    """面板顺序 → 数据列表顺序的映射测试"""

    @staticmethod
    def make_layers(*ids):
        return [
            UserLayer(
                name=f"图层 {i + 1}",
                pixels=__import__("numpy").full((2, 2, 3), 255, dtype="uint8"),
                mask=__import__("numpy").ones((2, 2), dtype=bool),
                bbox=(0, 0, 2, 2),
            )
            for i, _ in enumerate(ids)
        ]

    def test_panel_top_maps_to_list_tail(self):
        """面板顶行 → 列表尾部（画布最顶层）"""
        layers = self.make_layers("a", "b", "c")
        for layer, lid in zip(layers, ["a", "b", "c"], strict=True):
            layer.id = lid

        # 面板顶→底 = [c, b, a]（c 最顶层）
        result = order_layers_by_panel(["c", "b", "a"], layers)

        assert [layer.id for layer in result] == ["a", "b", "c"]

    def test_reorder_reflects_drag(self):
        """用户把图层 b 拖到面板顶部：b 成为画布最顶层（列表尾）"""
        layers = self.make_layers("a", "b")
        for layer, lid in zip(layers, ["a", "b"], strict=True):
            layer.id = lid

        # 拖动后面板顶→底 = [b, a]
        result = order_layers_by_panel(["b", "a"], layers)

        assert [layer.id for layer in result] == ["a", "b"]  # a 在列表头 = 最底层
        assert result[-1].id == "b"  # b 在列表尾 = 最顶层

    def test_filters_unknown_and_keeps_missing_tail(self):
        """面板中不存在的 ID 被跳过，图层对象保持同一引用"""
        layers = self.make_layers("a", "b")
        for layer, lid in zip(layers, ["a", "b"], strict=True):
            layer.id = lid

        result = order_layers_by_panel(["ghost", "b", "a"], layers)

        assert [layer.id for layer in result] == ["a", "b"]
        assert result[0] is layers[0]  # 同一对象，不是副本
        assert result[1] is layers[1]

    def test_empty_panel(self):
        """空面板：返回空列表"""
        assert order_layers_by_panel([], self.make_layers("a")) == []


class TestSyncRebuildOrder:
    """模拟 _sync_layers_panel 的面板重建顺序"""

    def test_rebuild_matches_canvas_stack(self):
        """按列表头→尾 = 底→顶的图层，重建后面板顶→底 = 顶→底、根在最后一行"""
        panel = make_panel()

        # 数据列表：a 最底层，c 最顶层（列表头→尾）
        user_layers = self.make_layers("a", "b", "c")
        for layer, lid in zip(user_layers, ["a", "b", "c"], strict=True):
            layer.id = lid

        # 模拟 _sync_layers_panel：逆序添加用户图层，根图层最后添加
        for layer in reversed(user_layers):
            panel.add_layer(layer.id, layer.name)
        panel.add_layer("root", "🖼️ test.png", is_root=True)

        assert panel_rows(panel) == ["c", "b", "a", "root"]
        # 顶行是画布最顶层，最后一行是根图层
        assert panel_rows(panel)[0] == "c"
        assert panel_rows(panel)[-1] == "root"

    def make_layers(self, *ids):
        return TestOrderLayersByPanel.make_layers(*ids)
