"""
AI 模型结果对比对话框

显示原图与处理后图像的对比，使用可拖动的分隔线。
"""

import numpy as np
from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QCursor
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QWidget,
)

from ..utils.translation_manager import get_translator


class ImageComparisonWidget(QWidget):
    """
    图像对比组件
    
    显示两张图像的对比，使用可拖动的垂直分隔线。
    """
    
    def __init__(self, original_image: np.ndarray, processed_image: np.ndarray, parent=None):
        """
        初始化图像对比组件
        
        Args:
            original_image: 原始图像 (H, W, 3) RGB
            processed_image: 处理后的图像 (H, W, 3) RGB
            parent: 父窗口
        """
        super().__init__(parent)
        
        self.original_image = original_image
        self.processed_image = processed_image
        
        # 转换为 QPixmap
        self.original_pixmap = self._numpy_to_pixmap(original_image)
        self.processed_pixmap = self._numpy_to_pixmap(processed_image)
        
        # 分隔线位置（0.0 到 1.0，默认居中）
        self.divider_position = 0.5
        
        # 拖动状态
        self.is_dragging = False
        
        # 设置最小尺寸
        self.setMinimumSize(800, 600)
        
        # 启用鼠标追踪
        self.setMouseTracking(True)
    
    def _numpy_to_pixmap(self, image: np.ndarray) -> QPixmap:
        """
        将 NumPy 数组转换为 QPixmap
        
        Args:
            image: NumPy 数组 (H, W, 3) RGB
            
        Returns:
            QPixmap 对象
        """
        h, w = image.shape[:2]
        
        # 确保是 RGB 格式
        if len(image.shape) == 2:
            # 灰度图转 RGB
            image = np.stack([image, image, image], axis=2)
        
        # 转换为 QImage
        bytes_per_line = 3 * w
        q_image = QImage(image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        return QPixmap.fromImage(q_image)
    
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        widget_width = self.width()
        widget_height = self.height()
        
        # 计算图像缩放以适应窗口
        img_width = self.original_pixmap.width()
        img_height = self.original_pixmap.height()
        
        scale_x = widget_width / img_width
        scale_y = widget_height / img_height
        scale = min(scale_x, scale_y)
        
        scaled_width = int(img_width * scale)
        scaled_height = int(img_height * scale)
        
        # 居中显示
        offset_x = (widget_width - scaled_width) // 2
        offset_y = (widget_height - scaled_height) // 2
        
        # 计算分隔线的实际位置
        divider_x = int(offset_x + scaled_width * self.divider_position)
        
        # 绘制处理后的图像（完整）
        scaled_processed = self.processed_pixmap.scaled(
            scaled_width, scaled_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        painter.drawPixmap(offset_x, offset_y, scaled_processed)
        
        # 绘制原始图像（左侧部分）
        if divider_x > offset_x:
            scaled_original = self.original_pixmap.scaled(
                scaled_width, scaled_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            # 裁剪左侧部分
            clip_width = divider_x - offset_x
            source_rect = QRect(0, 0, clip_width, scaled_height)
            target_rect = QRect(offset_x, offset_y, clip_width, scaled_height)
            
            painter.setClipRect(target_rect)
            painter.drawPixmap(offset_x, offset_y, scaled_original)
            painter.setClipping(False)
        
        # 获取主题颜色
        palette = self.palette()
        text_color = palette.windowText().color()
        highlight_color = palette.highlight().color()
        
        # 绘制分隔线
        pen = QPen(highlight_color, 3)
        painter.setPen(pen)
        painter.drawLine(divider_x, offset_y, divider_x, offset_y + scaled_height)
        
        # 绘制分隔线阴影（增强可见性）
        shadow_color = QColor(0, 0, 0, 100)
        pen = QPen(shadow_color, 1)
        painter.setPen(pen)
        painter.drawLine(divider_x - 2, offset_y, divider_x - 2, offset_y + scaled_height)
        painter.drawLine(divider_x + 2, offset_y, divider_x + 2, offset_y + scaled_height)
        
        # 绘制拖动手柄
        handle_size = 40
        handle_x = divider_x - handle_size // 2
        handle_y = (widget_height - handle_size) // 2
        
        # 手柄背景
        handle_bg = palette.window().color()
        handle_bg.setAlpha(220)
        painter.setBrush(handle_bg)
        painter.setPen(QPen(highlight_color, 2))
        painter.drawEllipse(handle_x, handle_y, handle_size, handle_size)
        
        # 手柄箭头
        painter.setPen(QPen(text_color, 2))
        center_x = divider_x
        center_y = handle_y + handle_size // 2
        
        # 左箭头
        painter.drawLine(center_x - 10, center_y, center_x - 5, center_y - 5)
        painter.drawLine(center_x - 10, center_y, center_x - 5, center_y + 5)
        
        # 右箭头
        painter.drawLine(center_x + 10, center_y, center_x + 5, center_y - 5)
        painter.drawLine(center_x + 10, center_y, center_x + 5, center_y + 5)
        
        # 绘制标签（更大的字体，带描边）
        from PySide6.QtGui import QFont
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        painter.setFont(font)
        
        # 原图标签
        original_text = "原图"
        text_x = offset_x + 20
        text_y = offset_y + 30
        
        # 绘制文字描边（黑色）
        painter.setPen(QPen(QColor(0, 0, 0), 3))
        painter.drawText(text_x - 1, text_y - 1, original_text)
        painter.drawText(text_x + 1, text_y - 1, original_text)
        painter.drawText(text_x - 1, text_y + 1, original_text)
        painter.drawText(text_x + 1, text_y + 1, original_text)
        
        # 绘制文字主体（白色）
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawText(text_x, text_y, original_text)
        
        # 处理后标签
        processed_text = "处理后"
        text_rect = painter.fontMetrics().boundingRect(processed_text)
        text_x = offset_x + scaled_width - text_rect.width() - 20
        text_y = offset_y + 30
        
        # 绘制文字描边（黑色）
        painter.setPen(QPen(QColor(0, 0, 0), 3))
        painter.drawText(text_x - 1, text_y - 1, processed_text)
        painter.drawText(text_x + 1, text_y - 1, processed_text)
        painter.drawText(text_x - 1, text_y + 1, processed_text)
        painter.drawText(text_x + 1, text_y + 1, processed_text)
        
        # 绘制文字主体（白色）
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawText(text_x, text_y, processed_text)
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            if self._is_near_divider(event.pos()):
                self.is_dragging = True
                self.setCursor(QCursor(Qt.SplitHCursor))
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.is_dragging:
            # 更新分隔线位置
            widget_width = self.width()
            img_width = self.original_pixmap.width()
            img_height = self.original_pixmap.height()
            
            scale_x = widget_width / img_width
            scale_y = self.height() / img_height
            scale = min(scale_x, scale_y)
            
            scaled_width = int(img_width * scale)
            offset_x = (widget_width - scaled_width) // 2
            
            # 计算新的分隔线位置
            mouse_x = event.pos().x()
            relative_x = mouse_x - offset_x
            
            if scaled_width > 0:
                self.divider_position = max(0.0, min(1.0, relative_x / scaled_width))
            
            self.update()
        else:
            # 更新鼠标光标
            if self._is_near_divider(event.pos()):
                self.setCursor(QCursor(Qt.SplitHCursor))
            else:
                self.setCursor(QCursor(Qt.ArrowCursor))
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            self.is_dragging = False
            self.setCursor(QCursor(Qt.ArrowCursor))
    
    def _is_near_divider(self, pos: QPoint) -> bool:
        """
        检查鼠标是否靠近分隔线
        
        Args:
            pos: 鼠标位置
            
        Returns:
            True 如果靠近分隔线
        """
        widget_width = self.width()
        widget_height = self.height()
        
        img_width = self.original_pixmap.width()
        img_height = self.original_pixmap.height()
        
        scale_x = widget_width / img_width
        scale_y = widget_height / img_height
        scale = min(scale_x, scale_y)
        
        scaled_width = int(img_width * scale)
        scaled_height = int(img_height * scale)
        
        offset_x = (widget_width - scaled_width) // 2
        offset_y = (widget_height - scaled_height) // 2
        
        divider_x = int(offset_x + scaled_width * self.divider_position)
        
        # 检查是否在图像范围内且靠近分隔线
        if offset_y <= pos.y() <= offset_y + scaled_height:
            if abs(pos.x() - divider_x) < 20:
                return True
        
        return False


class AIResultDialog(QDialog):
    """
    AI 模型结果对比对话框
    
    显示原图与处理后图像的对比。
    """
    
    # 信号：用户接受结果
    result_accepted = Signal(np.ndarray)
    
    def __init__(self, original_image: np.ndarray, processed_image: np.ndarray, 
                 title: str = None, parent=None):
        """
        初始化对话框
        
        Args:
            original_image: 原始图像 (H, W, 3) RGB
            processed_image: 处理后的图像 (H, W, 3) RGB
            title: 对话框标题
            parent: 父窗口
        """
        super().__init__(parent)
        
        self.tr = get_translator()
        self.processed_image = processed_image
        
        # 设置标题
        if title:
            self.setWindowTitle(title)
        else:
            self.setWindowTitle(self.tr.tr('ai_result.title'))
        
        # 设置对话框大小
        self.resize(1000, 700)
        
        self.setup_ui(original_image, processed_image)
    
    def setup_ui(self, original_image: np.ndarray, processed_image: np.ndarray):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 图像对比组件
        self.comparison_widget = ImageComparisonWidget(original_image, processed_image)
        layout.addWidget(self.comparison_widget, 1)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(16, 12, 16, 12)
        button_layout.setSpacing(12)
        
        button_layout.addStretch()
        
        # 取消按钮
        cancel_btn = QPushButton(self.tr.tr('ai_result.cancel'))
        cancel_btn.setMinimumSize(120, 40)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        # 应用按钮
        apply_btn = QPushButton(self.tr.tr('ai_result.apply'))
        apply_btn.setMinimumSize(120, 40)
        apply_btn.setDefault(True)
        apply_btn.clicked.connect(self.accept_result)
        button_layout.addWidget(apply_btn)
        
        layout.addLayout(button_layout)
    
    def accept_result(self):
        """接受结果"""
        self.result_accepted.emit(self.processed_image)
        self.accept()
