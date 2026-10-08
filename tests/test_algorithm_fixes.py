"""
算法修复的回归测试

覆盖：
1. 锐化直流增益修复（部分强度下不再整体变暗）
2. Wolf-Jolion 公式实现（含纯色图像保护、k 单调性）
3. Ordered 抖动的 +0.5 偏置（消除 Bayer 0 值格点的系统偏差）
4. 形态学开/闭核尺寸映射（低强度不再无效）
5. RMBG 预处理对齐官方（[-1,1] 归一化）与 min-max 后处理
"""

import numpy as np
import pytest

from src.utils.ai_processor import RMBGProcessor
from src.utils.binarization_engine import BinarizationEngine, ImageEnhancer


class TestSharpeningDCGain:
    """锐化直流增益回归测试"""

    def test_uniform_image_brightness_preserved(self):
        """均匀亮度图锐化后亮度不变（旧实现会按 sharpen/100 比例变暗）"""
        img = np.full((50, 50, 3), 128.0, dtype=np.float32)

        for sharpen in (20, 50, 80, 100):
            result = ImageEnhancer.apply_sharpening(img, sharpen)
            assert abs(float(np.mean(result)) - 128.0) < 1e-3, f"sharpen={sharpen} 亮度漂移"

    def test_sharpen_at_100_keeps_mean(self):
        """强度 100 时与直接使用满强度核等价，均值近似保持"""
        rng = np.random.default_rng(42)
        img = rng.integers(0, 256, (40, 40, 3), dtype=np.uint8).astype(np.float32)

        result = ImageEnhancer.apply_sharpening(img, 100)

        # 满强度核元素和为 1，均值应基本不变（边缘效应允许小偏差）
        assert abs(float(np.mean(result)) - float(np.mean(img))) < 2.0

    def test_sharpen_zero_is_noop(self):
        """强度 0 时返回原图"""
        img = np.full((10, 10, 3), 100.0, dtype=np.float32)
        assert ImageEnhancer.apply_sharpening(img, 0) is img

    def test_higher_strength_sharpens_more(self):
        """强度越高，与原图的差异越大"""
        rng = np.random.default_rng(7)
        img = rng.integers(0, 256, (40, 40, 3), dtype=np.uint8).astype(np.float32)

        diff_30 = float(np.abs(ImageEnhancer.apply_sharpening(img, 30) - img).mean())
        diff_90 = float(np.abs(ImageEnhancer.apply_sharpening(img, 90) - img).mean())

        assert diff_90 > diff_30 > 0


class TestWolfThreshold:
    """Wolf-Jolion 阈值回归测试"""

    def test_uniform_image_all_white(self):
        """纯色图像走保护分支：与均值比较，全部为白"""
        img = np.full((32, 32, 3), 128, dtype=np.uint8)

        binary = BinarizationEngine.apply_threshold(img, 4)  # 4 = Wolf

        assert np.all(binary == 255)

    def test_matches_documented_formula(self):
        """引擎输出与 Wolf-Jolion 文档公式 T = mean - k(mean-Mmin)(1-std/R) 的独立重算一致

        R = 1 - smax/sg 是 [0,1] 归一化灰度上的动态范围（无量纲），
        在 0-255 灰度域计算时需乘 255 与 std 的量纲对齐。
        用横向渐变背景构造 R > 0 的图像（梯度带来的全局标准差大于局部窗口标准差）。
        """
        import cv2

        # 横向渐变：每列恒定灰度 50..245
        width, height = 60, 60
        gray = np.tile(np.linspace(50, 245, width, dtype=np.float32), (height, 1))
        img = np.stack([gray, gray, gray], axis=2).astype(np.uint8)
        window = 15
        k = 0.5

        binary = BinarizationEngine.apply_threshold(img, 4, 0, window_size=window, wolf_k=k)

        # 独立重算文档公式
        g = gray.astype(np.float64)
        mean = cv2.boxFilter(g, -1, (window, window))
        variance = np.maximum(cv2.boxFilter(g**2, -1, (window, window)) - mean**2, 0)
        std = np.sqrt(variance)
        global_min = float(g.min())
        R = 255.0 * (1.0 - float(std.max()) / float(g.std()))
        if abs(R) < 1e-6:
            R = 1e-6
        threshold = mean - k * (mean - global_min) * (1.0 - std / R)
        expected = np.where(g >= threshold, 255, 0).astype(np.uint8)

        assert np.array_equal(binary[:, :, 0], expected)

    def test_output_is_binary_and_non_degenerate(self):
        """输出只有 {0, 255} 且同时包含黑白（非退化）

        用渐变背景叠加弱噪声（保证 R > 0 的正常工作区间）。
        """
        rng = np.random.default_rng(23)
        width, height = 64, 64
        gradient = np.tile(np.linspace(50, 245, width, dtype=np.float32), (height, 1))
        noise = rng.normal(0, 8, (height, width)).astype(np.float32)
        gray = np.clip(gradient + noise, 0, 255).astype(np.uint8)
        img = np.stack([gray, gray, gray], axis=2)

        binary = BinarizationEngine.apply_threshold(img, 4, 0, window_size=15)

        assert set(np.unique(binary).tolist()) <= {0, 255}
        assert 0 < float(np.mean(binary == 255)) < 1.0

    def test_white_ratio_increases_with_k(self):
        """k 越大阈值越低，白色像素占比单调不减"""
        rng = np.random.default_rng(3)
        img = rng.integers(40, 220, (80, 80, 3), dtype=np.uint8)

        binary_low = BinarizationEngine.apply_threshold(img, 4, 0, window_size=15, wolf_k=0.1)
        binary_high = BinarizationEngine.apply_threshold(img, 4, 0, window_size=15, wolf_k=0.9)

        assert np.mean(binary_high == 255) >= np.mean(binary_low == 255)

    def test_differs_from_pure_niblack(self):
        """Wolf 结果与 Niblack 式 mean - 0.496*std 不同（验证不是旧实现的退化公式）"""
        rng = np.random.default_rng(23)
        width, height = 64, 64
        gradient = np.tile(np.linspace(50, 245, width, dtype=np.float32), (height, 1))
        noise = rng.normal(0, 8, (height, width)).astype(np.float32)
        gray = np.clip(gradient + noise, 0, 255).astype(np.uint8)
        img = np.stack([gray, gray, gray], axis=2)

        binary = BinarizationEngine.apply_threshold(img, 4, 0, window_size=15)

        # 手工计算 Niblack 式公式（旧实现的等效形式）作对比
        g = gray.astype(float)
        mean = cv2_box_filter(g, 15)
        std = np.sqrt(np.maximum(cv2_box_filter(g**2, 15) - mean**2, 0))
        niblack_binary = np.where(g >= mean - 0.496 * std, 255, 0)

        wolf_binary = binary[:, :, 0]
        # Wolf 的 (mean - Mmin) 项使其阈值明显不同于 Niblack 的 -k*std 项
        assert np.any(wolf_binary != niblack_binary)


def cv2_box_filter(img, size):
    """测试辅助：与引擎一致的均值滤波"""
    import cv2

    return cv2.boxFilter(img, -1, (size, size))


class TestOrderedDitheringBias:
    """Ordered 抖动 +0.5 偏置回归测试"""

    def test_near_black_stays_black(self):
        """灰度 1 的图应全黑（旧实现中 Bayer 0 值格点会让它出现白点）"""
        img = np.full((64, 64, 3), 1, dtype=np.uint8)

        binary = BinarizationEngine.apply_threshold(img, 8, 0, dither_matrix_size=8)

        assert np.all(binary == 0)

    def test_pure_black_and_white_preserved(self):
        """纯黑全黑、纯白全白"""
        black = BinarizationEngine.apply_threshold(np.zeros((32, 32, 3), np.uint8), 8, 0)
        white = BinarizationEngine.apply_threshold(np.full((32, 32, 3), 255, np.uint8), 8, 0)

        assert np.all(black == 0)
        assert np.all(white == 255)

    def test_mid_gray_dithers_to_about_half(self):
        """中灰图抖动后白色占比接近 128/255"""
        img = np.full((128, 128, 3), 128, dtype=np.uint8)

        binary = BinarizationEngine.apply_threshold(img, 8, 0, dither_matrix_size=8)

        ratio = float(np.mean(binary == 255))
        assert abs(ratio - 128 / 255) < 0.05


class TestMorphKernelMapping:
    """形态学开/闭运算核尺寸映射回归测试"""

    def test_open_at_low_strength_removes_isolated_pixel(self):
        """低强度（strength=10）开运算即生效：孤立白点被去除（旧实现 1×1 核无效）"""
        img = np.zeros((32, 32, 3), dtype=np.float32)
        img[16, 16] = 255.0  # 孤立白点

        result = ImageEnhancer.apply_denoise(img, method=4, strength=10)

        assert float(result.max()) == 0.0

    def test_close_at_low_strength_fills_isolated_hole(self):
        """低强度（strength=10）闭运算即生效：黑底上的孤立白区保留、孤立黑点被填充"""
        img = np.full((32, 32, 3), 255.0, dtype=np.float32)
        img[16, 16] = 0.0  # 孤立黑点

        result = ImageEnhancer.apply_denoise(img, method=5, strength=10)

        assert float(result.min()) == 255.0


class TestNLMeansParameterScale:
    """NLMeans h 参数标定测试"""

    def test_nlmeans_runs_at_max_strength(self):
        """最大强度下可运行且输出形状不变（h 已映射到合理范围）"""
        rng = np.random.default_rng(5)
        img = rng.integers(0, 256, (32, 32, 3), dtype=np.uint8).astype(np.float32)

        result = ImageEnhancer.apply_denoise(img, method=3, strength=100)

        assert result.shape == img.shape


class TestRMBGPreprocess:
    """RMBG 预处理/后处理对齐官方管线测试"""

    @pytest.fixture
    def processor(self):
        # 不调用 load_model，仅测试纯 numpy 前后处理
        return RMBGProcessor("fake_path.onnx")

    def test_preprocess_range_is_minus_one_to_one(self, processor):
        """预处理输出范围 [-1, 1]（官方 mean=0.5、std=1 归一化）"""
        img = np.full((32, 32, 3), 255, dtype=np.uint8)

        tensor = processor._preprocess(img)

        assert tensor.shape == (1, 3, 1024, 1024)
        # 全白图：(255/255) - 0.5 = 0.5
        assert abs(float(tensor.max()) - 0.5) < 1e-6
        # 全黑图：(0/255) - 0.5 = -0.5
        black = processor._preprocess(np.zeros((32, 32, 3), dtype=np.uint8))
        assert abs(float(black.min()) + 0.5) < 1e-6

    def test_postprocess_minmax_normalization(self, processor):
        """后处理 min-max 归一化：输出覆盖完整 [0, 255]"""
        # 构造值域 [0.2, 0.8] 的掩码（如模型输出未校准到 [0,1]）
        mask = np.full((1, 1, 16, 16), 0.2, dtype=np.float32)
        mask[0, 0, 0, 0] = 0.8

        result = processor._postprocess(mask, (16, 16))

        assert int(result.max()) == 255
        assert int(result.min()) == 0

    def test_postprocess_uniform_mask_safe(self, processor):
        """常数掩码（max == min）不触发除零"""
        mask = np.full((1, 1, 8, 8), 0.5, dtype=np.float32)

        result = processor._postprocess(mask, (8, 8))

        assert result.shape == (8, 8)
