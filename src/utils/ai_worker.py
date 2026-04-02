"""
AI 处理工作线程

在后台线程中执行 AI 模型推理，避免阻塞 UI。
"""

import numpy as np
from PySide6.QtCore import QThread, Signal, QTimer

from .ai_processor import AIProcessor


class AIWorker(QThread):
    """
    AI 处理工作线程
    
    在后台执行 AI 模型推理。
    """
    
    # 信号：处理完成 (处理后的图像)
    processing_finished = Signal(np.ndarray)
    
    # 信号：处理失败 (错误信息)
    processing_failed = Signal(str)
    
    # 信号：进度更新 (进度百分比)
    progress_updated = Signal(int)
    
    def __init__(self, processor: AIProcessor, image: np.ndarray):
        """
        初始化工作线程
        
        Args:
            processor: AI 处理器实例
            image: 待处理的图像 (H, W, 3) RGB
        """
        super().__init__()
        self.processor = processor
        self.image = image
        self.should_stop = False
        self._loading_progress = 0
        self._loading_timer = None
    
    def run(self):
        """执行处理"""
        try:
            # 加载模型（如果未加载）
            if not self.processor.is_model_loaded():
                self.progress_updated.emit(5)
                
                # 启动模拟进度定时器（用于大模型加载时提供视觉反馈）
                self._loading_progress = 5
                self._start_loading_simulation()
                
                # 传递进度回调给处理器
                def load_progress_callback(progress):
                    """模型加载进度回调"""
                    # 将加载进度映射到 5-50% 范围
                    mapped_progress = int(5 + progress * 0.45)
                    self._loading_progress = mapped_progress
                    self.progress_updated.emit(mapped_progress)
                
                if not self.processor.load_model(progress_callback=load_progress_callback):
                    self._stop_loading_simulation()
                    self.processing_failed.emit("模型加载失败")
                    return
                
                self._stop_loading_simulation()
                self.progress_updated.emit(50)
            
            if self.should_stop:
                return
            
            # 处理图像
            self.progress_updated.emit(60)
            result = self.processor.process(self.image)
            
            if self.should_stop:
                return
            
            # 完成
            self.progress_updated.emit(100)
            self.processing_finished.emit(result)
            
        except Exception as e:
            self._stop_loading_simulation()
            self.processing_failed.emit(f"处理失败: {str(e)}")
    
    def _start_loading_simulation(self):
        """启动加载进度模拟（用于大模型加载时提供视觉反馈）"""
        # 注意：这个定时器在工作线程中，需要在主线程中创建
        # 所以我们改用简单的进度更新策略
        pass
    
    def _stop_loading_simulation(self):
        """停止加载进度模拟"""
        pass
    
    def stop(self):
        """停止处理"""
        self.should_stop = True
