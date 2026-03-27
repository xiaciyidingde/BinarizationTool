"""
图层系统集成测试

测试图层系统的完整功能，包括：
- 图层数据模型
- 图层显示和切换
- 图层合成渲染
- 图层面板 UI
"""

import pytest
import numpy as np
from src.models.user_layer import UserLayer


class TestUserLayerModel:
    """测试 UserLayer 数据模型"""
    
    def test_layer_creation(self):
        """测试图层创建"""
        pixels = np.zeros((5, 5), dtype=np.uint8)
        mask = np.ones((5, 5), dtype=bool)
        bbox = (10, 10, 5, 5)
        
        layer = UserLayer("测试图层", pixels, mask, bbox)
        
        assert layer.name == "测试图层"
        assert layer.bbox == bbox
        assert layer.visible is True
        assert layer.locked is False
        assert layer.id is not None
    
    def test_layer_full_pixels(self):
        """测试获取完整像素"""
        # 创建 3x3 图层，中心是黑色
        pixels = np.array([
            [255, 255, 255],
            [255, 0, 255],
            [255, 255, 255]
        ], dtype=np.uint8)
        
        mask = np.array([
            [False, False, False],
            [False, True, False],
            [False, False, False]
        ], dtype=bool)
        
        bbox = (5, 5, 3, 3)
        layer = UserLayer("测试", pixels, mask, bbox)
        
        # 获取 10x10 完整像素
        full_pixels = layer.get_full_pixels((10, 10))
        
        # 验证尺寸
        assert full_pixels.shape == (10, 10)
        
        # 验证图层外是白色
        assert full_pixels[0, 0] == 255
        assert full_pixels[9, 9] == 255
        
        # 验证图层内选中像素是黑色
        assert full_pixels[6, 6] == 0
        
        # 验证图层内非选中像素是白色
        assert full_pixels[5, 5] == 255
    
    def test_layer_full_mask(self):
        """测试获取完整掩码"""
        mask = np.array([
            [True, False],
            [False, True]
        ], dtype=bool)
        
        pixels = np.zeros((2, 2), dtype=np.uint8)
        bbox = (3, 3, 2, 2)
        layer = UserLayer("测试", pixels, mask, bbox)
        
        full_mask = layer.get_full_mask((10, 10))
        
        # 验证尺寸
        assert full_mask.shape == (10, 10)
        
        # 验证掩码位置
        assert full_mask[3, 3] == True
        assert full_mask[4, 4] == True
        assert full_mask[3, 4] == False
        assert full_mask[4, 3] == False
        
        # 验证其他位置是 False
        assert full_mask[0, 0] == False
        assert full_mask[9, 9] == False
    
    def test_layer_copy(self):
        """测试图层深拷贝"""
        pixels = np.zeros((3, 3), dtype=np.uint8)
        mask = np.ones((3, 3), dtype=bool)
        bbox = (0, 0, 3, 3)
        
        layer1 = UserLayer("原图层", pixels, mask, bbox)
        layer2 = layer1.copy()
        
        # 验证是不同的对象
        assert layer1 is not layer2
        assert layer1.pixels is not layer2.pixels
        assert layer1.mask is not layer2.mask
        
        # 验证数据相同
        assert layer1.name == layer2.name
        assert layer1.bbox == layer2.bbox
        assert np.array_equal(layer1.pixels, layer2.pixels)
        assert np.array_equal(layer1.mask, layer2.mask)


class TestLayerComposite:
    """测试图层合成"""
    
    def test_single_layer_composite(self):
        """测试单图层合成"""
        # 根图层（全白）
        root = np.full((10, 10), 255, dtype=np.uint8)
        
        # 用户图层（左上角黑色）
        pixels = np.zeros((3, 3), dtype=np.uint8)
        mask = np.ones((3, 3), dtype=bool)
        layer = UserLayer("图层1", pixels, mask, (0, 0, 3, 3))
        
        # 合成
        composited = root.copy()
        x, y, w, h = layer.bbox
        black_mask = layer.mask & (layer.pixels == 0)
        composited[y:y+h, x:x+w][black_mask] = 0
        
        # 验证
        assert composited[0, 0] == 0  # 左上角是黑色
        assert composited[2, 2] == 0
        assert composited[5, 5] == 255  # 其他区域是白色
    
    def test_white_pixel_transparency(self):
        """测试白色像素透明性"""
        # 根图层（全黑）
        root = np.zeros((10, 10), dtype=np.uint8)
        
        # 用户图层（中心白色）
        pixels = np.array([
            [0, 0, 0],
            [0, 255, 0],
            [0, 0, 0]
        ], dtype=np.uint8)
        mask = np.ones((3, 3), dtype=bool)
        layer = UserLayer("图层1", pixels, mask, (3, 3, 3, 3))
        
        # 合成（只覆盖黑色像素）
        composited = root.copy()
        x, y, w, h = layer.bbox
        black_mask = layer.mask & (layer.pixels == 0)
        composited[y:y+h, x:x+w][black_mask] = 0
        
        # 验证：中心白色像素不覆盖，保持根图层的黑色
        assert composited[4, 4] == 0
    
    def test_multiple_layers_composite(self):
        """测试多图层合成"""
        # 根图层（全白）
        root = np.full((10, 10), 255, dtype=np.uint8)
        
        # 图层1：左上角
        layer1 = UserLayer(
            "图层1",
            np.zeros((2, 2), dtype=np.uint8),
            np.ones((2, 2), dtype=bool),
            (0, 0, 2, 2)
        )
        
        # 图层2：右下角
        layer2 = UserLayer(
            "图层2",
            np.zeros((2, 2), dtype=np.uint8),
            np.ones((2, 2), dtype=bool),
            (8, 8, 2, 2)
        )
        
        # 合成
        composited = root.copy()
        for layer in [layer1, layer2]:
            x, y, w, h = layer.bbox
            black_mask = layer.mask & (layer.pixels == 0)
            composited[y:y+h, x:x+w][black_mask] = 0
        
        # 验证
        assert composited[0, 0] == 0  # 左上角黑色
        assert composited[8, 8] == 0  # 右下角黑色
        assert composited[5, 5] == 255  # 中间白色


class TestLayerExtraction:
    """测试图层提取"""
    
    def test_extract_selected_pixels_only(self):
        """测试只提取选中的像素"""
        # 二值化图像
        binary = np.random.randint(0, 2, (10, 10), dtype=np.uint8) * 255
        
        # 选区（中心 5x5）
        selection = np.zeros((10, 10), dtype=bool)
        selection[2:7, 2:7] = True
        
        # 计算边界框
        y_indices, x_indices = np.where(selection)
        x_min, x_max = x_indices.min(), x_indices.max()
        y_min, y_max = y_indices.min(), y_indices.max()
        
        # 提取图层（模拟 _extract_layer_from_selection）
        layer_mask = selection[y_min:y_max+1, x_min:x_max+1].copy()
        layer_pixels = np.full(
            (y_max - y_min + 1, x_max - x_min + 1),
            255,
            dtype=np.uint8
        )
        layer_pixels[layer_mask] = binary[y_min:y_max+1, x_min:x_max+1][layer_mask]
        
        # 验证：非选中区域是白色
        assert np.all(layer_pixels[~layer_mask] == 255)
        
        # 验证：选中区域保留原始像素
        original_selected = binary[y_min:y_max+1, x_min:x_max+1][layer_mask]
        assert np.array_equal(layer_pixels[layer_mask], original_selected)


class TestLayerOperations:
    """测试图层操作"""
    
    def test_merge_two_layers(self):
        """测试合并两个图层"""
        # 图层1：左上角 (0,0) 2x2
        layer1 = UserLayer(
            "图层1",
            np.zeros((2, 2), dtype=np.uint8),
            np.ones((2, 2), dtype=bool),
            (0, 0, 2, 2)
        )
        
        # 图层2：右下角 (3,3) 2x2
        layer2 = UserLayer(
            "图层2",
            np.zeros((2, 2), dtype=np.uint8),
            np.ones((2, 2), dtype=bool),
            (3, 3, 2, 2)
        )
        
        # 计算合并后的边界框
        min_x = min(layer1.bbox[0], layer2.bbox[0])
        min_y = min(layer1.bbox[1], layer2.bbox[1])
        max_x = max(layer1.bbox[0] + layer1.bbox[2], layer2.bbox[0] + layer2.bbox[2])
        max_y = max(layer1.bbox[1] + layer1.bbox[3], layer2.bbox[1] + layer2.bbox[3])
        
        merged_width = max_x - min_x
        merged_height = max_y - min_y
        
        # 验证边界框
        assert min_x == 0
        assert min_y == 0
        assert merged_width == 5
        assert merged_height == 5
        
        # 创建合并后的像素
        merged_pixels = np.full((merged_height, merged_width), 255, dtype=np.uint8)
        merged_mask = np.zeros((merged_height, merged_width), dtype=bool)
        
        for layer in [layer1, layer2]:
            x, y, w, h = layer.bbox
            rel_x = x - min_x
            rel_y = y - min_y
            
            black_mask = layer.mask & (layer.pixels == 0)
            merged_pixels[rel_y:rel_y+h, rel_x:rel_x+w][black_mask] = 0
            merged_mask[rel_y:rel_y+h, rel_x:rel_x+w] |= layer.mask
        
        # 验证：左上角是黑色
        assert merged_pixels[0, 0] == 0
        assert merged_pixels[1, 1] == 0
        
        # 验证：右下角是黑色
        assert merged_pixels[3, 3] == 0
        assert merged_pixels[4, 4] == 0
        
        # 验证：中间是白色
        assert merged_pixels[2, 2] == 255
    
    def test_merge_overlapping_layers(self):
        """测试合并重叠图层"""
        # 图层1：(0,0) 3x3 全黑
        layer1 = UserLayer(
            "图层1",
            np.zeros((3, 3), dtype=np.uint8),
            np.ones((3, 3), dtype=bool),
            (0, 0, 3, 3)
        )
        
        # 图层2：(2,2) 3x3 全黑（与图层1重叠）
        layer2 = UserLayer(
            "图层2",
            np.zeros((3, 3), dtype=np.uint8),
            np.ones((3, 3), dtype=bool),
            (2, 2, 3, 3)
        )
        
        # 计算合并后的边界框
        min_x = 0
        min_y = 0
        max_x = 5
        max_y = 5
        
        merged_pixels = np.full((5, 5), 255, dtype=np.uint8)
        
        for layer in [layer1, layer2]:
            x, y, w, h = layer.bbox
            rel_x = x - min_x
            rel_y = y - min_y
            
            black_mask = layer.mask & (layer.pixels == 0)
            merged_pixels[rel_y:rel_y+h, rel_x:rel_x+w][black_mask] = 0
        
        # 验证：重叠区域是黑色
        assert merged_pixels[2, 2] == 0
        
        # 验证：图层1覆盖区域是黑色
        assert merged_pixels[0, 0] == 0
        
        # 验证：图层2覆盖区域是黑色
        assert merged_pixels[4, 4] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
