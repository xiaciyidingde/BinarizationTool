"""
二值化设置面板

提供预处理和二值化参数调整控件。
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                QComboBox, QSlider, QGroupBox, QScrollArea, QCheckBox, QStyledItemDelegate, QPushButton)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QIcon, QPainter, QImage
from .view_mode_switcher import ViewModeSwitcher
from ..utils.translation_manager import get_translator


class BinarizationPanel(QWidget):
    """
    二值化设置面板类
    
    提供预处理参数和二值化方法选择控件。
    """
    
    # 信号：参数改变 (preprocess_params, binarization_method, threshold)
    parameters_changed = Signal(dict, int, int)
    
    # 信号：视图模式改变 (mode: 'original', 'preprocessed', 'binary')
    view_mode_changed = Signal(str)
    
    def __init__(self, parent=None, panel_width=300):
        """
        初始化二值化面板
        
        Args:
            parent: 父窗口部件
            panel_width: 面板宽度，用于动态调整内部组件宽度
        """
        super().__init__(parent)
        
        # 获取翻译器
        self.tr = get_translator()
        
        # 保存面板宽度
        self.panel_width = panel_width
        # 计算 QGroupBox 的最大宽度（面板宽度 - 左右边距）
        self.group_max_width = panel_width - 24  # 减去左右各12px的边距
        
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """设置 UI 布局"""
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 外层容器
        outer_container = QWidget()
        outer_layout = QVBoxLayout(outer_container)
        outer_layout.setContentsMargins(0, 6, 0, 6)  # 左右边距改为0
        outer_layout.setSpacing(8)
        
        # === 视图模式切换器区域（独立白色背景） ===
        view_mode_container = QWidget()
        view_mode_container.setObjectName("viewModeContainer")
        view_mode_container.setStyleSheet("""
            QWidget#viewModeContainer {
                background-color: #ffffff;
                border-radius: 8px;
            }
        """)
        view_mode_layout = QVBoxLayout(view_mode_container)
        view_mode_layout.setContentsMargins(12, 8, 12, 8)  # 左右边距12px
        view_mode_layout.setSpacing(0)
        
        self.view_mode_switcher = ViewModeSwitcher()
        view_mode_layout.addWidget(self.view_mode_switcher)
        
        outer_layout.addWidget(view_mode_container)
        
        # === 二值化设置区域（独立白色背景） ===
        settings_container = QWidget()
        settings_container.setObjectName("settingsContainer")
        settings_container.setStyleSheet("""
            QWidget#settingsContainer {
                background-color: #ffffff;
                border-radius: 8px;
            }
        """)
        settings_layout = QVBoxLayout(settings_container)
        settings_layout.setContentsMargins(12, 8, 12, 8)  # 左右边距12px
        settings_layout.setSpacing(8)
        
        # === 预处理参数 ===
        preprocess_group = QGroupBox(self.tr.tr('binarization_panel.preprocess'))
        preprocess_group.setMaximumWidth(self.group_max_width)
        preprocess_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #495057;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 8px;
                top: 0px;
                padding: 0 4px;
                background-color: #ffffff;
            }
        """)
        preprocess_layout = QVBoxLayout()
        preprocess_layout.setSpacing(6)
        
        # 曝光度（带重置按钮）
        self.exposure_slider = self._create_slider_with_reset(
            "exposure", -100, 100, 0, preprocess_layout
        )
        
        # 对比度
        self.contrast_slider = self._create_slider_with_reset(
            "contrast", -100, 100, 0, preprocess_layout
        )
        
        # 锐化
        self.sharpen_slider = self._create_slider_with_reset(
            "sharpness", 0, 100, 0, preprocess_layout
        )
        
        # 伽马
        self.gamma_slider = self._create_slider_with_reset(
            "gamma", 10, 300, 100, preprocess_layout, scale=0.01
        )
        
        # 平滑
        self.smooth_slider = self._create_slider_with_reset(
            "smooth", 0, 100, 0, preprocess_layout
        )
        
        preprocess_group.setLayout(preprocess_layout)
        settings_layout.addWidget(preprocess_group)
        
        # === RGB 通道调整 ===
        rgb_group = QGroupBox(self.tr.tr('binarization_panel.rgb_channels'))
        rgb_group.setMaximumWidth(self.group_max_width)
        rgb_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #495057;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 8px;
                top: 0px;
                padding: 0 4px;
                background-color: #ffffff;
            }
        """)
        rgb_layout = QVBoxLayout()
        rgb_layout.setSpacing(6)
        
        # 红色通道
        self.red_channel_slider = self._create_slider_with_reset(
            "red_channel", -100, 100, 0, rgb_layout
        )
        
        # 绿色通道
        self.green_channel_slider = self._create_slider_with_reset(
            "green_channel", -100, 100, 0, rgb_layout
        )
        
        # 蓝色通道
        self.blue_channel_slider = self._create_slider_with_reset(
            "blue_channel", -100, 100, 0, rgb_layout
        )
        
        rgb_group.setLayout(rgb_layout)
        settings_layout.addWidget(rgb_group)
        
        # === 边缘检测 ===
        edge_group = QGroupBox(self.tr.tr('binarization_panel.edge_detection'))
        edge_group.setMaximumWidth(self.group_max_width)
        edge_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #495057;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 8px;
                top: 0px;
                padding: 0 4px;
                background-color: #ffffff;
            }
        """)
        edge_layout = QVBoxLayout()
        edge_layout.setSpacing(6)
        
        # 边缘模式（左右布局）
        edge_mode_row = QHBoxLayout()
        edge_mode_label = QLabel(self.tr.tr('binarization_panel.edge_mode'))
        edge_mode_label.setMinimumWidth(70)
        edge_mode_row.addWidget(edge_mode_label)
        
        # 添加占位空间（对齐数值标签位置）
        edge_mode_row.addSpacing(25)
        
        self.edge_mode_combo = QComboBox()
        self.edge_mode_combo.setFixedWidth(140)
        self.edge_mode_combo.addItem(self.tr.tr('binarization_panel.edge_off'), 0)
        self.edge_mode_combo.addItem(self.tr.tr('binarization_panel.edge_canny'), 1)
        self.edge_mode_combo.addItem(self.tr.tr('binarization_panel.edge_enhance'), 2)
        self.edge_mode_combo.addItem(self.tr.tr('binarization_panel.edge_contour'), 3)
        
        edge_mode_row.addWidget(self.edge_mode_combo)
        edge_mode_row.addStretch()  # 添加弹性空间
        
        edge_layout.addLayout(edge_mode_row)
        
        # 边缘强度
        self.edge_strength_slider = self._create_slider_with_reset(
            "edge_strength", 0, 100, 50, edge_layout
        )
        
        # 边缘阈值（仅 Canny 模式显示）- 手动创建以便隐藏整行
        self.edge_threshold_row = QHBoxLayout()
        self.edge_threshold_row.setContentsMargins(0, 0, 0, 0)
        
        # 提取标签文本（移除占位符）
        full_text = self.tr.tr('binarization_panel.edge_threshold', value='')
        label_text = full_text.replace('{value}', '').strip()
        if not label_text.endswith('：') and not label_text.endswith(':'):
            label_text += '：' if '：' in full_text else ':'
        
        edge_threshold_label = QLabel(label_text)
        edge_threshold_label.setMinimumWidth(70)
        self.edge_threshold_row.addWidget(edge_threshold_label)
        
        self.edge_threshold_value_label = QLabel("150")
        self.edge_threshold_value_label.setMinimumWidth(25)
        self.edge_threshold_value_label.setMaximumWidth(25)
        self.edge_threshold_value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.edge_threshold_row.addWidget(self.edge_threshold_value_label)
        
        self.edge_threshold_slider = QSlider(Qt.Horizontal)
        self.edge_threshold_slider.setMinimum(0)
        self.edge_threshold_slider.setMaximum(255)
        self.edge_threshold_slider.setValue(150)
        self.edge_threshold_slider.valueChanged.connect(
            lambda v: self.edge_threshold_value_label.setText(str(v))
        )
        self.edge_threshold_row.addWidget(self.edge_threshold_slider, 1)
        
        # 重置按钮
        from ..utils.resources import REFRESH
        from ..utils.animations import create_rotation_animation
        edge_threshold_reset_btn = QPushButton()
        edge_threshold_reset_btn.setIcon(QIcon(QPixmap.fromImage(QImage.fromData(REFRESH))))
        edge_threshold_reset_btn.setFixedSize(24, 24)
        edge_threshold_reset_btn.setToolTip("重置为默认值")
        edge_threshold_reset_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-radius: 4px;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        
        def reset_edge_threshold():
            animation = create_rotation_animation(edge_threshold_reset_btn, duration=300, angle=360)
            animation.start()
            self.edge_threshold_slider.setValue(150)
        
        edge_threshold_reset_btn.clicked.connect(reset_edge_threshold)
        self.edge_threshold_row.addWidget(edge_threshold_reset_btn)
        
        # 创建一个容器 widget 来包装边缘阈值行，方便隐藏
        self.edge_threshold_container = QWidget()
        self.edge_threshold_container.setLayout(self.edge_threshold_row)
        edge_layout.addWidget(self.edge_threshold_container)
        
        edge_group.setLayout(edge_layout)
        settings_layout.addWidget(edge_group)
        
        # === 二值化方法 ===
        binarization_group = QGroupBox(self.tr.tr('binarization_panel.binarization'))
        binarization_group.setMaximumWidth(self.group_max_width)
        binarization_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #495057;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 8px;
                top: 0px;
                padding: 0 4px;
                background-color: #ffffff;
            }
        """)
        binarization_layout = QVBoxLayout()
        binarization_layout.setSpacing(6)
        
        # 方法选择（左右布局）
        method_row = QHBoxLayout()
        method_label = QLabel(self.tr.tr('binarization_panel.method'))
        method_label.setMinimumWidth(70)
        method_row.addWidget(method_label)
        
        # 添加占位空间（对齐数值标签位置）
        method_row.addSpacing(25)
        
        self.method_combo = QComboBox()
        self.method_combo.setFixedWidth(130)
        self.method_combo.addItem(self.tr.tr('binarization_panel.method_fixed'), 0)
        self.method_combo.addItem(self.tr.tr('binarization_panel.method_adaptive'), 1)
        self.method_combo.addItem(self.tr.tr('binarization_panel.method_otsu'), 2)
        self.method_combo.addItem(self.tr.tr('binarization_panel.method_sauvola'), 3)
        self.method_combo.addItem(self.tr.tr('binarization_panel.method_wolf'), 4)
        self.method_combo.addItem(self.tr.tr('binarization_panel.method_nick'), 5)
        self.method_combo.addItem(self.tr.tr('binarization_panel.method_bernsen'), 6)
        # 添加分隔线（使用禁用的项）
        self.method_combo.insertSeparator(7)
        self.method_combo.addItem(self.tr.tr('binarization_panel.method_floyd'), 7)
        self.method_combo.addItem(self.tr.tr('binarization_panel.method_ordered'), 8)
        self.method_combo.addItem(self.tr.tr('binarization_panel.method_atkinson'), 9)
        self.method_combo.setCurrentIndex(1)  # 默认自适应阈值
        
        method_row.addWidget(self.method_combo)
        method_row.addStretch()  # 添加弹性空间
        
        binarization_layout.addLayout(method_row)
        
        # 阈值（左右布局）- 手动创建以便隐藏整行
        self.threshold_row = QHBoxLayout()
        self.threshold_row.setContentsMargins(0, 0, 0, 0)
        
        # 提取标签文本（移除占位符）
        full_text = self.tr.tr('binarization_panel.threshold', value='')
        label_text = full_text.replace('{value}', '').strip()
        if not label_text.endswith('：') and not label_text.endswith(':'):
            label_text += '：' if '：' in full_text else ':'
        
        threshold_label_text = QLabel(label_text)
        threshold_label_text.setMinimumWidth(70)
        self.threshold_row.addWidget(threshold_label_text)
        
        self.threshold_label = QLabel("127")
        self.threshold_label.setMinimumWidth(25)
        self.threshold_label.setMaximumWidth(25)
        self.threshold_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.threshold_row.addWidget(self.threshold_label)
        
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setMinimum(0)
        self.threshold_slider.setMaximum(255)
        self.threshold_slider.setValue(127)
        self.threshold_row.addWidget(self.threshold_slider, 1)
        
        # 重置按钮
        from ..utils.animations import create_rotation_animation
        threshold_reset_btn = QPushButton()
        threshold_reset_btn.setIcon(QIcon(QPixmap.fromImage(QImage.fromData(REFRESH))))
        threshold_reset_btn.setFixedSize(24, 24)
        threshold_reset_btn.setToolTip("重置为默认值")
        threshold_reset_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-radius: 4px;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        
        def reset_threshold():
            animation = create_rotation_animation(threshold_reset_btn, duration=300, angle=360)
            animation.start()
            self.threshold_slider.setValue(127)
        
        threshold_reset_btn.clicked.connect(reset_threshold)
        self.threshold_row.addWidget(threshold_reset_btn)
        
        # 创建一个容器 widget 来包装阈值行，方便隐藏
        self.threshold_container = QWidget()
        self.threshold_container.setLayout(self.threshold_row)
        binarization_layout.addWidget(self.threshold_container)
        
        # === 自适应阈值参数 ===
        self.adaptive_params_container = self._create_adaptive_params()
        binarization_layout.addWidget(self.adaptive_params_container)
        
        # === Sauvola 参数 ===
        self.sauvola_params_container = self._create_sauvola_params()
        binarization_layout.addWidget(self.sauvola_params_container)
        
        # === Wolf 参数 ===
        self.wolf_params_container = self._create_wolf_params()
        binarization_layout.addWidget(self.wolf_params_container)
        
        # === Nick 参数 ===
        self.nick_params_container = self._create_nick_params()
        binarization_layout.addWidget(self.nick_params_container)
        
        # === Bernsen 参数 ===
        self.bernsen_params_container = self._create_bernsen_params()
        binarization_layout.addWidget(self.bernsen_params_container)
        
        # === 抖动参数 ===
        self.dithering_params_container = self._create_dithering_params()
        binarization_layout.addWidget(self.dithering_params_container)
        
        binarization_group.setLayout(binarization_layout)
        settings_layout.addWidget(binarization_group)
        
        # === 降噪功能 ===
        denoise_group = QGroupBox(self.tr.tr('binarization_panel.denoise'))
        denoise_group.setMaximumWidth(self.group_max_width)
        denoise_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #495057;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 8px;
                top: 0px;
                padding: 0 4px;
                background-color: #ffffff;
            }
        """)
        denoise_layout = QVBoxLayout()
        denoise_layout.setSpacing(6)
        
        # 降噪方法（左右布局）
        denoise_method_row = QHBoxLayout()
        denoise_method_label = QLabel(self.tr.tr('binarization_panel.denoise_method'))
        denoise_method_label.setMinimumWidth(70)
        denoise_method_row.addWidget(denoise_method_label)
        
        # 添加占位空间（对齐数值标签位置）
        denoise_method_row.addSpacing(25)
        
        self.denoise_method_combo = QComboBox()
        self.denoise_method_combo.setFixedWidth(130)
        self.denoise_method_combo.addItem(self.tr.tr('binarization_panel.denoise_gaussian'), 0)
        self.denoise_method_combo.addItem(self.tr.tr('binarization_panel.denoise_median'), 1)
        self.denoise_method_combo.addItem(self.tr.tr('binarization_panel.denoise_bilateral'), 2)
        self.denoise_method_combo.addItem(self.tr.tr('binarization_panel.denoise_nlmeans'), 3)
        self.denoise_method_combo.addItem(self.tr.tr('binarization_panel.denoise_morph_open'), 4)
        self.denoise_method_combo.addItem(self.tr.tr('binarization_panel.denoise_morph_close'), 5)
        
        denoise_method_row.addWidget(self.denoise_method_combo)
        denoise_method_row.addStretch()  # 添加弹性空间
        
        denoise_layout.addLayout(denoise_method_row)
        
        # 降噪强度
        self.denoise_slider = self._create_slider_with_reset(
            "denoise_strength", 0, 100, 0, denoise_layout
        )
        
        denoise_group.setLayout(denoise_layout)
        settings_layout.addWidget(denoise_group)
        
        # 添加弹性空间
        settings_layout.addStretch()
        
        outer_layout.addWidget(settings_container)
        
        # 设置滚动区域
        scroll.setWidget(outer_container)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        
        # 初始状态:固定阈值控件启用
        self._update_threshold_enabled()
        self._update_edge_threshold_enabled()
    
    def _create_slider_with_label(self, label_key, min_val, max_val, default_val, 
                                  parent_layout, scale=1.0):
        """创建带标签的滑块（左右布局）
        
        Args:
            label_key: 翻译键（不带冒号）
            min_val: 最小值
            max_val: 最大值
            default_val: 默认值
            parent_layout: 父布局
            scale: 缩放比例
        """
        # 标签和滑块的水平布局
        row_layout = QHBoxLayout()
        
        # 左侧：标签（使用翻译键，只取冒号前的部分）
        full_text = self.tr.tr(f'binarization_panel.{label_key}', value='')
        # 移除占位符，只保留标签文本
        label_text = full_text.replace('{value}', '').replace('：', '：').replace(': ', ': ').strip()
        if not label_text.endswith('：') and not label_text.endswith(':'):
            label_text += '：' if '：' in full_text else ':'
        
        label = QLabel(label_text)
        label.setMinimumWidth(70)
        row_layout.addWidget(label)
        
        # 数值标签
        value_label = QLabel(str(int(default_val * scale)))
        value_label.setMinimumWidth(25)
        value_label.setMaximumWidth(25)
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row_layout.addWidget(value_label)
        
        # 右侧：滑块
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(default_val)
        row_layout.addWidget(slider, 1)  # 滑块占据剩余空间
        
        parent_layout.addLayout(row_layout)
        
        # 连接信号更新标签
        slider.valueChanged.connect(
            lambda v: value_label.setText(f"{v * scale:.2f}" if scale != 1.0 else str(v))
        )
        
        # 保存标签引用
        slider.value_label = value_label
        slider.text_label = label
        
        return slider
    
    def _create_slider_with_reset(self, label_key, min_val, max_val, default_val, 
                                   parent_layout, scale=1.0):
        """创建带重置按钮的滑块（左右布局）
        
        Args:
            label_key: 翻译键（不带冒号）
            min_val: 最小值
            max_val: 最大值
            default_val: 默认值
            parent_layout: 父布局
            scale: 缩放比例
        """
        # 标签和滑块的水平布局
        row_layout = QHBoxLayout()
        
        # 左侧：标签（使用翻译键，只取冒号前的部分）
        full_text = self.tr.tr(f'binarization_panel.{label_key}', value='')
        # 移除占位符，只保留标签文本
        label_text = full_text.replace('{value}', '').replace('：', '：').replace(': ', ': ').strip()
        if not label_text.endswith('：') and not label_text.endswith(':'):
            label_text += '：' if '：' in full_text else ':'
        
        label = QLabel(label_text)
        label.setMinimumWidth(70)
        row_layout.addWidget(label)
        
        # 数值标签
        value_label = QLabel(str(int(default_val * scale)))
        value_label.setMinimumWidth(25)
        value_label.setMaximumWidth(25)
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row_layout.addWidget(value_label)
        
        # 右侧：滑块
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(default_val)
        row_layout.addWidget(slider, 1)  # 滑块占据剩余空间
        
        # 重置按钮
        from ..utils.resources import REFRESH
        from ..utils.animations import create_rotation_animation
        reset_btn = QPushButton()
        reset_btn.setIcon(QIcon(QPixmap.fromImage(QImage.fromData(REFRESH))))
        reset_btn.setFixedSize(24, 24)
        reset_btn.setToolTip("重置为默认值")
        reset_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-radius: 4px;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        
        # 重置按钮点击事件（带动画）
        def reset_value():
            # 播放旋转动画
            animation = create_rotation_animation(reset_btn, duration=300, angle=360)
            animation.start()
            # 重置滑块值
            slider.setValue(default_val)
        
        reset_btn.clicked.connect(reset_value)
        row_layout.addWidget(reset_btn)
        
        parent_layout.addLayout(row_layout)
        
        # 连接信号更新标签
        slider.valueChanged.connect(
            lambda v: value_label.setText(f"{v * scale:.2f}" if scale != 1.0 else str(v))
        )
        
        # 保存标签引用和默认值
        slider.value_label = value_label
        slider.text_label = label
        slider.default_value = default_val
        
        return slider
    
    def _create_adaptive_params(self):
        """创建自适应阈值参数容器"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # 块大小
        self.adaptive_block_size_slider = self._create_slider_with_reset(
            "block_size", 3, 51, 11, layout
        )
        
        return container
    
    def _create_sauvola_params(self):
        """创建 Sauvola 参数容器"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # 窗口大小
        self.sauvola_window_slider = self._create_slider_with_reset(
            "window_size", 3, 51, 15, layout
        )
        
        # k 参数
        self.sauvola_k_slider = self._create_slider_with_reset(
            "k_param", 0, 100, 20, layout, scale=0.01
        )
        
        # R 参数
        self.sauvola_r_slider = self._create_slider_with_reset(
            "r_param", 0, 255, 128, layout
        )
        
        return container
    
    def _create_wolf_params(self):
        """创建 Wolf 参数容器"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # 窗口大小
        self.wolf_window_slider = self._create_slider_with_reset(
            "window_size", 3, 51, 15, layout
        )
        
        # k 参数
        self.wolf_k_slider = self._create_slider_with_reset(
            "k_param", 0, 100, 50, layout, scale=0.01
        )
        
        return container
    
    def _create_nick_params(self):
        """创建 Nick 参数容器"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # 窗口大小
        self.nick_window_slider = self._create_slider_with_reset(
            "window_size", 3, 51, 15, layout
        )
        
        # k 参数 (-1.0 到 0.0)
        self.nick_k_slider = self._create_slider_with_reset(
            "k_param", -100, 0, -10, layout, scale=0.01
        )
        
        return container
    
    def _create_bernsen_params(self):
        """创建 Bernsen 参数容器"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # 窗口大小
        self.bernsen_window_slider = self._create_slider_with_reset(
            "window_size", 3, 51, 15, layout
        )
        
        # 对比度阈值
        self.bernsen_contrast_slider = self._create_slider_with_reset(
            "contrast_threshold", 0, 255, 15, layout
        )
        
        return container
    
    def _create_dithering_params(self):
        """创建抖动参数容器"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # 抖动强度（用于 Floyd-Steinberg 和 Atkinson）
        self.dither_strength_container = QWidget()
        strength_layout = QVBoxLayout(self.dither_strength_container)
        strength_layout.setContentsMargins(0, 0, 0, 0)
        strength_layout.setSpacing(6)
        self.dither_strength_slider = self._create_slider_with_reset(
            "dither_strength", 0, 100, 100, strength_layout
        )
        layout.addWidget(self.dither_strength_container)
        
        # 矩阵大小（仅用于 Ordered 抖动）
        self.dither_matrix_size_container = QWidget()
        matrix_layout = QVBoxLayout(self.dither_matrix_size_container)
        matrix_layout.setContentsMargins(0, 0, 0, 0)
        matrix_layout.setSpacing(6)
        self.dither_matrix_size_slider = self._create_slider_with_reset(
            "matrix_size", 2, 16, 8, matrix_layout
        )
        layout.addWidget(self.dither_matrix_size_container)
        
        return container
    
    def connect_signals(self):
        """连接信号"""
        self.method_combo.currentIndexChanged.connect(self._on_parameters_changed)
        self.threshold_slider.valueChanged.connect(self._on_threshold_changed)
        
        # 预处理参数信号
        self.exposure_slider.valueChanged.connect(self._on_parameters_changed)
        self.contrast_slider.valueChanged.connect(self._on_parameters_changed)
        self.sharpen_slider.valueChanged.connect(self._on_parameters_changed)
        self.gamma_slider.valueChanged.connect(self._on_parameters_changed)
        self.smooth_slider.valueChanged.connect(self._on_parameters_changed)
        
        # RGB 通道调整信号
        self.red_channel_slider.valueChanged.connect(self._on_parameters_changed)
        self.green_channel_slider.valueChanged.connect(self._on_parameters_changed)
        self.blue_channel_slider.valueChanged.connect(self._on_parameters_changed)
        
        # 边缘检测参数信号
        self.edge_mode_combo.currentIndexChanged.connect(self._on_edge_mode_changed)
        self.edge_strength_slider.valueChanged.connect(self._on_parameters_changed)
        self.edge_threshold_slider.valueChanged.connect(self._on_parameters_changed)
        
        # 二值化方法参数信号
        self.adaptive_block_size_slider.valueChanged.connect(self._on_parameters_changed)
        self.sauvola_window_slider.valueChanged.connect(self._on_parameters_changed)
        self.sauvola_k_slider.valueChanged.connect(self._on_parameters_changed)
        self.sauvola_r_slider.valueChanged.connect(self._on_parameters_changed)
        self.wolf_window_slider.valueChanged.connect(self._on_parameters_changed)
        self.wolf_k_slider.valueChanged.connect(self._on_parameters_changed)
        self.nick_window_slider.valueChanged.connect(self._on_parameters_changed)
        self.nick_k_slider.valueChanged.connect(self._on_parameters_changed)
        self.bernsen_window_slider.valueChanged.connect(self._on_parameters_changed)
        self.bernsen_contrast_slider.valueChanged.connect(self._on_parameters_changed)
        
        # 抖动参数信号
        self.dither_strength_slider.valueChanged.connect(self._on_parameters_changed)
        self.dither_matrix_size_slider.valueChanged.connect(self._on_parameters_changed)
        
        # 降噪参数信号
        self.denoise_method_combo.currentIndexChanged.connect(self._on_parameters_changed)
        self.denoise_slider.valueChanged.connect(self._on_parameters_changed)
        
        # 视图模式切换信号
        self.view_mode_switcher.mode_changed.connect(self._on_view_mode_changed)
    
    def _on_parameters_changed(self):
        """参数改变事件"""
        self._update_threshold_enabled()
        self._update_edge_threshold_enabled()
        self._emit_change()
    
    def _on_edge_mode_changed(self):
        """边缘模式改变事件"""
        self._update_edge_threshold_enabled()
        self._emit_change()
    
    def _on_threshold_changed(self, value):
        """阈值改变事件"""
        self.threshold_label.setText(str(value))
        self._emit_change()
    
    def _on_view_mode_changed(self, mode: str):
        """视图模式改变事件"""
        self.view_mode_changed.emit(mode)
    
    def _update_threshold_enabled(self):
        """更新二值化方法参数的显示状态"""
        method = self.method_combo.currentData()
        
        # 隐藏所有参数容器
        self.threshold_container.setVisible(False)
        self.adaptive_params_container.setVisible(False)
        self.sauvola_params_container.setVisible(False)
        self.wolf_params_container.setVisible(False)
        self.nick_params_container.setVisible(False)
        self.bernsen_params_container.setVisible(False)
        self.dithering_params_container.setVisible(False)
        
        # 根据方法显示对应的参数
        if method == 0:  # 固定阈值
            self.threshold_container.setVisible(True)
        elif method == 1:  # 自适应阈值
            self.threshold_container.setVisible(True)
            self.adaptive_params_container.setVisible(True)
        elif method == 2:  # Otsu - 无参数
            pass
        elif method == 3:  # Sauvola
            self.sauvola_params_container.setVisible(True)
        elif method == 4:  # Wolf
            self.wolf_params_container.setVisible(True)
        elif method == 5:  # Nick
            self.nick_params_container.setVisible(True)
        elif method == 6:  # Bernsen
            self.bernsen_params_container.setVisible(True)
        elif method == 7:  # Floyd-Steinberg 抖动
            self.dithering_params_container.setVisible(True)
            self.dither_strength_container.setVisible(True)
            self.dither_matrix_size_container.setVisible(False)
        elif method == 8:  # Ordered 抖动
            self.dithering_params_container.setVisible(True)
            self.dither_strength_container.setVisible(False)
            self.dither_matrix_size_container.setVisible(True)
        elif method == 9:  # Atkinson 抖动
            self.dithering_params_container.setVisible(True)
            self.dither_strength_container.setVisible(True)
            self.dither_matrix_size_container.setVisible(False)
    
    def _update_edge_threshold_enabled(self):
        """更新边缘阈值控件的显示状态"""
        edge_mode = self.edge_mode_combo.currentData()
        # 仅 Canny 模式(1)显示边缘阈值
        visible = (edge_mode == 1)
        self.edge_threshold_container.setVisible(visible)
    
    def _emit_change(self):
        """发射参数改变信号"""
        preprocess_params = self.get_preprocess_params()
        method = self.get_method()
        threshold = self.get_threshold()
        self.parameters_changed.emit(preprocess_params, method, threshold)
    
    def get_method_params(self) -> dict:
        """
        获取当前二值化方法的特定参数
        
        Returns:
            方法参数字典
        """
        method = self.get_method()
        params = {}
        
        if method == 1:  # 自适应阈值
            params['block_size'] = self.adaptive_block_size_slider.value()
        elif method == 3:  # Sauvola
            params['window_size'] = self.sauvola_window_slider.value()
            params['sauvola_k'] = self.sauvola_k_slider.value() * 0.01
            params['sauvola_r'] = self.sauvola_r_slider.value()
        elif method == 4:  # Wolf
            params['window_size'] = self.wolf_window_slider.value()
            params['wolf_k'] = self.wolf_k_slider.value() * 0.01
        elif method == 5:  # Nick
            params['window_size'] = self.nick_window_slider.value()
            params['nick_k'] = self.nick_k_slider.value() * 0.01
        elif method == 6:  # Bernsen
            params['window_size'] = self.bernsen_window_slider.value()
            params['bernsen_contrast'] = self.bernsen_contrast_slider.value()
        elif method in [7, 9]:  # Floyd-Steinberg 或 Atkinson 抖动
            params['dither_strength'] = self.dither_strength_slider.value()
        elif method == 8:  # Ordered 抖动
            params['dither_matrix_size'] = self.dither_matrix_size_slider.value()
        
        return params
    
    def get_preprocess_params(self) -> dict:
        """
        获取预处理参数
        
        Returns:
            预处理参数字典
        """
        return {
            'exposure': self.exposure_slider.value(),
            'contrast': self.contrast_slider.value(),
            'sharpen': self.sharpen_slider.value(),
            'gamma': self.gamma_slider.value() * 0.01,
            'smooth': self.smooth_slider.value(),
            'red_channel': self.red_channel_slider.value(),
            'green_channel': self.green_channel_slider.value(),
            'blue_channel': self.blue_channel_slider.value(),
            'edge_mode': self.edge_mode_combo.currentData(),
            'edge_strength': self.edge_strength_slider.value(),
            'edge_threshold': self.edge_threshold_slider.value(),
            'denoise_method': self.denoise_method_combo.currentData(),
            'denoise': self.denoise_slider.value(),
        }
    
    def get_method(self) -> int:
        """
        获取当前选择的二值化方法
        
        Returns:
            方法编号 (0-6)
        """
        return self.method_combo.currentData()
    
    def get_threshold(self) -> int:
        """
        获取当前阈值
        
        Returns:
            阈值 (0-255)
        """
        return self.threshold_slider.value()
    
    def set_method(self, method: int):
        """
        设置二值化方法
        
        Args:
            method: 方法编号 (0-6)
        """
        for i in range(self.method_combo.count()):
            if self.method_combo.itemData(i) == method:
                self.method_combo.setCurrentIndex(i)
                break
    
    def set_threshold(self, threshold: int):
        """
        设置阈值
        
        Args:
            threshold: 阈值 (0-255)
        """
        self.threshold_slider.setValue(threshold)
    
    def set_enabled(self, enabled: bool):
        """
        设置面板启用状态
        
        Args:
            enabled: 是否启用
        """
        self.method_combo.setEnabled(enabled)
        self.exposure_slider.setEnabled(enabled)
        self.contrast_slider.setEnabled(enabled)
        self.sharpen_slider.setEnabled(enabled)
        self.gamma_slider.setEnabled(enabled)
        self.smooth_slider.setEnabled(enabled)
        self.red_channel_slider.setEnabled(enabled)
        self.green_channel_slider.setEnabled(enabled)
        self.blue_channel_slider.setEnabled(enabled)
    
    def retranslate_ui(self):
        """重新翻译 UI 文本（用于语言切换）"""
        # 更新组标题
        # 注意：QGroupBox 的标题需要通过 setTitle 更新
        # 这里只是示例，实际需要保存对 QGroupBox 的引用
        pass
        self.edge_mode_combo.setEnabled(enabled)
        self.edge_strength_slider.setEnabled(enabled)
        self.edge_threshold_slider.setEnabled(enabled)
        self.threshold_slider.setEnabled(enabled)
        self.denoise_method_combo.setEnabled(enabled)
        self.denoise_slider.setEnabled(enabled)
        
        if enabled:
            self._update_threshold_enabled()
            self._update_edge_threshold_enabled()
