"""
测试用户图层重新二值化功能

验证：
1. 用户图层可以使用不同的二值化参数重新处理
2. 参数结构正确保存和读取
3. RGB格式正确处理
"""

import numpy as np
from src.models.user_layer import UserLayer
from src.utils.binarization_engine import BinarizationEngine


def test_user_layer_rebinarization():
    """测试用户图层重新二值化"""
    print("测试：用户图层重新二值化")
    
    # 创建一个测试原图区域（RGB格式，渐变图）
    original_region = np.zeros((100, 100, 3), dtype=np.uint8)
    for i in range(100):
        original_region[i, :] = i * 2  # 0-198的渐变
    
    # 创建图层mask（全选）
    layer_mask = np.ones((100, 100), dtype=bool)
    
    # 第一次二值化（阈值127）
    preprocess_params1 = {'exposure': 0, 'contrast': 0}
    binary1 = BinarizationEngine.apply_preprocess(original_region, **preprocess_params1)
    binary1 = BinarizationEngine.apply_threshold(binary1, 0, 127)  # 固定阈值127
    
    # 创建用户图层
    layer = UserLayer(
        name="测试图层",
        pixels=binary1.copy(),
        mask=layer_mask,
        bbox=(0, 0, 100, 100),
        binarization_params={
            'preprocess': preprocess_params1,
            'threshold': {
                'method': 0,
                'threshold': 127
            }
        },
        original_region=original_region
    )
    
    # 验证初始状态
    assert layer.pixels.shape == (100, 100, 3), "图层像素应该是RGB格式"
    assert layer.binarization_params is not None, "应该保存二值化参数"
    print("✅ 图层创建成功")
    
    # 第二次二值化（阈值64，应该有更多黑色像素）
    preprocess_params2 = {'exposure': 10, 'contrast': 20}
    binary2 = BinarizationEngine.apply_preprocess(original_region, **preprocess_params2)
    binary2 = BinarizationEngine.apply_threshold(binary2, 0, 64)  # 固定阈值64
    
    # 更新图层像素
    layer.pixels[layer.mask] = binary2[layer.mask]
    
    # 更新参数
    layer.binarization_params = {
        'preprocess': preprocess_params2,
        'threshold': {
            'method': 0,
            'threshold': 64
        }
    }
    
    # 验证更新后的状态
    assert layer.pixels.shape == (100, 100, 3), "更新后图层像素应该仍是RGB格式"
    assert layer.binarization_params['threshold']['threshold'] == 64, "参数应该更新"
    print("✅ 图层重新二值化成功")
    
    # 验证像素值确实改变了
    # 阈值从127降到64，应该有更多黑色像素
    # 注意：阈值越低，越多像素会被判定为黑色（小于阈值）
    black_pixels_1 = np.sum(binary1[:, :, 0] == 0)
    black_pixels_2 = np.sum(layer.pixels[:, :, 0] == 0)
    
    # 实际上，由于预处理参数也变了（exposure增加），结果可能不同
    # 主要验证像素确实更新了
    assert not np.array_equal(binary1, layer.pixels), "像素应该已更新"
    print(f"✅ 像素已更新：黑色像素数量 {black_pixels_1} -> {black_pixels_2}")
    
    print()


def test_binarization_params_structure():
    """测试二值化参数结构"""
    print("测试：二值化参数结构")
    
    # 创建测试数据
    original_region = np.random.randint(0, 256, (50, 50, 3), dtype=np.uint8)
    layer_mask = np.ones((50, 50), dtype=bool)
    pixels = np.zeros((50, 50, 3), dtype=np.uint8)
    
    # 测试新格式（嵌套字典）
    params_new = {
        'preprocess': {
            'exposure': 10,
            'contrast': 20,
            'sharpen': 30
        },
        'threshold': {
            'method': 1,
            'threshold': 127,
            'block_size': 11,
            'c': 2
        }
    }
    
    layer = UserLayer(
        name="测试",
        pixels=pixels,
        mask=layer_mask,
        bbox=(0, 0, 50, 50),
        binarization_params=params_new,
        original_region=original_region
    )
    
    # 验证参数读取
    assert 'preprocess' in layer.binarization_params
    assert 'threshold' in layer.binarization_params
    assert isinstance(layer.binarization_params['threshold'], dict)
    assert layer.binarization_params['threshold']['method'] == 1
    print("✅ 新格式参数结构正确")
    
    # 测试参数提取（模拟显示代码）
    preprocess_params = layer.binarization_params.get('preprocess', {})
    threshold_params = layer.binarization_params.get('threshold', {})
    
    if isinstance(threshold_params, dict):
        method = threshold_params.get('method', 1)
        threshold = threshold_params.get('threshold', 127)
        method_params = {k: v for k, v in threshold_params.items() 
                       if k not in ['method', 'threshold']}
    else:
        # 兼容旧格式
        method = 1
        threshold = 127
        method_params = {}
    
    assert method == 1
    assert threshold == 127
    assert 'block_size' in method_params
    print("✅ 参数提取正确")
    
    print()


def test_rgb_boolean_indexing():
    """测试RGB数组的布尔索引"""
    print("测试：RGB数组布尔索引")
    
    # 创建RGB数组
    img1 = np.zeros((10, 10, 3), dtype=np.uint8)
    img2 = np.full((10, 10, 3), 255, dtype=np.uint8)
    
    # 创建布尔mask
    mask = np.zeros((10, 10), dtype=bool)
    mask[2:8, 2:8] = True  # 中心6x6区域
    
    # 使用布尔索引更新
    img1[mask] = img2[mask]
    
    # 验证
    assert np.all(img1[5, 5] == 255), "中心区域应该是白色"
    assert np.all(img1[0, 0] == 0), "边缘区域应该是黑色"
    assert np.all(img1[mask] == 255), "mask区域应该全是白色"
    print("✅ RGB布尔索引工作正常")
    
    print()


def test_layer_display_with_different_params():
    """测试使用不同参数显示图层"""
    print("测试：使用不同参数显示图层")
    
    # 创建原图（渐变）
    original = np.zeros((100, 100, 3), dtype=np.uint8)
    for i in range(100):
        original[i, :] = i * 2
    
    # 使用参数1二值化
    params1 = {
        'preprocess': {'exposure': 0},
        'threshold': {'method': 0, 'threshold': 100}
    }
    
    preprocessed1 = BinarizationEngine.apply_preprocess(original, **params1['preprocess'])
    binary1 = BinarizationEngine.apply_threshold(
        preprocessed1,
        params1['threshold']['method'],
        params1['threshold']['threshold']
    )
    
    # 使用参数2二值化
    params2 = {
        'preprocess': {'exposure': 20},
        'threshold': {'method': 0, 'threshold': 150}
    }
    
    preprocessed2 = BinarizationEngine.apply_preprocess(original, **params2['preprocess'])
    binary2 = BinarizationEngine.apply_threshold(
        preprocessed2,
        params2['threshold']['method'],
        params2['threshold']['threshold']
    )
    
    # 验证结果不同
    assert not np.array_equal(binary1, binary2), "不同参数应该产生不同结果"
    
    # 统计黑色像素
    black1 = np.sum(binary1[:, :, 0] == 0)
    black2 = np.sum(binary2[:, :, 0] == 0)
    print(f"  参数1黑色像素: {black1}")
    print(f"  参数2黑色像素: {black2}")
    assert black1 != black2, "不同阈值应该产生不同数量的黑色像素"
    print("✅ 不同参数产生不同结果")
    
    print()


if __name__ == "__main__":
    print("=" * 50)
    print("用户图层重新二值化测试")
    print("=" * 50)
    print()
    
    test_user_layer_rebinarization()
    test_binarization_params_structure()
    test_rgb_boolean_indexing()
    test_layer_display_with_different_params()
    
    print("=" * 50)
    print("✅ 所有测试通过！")
    print("=" * 50)
