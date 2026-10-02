"""
二值化方法/边缘模式常量的契约测试

这些编号会持久化到图层参数与配置文件中，数值一旦发布不可变更。
此测试用于锁定契约，防止无意中改动编号导致旧数据无法解析。
"""

from src.utils.binarization_engine import EdgeDetectionMode, ThresholdMethod


class TestThresholdMethodContract:
    """ThresholdMethod 编号契约"""

    def test_values_are_locked(self):
        """编号与发布版本一致：0-9"""
        assert ThresholdMethod.FIXED == 0
        assert ThresholdMethod.ADAPTIVE == 1
        assert ThresholdMethod.OTSU == 2
        assert ThresholdMethod.SAUVOLA == 3
        assert ThresholdMethod.WOLF == 4
        assert ThresholdMethod.NICK == 5
        assert ThresholdMethod.BERNSEN == 6
        assert ThresholdMethod.DITHER_FLOYD_STEINBERG == 7
        assert ThresholdMethod.DITHER_ORDERED == 8
        assert ThresholdMethod.DITHER_ATKINSON == 9

    def test_all_values_unique(self):
        """所有编号唯一"""
        values = [v for k, v in vars(ThresholdMethod).items() if not k.startswith("_") and isinstance(v, int)]
        assert len(values) == len(set(values)) == 10


class TestEdgeDetectionModeContract:
    """EdgeDetectionMode 编号契约"""

    def test_values_are_locked(self):
        """编号与发布版本一致：0-3"""
        assert EdgeDetectionMode.OFF == 0
        assert EdgeDetectionMode.CANNY == 1
        assert EdgeDetectionMode.ENHANCE == 2
        assert EdgeDetectionMode.CONTOUR == 3
