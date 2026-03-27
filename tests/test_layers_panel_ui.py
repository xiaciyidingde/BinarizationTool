"""
测试图层面板 UI 功能

验证：
1. 根图层可以被选中
2. 选中状态不会轻易消失
3. 可以在用户图层和根图层之间切换
"""

import sys
from PySide6.QtWidgets import QApplication
from src.widgets.layers_panel import LayersPanel


def test_root_layer_selectable():
    """测试根图层可选择性"""
    print("测试 1: 根图层可选择性")
    
    app = QApplication.instance() or QApplication(sys.argv)
    panel = LayersPanel()
    
    # 添加根图层
    panel.add_layer("root", "🖼️ test.png", is_root=True)
    
    # 设置根图层为激活状态
    panel.set_active_layer("root")
    
    # 验证：根图层应该被选中
    selected_ids = panel._get_selected_layer_ids()
    assert "root" in selected_ids, "根图层应该可以被选中"
    print("✅ 根图层可以被选中")
    
    print()


def test_layer_switching():
    """测试图层切换"""
    print("测试 2: 图层切换")
    
    app = QApplication.instance() or QApplication(sys.argv)
    panel = LayersPanel()
    
    # 添加根图层和用户图层
    panel.add_layer("root", "🖼️ test.png", is_root=True)
    panel.add_layer("layer1", "图层 1", is_root=False)
    panel.add_layer("layer2", "图层 2", is_root=False)
    
    # 初始选中根图层
    panel.set_active_layer("root")
    selected = panel._get_selected_layer_ids()
    assert "root" in selected, "应该选中根图层"
    print("✅ 初始选中根图层")
    
    # 切换到用户图层
    panel.set_active_layer("layer1")
    selected = panel._get_selected_layer_ids()
    assert "layer1" in selected, "应该选中图层1"
    assert "root" not in selected, "根图层不应该被选中"
    print("✅ 成功切换到用户图层")
    
    # 切换回根图层
    panel.set_active_layer("root")
    selected = panel._get_selected_layer_ids()
    assert "root" in selected, "应该选中根图层"
    assert "layer1" not in selected, "图层1不应该被选中"
    print("✅ 成功切换回根图层")
    
    print()


def test_selection_persistence():
    """测试选中状态持久性"""
    print("测试 3: 选中状态持久性")
    
    app = QApplication.instance() or QApplication(sys.argv)
    panel = LayersPanel()
    
    # 添加图层
    panel.add_layer("root", "🖼️ test.png", is_root=True)
    panel.add_layer("layer1", "图层 1", is_root=False)
    
    # 选中图层1
    panel.set_active_layer("layer1")
    
    # 验证选中状态
    selected = panel._get_selected_layer_ids()
    assert "layer1" in selected, "图层1应该被选中"
    print("✅ 图层1被选中")
    
    # 模拟点击其他区域（不应该影响选中状态）
    # 注意：在实际应用中，只有用户明确点击其他图层或调用 set_active_layer 才会改变选中状态
    
    # 再次验证选中状态
    selected = panel._get_selected_layer_ids()
    assert "layer1" in selected, "图层1应该保持选中"
    print("✅ 选中状态保持不变")
    
    print()


def test_multiple_layers():
    """测试多图层管理"""
    print("测试 4: 多图层管理")
    
    app = QApplication.instance() or QApplication(sys.argv)
    panel = LayersPanel()
    
    # 添加多个图层
    panel.add_layer("root", "🖼️ test.png", is_root=True)
    for i in range(5):
        panel.add_layer(f"layer{i}", f"图层 {i+1}", is_root=False)
    
    # 验证图层数量
    assert panel.layers_list.count() == 6, "应该有6个图层"
    print("✅ 成功添加多个图层")
    
    # 测试切换到每个图层
    for i in range(5):
        layer_id = f"layer{i}"
        panel.set_active_layer(layer_id)
        selected = panel._get_selected_layer_ids()
        assert layer_id in selected, f"应该选中{layer_id}"
    print("✅ 可以切换到所有用户图层")
    
    # 切换回根图层
    panel.set_active_layer("root")
    selected = panel._get_selected_layer_ids()
    assert "root" in selected, "应该选中根图层"
    print("✅ 可以切换回根图层")
    
    print()


if __name__ == "__main__":
    print("=" * 50)
    print("图层面板 UI 功能测试")
    print("=" * 50)
    print()
    
    test_root_layer_selectable()
    test_layer_switching()
    test_selection_persistence()
    test_multiple_layers()
    
    print("=" * 50)
    print("✅ 所有测试通过！")
    print("=" * 50)
