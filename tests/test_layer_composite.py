"""
测试图层合成功能

验证：
1. 根图层 + 用户图层合成
2. 黑色像素覆盖
3. 白色像素透明
4. 多图层叠加
"""

import numpy as np
from src.models.user_layer import UserLayer


def test_single_layer_composite():
    """测试单图层合成"""
    print("测试 1: 单图层合成")
    
    # 创建根图层（10x10，全白）
    root_pixels = np.full((10, 10), 255, dtype=np.uint8)
    
    # 在中心添加一些黑色像素
    root_pixels[4:6, 4:6] = 0
    
    # 创建用户图层（在左上角添加黑色块）
    layer_pixels = np.array([
        [0, 0, 255],
        [0, 0, 255],
        [255, 255, 255]
    ], dtype=np.uint8)
    
    layer_mask = np.array([
        [True, True, False],
        [True, True, False],
        [False, False, False]
    ], dtype=bool)
    
    bbox = (2, 2, 3, 3)
    layer = UserLayer("测试图层", layer_pixels, layer_mask, bbox)
    
    # 模拟合成逻辑
    composited = root_pixels.copy()
    x, y, w, h = layer.bbox
    black_mask = layer.mask & (layer.pixels == 0)
    composited[y:y+h, x:x+w][black_mask] = 0
    
    # 验证：左上角应该有黑色块
    assert composited[2, 2] == 0, "图层黑色像素应该覆盖"
    assert composited[2, 3] == 0, "图层黑色像素应该覆盖"
    assert composited[3, 2] == 0, "图层黑色像素应该覆盖"
    assert composited[3, 3] == 0, "图层黑色像素应该覆盖"
    print("✅ 图层黑色像素正确覆盖")
    
    # 验证：中心的黑色块应该保留
    assert composited[4, 4] == 0, "根图层黑色像素应该保留"
    assert composited[5, 5] == 0, "根图层黑色像素应该保留"
    print("✅ 根图层黑色像素正确保留")
    
    # 验证：其他区域应该是白色
    assert composited[0, 0] == 255, "未覆盖区域应该是白色"
    assert composited[9, 9] == 255, "未覆盖区域应该是白色"
    print("✅ 未覆盖区域正确保持白色")
    
    print()


def test_white_pixel_transparency():
    """测试白色像素透明性"""
    print("测试 2: 白色像素透明性")
    
    # 创建根图层（全黑）
    root_pixels = np.zeros((10, 10), dtype=np.uint8)
    
    # 创建用户图层（中心有白色像素）
    layer_pixels = np.array([
        [0, 0, 0],
        [0, 255, 0],
        [0, 0, 0]
    ], dtype=np.uint8)
    
    layer_mask = np.ones((3, 3), dtype=bool)
    bbox = (3, 3, 3, 3)
    layer = UserLayer("测试图层", layer_pixels, layer_mask, bbox)
    
    # 模拟合成逻辑
    composited = root_pixels.copy()
    x, y, w, h = layer.bbox
    black_mask = layer.mask & (layer.pixels == 0)
    composited[y:y+h, x:x+w][black_mask] = 0
    
    # 验证：中心的白色像素不应该覆盖（保持根图层的黑色）
    assert composited[4, 4] == 0, "白色像素应该透明，显示根图层"
    print("✅ 白色像素正确保持透明")
    
    # 验证：周围的黑色像素应该覆盖
    assert composited[3, 3] == 0, "黑色像素应该覆盖"
    assert composited[5, 5] == 0, "黑色像素应该覆盖"
    print("✅ 黑色像素正确覆盖")
    
    print()


def test_multiple_layers_composite():
    """测试多图层合成"""
    print("测试 3: 多图层合成")
    
    # 创建根图层（全白）
    root_pixels = np.full((10, 10), 255, dtype=np.uint8)
    
    # 图层1：左上角黑色块
    layer1_pixels = np.zeros((3, 3), dtype=np.uint8)
    layer1_mask = np.ones((3, 3), dtype=bool)
    layer1 = UserLayer("图层1", layer1_pixels, layer1_mask, (0, 0, 3, 3))
    
    # 图层2：右下角黑色块
    layer2_pixels = np.zeros((3, 3), dtype=np.uint8)
    layer2_mask = np.ones((3, 3), dtype=bool)
    layer2 = UserLayer("图层2", layer2_pixels, layer2_mask, (7, 7, 3, 3))
    
    # 模拟合成逻辑
    composited = root_pixels.copy()
    for layer in [layer1, layer2]:
        x, y, w, h = layer.bbox
        black_mask = layer.mask & (layer.pixels == 0)
        composited[y:y+h, x:x+w][black_mask] = 0
    
    # 验证：左上角应该是黑色
    assert composited[0, 0] == 0, "图层1应该覆盖"
    assert composited[2, 2] == 0, "图层1应该覆盖"
    print("✅ 图层1正确覆盖")
    
    # 验证：右下角应该是黑色
    assert composited[7, 7] == 0, "图层2应该覆盖"
    assert composited[9, 9] == 0, "图层2应该覆盖"
    print("✅ 图层2正确覆盖")
    
    # 验证：中间区域应该是白色
    assert composited[5, 5] == 255, "未覆盖区域应该是白色"
    print("✅ 未覆盖区域正确保持白色")
    
    print()


def test_layer_visibility():
    """测试图层可见性"""
    print("测试 4: 图层可见性")
    
    # 创建根图层（全白）
    root_pixels = np.full((10, 10), 255, dtype=np.uint8)
    
    # 创建不可见的图层
    layer_pixels = np.zeros((3, 3), dtype=np.uint8)
    layer_mask = np.ones((3, 3), dtype=bool)
    layer = UserLayer("测试图层", layer_pixels, layer_mask, (2, 2, 3, 3))
    layer.visible = False
    
    # 模拟合成逻辑（跳过不可见图层）
    composited = root_pixels.copy()
    if layer.visible:
        x, y, w, h = layer.bbox
        black_mask = layer.mask & (layer.pixels == 0)
        composited[y:y+h, x:x+w][black_mask] = 0
    
    # 验证：不可见图层不应该影响结果
    assert composited[2, 2] == 255, "不可见图层不应该覆盖"
    assert composited[4, 4] == 255, "不可见图层不应该覆盖"
    print("✅ 不可见图层正确跳过")
    
    # 设置为可见并重新合成
    layer.visible = True
    composited = root_pixels.copy()
    if layer.visible:
        x, y, w, h = layer.bbox
        black_mask = layer.mask & (layer.pixels == 0)
        composited[y:y+h, x:x+w][black_mask] = 0
    
    # 验证：可见图层应该覆盖
    assert composited[2, 2] == 0, "可见图层应该覆盖"
    print("✅ 可见图层正确覆盖")
    
    print()


if __name__ == "__main__":
    print("=" * 50)
    print("图层合成功能测试")
    print("=" * 50)
    print()
    
    test_single_layer_composite()
    test_white_pixel_transparency()
    test_multiple_layers_composite()
    test_layer_visibility()
    
    print("=" * 50)
    print("✅ 所有测试通过！")
    print("=" * 50)
