"""
AI 工作线程的单元测试

覆盖：模型加载失败、处理异常（错误信息包含异常类型）、
正常完成路径、stop 标志。直接同步调用 run()，不经真实线程调度。
"""

import sys

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from src.utils.ai_worker import AIWorker


@pytest.fixture(scope="module")
def qapp():
    """确保存在 QApplication 实例"""
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


class Recorder:
    """记录信号发射"""

    def __init__(self, worker):
        worker.processing_finished.connect(self._on_finished)
        worker.processing_failed.connect(self._on_failed)
        worker.progress_updated.connect(self._on_progress)
        self.finished = []
        self.failed = []
        self.progresses = []

    def _on_finished(self, result):
        self.finished.append(result)

    def _on_failed(self, message):
        self.failed.append(message)

    def _on_progress(self, value):
        self.progresses.append(value)


class FakeProcessor:
    """可编程的假 AI 处理器"""

    def __init__(self, loaded=True, load_result=True, process_result=None, process_error=None):
        self._loaded = loaded
        self._load_result = load_result
        self._process_result = process_result
        self._process_error = process_error
        self.load_calls = 0

    def is_model_loaded(self):
        return self._loaded

    def load_model(self, progress_callback=None):
        self.load_calls += 1
        return self._load_result

    def process(self, image):
        if self._process_error is not None:
            raise self._process_error
        return self._process_result


IMAGE = np.zeros((4, 4, 3), dtype=np.uint8)


class TestAIWorker:
    """AIWorker 测试类"""

    def test_success_without_load(self, qapp):
        """模型已加载：直接处理并发出完成信号，进度到 100"""
        result_image = np.ones((4, 4, 3), dtype=np.uint8)
        worker = AIWorker(FakeProcessor(loaded=True, process_result=result_image), IMAGE)
        recorder = Recorder(worker)

        worker.run()

        assert len(recorder.failed) == 0
        assert len(recorder.finished) == 1
        assert np.array_equal(recorder.finished[0], result_image)
        assert recorder.progresses == [60, 100]

    def test_success_with_load(self, qapp):
        """模型未加载：先加载再处理，进度经过 5 与 50"""
        worker = AIWorker(FakeProcessor(loaded=False, process_result=IMAGE), IMAGE)
        recorder = Recorder(worker)

        worker.run()

        assert len(recorder.failed) == 0
        assert len(recorder.finished) == 1
        assert 5 in recorder.progresses
        assert 50 in recorder.progresses
        assert recorder.progresses[-1] == 100

    def test_load_failure_emits_message(self, qapp):
        """模型加载失败：发出失败信号，不调用处理"""
        worker = AIWorker(FakeProcessor(loaded=False, load_result=False), IMAGE)
        recorder = Recorder(worker)

        worker.run()

        assert recorder.failed == ["模型加载失败"]
        assert recorder.finished == []
        assert recorder.progresses == [5]  # 只发了加载起始进度

    def test_process_exception_includes_type_and_message(self, qapp):
        """处理异常：失败信息包含异常类型名与原因，便于诊断"""
        worker = AIWorker(FakeProcessor(loaded=True, process_error=RuntimeError("显存不足")), IMAGE)
        recorder = Recorder(worker)

        worker.run()

        assert len(recorder.failed) == 1
        assert "RuntimeError" in recorder.failed[0]
        assert "显存不足" in recorder.failed[0]
        assert recorder.finished == []

    def test_stop_before_process_skips_work(self, qapp):
        """模型已加载但 stop 被置位：跳过处理，不发任何完成/失败信号"""
        worker = AIWorker(FakeProcessor(loaded=True, process_result=IMAGE), IMAGE)
        recorder = Recorder(worker)
        worker.stop()

        worker.run()

        assert recorder.finished == []
        assert recorder.failed == []

    def test_stop_between_load_and_process(self, qapp):
        """加载完成后 stop 被置位：不再处理"""
        worker = AIWorker(FakeProcessor(loaded=False, process_result=IMAGE), IMAGE)
        recorder = Recorder(worker)

        processor = FakeProcessor(loaded=False, process_result=IMAGE)
        load_calls = []

        def load_model(progress_callback=None):
            load_calls.append(1)
            worker.should_stop = True  # 加载期间用户取消
            return True

        processor.load_model = load_model
        worker.processor = processor

        worker.run()

        assert recorder.finished == []
        assert recorder.failed == []
        assert len(load_calls) == 1
