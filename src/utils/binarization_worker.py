"""
异步二值化工作线程

在后台线程中执行二值化处理，避免阻塞 UI。
"""

import numpy as np
from PySide6.QtCore import QThread, Signal
from .binarization_engine import BinarizationEngine


class BinarizationWorker(QThread):
    """
    二值化工作线程
    
    在后台执行预处理和二值化操作，完成后发送信号。
    """
    
    # 信号：处理完成 (binary_pixels)
    finished = Signal(np.ndarray)
    
    # 信号：处理出错 (error_message)
    error = Signal(str)
    
    def __init__(self, original_pixels: np.ndarray, preprocess_params: dict, 
                 method: int, threshold: int):
        """
        初始化工作线程
        
        Args:
            original_pixels: 原始图片数据
            preprocess_params: 预处理参数
            method: 二值化方法
            threshold: 阈值参数
        """
        super().__init__()
        self.original_pixels = original_pixels.copy()
        self.preprocess_params = preprocess_params
        self.method = method
        self.threshold = threshold
        self._is_cancelled = False
    
    def run(self):
        """执行二值化处理"""
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
            
            # 二值化
            binary_pixels = BinarizationEngine.apply_threshold(
                preprocessed, self.method, self.threshold
            )
            
            # 检查是否已取消
            if self._is_cancelled:
                return
            
            # 发送结果
            self.finished.emit(binary_pixels)
            
        except Exception as e:
            self.error.emit(str(e))
    
    def cancel(self):
        """取消处理"""
        self._is_cancelled = True
