"""
选区边框渲染器

实现静态虚线边框效果，支持增量轮廓更新和 Cython 加速
"""

import cv2
import numpy as np
from PySide6.QtCore import Qt, QThread, Signal, QMutex, QMutexLocker, QWaitCondition
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen

# 尝试导入 Cython 加速模块
try:
    from ..cython_core import contour_extractor
    HAS_CYTHON = True
except ImportError:
    HAS_CYTHON = False


class ContourUpdateThread(QThread):
    """
    轮廓更新后台线程
    
    支持增量更新：只计算变化区域的轮廓
    """
    contours_ready = Signal(list, bool)  # (轮廓列表, 是否增量更新)
    
    def __init__(self):
        super().__init__()
        self.mask = None
        self.dirty_rect = None  # (x1, y1, x2, y2) 或 None 表示全量更新
        self.view_scale = 1.0  # 视图缩放比例
        self.pending = False
        self.lock = QMutex()
        self.condition = QWaitCondition()
        self.should_stop = False
        
    def update_mask(self, mask: np.ndarray, dirty_rect=None, view_scale=1.0):
        """
        更新待处理的蒙版（支持增量更新和动态降采样）
        
        Args:
            mask: 选区蒙版 (H, W), dtype=bool
            dirty_rect: 变化区域 (x1, y1, x2, y2)，None 表示全量更新
            view_scale: 视图缩放比例，用于动态调整质量
        """
        self.lock.lock()
        self.mask = mask
        self.dirty_rect = dirty_rect
        self.view_scale = view_scale
        self.pending = True
        self.condition.wakeOne()
        self.lock.unlock()
    
    def stop(self):
        """停止线程"""
        with QMutexLocker(self.lock):
            self.should_stop = True
            self.condition.wakeOne()
        self.wait()
    
    def run(self):
        """线程主循环"""
        while not self.should_stop:
            with QMutexLocker(self.lock):
                if not self.pending:
                    self.condition.wait(self.lock, 100)
                    continue
                
                mask_ref = self.mask
                dirty_rect = self.dirty_rect
                view_scale = self.view_scale
                self.pending = False
            
            # 拷贝数据
            if mask_ref is not None:
                mask_copy = mask_ref.copy()
            else:
                mask_copy = None
            
            # 提取轮廓（增量或全量）
            is_incremental = dirty_rect is not None
            if is_incremental and mask_copy is not None:
                contours = self._extract_contours_incremental(mask_copy, dirty_rect)
            else:
                contours = self._extract_contours_full(mask_copy, view_scale)
            
            # 发送信号，标记是否为增量更新
            self.contours_ready.emit(contours, is_incremental)
    
    def _extract_contours_incremental(self, mask, dirty_rect):
        """
        增量提取轮廓：只计算变化区域
        
        Args:
            mask: 完整蒙版
            dirty_rect: (x1, y1, x2, y2)
        """
        x1, y1, x2, y2 = dirty_rect
        h, w = mask.shape
        
        # 扩展区域边界（确保能捕获到轮廓）
        margin = 2
        
        # 使用 Cython 加速提取区域
        if HAS_CYTHON:
            mask_uint8 = mask.astype(np.uint8) * 255
            sub_mask, ax1, ay1 = contour_extractor.extract_region_mask(
                mask_uint8, x1, y1, x2, y2, margin
            )
        else:
            # 纯 Python 降级实现
            ax1 = max(0, x1 - margin)
            ay1 = max(0, y1 - margin)
            ax2 = min(w, x2 + margin)
            ay2 = min(h, y2 + margin)
            sub_mask = mask[ay1:ay2, ax1:ax2].astype(np.uint8) * 255
        
        if sub_mask.size == 0 or (HAS_CYTHON and contour_extractor.check_mask_empty(sub_mask)):
            return []
        elif not HAS_CYTHON and not sub_mask.any():
            return []
        
        # 在子区域中提取轮廓
        contours, _ = cv2.findContours(sub_mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        
        # 转换轮廓坐标（加上偏移）
        result = []
        for contour in contours:
            points = contour.squeeze()
            if len(points.shape) == 1:
                points = points.reshape(1, -1)
            if len(points) >= 3:
                # 坐标偏移到全局
                points[:, 0] += ax1
                points[:, 1] += ay1
                result.append(points)
        
        return result
    
    def _extract_contours_full(self, mask, view_scale=1.0):
        """
        全量提取轮廓（根据图片尺寸和缩放级别动态调整降采样）
        
        Args:
            mask: 选区蒙版
            view_scale: 视图缩放比例（0.1 = 缩小10倍，2.0 = 放大2倍）
        """
        if mask is None:
            return []
        
        h, w = mask.shape
        image_size = max(h, w)
        
        # 根据图片尺寸和视图缩放动态决定降采样倍数
        if image_size < 4000:
            downsample = 1
        elif image_size < 5000:
            if view_scale >= 0.5:
                downsample = 1
            else:
                downsample = 2
        elif image_size < 8000:
            if view_scale >= 1.0:
                downsample = 1
            elif view_scale >= 0.5:
                downsample = 2
            else:
                downsample = 3
        else:
            if view_scale >= 1.0:
                downsample = 2
            elif view_scale >= 0.5:
                downsample = 3
            elif view_scale >= 0.25:
                downsample = 4
            else:
                downsample = 5
        
        # 执行降采样（使用 Cython 加速）
        if downsample > 1:
            mask_uint8 = mask.astype(np.uint8) * 255
            
            if HAS_CYTHON:
                small_mask = contour_extractor.downsample_mask(mask_uint8, downsample)
            else:
                small_mask = mask_uint8[::downsample, ::downsample]
            
            contours, _ = cv2.findContours(small_mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
            
            # 放大轮廓坐标（使用 Cython 加速）
            result = []
            for contour in contours:
                points = contour.squeeze()
                if len(points.shape) == 1:
                    points = points.reshape(1, -1)
                if len(points) >= 3:
                    if HAS_CYTHON:
                        points = contour_extractor.scale_contour_points(points, downsample)
                    else:
                        points = points * downsample
                    result.append(points)
            return result
        else:
            # 不降采样
            mask_uint8 = mask.astype(np.uint8) * 255
            contours, _ = cv2.findContours(mask_uint8, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
            
            result = []
            for contour in contours:
                points = contour.squeeze()
                if len(points.shape) == 1:
                    points = points.reshape(1, -1)
                if len(points) >= 3:
                    result.append(points)
            
            return result


class SelectionBorderRenderer:
    """
    选区边框渲染器
    
    提取选区外轮廓并绘制明显的虚线边框
    """
    
    # 暴露 Cython 可用性标志
    HAS_CYTHON = HAS_CYTHON
    
    def __init__(self):
        """初始化渲染器"""
        self.contours = []  # 轮廓列表，每个轮廓是点的列表
        self.contour_lock = QMutex()  # 保护 contours 的锁
        
        # 创建并启动后台线程
        self.update_thread = ContourUpdateThread()
        self.update_thread.contours_ready.connect(self._on_contours_ready)
        self.update_thread.start()
    
    def cleanup(self):
        """清理资源（在对象销毁前调用）"""
        if hasattr(self, 'update_thread'):
            self.update_thread.stop()
    
    def _on_contours_ready(self, new_contours, is_incremental):
        """
        轮廓计算完成的回调
        
        Args:
            new_contours: 新计算的轮廓列表
            is_incremental: 是否为增量更新
        """
        with QMutexLocker(self.contour_lock):
            if is_incremental:
                # 增量更新：合并新旧轮廓
                # 简单策略：直接添加新轮廓（后续可优化去重）
                self.contours.extend(new_contours)
            else:
                # 全量更新：替换所有轮廓
                self.contours = new_contours
        
    def update_contours(self, selection_mask: np.ndarray, dirty_rect=None, view_scale=1.0):
        """
        异步更新轮廓（支持增量更新和动态质量调整）
        
        Args:
            selection_mask: 选区蒙版 (H, W), dtype=bool
            dirty_rect: 变化区域 (x1, y1, x2, y2)，None 表示全量更新
            view_scale: 视图缩放比例
        """
        self.update_thread.update_mask(selection_mask, dirty_rect, view_scale)
    
    def render(self, painter: QPainter, view_transform):
        """
        渲染选区边框（明显的静态虚线）
        
        Args:
            painter: QPainter 对象
            view_transform: ViewTransform 对象
        """
        # 获取当前轮廓（线程安全，但不拷贝）
        self.contour_lock.lock()
        contours = self.contours
        has_contours = len(contours) > 0 if contours else False
        
        if not has_contours:
            self.contour_lock.unlock()
            return
        
        # 保存状态
        painter.save()
        
        scale = view_transform.scale
        offset_x = view_transform.offset_x
        offset_y = view_transform.offset_y
        
        # 遍历所有轮廓（在锁内快速渲染）
        for contour_points in contours:
            # 创建路径
            path = QPainterPath()
            
            # 将轮廓点连接成路径
            if len(contour_points) > 0:
                # 第一个点
                x, y = contour_points[0]
                view_x = x * scale + offset_x
                view_y = y * scale + offset_y
                path.moveTo(view_x, view_y)
                
                # 连接其他点
                for i in range(1, len(contour_points)):
                    x, y = contour_points[i]
                    view_x = x * scale + offset_x
                    view_y = y * scale + offset_y
                    path.lineTo(view_x, view_y)
                
                # 闭合路径
                path.closeSubpath()
            
            # 绘制白色虚线（外层，更粗）
            pen = QPen(QColor(255, 255, 255), 2)  # 2像素粗
            pen.setStyle(Qt.CustomDashLine)
            pen.setDashPattern([6, 3])  # 6像素实线，3像素空白
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)
            
            # 绘制黑色虚线（内层，形成对比）
            pen = QPen(QColor(0, 0, 0), 2)  # 2像素粗
            pen.setStyle(Qt.CustomDashLine)
            pen.setDashPattern([6, 3])
            pen.setDashOffset(4.5)  # 偏移形成相间效果
            painter.setPen(pen)
            painter.drawPath(path)
        
        # 释放锁
        self.contour_lock.unlock()
        
        # 恢复状态
        painter.restore()

