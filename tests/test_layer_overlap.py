"""
图层重叠计算辅助函数的单元测试

覆盖 get_layer_overlap 的边界情况：完全在图像内、负偏移越界、
右/下边界溢出、完全在图像外。
"""

from src.views.main_window import get_layer_overlap


class TestGetLayerOverlap:
    """get_layer_overlap 测试类"""

    def test_fully_inside(self):
        """图层完全在图像内：重叠区等于 bbox 本身"""
        overlap = get_layer_overlap((10, 20, 30, 40), 100, 100)

        assert overlap is not None
        assert (overlap.x_start, overlap.y_start) == (10, 20)
        assert (overlap.x_end, overlap.y_end) == (40, 60)
        assert (overlap.layer_x_offset, overlap.layer_y_offset) == (0, 0)
        assert (overlap.layer_w, overlap.layer_h) == (30, 40)

    def test_negative_offset(self):
        """图层左上角越出图像左上边界：图像侧被裁剪，图层侧偏移为正"""
        overlap = get_layer_overlap((-5, -5, 20, 20), 100, 100)

        assert overlap is not None
        assert (overlap.x_start, overlap.y_start) == (0, 0)
        assert (overlap.x_end, overlap.y_end) == (15, 15)
        assert (overlap.layer_x_offset, overlap.layer_y_offset) == (5, 5)
        assert (overlap.layer_w, overlap.layer_h) == (15, 15)

    def test_overflow_right_bottom(self):
        """图层右下角越出图像右下边界：重叠区被裁剪到图像边缘"""
        overlap = get_layer_overlap((90, 90, 30, 30), 100, 100)

        assert overlap is not None
        assert (overlap.x_end, overlap.y_end) == (100, 100)
        assert (overlap.layer_x_offset, overlap.layer_y_offset) == (0, 0)
        assert (overlap.layer_w, overlap.layer_h) == (10, 10)

    def test_zero_size_bbox(self):
        """零尺寸 bbox：返回零面积重叠（调用方按空切片处理，与重构前语义一致）"""
        overlap = get_layer_overlap((10, 10, 0, 0), 100, 100)

        assert overlap is not None
        assert (overlap.layer_w, overlap.layer_h) == (0, 0)

    def test_fully_outside(self):
        """图层完全在图像外：返回 None"""
        # 右下方完全在外
        assert get_layer_overlap((150, 150, 10, 10), 100, 100) is None
        # 左上方完全在外（x + w <= 0）
        assert get_layer_overlap((-20, 0, 10, 10), 100, 100) is None
        # 上方完全在外（y + h <= 0）
        assert get_layer_overlap((0, -20, 10, 10), 100, 100) is None

    def test_touching_edge_only(self):
        """图层边缘恰好与图像边缘相接（无实际重叠面积）：返回 None"""
        # x 从 100 开始（图像宽 100）
        assert get_layer_overlap((100, 0, 10, 10), 100, 100) is None
        # x + w 恰好为 0
        assert get_layer_overlap((-10, 0, 10, 10), 100, 100) is None

    def test_bbox_larger_than_image(self):
        """bbox 比图像还大：重叠区为整个图像"""
        overlap = get_layer_overlap((0, 0, 500, 500), 100, 200)

        assert overlap is not None
        assert (overlap.x_start, overlap.y_start) == (0, 0)
        assert (overlap.x_end, overlap.y_end) == (200, 100)
        assert (overlap.layer_w, overlap.layer_h) == (200, 100)

    def test_consistency_of_offsets(self):
        """图层侧偏移与图像侧起点满足恒等关系：x_start - layer_x_offset == bbox.x"""
        bbox = (-7, 3, 50, 50)
        overlap = get_layer_overlap(bbox, 100, 100)

        assert overlap is not None
        assert overlap.x_start - overlap.layer_x_offset == bbox[0]
        assert overlap.y_start - overlap.layer_y_offset == bbox[1]
