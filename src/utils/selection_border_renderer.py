"""
选区边框渲染器

实现静态虚线边框效果
"""

import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen


class SelectionBorderRenderer:
    """
    选区边框渲染器
    
    提取选区外轮廓并绘制明显的虚线边框
    """
    
    def __init__(self):
        """初始化渲染器"""
        self.contours = []  # 轮廓列表，每个轮廓是点的列表
        
    def update_contours(self, selection_mask: np.ndarray):
        """
        从选区蒙版提取所有轮廓（包括外轮廓和内部孔洞）
        
        Args:
            selection_mask: 选区蒙版 (H, W), dtype=bool
        """
        if selection_mask is None or not selection_mask.any():
            self.contours = []
            return
        
        # 转换为uint8格式（OpenCV要求）
        mask_uint8 = selection_mask.astype(np.uint8) * 255
        
        # 使用OpenCV提取所有轮廓（包括孔洞）
        # RETR_CCOMP: 提取所有轮廓，并组织成两层结构（外轮廓和孔洞）
        # CHAIN_APPROX_SIMPLE: 压缩水平、垂直和对角线段，只保留端点
        contours, hierarchy = cv2.findContours(mask_uint8, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        
        # 转换轮廓格式：从OpenCV格式转为点列表
        # RETR_CCOMP返回的hierarchy: [Next, Previous, First_Child, Parent]
        # 我们需要绘制所有轮廓（外轮廓和孔洞都要显示）
        self.contours = []
        for contour in contours:
            # contour shape: (N, 1, 2)，转换为 (N, 2)
            points = contour.squeeze()
            if len(points.shape) == 1:  # 单点情况
                points = points.reshape(1, -1)
            if len(points) >= 3:  # 至少3个点才能形成轮廓
                self.contours.append(points)
    
    def render(self, painter: QPainter, view_transform):
        """
        渲染选区边框（明显的静态虚线）
        
        Args:
            painter: QPainter 对象
            view_transform: ViewTransform 对象
        """
        if not self.contours:
            return
        
        # 保存状态
        painter.save()
        
        scale = view_transform.scale
        offset_x = view_transform.offset_x
        offset_y = view_transform.offset_y
        
        # 遍历所有轮廓
        for contour_points in self.contours:
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
        
        # 恢复状态
        painter.restore()

