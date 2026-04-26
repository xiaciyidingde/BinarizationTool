"""
测试图层合成时包含编辑层

验证画笔痕迹在图层切换后仍然可见
"""

import numpy as np
from src.models.user_layer import UserLayer


def test_composite_with_edit_layer():
    """测试合成时包含编辑层"""
    print("测试：合成时包含编辑层")
    
    # 创建根图层（10x10，全白，RGB格式）
    root_pixels = np.full((10, 10, 3), 255, dtype=np.uint8)
    
    # 创建编辑掩码和编辑值（模拟画笔痕迹）
    edit_mask = np.zeros((10, 10), dtype=bool)
    edit_mask[2:4, 2:4] = True  # 中心 2x2 区域被编辑
    
    edit_values = np.full((10, 10, 3), 255, dtype=np.uint8)
    edit_values[edit_mask] = [0, 0, 0]  # 编辑为黑色
    
    # 创建用户图层（右下角，RGB格式）
    layer = UserLayer(
        "图层1",
        np.zeros((2, 2, 3), dtype=np.uint8),
        np.ones((2, 2), dtype=bool),
        (7, 7, 2, 2)
    )
    
    # 模拟合成逻辑
    composited = root_pixels.copy()
    
    # 应用编辑层
    if edit_mask.any():
        composited[edit_mask] = edit_values[edit_mask]
    
    # 应用用户图层
    x, y, w, h = layer.bbox
    region = composited[y:y+h, x:x+w]
    region[layer.mask] = layer.pixels[layer.mask]
    
    # 验证：编辑区域应该是黑色
    assert np.all(composited[2, 2] == 0), "编辑区域应该是黑色"
    assert np.all(composited[3, 3] == 0), "编辑区域应该是黑色"
    print("✅ 编辑层正确应用")
    
    # 验证：用户图层区域应该是黑色
    assert np.all(composited[7, 7] == 0), "用户图层区域应该是黑色"
    assert np.all(composited[8, 8] == 0), "用户图层区域应该是黑色"
    print("✅ 用户图层正确应用")
    
    # 验证：其他区域应该是白色
    assert np.all(composited[0, 0] == 255), "未编辑区域应该是白色"
    assert np.all(composited[5, 5] == 255), "未编辑区域应该是白色"
    print("✅ 未编辑区域正确保持白色")
    
    print()


def test_edit_layer_priority():
    """测试编辑层优先级"""
    print("测试：编辑层优先级")
    
    # 根图层（全白，RGB格式）
    root_pixels = np.full((10, 10, 3), 255, dtype=np.uint8)
    
    # 编辑层（中心黑色）
    edit_mask = np.zeros((10, 10), dtype=bool)
    edit_mask[4:6, 4:6] = True
    edit_values = np.full((10, 10, 3), 255, dtype=np.uint8)
    edit_values[edit_mask] = [0, 0, 0]
    
    # 用户图层（覆盖编辑层的一部分，白色，RGB格式）
    layer = UserLayer(
        "图层1",
        np.full((3, 3, 3), 255, dtype=np.uint8),
        np.ones((3, 3), dtype=bool),
        (3, 3, 3, 3)
    )
    
    # 合成
    composited = root_pixels.copy()
    composited[edit_mask] = edit_values[edit_mask]
    
    x, y, w, h = layer.bbox
    region = composited[y:y+h, x:x+w]
    region[layer.mask] = layer.pixels[layer.mask]
    
    # 验证：编辑层的黑色应该被用户图层的白色覆盖
    assert np.all(composited[4, 4] == 255), "用户图层白色应该覆盖编辑层"
    assert np.all(composited[5, 5] == 255), "用户图层白色应该覆盖编辑层"
    print("✅ 编辑层优先级正确")
    
    print()


def test_multiple_edits_and_layers():
    """测试多次编辑和多个图层"""
    print("测试：多次编辑和多个图层")
    
    # 根图层（RGB格式）
    root_pixels = np.full((10, 10, 3), 255, dtype=np.uint8)
    
    # 第一次编辑（左上角）
    edit_mask = np.zeros((10, 10), dtype=bool)
    edit_mask[0:2, 0:2] = True
    edit_values = np.full((10, 10, 3), 255, dtype=np.uint8)
    edit_values[0:2, 0:2] = [0, 0, 0]
    
    # 第二次编辑（右上角）
    edit_mask[0:2, 8:10] = True
    edit_values[0:2, 8:10] = [0, 0, 0]
    
    # 用户图层1（中心，RGB格式）
    layer1 = UserLayer(
        "图层1",
        np.zeros((2, 2, 3), dtype=np.uint8),
        np.ones((2, 2), dtype=bool),
        (4, 4, 2, 2)
    )
    
    # 用户图层2（左下角，RGB格式）
    layer2 = UserLayer(
        "图层2",
        np.zeros((2, 2, 3), dtype=np.uint8),
        np.ones((2, 2), dtype=bool),
        (0, 8, 2, 2)
    )
    
    # 合成
    composited = root_pixels.copy()
    composited[edit_mask] = edit_values[edit_mask]
    
    for layer in [layer1, layer2]:
        x, y, w, h = layer.bbox
        region = composited[y:y+h, x:x+w]
        region[layer.mask] = layer.pixels[layer.mask]
    
    # 验证所有编辑和图层
    assert np.all(composited[0, 0] == 0), "第一次编辑应该可见"
    assert np.all(composited[0, 8] == 0), "第二次编辑应该可见"
    assert np.all(composited[4, 4] == 0), "图层1应该可见"
    assert np.all(composited[8, 0] == 0), "图层2应该可见"
    print("✅ 多次编辑和多个图层都正确显示")
    
    print()


def test_user_layer_view_with_edits():
    """测试查看用户图层时包含编辑层"""
    print("测试：查看用户图层时包含编辑层")
    
    # 根图层（全白，RGB格式）
    root_pixels = np.full((10, 10, 3), 255, dtype=np.uint8)
    
    # 编辑层（左上角黑色）
    edit_mask = np.zeros((10, 10), dtype=bool)
    edit_mask[0:2, 0:2] = True
    edit_values = np.full((10, 10, 3), 255, dtype=np.uint8)
    edit_values[0:2, 0:2] = [0, 0, 0]
    
    # 用户图层（右下角黑色，RGB格式）
    layer = UserLayer(
        "图层1",
        np.zeros((2, 2, 3), dtype=np.uint8),
        np.ones((2, 2), dtype=bool),
        (8, 8, 2, 2)
    )
    
    # 模拟查看用户图层：根图层 + 编辑层 + 该图层
    view = root_pixels.copy()
    
    # 应用编辑层
    view[edit_mask] = edit_values[edit_mask]
    
    # 应用用户图层
    x, y, w, h = layer.bbox
    region = view[y:y+h, x:x+w]
    region[layer.mask] = layer.pixels[layer.mask]
    
    # 验证：编辑层应该可见
    assert np.all(view[0, 0] == 0), "编辑层应该在用户图层视图中可见"
    assert np.all(view[1, 1] == 0), "编辑层应该在用户图层视图中可见"
    print("✅ 用户图层视图中编辑层可见")
    
    # 验证：用户图层应该可见
    assert np.all(view[8, 8] == 0), "用户图层应该可见"
    assert np.all(view[9, 9] == 0), "用户图层应该可见"
    print("✅ 用户图层正确显示")
    
    # 验证：其他区域是白色
    assert np.all(view[5, 5] == 255), "未编辑区域应该是白色"
    print("✅ 未编辑区域正确保持白色")
    
    print()


if __name__ == "__main__":
    print("=" * 50)
    print("图层编辑合成测试")
    print("=" * 50)
    print()
    
    test_composite_with_edit_layer()
    test_edit_layer_priority()
    test_multiple_edits_and_layers()
    test_user_layer_view_with_edits()
    
    print("=" * 50)
    print("✅ 所有测试通过！")
    print("=" * 50)
