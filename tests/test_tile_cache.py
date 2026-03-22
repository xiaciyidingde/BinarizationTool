"""
分块缓存测试

包括单元测试和基于属性的测试（Hypothesis）
"""

import numpy as np
import pytest
from hypothesis import given, strategies as st, assume, settings
from PySide6.QtWidgets import QApplication
from src.models.tile_cache import TileCache


# 确保 QApplication 实例存在
@pytest.fixture(scope="module")
def qapp():
    """创建 QApplication 实例"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# ============================================================================
# 单元测试
# ============================================================================

def test_tile_cache_initialization(qapp):
    """测试分块缓存初始化"""
    cache = TileCache(tile_size=256, max_tiles=100)
    
    assert cache.tile_size == 256
    assert cache.max_tiles == 100
    assert cache.pixels is None
    assert len(cache.cache) == 0


def test_set_image(qapp):
    """测试设置图片数据"""
    cache = TileCache()
    pixels = np.zeros((512, 512), dtype=np.uint8)
    
    cache.set_image(pixels)
    
    assert cache.image_width == 512
    assert cache.image_height == 512
    assert np.array_equal(cache.pixels, pixels)


def test_set_image_clears_cache(qapp):
    """测试设置新图片会清空缓存"""
    cache = TileCache()
    pixels1 = np.zeros((256, 256), dtype=np.uint8)
    cache.set_image(pixels1)
    
    # 生成一些缓存
    cache.get_tile(0, 0)
    assert len(cache.cache) > 0
    
    # 设置新图片
    pixels2 = np.ones((256, 256), dtype=np.uint8)
    cache.set_image(pixels2)
    
    # 缓存应该被清空
    assert len(cache.cache) == 0


def test_update_image_preserves_cache(qapp):
    """测试更新图片不清空缓存"""
    cache = TileCache()
    pixels1 = np.zeros((256, 256), dtype=np.uint8)
    cache.set_image(pixels1)
    
    # 生成一些缓存
    cache.get_tile(0, 0)
    cache_size = len(cache.cache)
    
    # 更新图片
    pixels2 = np.ones((256, 256), dtype=np.uint8)
    cache.update_image(pixels2)
    
    # 缓存应该保留
    assert len(cache.cache) == cache_size


def test_set_scale_clears_cache(qapp):
    """测试改变缩放级别会清空缓存"""
    cache = TileCache()
    pixels = np.zeros((256, 256), dtype=np.uint8)
    cache.set_image(pixels)
    cache.set_scale(1.0)
    
    # 生成一些缓存
    cache.get_tile(0, 0)
    assert len(cache.cache) > 0
    
    # 改变缩放级别
    cache.set_scale(2.0)
    
    # 缓存应该被清空
    assert len(cache.cache) == 0


def test_get_tile_basic(qapp):
    """测试获取基本块"""
    cache = TileCache(tile_size=256)
    pixels = np.random.randint(0, 256, (512, 512), dtype=np.uint8)
    cache.set_image(pixels)
    cache.set_scale(1.0)
    
    # 获取第一个块
    pixmap = cache.get_tile(0, 0)
    
    assert pixmap is not None
    assert pixmap.width() == 256
    assert pixmap.height() == 256


def test_get_tile_edge(qapp):
    """测试获取边缘块（不完整的块）"""
    cache = TileCache(tile_size=256)
    # 创建 300x300 的图片，边缘块只有 44x44
    pixels = np.random.randint(0, 256, (300, 300), dtype=np.uint8)
    cache.set_image(pixels)
    cache.set_scale(1.0)
    
    # 获取边缘块 (1, 1)
    pixmap = cache.get_tile(1, 1)
    
    assert pixmap is not None
    # 边缘块应该是 44x44
    assert pixmap.width() == 44
    assert pixmap.height() == 44


def test_get_tile_out_of_bounds(qapp):
    """测试获取超出范围的块"""
    cache = TileCache(tile_size=256)
    pixels = np.zeros((256, 256), dtype=np.uint8)
    cache.set_image(pixels)
    cache.set_scale(1.0)
    
    # 获取超出范围的块
    pixmap = cache.get_tile(10, 10)
    
    assert pixmap is None


def test_tile_cache_lru(qapp):
    """测试 LRU 缓存淘汰"""
    cache = TileCache(tile_size=256, max_tiles=3)
    pixels = np.zeros((1024, 1024), dtype=np.uint8)
    cache.set_image(pixels)
    cache.set_scale(1.0)
    
    # 生成 4 个块
    cache.get_tile(0, 0)
    cache.get_tile(0, 1)
    cache.get_tile(1, 0)
    cache.get_tile(1, 1)  # 这个会触发 LRU 淘汰
    
    # 应该只有 3 个块
    assert len(cache.cache) == 3
    
    # 第一个块 (0, 0) 应该被淘汰
    scale_key = cache._get_scale_key()
    assert (scale_key, 0, 0) not in cache.cache


def test_invalidate_region(qapp):
    """测试区域失效"""
    cache = TileCache(tile_size=256)
    pixels = np.zeros((512, 512), dtype=np.uint8)
    cache.set_image(pixels)
    cache.set_scale(1.0)
    
    # 生成所有 4 个块
    cache.get_tile(0, 0)
    cache.get_tile(0, 1)
    cache.get_tile(1, 0)
    cache.get_tile(1, 1)
    
    assert len(cache.cache) == 4
    
    # 使左上角区域失效
    cache.invalidate_region(0, 0, 256, 256)
    
    # 只有 (0, 0) 块应该被移除
    assert len(cache.cache) == 3
    scale_key = cache._get_scale_key()
    assert (scale_key, 0, 0) not in cache.cache


def test_get_tiles_in_viewport(qapp):
    """测试获取视口内的块"""
    cache = TileCache(tile_size=256)
    pixels = np.zeros((512, 512), dtype=np.uint8)
    cache.set_image(pixels)
    cache.set_scale(1.0)
    
    # 获取整个视口的块
    tiles = cache.get_tiles_in_viewport(0, 0, 512, 512)
    
    # 应该有 4 个块 (2x2)
    assert len(tiles) == 4


def test_tile_cache_with_selection(qapp):
    """测试带选区的分块缓存"""
    cache = TileCache(tile_size=256)
    pixels = np.zeros((512, 512), dtype=np.uint8)
    selection = np.zeros((512, 512), dtype=bool)
    selection[100:200, 100:200] = True
    
    cache.set_image(pixels, selection)
    cache.set_scale(1.0)
    
    # 获取包含选区的块
    pixmap = cache.get_tile(0, 0)
    
    assert pixmap is not None


def test_tile_cache_color_image(qapp):
    """测试彩色图片的分块缓存"""
    cache = TileCache(tile_size=256)
    # 创建 RGB 图片
    pixels = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
    cache.set_image(pixels)
    cache.set_scale(1.0)
    
    pixmap = cache.get_tile(0, 0)
    
    assert pixmap is not None
    assert pixmap.width() == 256
    assert pixmap.height() == 256


# ============================================================================
# Hypothesis 属性测试
# ============================================================================

@given(
    tile_size=st.integers(min_value=64, max_value=512),
    max_tiles=st.integers(min_value=1, max_value=200)
)
def test_property_cache_respects_max_tiles(tile_size, max_tiles):
    """
    属性：缓存大小永远不超过 max_tiles
    """
    cache = TileCache(tile_size=tile_size, max_tiles=max_tiles)
    pixels = np.zeros((1024, 1024), dtype=np.uint8)
    cache.set_image(pixels)
    cache.set_scale(1.0)
    
    # 尝试生成很多块
    num_tiles = (1024 // tile_size) + 1
    for y in range(num_tiles):
        for x in range(num_tiles):
            cache.get_tile(x, y)
    
    # 缓存大小不应超过 max_tiles
    assert len(cache.cache) <= max_tiles


@given(
    width=st.integers(min_value=100, max_value=2000),
    height=st.integers(min_value=100, max_value=2000),
    scale=st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False)
)
def test_property_set_image_updates_dimensions(width, height, scale):
    """
    属性：set_image 正确更新图片尺寸
    
    注意：set_scale 有 0.001 的容差，小于此值的变化会被忽略（性能优化）
    """
    cache = TileCache()
    pixels = np.zeros((height, width), dtype=np.uint8)
    cache.set_image(pixels)
    
    initial_scale = cache.current_scale  # 默认是 1.0
    cache.set_scale(scale)
    
    assert cache.image_width == width
    assert cache.image_height == height
    
    # set_scale 只在差异 > 0.001 时更新（这是有意的设计）
    if abs(scale - initial_scale) > 0.001:
        assert cache.current_scale == scale
    else:
        # 差异太小，保持原值
        assert cache.current_scale == initial_scale


@given(
    tile_size=st.integers(min_value=64, max_value=512),
    image_size=st.integers(min_value=100, max_value=1000),
    tile_x=st.integers(min_value=0, max_value=10),
    tile_y=st.integers(min_value=0, max_value=10)
)
def test_property_tile_within_bounds_or_none(tile_size, image_size, tile_x, tile_y):
    """
    属性：get_tile 要么返回有效的 pixmap，要么返回 None
    """
    cache = TileCache(tile_size=tile_size)
    pixels = np.zeros((image_size, image_size), dtype=np.uint8)
    cache.set_image(pixels)
    cache.set_scale(1.0)
    
    pixmap = cache.get_tile(tile_x, tile_y)
    
    # 计算块是否在范围内
    pixel_x = tile_x * tile_size
    pixel_y = tile_y * tile_size
    in_bounds = pixel_x < image_size and pixel_y < image_size
    
    if in_bounds:
        assert pixmap is not None
    else:
        assert pixmap is None


@given(
    scale1=st.floats(min_value=0.5, max_value=5.0),
    scale2=st.floats(min_value=0.5, max_value=5.0)
)
def test_property_scale_change_clears_cache(scale1, scale2):
    """
    属性：改变缩放级别会清空缓存（如果缩放级别确实改变）
    """
    assume(abs(scale1 - scale2) > 0.001)  # 确保缩放级别确实改变
    
    cache = TileCache()
    pixels = np.zeros((512, 512), dtype=np.uint8)
    cache.set_image(pixels)
    cache.set_scale(scale1)
    
    # 生成一些缓存
    cache.get_tile(0, 0)
    assert len(cache.cache) > 0
    
    # 改变缩放级别
    cache.set_scale(scale2)
    
    # 缓存应该被清空
    assert len(cache.cache) == 0


@given(
    x=st.integers(min_value=0, max_value=500),
    y=st.integers(min_value=0, max_value=500),
    width=st.integers(min_value=1, max_value=200),
    height=st.integers(min_value=1, max_value=200)
)
def test_property_invalidate_region_removes_affected_tiles(x, y, width, height):
    """
    属性：invalidate_region 移除受影响的块
    """
    cache = TileCache(tile_size=256)
    pixels = np.zeros((1024, 1024), dtype=np.uint8)
    cache.set_image(pixels)
    cache.set_scale(1.0)
    
    # 生成所有块
    for ty in range(4):
        for tx in range(4):
            cache.get_tile(tx, ty)
    
    initial_count = len(cache.cache)
    
    # 使区域失效
    cache.invalidate_region(x, y, width, height)
    
    # 缓存大小应该减少或保持不变
    assert len(cache.cache) <= initial_count


@given(
    tile_size=st.integers(min_value=64, max_value=512),
    image_size=st.integers(min_value=200, max_value=1000)
)
def test_property_cache_hit_returns_same_pixmap(tile_size, image_size):
    """
    属性：多次获取同一个块返回相同的 pixmap（缓存命中）
    """
    cache = TileCache(tile_size=tile_size, max_tiles=100)
    pixels = np.random.randint(0, 256, (image_size, image_size), dtype=np.uint8)
    cache.set_image(pixels)
    cache.set_scale(1.0)
    
    # 第一次获取
    pixmap1 = cache.get_tile(0, 0)
    
    # 第二次获取
    pixmap2 = cache.get_tile(0, 0)
    
    # 应该是同一个对象
    assert pixmap1 is pixmap2


@given(
    view_x=st.floats(min_value=-500, max_value=500),
    view_y=st.floats(min_value=-500, max_value=500),
    view_width=st.integers(min_value=100, max_value=1000),
    view_height=st.integers(min_value=100, max_value=1000)
)
def test_property_viewport_tiles_are_valid(view_x, view_y, view_width, view_height):
    """
    属性：get_tiles_in_viewport 返回的所有块都是有效的
    """
    cache = TileCache(tile_size=256)
    pixels = np.zeros((1024, 1024), dtype=np.uint8)
    cache.set_image(pixels)
    cache.set_scale(1.0)
    
    tiles = cache.get_tiles_in_viewport(view_x, view_y, view_width, view_height)
    
    # 所有返回的块都应该有有效的 pixmap
    for tile_x, tile_y, draw_x, draw_y, width, height, pixmap in tiles:
        assert pixmap is not None
        assert width > 0
        assert height > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
