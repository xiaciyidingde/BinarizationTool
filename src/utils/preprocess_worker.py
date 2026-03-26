"""
异步预处理工作线程

在后台线程中执行预处理，避免阻塞 UI。
"""

import numpy as np
from PySide6.QtCore import QThread, Signal

from .binarization_engine import BinarizationEngine


class PreprocessWorker(QThread):
    """
    预处理工作线程

    在后台执行预处理操作，完成后发送信号。
    """

    # 信号：处理完成 (preprocessed_pixels)
    finished = Signal(np.ndarray)

    # 信号：处理出错 (error_message)
    error = Signal(str)

    def __init__(self, original_pixels: np.ndarray, preprocess_params: dict):
        """
        初始化工作线程

        Args:
            original_pixels: 原始图片数据
            preprocess_params: 预处理参数
        """
        super().__init__()
        self.original_pixels = original_pixels.copy()
        self.preprocess_params = preprocess_params
        self._is_cancelled = False

    def run(self):
        """执行预处理"""
        try:
            # 检查是否已取消
            if self._is_cancelled:
                return

            # 预处理
            preprocessed = BinarizationEngine.apply_preprocess(
                self.original_pixels,
                **self.preprocess_params
            )

            # 检查是否已取消
            if self._is_cancelled:
                return

            # 发送结果
            self.finished.emit(preprocessed)

        except Exception as e:
            self.error.emit(str(e))

    def cancel(self):
        """取消处理"""
        self._is_cancelled = True
