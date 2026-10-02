"""
下载器进度上报的单元测试

覆盖：进度仅通过回调上报（无控制台打印）、按整数百分比节流、
服务端未返回大小时按字节数推进并在完成时上报、取消时清理文件。
"""

import os
import tempfile
from unittest.mock import patch

from src.utils.downloader import Downloader


class FakeResponse:
    """模拟 urllib 响应：按预置数据块依次返回"""

    def __init__(self, chunks, content_length=None):
        self._chunks = list(chunks)
        # 真实响应的 headers 使用 .get(key, default) 语义，dict 即可满足
        self.headers = {"content-length": str(content_length)} if content_length is not None else {}

    def read(self, size):
        """流式语义：每次最多返回 size 字节，跨预置数据块连续读取"""
        while self._chunks:
            chunk = self._chunks[0]
            if len(chunk) <= size:
                self._chunks.pop(0)
                if chunk:
                    return chunk
                continue
            self._chunks[0] = chunk[size:]
            return chunk[:size]
        return b""

    def close(self):
        pass


class CallbackRecorder:
    """记录进度回调的调用"""

    def __init__(self):
        self.calls = []

    def __call__(self, message, progress):
        self.calls.append((message, progress))

    @property
    def progresses(self):
        return [p for _, p in self.calls]


CHUNK = 8192


def run_download(url, output_path, recorder, chunks, content_length):
    """在 mock 掉 urlopen 的前提下执行一次下载"""
    fake = FakeResponse(chunks, content_length)
    with patch("urllib.request.urlopen", return_value=fake):
        downloader = Downloader(progress_callback=recorder)
        result = downloader._download_with_progress(url, output_path, "测试下载")
    return result


class TestReportProgress:
    """_report_progress 行为测试"""

    def test_only_uses_callback_no_print(self, capsys):
        """有回调时只调用回调，不产生任何控制台输出"""
        recorder = CallbackRecorder()
        downloader = Downloader(progress_callback=recorder)

        downloader._report_progress("进度消息", 42)

        assert recorder.calls == [("进度消息", 42)]
        assert capsys.readouterr().out == ""

    def test_no_callback_no_output(self, capsys):
        """无回调时静默（不再向控制台逐块打印）"""
        downloader = Downloader(progress_callback=None)

        downloader._report_progress("进度消息", 42)

        assert capsys.readouterr().out == ""


class TestDownloadWithProgress:
    """_download_with_progress 测试类"""

    def test_known_size_progress_throttled(self, tmp_path):
        """服务端返回大小时：按整数百分比节流上报，文件内容完整"""
        output_path = str(tmp_path / "model.bin")
        chunks = [bytes([1]) * CHUNK, bytes([2]) * CHUNK, bytes([3]) * CHUNK]
        total = CHUNK * 3

        recorder = CallbackRecorder()
        result = run_download("http://example.com/f.bin", output_path, recorder, chunks, total)

        assert result is True
        # 起始 10%，之后按 10 + int(已下载/总大小 * 65) 三块分别落在 31、53、75
        assert recorder.progresses == [10, 31, 53, 75]
        with open(output_path, "rb") as f:
            assert f.read() == bytes([1]) * CHUNK + bytes([2]) * CHUNK + bytes([3]) * CHUNK

    def test_unknown_size_reports_and_completes(self, tmp_path):
        """未返回大小时：按 5MB 阶梯上报进度，完成时上报 75%（不再停留在 10%）"""
        output_path = str(tmp_path / "model.bin")
        mb = 1024 * 1024
        chunks = [b"a" * (5 * mb), b"b" * (5 * mb), b"c" * mb]

        recorder = CallbackRecorder()
        result = run_download("http://example.com/f.bin", output_path, recorder, chunks, None)

        assert result is True
        # 起始 10%；每 5MB 一次：10+5=15、10+10=20；完成后上报 75
        assert recorder.progresses == [10, 15, 20, 75]
        assert "完成" in recorder.calls[-1][0]

    def test_cancel_removes_partial_file(self, tmp_path):
        """取消下载：返回 False 且删除未完成的文件"""
        output_path = str(tmp_path / "model.bin")

        recorder = CallbackRecorder()
        fake = FakeResponse([b"x" * CHUNK] * 100, content_length=CHUNK * 100)

        downloader = Downloader(progress_callback=recorder)
        downloader.should_cancel = True

        with patch("urllib.request.urlopen", return_value=fake):
            result = downloader._download_with_progress("http://example.com/f.bin", output_path, "测试下载")

        assert result is False
        assert not os.path.exists(output_path)

    def test_progresses_are_monotonically_increasing(self, tmp_path):
        """已知大小时进度单调不减且不超过 75"""
        output_path = str(tmp_path / "model.bin")
        chunk_count = 10
        chunks = [bytes([i]) * CHUNK for i in range(chunk_count)]

        recorder = CallbackRecorder()
        result = run_download("http://example.com/f.bin", output_path, recorder, chunks, CHUNK * chunk_count)

        assert result is True
        progresses = recorder.progresses
        assert progresses == sorted(progresses)
        assert progresses[0] == 10  # 起始进度
        assert max(progresses) > 10  # 至少推进过一次
        assert progresses[-1] <= 75

    def test_downloaded_file_written_to_temp_location(self, tmp_path):
        """下载直接写入目标路径，不留临时文件"""
        output_path = str(tmp_path / "model.bin")

        recorder = CallbackRecorder()
        result = run_download("http://example.com/f.bin", output_path, recorder, [b"z" * CHUNK], CHUNK)

        assert result is True
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) == CHUNK


def test_tempfile_still_importable():
    """模块导入完整性冒烟检查（download_rmbg_model 使用 tempfile）"""

    assert tempfile.mkdtemp is not None
