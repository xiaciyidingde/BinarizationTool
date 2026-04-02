"""
AI 模型结果对比对话框

显示原图与处理后图像的对比，使用可拖动的分隔线。
左侧提供参数调节面板。
"""

import numpy as np
from PySide6.QtCore import Qt, QRect, QPoint, Signal, QTimer
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QCursor
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QWidget,
    QSlider,
    QComboBox,
    QCheckBox,
    QGroupBox,
    QScrollArea,
    QFrame,
)

from ..utils.translation_manager import get_translator
from ..utils.config_manager import get_config_manager


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
    
    显示原图与处理后图像的对比，左侧提供参数调节面板。
    """
    
    # 信号：用户接受结果
    result_accepted = Signal(np.ndarray)
    
    # 信号：参数改变，需要重新处理
    parameters_changed = Signal(dict)
    
    def __init__(self, original_image: np.ndarray, processed_image: np.ndarray, 
                 title: str = None, parent=None, show_parameters: bool = True,
                 processor=None):
        """
        初始化对话框
        
        Args:
            original_image: 原始图像 (H, W, 3) RGB
            processed_image: 处理后的图像 (H, W, 3) RGB
            title: 对话框标题
            parent: 父窗口
            show_parameters: 是否显示参数面板
            processor: AI处理器实例（用于重新处理）
        """
        super().__init__(parent)
        
        self.tr = get_translator()
        self.processed_image = processed_image
        self.original_image = original_image
        self.show_parameters = show_parameters
        self.processor = processor
        
        # 获取配置管理器
        self.config_manager = get_config_manager()
        
        # 参数更新定时器
        self.update_timer = QTimer(self)
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self._process_with_parameters)
        
        # 是否正在处理
        self.is_processing = False
        
        # 设置标题
        if title:
            self.setWindowTitle(title)
        else:
            self.setWindowTitle(self.tr.tr('ai_result.title'))
        
        # 设置对话框大小
        if show_parameters:
            self.resize(1300, 700)  # 更宽以容纳参数面板
        else:
            self.resize(1000, 700)
        
        self.setup_ui(original_image, processed_image)
        
        # 应用深色标题栏
        from ..utils.window_utils import apply_dark_titlebar
        apply_dark_titlebar(self)
    
    def setup_ui(self, original_image: np.ndarray, processed_image: np.ndarray):
        """设置 UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 左侧：参数面板（如果启用）
        if self.show_parameters:
            self.parameters_panel = self._create_parameters_panel()
            main_layout.addWidget(self.parameters_panel)
        
        # 右侧：图像对比
        self.comparison_widget = ImageComparisonWidget(original_image, processed_image)
        main_layout.addWidget(self.comparison_widget, 1)
    
    def _create_parameters_panel(self) -> QWidget:
        """创建参数调节面板"""
        panel = QFrame()
        panel.setObjectName("parametersPanel")
        panel.setFrameShape(QFrame.StyledPanel)
        panel.setMinimumWidth(300)
        panel.setMaximumWidth(300)
        
        # 主布局
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)
        
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        
        # 内容容器
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)
        
        # 阈值设置组
        threshold_group = self._create_threshold_group()
        content_layout.addWidget(threshold_group)
        
        # 边缘处理组
        edge_group = self._create_edge_group()
        content_layout.addWidget(edge_group)
        
        # 背景设置组
        background_group = self._create_background_group()
        content_layout.addWidget(background_group)
        
        content_layout.addStretch()
        
        scroll.setWidget(content)
        panel_layout.addWidget(scroll, 1)
        
        # 按钮区域（固定在底部）
        button_container = QWidget()
        button_container.setObjectName("parametersButtonContainer")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(16, 12, 16, 12)
        button_layout.setSpacing(8)
        
        # 应用按钮 - 使用与取消按钮相同的样式
        apply_btn = QPushButton(self.tr.tr('ai_result.apply'))
        apply_btn.setMinimumHeight(36)
        apply_btn.clicked.connect(self.accept_result)
        # 强制设置为普通按钮样式，不使用default样式
        apply_btn.setAutoDefault(False)
        apply_btn.setDefault(False)
        button_layout.addWidget(apply_btn)
        
        # 取消按钮
        cancel_btn = QPushButton(self.tr.tr('ai_result.cancel'))
        cancel_btn.setMinimumHeight(36)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setAutoDefault(False)
        button_layout.addWidget(cancel_btn)
        
        panel_layout.addWidget(button_container)
        
        return panel
    
    def _create_threshold_group(self) -> QGroupBox:
        """创建阈值设置组"""
        group = QGroupBox(self.tr.tr('ai_result.threshold_settings'))
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        
        # 阈值模式
        mode_layout = QHBoxLayout()
        mode_label = QLabel(self.tr.tr('ai_result.threshold_mode'))
        self.threshold_mode_combo = QComboBox()
        self.threshold_mode_combo.addItem(self.tr.tr('ai_result.threshold_auto'), 'auto')
        self.threshold_mode_combo.addItem(self.tr.tr('ai_result.threshold_manual'), 'manual')
        self.threshold_mode_combo.currentIndexChanged.connect(self._on_threshold_mode_changed)
        mode_layout.addWidget(mode_label)
        mode_layout.addStretch()
        mode_layout.addWidget(self.threshold_mode_combo)
        layout.addLayout(mode_layout)
        
        # 手动阈值滑块（左右布局）- 创建为独立的widget以便整体隐藏
        self.manual_threshold_widget = QWidget()
        threshold_layout = QHBoxLayout(self.manual_threshold_widget)
        threshold_layout.setContentsMargins(0, 0, 0, 0)
        
        threshold_label = QLabel(self.tr.tr('ai_result.manual_threshold_label'))
        threshold_label.setMinimumWidth(70)
        threshold_layout.addWidget(threshold_label)
        
        self.manual_threshold_value_label = QLabel('127')
        self.manual_threshold_value_label.setMinimumWidth(25)
        self.manual_threshold_value_label.setMaximumWidth(25)
        self.manual_threshold_value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        threshold_layout.addWidget(self.manual_threshold_value_label)
        
        self.manual_threshold_slider = QSlider(Qt.Horizontal)
        self.manual_threshold_slider.setRange(0, 255)
        self.manual_threshold_slider.setValue(127)
        # 使用 valueChanged 更新标签，但不触发处理
        self.manual_threshold_slider.valueChanged.connect(self._on_manual_threshold_value_changed)
        # 使用 sliderReleased 触发处理
        self.manual_threshold_slider.sliderReleased.connect(self._emit_parameters_changed)
        threshold_layout.addWidget(self.manual_threshold_slider, 1)
        
        # 默认隐藏（因为默认是自动模式）
        self.manual_threshold_widget.setVisible(False)
        
        layout.addWidget(self.manual_threshold_widget)
        
        return group
    
    def _create_edge_group(self) -> QGroupBox:
        """创建边缘处理组"""
        group = QGroupBox(self.tr.tr('ai_result.edge_settings'))
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        
        # 边缘羽化开关
        feather_layout = QHBoxLayout()
        feather_label = QLabel(self.tr.tr('ai_result.edge_feather'))
        from ..widgets.toggle_switch import ToggleSwitch
        self.edge_feather_check = ToggleSwitch()
        self.edge_feather_check.setChecked(True)
        self.edge_feather_check.toggled.connect(self._on_edge_feather_changed)
        feather_layout.addWidget(feather_label)
        feather_layout.addStretch()
        feather_layout.addWidget(self.edge_feather_check)
        layout.addLayout(feather_layout)
        
        # 羽化强度（左右布局）- 创建为独立的widget以便整体隐藏
        self.feather_strength_widget = QWidget()
        strength_layout = QHBoxLayout(self.feather_strength_widget)
        strength_layout.setContentsMargins(0, 0, 0, 0)
        
        strength_label = QLabel(self.tr.tr('ai_result.feather_strength_label'))
        strength_label.setMinimumWidth(70)
        strength_layout.addWidget(strength_label)
        
        self.feather_strength_value_label = QLabel('50')
        self.feather_strength_value_label.setMinimumWidth(25)
        self.feather_strength_value_label.setMaximumWidth(25)
        self.feather_strength_value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        strength_layout.addWidget(self.feather_strength_value_label)
        
        self.feather_strength_slider = QSlider(Qt.Horizontal)
        self.feather_strength_slider.setRange(0, 100)
        self.feather_strength_slider.setValue(50)
        # 使用 valueChanged 更新标签，但不触发处理
        self.feather_strength_slider.valueChanged.connect(self._on_feather_strength_value_changed)
        # 使用 sliderReleased 触发处理
        self.feather_strength_slider.sliderReleased.connect(self._emit_parameters_changed)
        strength_layout.addWidget(self.feather_strength_slider, 1)
        
        layout.addWidget(self.feather_strength_widget)
        
        return group
    
    def _create_background_group(self) -> QGroupBox:
        """创建背景设置组"""
        group = QGroupBox(self.tr.tr('ai_result.background_settings'))
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        
        # 背景颜色
        bg_layout = QHBoxLayout()
        bg_label = QLabel(self.tr.tr('ai_result.background_color'))
        self.background_combo = QComboBox()
        self.background_combo.addItem(self.tr.tr('ai_result.bg_white'), 'white')
        self.background_combo.addItem(self.tr.tr('ai_result.bg_black'), 'black')
        self.background_combo.addItem(self.tr.tr('ai_result.bg_transparent'), 'transparent')
        self.background_combo.currentIndexChanged.connect(self._on_background_changed)
        bg_layout.addWidget(bg_label)
        bg_layout.addStretch()
        bg_layout.addWidget(self.background_combo)
        layout.addLayout(bg_layout)
        
        return group
    
    def _on_threshold_mode_changed(self, index):
        """阈值模式改变"""
        mode = self.threshold_mode_combo.currentData()
        is_manual = (mode == 'manual')
        # 显示/隐藏整个手动阈值widget
        self.manual_threshold_widget.setVisible(is_manual)
        self._emit_parameters_changed()
    
    def _on_manual_threshold_value_changed(self, value):
        """手动阈值值改变（仅更新标签）"""
        self.manual_threshold_value_label.setText(str(value))
    
    def _on_feather_strength_value_changed(self, value):
        """羽化强度值改变（仅更新标签）"""
        self.feather_strength_value_label.setText(str(value))
    
    def _on_edge_feather_changed(self, checked):
        """边缘羽化开关改变"""
        # 显示/隐藏整个羽化强度widget
        self.feather_strength_widget.setVisible(checked)
        self._emit_parameters_changed()
    
    def _on_background_changed(self, index):
        """背景颜色改变"""
        self._emit_parameters_changed()
    
    def _emit_parameters_changed(self):
        """发射参数改变信号"""
        params = self.get_parameters()
        self.parameters_changed.emit(params)
        
        # 如果有处理器，启动延迟更新
        if self.processor and self.show_parameters:
            # 停止之前的定时器
            self.update_timer.stop()
            
            # 获取延迟时间（毫秒）
            delay = self.config_manager.get('performance', 'debounce_delay', 150)
            
            # 启动新的定时器
            self.update_timer.start(delay)
    
    def _process_with_parameters(self):
        """使用当前参数重新处理图像"""
        if self.is_processing or not self.processor:
            return
        
        self.is_processing = True
        
        # 显示处理提示
        self._show_processing_indicator()
        
        # 使用 QTimer.singleShot 延迟执行实际处理，让UI有时间更新
        QTimer.singleShot(50, self._do_process_with_parameters)
    
    def _show_processing_indicator(self):
        """显示处理中指示器"""
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        
        # 创建一个简洁的处理提示标签
        if not hasattr(self, 'processing_overlay'):
            self.processing_overlay = QLabel(self.comparison_widget)
            self.processing_overlay.setAlignment(Qt.AlignCenter)
            self.processing_overlay.setStyleSheet("""
                QLabel {
                    background-color: rgba(255, 255, 255, 230);
                    color: #646464;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 12px 32px;
                    border: 1px solid #c8c8c8;
                    border-radius: 6px;
                }
            """)
            self.processing_overlay.setText(self.tr.tr('app.processing'))
        
        # 调整覆盖层大小和位置（顶部居中）
        metrics = self.processing_overlay.fontMetrics()
        text_width = metrics.horizontalAdvance(self.processing_overlay.text())
        overlay_width = text_width + 64
        overlay_height = metrics.height() + 24
        x = (self.comparison_widget.width() - overlay_width) // 2
        y = 30  # 距离顶部30px
        self.processing_overlay.setGeometry(x, y, overlay_width, overlay_height)
        self.processing_overlay.show()
        self.processing_overlay.raise_()
        
        # 强制刷新界面
        QApplication.processEvents()
    
    def _do_process_with_parameters(self):
        """实际执行参数处理"""
        try:
            # 获取当前参数
            params = self.get_parameters()
            
            # 使用参数处理图像
            processed = self.processor.process_with_parameters(
                self.original_image,
                threshold_mode=params['threshold_mode'],
                manual_threshold=params['manual_threshold'],
                edge_feather=params['edge_feather'],
                feather_strength=params['feather_strength'] / 100.0,  # 转换为 0-1
                background_color=params['background_color']
            )
            
            # 更新显示
            self.update_processed_image(processed)
            
        except Exception as e:
            print(f"重新处理图像失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 隐藏处理提示
            if hasattr(self, 'processing_overlay'):
                self.processing_overlay.hide()
            self.is_processing = False
    
    def get_parameters(self) -> dict:
        """
        获取当前参数
        
        Returns:
            参数字典
        """
        return {
            'threshold_mode': self.threshold_mode_combo.currentData(),
            'manual_threshold': self.manual_threshold_slider.value(),
            'edge_feather': self.edge_feather_check.isChecked(),
            'feather_strength': self.feather_strength_slider.value(),
            'background_color': self.background_combo.currentData(),
        }
    
    def update_processed_image(self, processed_image: np.ndarray):
        """
        更新处理后的图像
        
        Args:
            processed_image: 新的处理后图像
        """
        self.processed_image = processed_image
        self.comparison_widget.processed_image = processed_image
        self.comparison_widget.processed_pixmap = self.comparison_widget._numpy_to_pixmap(processed_image)
        self.comparison_widget.update()
    
    def accept_result(self):
        """接受结果"""
        self.result_accepted.emit(self.processed_image)
        self.accept()
