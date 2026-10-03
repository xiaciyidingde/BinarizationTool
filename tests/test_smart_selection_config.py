"""
智能选择参数配置的回归测试

覆盖：
1. 置信度概率 → logits 阈值换算
2. smart_select_by_point 参数透传
3. predict 的掩码级别选择与阈值分支
4. 边缘吸附 Canny 高阈值（edge_canny_high）
5. 左面板配置区 UI（默认值、显隐、信号、配置往返）
6. 参数持久化往返
"""

import copy
import sys
from unittest.mock import patch

import cv2
import numpy as np
import pytest

from src.models.selection_tool import SelectionTool
from src.utils.config_manager import ConfigManager
from src.utils.sam_processor import SAMProcessor


class TestProbabilityToLogit:
    """置信度概率 → logits 阈值换算"""

    def test_midpoint_is_zero(self):
        """0.5 概率对应 logits 阈值 0（默认行为与旧实现一致）"""
        assert SAMProcessor.probability_to_logit(0.5) == pytest.approx(0.0, abs=1e-9)

    def test_high_confidence_positive(self):
        """高置信度为正阈值（选区收紧）"""
        assert SAMProcessor.probability_to_logit(0.9) == pytest.approx(np.log(9.0), rel=1e-6)

    def test_low_confidence_negative(self):
        """低置信度为负阈值（选区扩张）"""
        assert SAMProcessor.probability_to_logit(0.1) == pytest.approx(-np.log(9.0), rel=1e-6)

    def test_endpoints_clamped_finite(self):
        """端点 0/1 被夹取，输出有限值"""
        for p in (0.0, 1.0):
            assert np.isfinite(SAMProcessor.probability_to_logit(p))


class RecordingProcessor:
    """记录 predict 调用参数的假 SAM 处理器"""

    def __init__(self):
        self.calls = []
        self.mask = np.full((16, 16), 255, dtype=np.uint8)

    def is_model_loaded(self):
        return True

    def predict(self, point_coords, point_labels, logit_threshold=0.0, mask_index="auto"):
        self.calls.append(
            {
                "points": list(point_coords),
                "labels": list(point_labels),
                "logit_threshold": logit_threshold,
                "mask_index": mask_index,
            }
        )
        return self.mask.copy(), 0.87


class _DummyImageData:
    """smart_select_by_point 不读取图像内容，仅作占位"""


class TestSmartSelectPassThrough:
    """smart_select_by_point 参数透传"""

    def _make_tool(self):
        tool = SelectionTool()
        tool.sam_processor = RecordingProcessor()
        return tool

    def test_defaults_forwarded(self):
        """默认参数：logit_threshold=0.0、mask_index='auto'"""
        tool = self._make_tool()

        ok, iou = tool.smart_select_by_point(_DummyImageData(), 5, 5)

        assert (ok, iou) == (True, 0.87)
        call = tool.sam_processor.calls[0]
        assert call["logit_threshold"] == pytest.approx(0.0)
        assert call["mask_index"] == "auto"
        assert call["points"] == [(5, 5)]
        assert call["labels"] == [1]

    @pytest.mark.parametrize("confidence,expected", [(0.9, np.log(9.0)), (0.1, -np.log(9.0))])
    def test_confidence_converted_to_logit(self, confidence, expected):
        """置信度概率被换算为 logits 阈值"""
        tool = self._make_tool()

        tool.smart_select_by_point(_DummyImageData(), 5, 5, confidence=confidence)

        assert tool.sam_processor.calls[0]["logit_threshold"] == pytest.approx(expected, rel=1e-6)

    def test_mask_level_forwarded(self):
        """掩码级别透传给 predict"""
        tool = self._make_tool()

        tool.smart_select_by_point(_DummyImageData(), 5, 5, mask_index=2)

        assert tool.sam_processor.calls[0]["mask_index"] == 2

    def test_add_mode_merges_mask(self):
        """添加模式下 SAM 掩码并入选区"""
        tool = self._make_tool()

        tool.smart_select_by_point(_DummyImageData(), 5, 5)

        assert tool.selection_mask is not None
        assert tool.selection_mask.shape == (16, 16)
        assert bool(tool.selection_mask.all())


class FakeDecoderSession:
    """返回固定掩码与 IoU 的假解码器会话"""

    def __init__(self, masks, ious):
        self._masks = masks
        self._ious = ious

    def run(self, names, feeds):
        return [self._masks, self._ious]


def _make_processor(masks, ious):
    """构造跳过模型加载、注入假会话的 SAM 处理器"""
    processor = SAMProcessor("fake_encoder.onnx", "fake_decoder.onnx")
    processor.is_loaded = True
    processor.image_embedding = np.zeros((1, 256, 64, 64), dtype=np.float32)
    processor.high_res_feats_0 = np.zeros((1, 32, 256, 256), dtype=np.float32)
    processor.high_res_feats_1 = np.zeros((1, 64, 128, 128), dtype=np.float32)
    processor.current_image_shape = (32, 32)
    processor.decoder_session = FakeDecoderSession(masks, ious)
    return processor


@pytest.fixture
def fake_decoder():
    """三个级别的掩码 logits 分别为常数 -1 / 0.5 / 3.0，IoU 为 0.2 / 0.9 / 0.5"""
    masks = np.zeros((1, 3, 16, 16), dtype=np.float32)
    masks[0, 0] = -1.0
    masks[0, 1] = 0.5
    masks[0, 2] = 3.0
    ious = np.array([[0.2, 0.9, 0.5]], dtype=np.float32)
    return _make_processor(masks, ious)


class TestPredictMaskSelection:
    """predict 的掩码级别选择与阈值分支"""

    def test_auto_picks_highest_iou(self, fake_decoder):
        """auto 模式取 IoU 最高的级别 1（logits 0.5 > 0 → 全白）"""
        result = fake_decoder.predict([(8, 8)], [1])

        assert result is not None
        mask, iou = result
        assert iou == pytest.approx(0.9, abs=1e-6)
        assert mask.shape == (32, 32)
        assert np.all(mask == 255)

    def test_fixed_level_uses_index(self, fake_decoder):
        """指定级别 0（logits -1 < 0 → 全黑），IoU 为该级别的分数"""
        mask, iou = fake_decoder.predict([(8, 8)], [1], mask_index=0)

        assert iou == pytest.approx(0.2, abs=1e-6)
        assert np.all(mask == 0)

    def test_threshold_tightens_selection(self, fake_decoder):
        """logits 0.5 的掩码在阈值 1.0 下变全黑（默认阈值 0 时全白）"""
        mask_default, _ = fake_decoder.predict([(8, 8)], [1], mask_index=1)
        mask_strict, _ = fake_decoder.predict([(8, 8)], [1], logit_threshold=1.0, mask_index=1)

        assert np.all(mask_default == 255)
        assert np.all(mask_strict == 0)

    def test_invalid_level_falls_back_to_auto(self, fake_decoder):
        """越界的级别编号回退到 auto（IoU 最高）"""
        mask, iou = fake_decoder.predict([(8, 8)], [1], mask_index=7)

        assert iou == pytest.approx(0.9, abs=1e-6)
        assert np.all(mask == 255)


class FakeEdgeImageData:
    """返回固定像素的假图像数据"""

    def __init__(self, pixels):
        self._pixels = pixels

    def get_current_pixels(self):
        return self._pixels


class TestEdgeCannyHigh:
    """边缘吸附 Canny 高阈值（edge_canny_high）"""

    @pytest.fixture
    def tool_and_captor(self, monkeypatch):
        tool = SelectionTool()
        captured = {}

        def fake_canny(region, threshold1, threshold2, apertureSize):
            captured["t1"] = threshold1
            captured["t2"] = threshold2
            return np.zeros(region.shape[:2], dtype=np.uint8)

        monkeypatch.setattr(cv2, "Canny", fake_canny)

        # 带垂直强边缘的图与全真选区
        pixels = np.full((64, 64, 3), 40, dtype=np.uint8)
        pixels[:, 32:] = 200
        tool.edge_image = FakeEdgeImageData(pixels)
        tool.edge_mask = np.ones((64, 64), dtype=bool)
        tool.captured = captured
        return tool

    def test_default_threshold_is_200(self, tool_and_captor):
        """默认高阈值 200，低阈值取其一半"""
        tool = tool_and_captor

        tool._detect_edges_in_region(tool.edge_image, tool.edge_mask, margin=8, threshold1=50, threshold2=150)

        assert tool.captured["t2"] == 200
        assert tool.captured["t1"] == 100

    def test_panel_value_overrides(self, tool_and_captor):
        """面板调高阈值时生效（低阈值跟随一半）"""
        tool = tool_and_captor
        tool.edge_canny_high = 350

        tool._detect_edges_in_region(tool.edge_image, tool.edge_mask, margin=8, threshold1=50, threshold2=150)

        assert tool.captured["t2"] == 350
        assert tool.captured["t1"] == 175

    def test_panel_value_below_call_param_ignored(self, tool_and_captor):
        """面板值低于调用参数时取调用参数（max 语义保留）"""
        tool = tool_and_captor
        tool.edge_canny_high = 100

        tool._detect_edges_in_region(tool.edge_image, tool.edge_mask, margin=8, threshold1=50, threshold2=150)

        assert tool.captured["t2"] == 150
        assert tool.captured["t1"] == 75


class TestPanelSmartConfig:
    """左面板智能选择配置区 UI"""

    @pytest.fixture
    def panel(self):
        from PySide6.QtWidgets import QApplication

        from src.views.binarization_panel import BinarizationPanel

        _app = QApplication.instance() or QApplication(sys.argv)
        return BinarizationPanel()

    def test_hidden_by_default_and_toggle(self, panel):
        """默认隐藏，开关切换可见性"""
        assert panel.smart_config_widget.isHidden()

        panel.set_smart_config_visible(True)
        assert not panel.smart_config_widget.isHidden()

        panel.set_smart_config_visible(False)
        assert panel.smart_config_widget.isHidden()

    def test_default_config(self, panel):
        """默认参数：置信度 0.5、级别 auto、吸附 200"""
        assert panel.get_smart_selection_config() == {"confidence": 0.5, "mask_level": "auto", "canny_high": 200}

    def test_signal_emitted_with_current_config(self, panel):
        """任一控件变化发出完整配置字典"""
        received = []
        panel.smart_config_changed.connect(received.append)

        panel.confidence_slider.setValue(70)
        panel.mask_level_combo.setCurrentIndex(1)
        panel.edge_snap_slider.setValue(300)

        assert len(received) == 3
        assert received[-1] == {"confidence": pytest.approx(0.7), "mask_level": 2, "canny_high": 300}

    def test_mask_level_data_values(self, panel):
        """下拉项 userData：自动 / 粗糙(2，大区域) / 精细(0，小区域)——顺序以模型实测为准"""
        panel.mask_level_combo.setCurrentIndex(0)
        assert panel.mask_level_combo.currentData() == "auto"
        panel.mask_level_combo.setCurrentIndex(1)
        assert panel.mask_level_combo.currentData() == 2
        panel.mask_level_combo.setCurrentIndex(2)
        assert panel.mask_level_combo.currentData() == 0

    def test_apply_config_roundtrip(self, panel):
        """apply_smart_selection_config 恢复 UI 后读取一致"""
        panel.apply_smart_selection_config({"confidence": 0.3, "mask_level": 0, "canny_high": 150})

        assert panel.get_smart_selection_config() == {
            "confidence": pytest.approx(0.3),
            "mask_level": 0,
            "canny_high": 150,
        }

    def test_initial_slider_label_uses_scaled_format(self, panel):
        """缩放滑块初值标签显示换算后的值（0.50，而不是 int 截断的 0）"""
        assert panel.confidence_slider.value_label.text() == "0.50"

    def test_edge_snap_slider_min_matches_effective_floor(self, panel):
        """边缘吸附滑块下限与 optimize_selection_boundary 的 threshold2=150 托底一致，无死区"""
        assert panel.edge_snap_slider.minimum() == 150


class TestSmartConfigPersistence:
    """智能选择参数持久化往返"""

    def test_roundtrip(self, tmp_path):
        """set + save 后重新加载读到相同值（未知配置节被保留）"""
        config_path = tmp_path / "config.json"
        with patch.object(ConfigManager, "get_config_file", return_value=config_path):
            manager = ConfigManager()
            default_config = copy.deepcopy(manager.config)

            manager.set("smart_selection", "confidence", 0.75)
            manager.set("smart_selection", "mask_level", 2)
            manager.set("smart_selection", "canny_high", 320)
            assert manager.save()

            reloaded = ConfigManager()
            assert reloaded.get("smart_selection", "confidence") == 0.75
            assert reloaded.get("smart_selection", "mask_level") == 2
            assert reloaded.get("smart_selection", "canny_high") == 320
            # 原有配置节不受影响
            assert reloaded.config.get("editor", {}) == default_config.get("editor", {})
