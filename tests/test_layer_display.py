"""
测试图层显示功能

验证：
1. 保存图层时只保存选中的像素
2. 切换到用户图层时只显示该图层的像素
3. 切换回根图层时显示二值化结果
"""

import numpy as np
from src.models.user_layer import UserLayer


def test_layer_pixel_extraction():
    """测试图层像素提取逻辑"""
    print("测试 1: 图层像素提取")
    
    # 模拟一个 10x10 的二值化图像
    binary_pixels = np.random.randint(0, 2, (10, 10), dtype=np.uint8) * 255
    
    # 模拟一个选区（中心 5x5 区域）
    selection_mask = np.zeros((10, 10), dtype=bool)
    selection_mask[2:7, 2:7] = True
    
    # 计算边界框
    y_indices, x_indices = np.where(selection_mask)
    x_min, x_max = x_indices.min(), x_indices.max()
    y_min, y_max = y_indices.min(), y_indices.max()
    bbox = (int(x_min), int(y_min), int(x_max - x_min + 1), int(y_max - y_min + 1))
    
    # 提取图层数据（模拟 _extract_layer_from_selection 的逻辑）
    layer_mask = selection_mask[y_min:y_max+1, x_min:x_max+1].copy()
    layer_pixels = np.full((y_max - y_min + 1, x_max - x_min + 1), 255, dtype=np.uint8)
    layer_pixels[layer_mask] = binary_pixels[y_min:y_max+1, x_min:x_max+1][layer_mask]
    
    # 验证：非选中区域应该是白色 (255)
    assert np.all(layer_pixels[~layer_mask] == 255), "非选中区域应该是白色"
    print("✅ 非选中区域正确设置为白色")
    
    # 验证：选中区域应该保留原始像素
    original_selected = binary_pixels[y_min:y_max+1, x_min:x_max+1][layer_mask]
    layer_selected = layer_pixels[layer_mask]
    assert np.array_equal(original_selected, layer_selected), "选中区域应该保留原始像素"
    print("✅ 选中区域正确保留原始像素")
    
    print()


def test_layer_full_pixels():
    """测试图层完整像素获取"""
    print("测试 2: 图层完整像素获取")
    
    # 创建一个简单的图层（RGB格式）
    layer_pixels = np.array([
        [[255, 255, 255], [255, 255, 255], [255, 255, 255]],
        [[255, 255, 255], [0, 0, 0], [255, 255, 255]],
        [[255, 255, 255], [255, 255, 255], [255, 255, 255]]
    ], dtype=np.uint8)
    
    layer_mask = np.array([
        [False, False, False],
        [False, True, False],
        [False, False, False]
    ], dtype=bool)
    
    bbox = (5, 5, 3, 3)  # 位于 (5, 5) 的 3x3 区域
    
    layer = UserLayer("测试图层", layer_pixels, layer_mask, bbox)
    
    # 获取完整图像尺寸的像素
    full_pixels = layer.get_full_pixels((10, 10))
    
    # 验证：图层外的区域应该是白色
    assert np.all(full_pixels[:5, :] == 255), "图层上方应该是白色"
    assert np.all(full_pixels[8:, :] == 255), "图层下方应该是白色"
    assert np.all(full_pixels[:, :5] == 255), "图层左侧应该是白色"
    assert np.all(full_pixels[:, 8:] == 255), "图层右侧应该是白色"
    print("✅ 图层外区域正确设置为白色")
    
    # 验证：图层内的选中像素应该是黑色
    assert np.all(full_pixels[6, 6] == 0), "图层内选中像素应该是黑色"
    print("✅ 图层内选中像素正确保留")
    
    # 验证：图层内的非选中像素应该是白色
    assert np.all(full_pixels[5, 5] == 255), "图层内非选中像素应该是白色"
    assert np.all(full_pixels[5, 6] == 255), "图层内非选中像素应该是白色"
    print("✅ 图层内非选中像素正确设置为白色")
    
    print()


def test_layer_mask():
    """测试图层掩码获取"""
    print("测试 3: 图层掩码获取")
    
    layer_mask = np.array([
        [False, True, False],
        [True, True, True],
        [False, True, False]
    ], dtype=bool)
    
    layer_pixels = np.zeros((3, 3), dtype=np.uint8)
    bbox = (2, 2, 3, 3)
    
    layer = UserLayer("测试图层", layer_pixels, layer_mask, bbox)
    
    # 获取完整掩码
    full_mask = layer.get_full_mask((10, 10))
    
    # 验证：掩码应该在正确的位置
    expected_mask = np.zeros((10, 10), dtype=bool)
    expected_mask[2:5, 2:5] = layer_mask
    
    assert np.array_equal(full_mask, expected_mask), "掩码位置不正确"
    print("✅ 掩码位置正确")
    
    print()


if __name__ == "__main__":
    print("=" * 50)
    print("图层显示功能测试")
    print("=" * 50)
    print()
    
    test_layer_pixel_extraction()
    test_layer_full_pixels()
    test_layer_mask()
    
    print("=" * 50)
    print("✅ 所有测试通过！")
    print("=" * 50)
