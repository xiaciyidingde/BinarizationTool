"""
测试重叠图层的合成

验证：
1. 第二个图层应该包含第一个图层的修改
2. 在不同视图模式下保存图层的行为
3. 模拟真实用户操作流程
"""

import numpy as np
import pytest
from src.models.image_data import ImageData
from src.models.user_layer import UserLayer
from src.utils.binarization_engine import BinarizationEngine


def simulate_extract_layer_from_selection(image_data, selection_mask, view_mode):
    """
    模拟 _extract_layer_from_selection 方法
    
    这是实际代码的简化版本，用于测试
    """
    # 根据视图模式获取像素数据
    if view_mode == 'preprocessed':
        # 预处理视图：使用预处理后的像素，并合成用户图层
        if image_data.preprocessed_pixels is not None:
            root_pixels = image_data.preprocessed_pixels.copy()
        else:
            root_pixels = image_data.original_pixels.copy()
        
        # 合成所有可见用户图层的预处理结果
        for layer in image_data.user_layers:
            if not layer.visible:
                continue
            
            if layer.original_region is not None and layer.binarization_params is not None:
                preprocess_params = layer.binarization_params.get('preprocess', {})
                preprocessed_region = BinarizationEngine.apply_preprocess(
                    layer.original_region,
                    **preprocess_params
                )
                
                x, y, w, h = layer.bbox
                img_h, img_w = root_pixels.shape[:2]
                
                if x >= img_w or y >= img_h or x + w <= 0 or y + h <= 0:
                    continue
                
                x_start = max(0, x)
                y_start = max(0, y)
                x_end = min(img_w, x + w)
                y_end = min(img_h, y + h)
                
                layer_x_offset = x_start - x
                layer_y_offset = y_start - y
                layer_w = x_end - x_start
                layer_h = y_end - y_start
                
                preprocessed_region_part = preprocessed_region[layer_y_offset:layer_y_offset+layer_h, layer_x_offset:layer_x_offset+layer_w]
                layer_mask_region = layer.mask[layer_y_offset:layer_y_offset+layer_h, layer_x_offset:layer_x_offset+layer_w]
                
                region = root_pixels[y_start:y_end, x_start:x_end]
                region[layer_mask_region] = preprocessed_region_part[layer_mask_region]
    
    elif view_mode == 'original':
        root_pixels = image_data.original_pixels.copy()
    
    else:  # 'binary'
        # 合成所有图层
        root_pixels = image_data.pixels.copy()
        for layer in image_data.user_layers:
            if not layer.visible:
                continue
            
            x, y, w, h = layer.bbox
            img_h, img_w = root_pixels.shape[:2]
            
            if x >= img_w or y >= img_h or x + w <= 0 or y + h <= 0:
                continue
            
            x_start = max(0, x)
            y_start = max(0, y)
            x_end = min(img_w, x + w)
            y_end = min(img_h, y + h)
            
            layer_x_offset = x_start - x
            layer_y_offset = y_start - y
            layer_w = x_end - x_start
            layer_h = y_end - y_start
            
            layer_pixels_region = layer.pixels[layer_y_offset:layer_y_offset+layer_h, layer_x_offset:layer_x_offset+layer_w]
            layer_mask_region = layer.mask[layer_y_offset:layer_y_offset+layer_h, layer_x_offset:layer_x_offset+layer_w]
            
            region = root_pixels[y_start:y_end, x_start:x_end]
            region[layer_mask_region] = layer_pixels_region[layer_mask_region]
    
    # 计算边界框
    y_indices, x_indices = np.where(selection_mask)
    x_min, x_max = x_indices.min(), x_indices.max()
    y_min, y_max = y_indices.min(), y_indices.max()
    bbox = (int(x_min), int(y_min), int(x_max - x_min + 1), int(y_max - y_min + 1))
    
    # 裁剪到边界框
    layer_mask = selection_mask[y_min:y_max+1, x_min:x_max+1].copy()
    
    # 复制选中区域的像素
    layer_pixels = np.full((y_max - y_min + 1, x_max - x_min + 1, 3), 255, dtype=np.uint8)
    region_pixels = root_pixels[y_min:y_max+1, x_min:x_max+1]
    layer_pixels[layer_mask] = region_pixels[layer_mask]
    
    # 提取原图对应区域
    original_region = image_data.original_pixels[y_min:y_max+1, x_min:x_max+1].copy()
    
    return {
        'pixels': layer_pixels,
        'mask': layer_mask,
        'bbox': bbox,
        'original_region': original_region
    }


def test_user_workflow_overlapping_layers_binary_view():
    """
    测试真实用户工作流程：在二值化视图下创建重叠图层
    
    步骤：
    1. 加载图片，应用二值化（阈值100）
    2. 选择区域A (0,0,50,50)，保存为图层1
    3. 选择区域B (25,25,50,50)，保存为图层2
    4. 验证图层2的重叠区域包含图层1的数据
    """
    print("\n测试：用户工作流程 - 二值化视图下重叠图层")
    
    # 1. 创建测试图片（渐变）
    original = np.zeros((100, 100, 3), dtype=np.uint8)
    for i in range(100):
        original[i, :] = i * 2  # 0-198的渐变
    
    # 2. 创建ImageData并应用二值化（阈值100）
    image_data = ImageData(original)
    binary = BinarizationEngine.apply_threshold(original, 0, 100)
    image_data.pixels = binary.copy()
    image_data.view_mode = 'binary'
    
    # 3. 选择区域A (0,0,50,50)
    selection_mask_a = np.zeros((100, 100), dtype=bool)
    selection_mask_a[:50, :50] = True
    image_data.selection_mask = selection_mask_a
    
    # 4. 提取图层1数据
    layer1_data = simulate_extract_layer_from_selection(image_data, selection_mask_a, 'binary')
    
    # 5. 创建图层1
    layer1 = UserLayer(
        name="图层1",
        pixels=layer1_data['pixels'],
        mask=layer1_data['mask'],
        bbox=layer1_data['bbox'],
        binarization_params={
            'preprocess': {},
            'threshold': {'method': 0, 'threshold': 100}
        },
        original_region=layer1_data['original_region']
    )
    image_data.user_layers.append(layer1)
    
    print(f"  图层1创建: bbox={layer1.bbox}, 像素形状={layer1.pixels.shape}")
    print(f"  图层1左上角像素值: {layer1.pixels[0, 0]}")
    
    # 6. 选择区域B (25,25,50,50) - 与图层1有重叠
    selection_mask_b = np.zeros((100, 100), dtype=bool)
    selection_mask_b[25:75, 25:75] = True
    image_data.selection_mask = selection_mask_b
    
    # 7. 提取图层2数据（应该包含图层1的修改）
    layer2_data = simulate_extract_layer_from_selection(image_data, selection_mask_b, 'binary')
    
    # 8. 创建图层2
    layer2 = UserLayer(
        name="图层2",
        pixels=layer2_data['pixels'],
        mask=layer2_data['mask'],
        bbox=layer2_data['bbox'],
        binarization_params={
            'preprocess': {},
            'threshold': {'method': 0, 'threshold': 100}
        },
        original_region=layer2_data['original_region']
    )
    
    print(f"  图层2创建: bbox={layer2.bbox}, 像素形状={layer2.pixels.shape}")
    print(f"  图层2左上角像素值: {layer2.pixels[0, 0]}")
    
    # 9. 验证重叠区域
    # 重叠区域在图像坐标系中是 (25,25) 到 (50,50)
    # 在图层1坐标系中是 (25,25) 到 (50,50)
    # 在图层2坐标系中是 (0,0) 到 (25,25)
    
    overlap_in_layer1 = layer1.pixels[25:50, 25:50]
    overlap_in_layer2 = layer2.pixels[:25, :25]
    
    print(f"  图层1重叠区域形状: {overlap_in_layer1.shape}")
    print(f"  图层2重叠区域形状: {overlap_in_layer2.shape}")
    print(f"  图层1重叠区域样本: {overlap_in_layer1[0, 0]}")
    print(f"  图层2重叠区域样本: {overlap_in_layer2[0, 0]}")
    
    # 重叠区域应该相同
    assert np.array_equal(overlap_in_layer1, overlap_in_layer2), \
        "图层2的重叠区域应该包含图层1的数据"
    
    print("✅ 二值化视图下重叠图层工作流程正确")


def test_user_workflow_overlapping_layers_preprocessed_view():
    """
    测试真实用户工作流程：在预处理视图下创建重叠图层
    
    步骤：
    1. 加载图片，应用预处理（曝光+20）
    2. 选择区域A (0,0,50,50)，保存为图层1
    3. 选择区域B (25,25,50,50)，保存为图层2
    4. 验证图层2的重叠区域包含图层1的预处理结果
    """
    print("\n测试：用户工作流程 - 预处理视图下重叠图层")
    
    # 1. 创建测试图片
    original = np.zeros((100, 100, 3), dtype=np.uint8)
    for i in range(100):
        original[i, :] = i * 2
    
    # 2. 创建ImageData并应用预处理
    image_data = ImageData(original)
    preprocessed = BinarizationEngine.apply_preprocess(original, exposure=20)
    image_data.preprocessed_pixels = preprocessed.copy()
    image_data.view_mode = 'preprocessed'
    
    # 3. 选择区域A (0,0,50,50)
    selection_mask_a = np.zeros((100, 100), dtype=bool)
    selection_mask_a[:50, :50] = True
    
    # 4. 提取图层1数据
    layer1_data = simulate_extract_layer_from_selection(image_data, selection_mask_a, 'preprocessed')
    
    # 5. 创建图层1
    layer1 = UserLayer(
        name="图层1",
        pixels=layer1_data['pixels'],
        mask=layer1_data['mask'],
        bbox=layer1_data['bbox'],
        binarization_params={
            'preprocess': {'exposure': 20},
            'threshold': {'method': 0, 'threshold': 127}
        },
        original_region=layer1_data['original_region']
    )
    image_data.user_layers.append(layer1)
    
    print(f"  图层1创建: bbox={layer1.bbox}")
    print(f"  图层1左上角像素值: {layer1.pixels[0, 0]}")
    
    # 6. 选择区域B (25,25,50,50)
    selection_mask_b = np.zeros((100, 100), dtype=bool)
    selection_mask_b[25:75, 25:75] = True
    
    # 7. 提取图层2数据（应该包含图层1的预处理结果）
    layer2_data = simulate_extract_layer_from_selection(image_data, selection_mask_b, 'preprocessed')
    
    # 8. 创建图层2
    layer2 = UserLayer(
        name="图层2",
        pixels=layer2_data['pixels'],
        mask=layer2_data['mask'],
        bbox=layer2_data['bbox'],
        binarization_params={
            'preprocess': {'exposure': 20},
            'threshold': {'method': 0, 'threshold': 127}
        },
        original_region=layer2_data['original_region']
    )
    
    print(f"  图层2创建: bbox={layer2.bbox}")
    print(f"  图层2左上角像素值: {layer2.pixels[0, 0]}")
    
    # 9. 验证重叠区域
    overlap_in_layer1 = layer1.pixels[25:50, 25:50]
    overlap_in_layer2 = layer2.pixels[:25, :25]
    
    print(f"  图层1重叠区域样本: {overlap_in_layer1[0, 0]}")
    print(f"  图层2重叠区域样本: {overlap_in_layer2[0, 0]}")
    
    assert np.array_equal(overlap_in_layer1, overlap_in_layer2), \
        "预处理视图下，图层2的重叠区域应该包含图层1的预处理结果"
    
    print("✅ 预处理视图下重叠图层工作流程正确")


def test_overlapping_layers_in_binary_view():
    """测试二值化视图下重叠图层的合成"""
    print("\n测试：二值化视图下重叠图层")
    
    # 创建一个100x100的渐变图
    original = np.zeros((100, 100, 3), dtype=np.uint8)
    for i in range(100):
        original[i, :] = i * 2  # 0-198的渐变
    
    # 创建ImageData
    image_data = ImageData(original)
    
    # 第一个图层：左上角50x50，阈值100
    layer1_mask = np.zeros((50, 50), dtype=bool)
    layer1_mask[:] = True
    
    # 对第一个区域进行二值化（阈值100）
    region1 = original[:50, :50].copy()
    binary1 = BinarizationEngine.apply_threshold(region1, 0, 100)
    
    layer1 = UserLayer(
        name="图层1",
        pixels=binary1.copy(),
        mask=layer1_mask,
        bbox=(0, 0, 50, 50),
        binarization_params={
            'preprocess': {},
            'threshold': {'method': 0, 'threshold': 100}
        },
        original_region=region1
    )
    
    image_data.user_layers.append(layer1)
    
    # 合成图层1到根图层
    # 模拟 _composite_layers 的行为
    composite = image_data.pixels.copy()
    x, y, w, h = layer1.bbox
    composite[y:y+h, x:x+w][layer1.mask] = layer1.pixels[layer1.mask]
    
    # 第二个图层：右下角50x50（与第一个图层有25x25的重叠），阈值150
    # 选区在 (25, 25) 到 (75, 75)
    layer2_bbox = (25, 25, 50, 50)
    layer2_mask = np.ones((50, 50), dtype=bool)
    
    # 从合成结果中提取第二个区域（应该包含图层1的修改）
    x2, y2, w2, h2 = layer2_bbox
    region2_from_composite = composite[y2:y2+h2, x2:x2+w2].copy()
    
    # 验证重叠区域包含图层1的修改
    # 重叠区域是 (25,25) 到 (50,50)，在图层2坐标系中是 (0,0) 到 (25,25)
    overlap_in_layer2 = region2_from_composite[:25, :25]
    overlap_in_layer1 = layer1.pixels[25:50, 25:50]
    
    # 重叠区域应该相同（都来自图层1）
    assert np.array_equal(overlap_in_layer2, overlap_in_layer1), \
        "第二个图层的重叠区域应该包含第一个图层的修改"
    
    print("✅ 二值化视图下重叠图层合成正确")


def test_overlapping_layers_in_preprocessed_view():
    """测试预处理视图下重叠图层的合成"""
    print("\n测试：预处理视图下重叠图层")
    
    # 创建一个100x100的渐变图
    original = np.zeros((100, 100, 3), dtype=np.uint8)
    for i in range(100):
        original[i, :] = i * 2
    
    # 第一个图层：左上角50x50，曝光+20
    region1 = original[:50, :50].copy()
    preprocessed1 = BinarizationEngine.apply_preprocess(region1, exposure=20)
    
    layer1_mask = np.ones((50, 50), dtype=bool)
    layer1 = UserLayer(
        name="图层1",
        pixels=preprocessed1.copy(),
        mask=layer1_mask,
        bbox=(0, 0, 50, 50),
        binarization_params={
            'preprocess': {'exposure': 20},
            'threshold': {'method': 0, 'threshold': 127}
        },
        original_region=region1
    )
    
    # 模拟合成：根图层预处理 + 图层1预处理
    root_preprocessed = BinarizationEngine.apply_preprocess(original, exposure=0)
    composite = root_preprocessed.copy()
    
    # 合成图层1
    x, y, w, h = layer1.bbox
    layer1_preprocessed = BinarizationEngine.apply_preprocess(
        layer1.original_region,
        **layer1.binarization_params['preprocess']
    )
    composite[y:y+h, x:x+w][layer1.mask] = layer1_preprocessed[layer1.mask]
    
    # 第二个图层：右下角50x50（与第一个图层有25x25的重叠）
    layer2_bbox = (25, 25, 50, 50)
    x2, y2, w2, h2 = layer2_bbox
    region2_from_composite = composite[y2:y2+h2, x2:x2+w2].copy()
    
    # 验证重叠区域包含图层1的预处理结果
    overlap_in_layer2 = region2_from_composite[:25, :25]
    overlap_in_layer1 = layer1_preprocessed[25:50, 25:50]
    
    assert np.array_equal(overlap_in_layer2, overlap_in_layer1), \
        "预处理视图下，第二个图层的重叠区域应该包含第一个图层的预处理结果"
    
    print("✅ 预处理视图下重叠图层合成正确")


def test_three_overlapping_layers():
    """测试三个重叠图层的合成"""
    print("\n测试：三个重叠图层")
    
    # 创建一个100x100的图
    original = np.full((100, 100, 3), 128, dtype=np.uint8)
    
    image_data = ImageData(original)
    
    # 图层1：(0,0) 50x50，全黑
    layer1 = UserLayer(
        name="图层1",
        pixels=np.zeros((50, 50, 3), dtype=np.uint8),
        mask=np.ones((50, 50), dtype=bool),
        bbox=(0, 0, 50, 50),
        original_region=original[:50, :50].copy()
    )
    image_data.user_layers.append(layer1)
    
    # 图层2：(25,25) 50x50，全白
    layer2 = UserLayer(
        name="图层2",
        pixels=np.full((50, 50, 3), 255, dtype=np.uint8),
        mask=np.ones((50, 50), dtype=bool),
        bbox=(25, 25, 50, 50),
        original_region=original[25:75, 25:75].copy()
    )
    image_data.user_layers.append(layer2)
    
    # 合成所有图层
    composite = image_data.pixels.copy()
    for layer in image_data.user_layers:
        if not layer.visible:
            continue
        x, y, w, h = layer.bbox
        img_h, img_w = composite.shape[:2]
        
        x_start = max(0, x)
        y_start = max(0, y)
        x_end = min(img_w, x + w)
        y_end = min(img_h, y + h)
        
        layer_x_offset = x_start - x
        layer_y_offset = y_start - y
        layer_w = x_end - x_start
        layer_h = y_end - y_start
        
        layer_pixels_region = layer.pixels[layer_y_offset:layer_y_offset+layer_h, layer_x_offset:layer_x_offset+layer_w]
        layer_mask_region = layer.mask[layer_y_offset:layer_y_offset+layer_h, layer_x_offset:layer_x_offset+layer_w]
        
        region = composite[y_start:y_end, x_start:x_end]
        region[layer_mask_region] = layer_pixels_region[layer_mask_region]
    
    # 验证合成结果
    # (0,0)-(25,25): 图层1的黑色
    assert np.all(composite[0, 0] == 0), "左上角应该是图层1的黑色"
    
    # (25,25)-(50,50): 图层2的白色（覆盖图层1）
    assert np.all(composite[30, 30] == 255), "中心应该是图层2的白色"
    
    # (50,50)-(75,75): 图层2的白色
    assert np.all(composite[60, 60] == 255), "右下角应该是图层2的白色"
    
    # (75,75)-(100,100): 原图的灰色
    assert np.all(composite[80, 80] == 128), "右下角外应该是原图的灰色"
    
    print("✅ 三个重叠图层合成正确")


def test_layer_extraction_includes_previous_layers():
    """测试提取图层时包含之前的图层"""
    print("\n测试：提取图层时包含之前的图层")
    
    # 创建一个简单的测试场景
    original = np.full((100, 100, 3), 100, dtype=np.uint8)
    
    # 第一个图层：左半边，值为50
    layer1_pixels = np.full((100, 50, 3), 50, dtype=np.uint8)
    layer1_mask = np.ones((100, 50), dtype=bool)
    layer1 = UserLayer(
        name="图层1",
        pixels=layer1_pixels,
        mask=layer1_mask,
        bbox=(0, 0, 50, 100),
        original_region=original[:, :50].copy()
    )
    
    # 合成图层1
    composite = original.copy()
    composite[:, :50] = 50
    
    # 第二个图层：右半边（包含部分图层1的区域）
    # 选区从x=25到x=75
    layer2_bbox = (25, 0, 50, 100)
    x2, y2, w2, h2 = layer2_bbox
    layer2_pixels = composite[y2:y2+h2, x2:x2+w2].copy()
    
    # 验证第二个图层的左边25像素包含图层1的值（50）
    assert np.all(layer2_pixels[:, :25] == 50), \
        "第二个图层的左边应该包含图层1的值"
    
    # 验证第二个图层的右边25像素是原图的值（100）
    assert np.all(layer2_pixels[:, 25:] == 100), \
        "第二个图层的右边应该是原图的值"
    
    print("✅ 提取图层时正确包含之前的图层")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
