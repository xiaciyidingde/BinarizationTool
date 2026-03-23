"""
二值化设置面板

提供预处理和二值化参数调整控件。
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                QComboBox, QSlider, QGroupBox, QScrollArea, QCheckBox, QStyledItemDelegate)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QIcon, QPainter
from .view_mode_switcher import ViewModeSwitcher


class BinarizationPanel(QWidget):
    """
    二值化设置面板类
    
    提供预处理参数和二值化方法选择控件。
    """
    
    # 信号：参数改变 (preprocess_params, binarization_method, threshold)
    parameters_changed = Signal(dict, int, int)
    
    # 信号：视图模式改变 (mode: 'original', 'preprocessed', 'binary')
    view_mode_changed = Signal(str)
    
    def __init__(self, parent=None):
        """
        初始化二值化面板
        
        Args:
            parent: 父窗口部件
        """
        super().__init__(parent)
        
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
        outer_layout.setContentsMargins(6, 6, 6, 6)
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
        view_mode_layout.setContentsMargins(8, 8, 8, 8)
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
        settings_layout.setContentsMargins(8, 8, 8, 8)
        settings_layout.setSpacing(8)
        
        # === 预处理参数 ===
        preprocess_group = QGroupBox("预处理")
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
        
        # 曝光度
        self.exposure_slider = self._create_slider_with_label(
            "曝光度:", -100, 100, 0, preprocess_layout
        )
        
        # 对比度
        self.contrast_slider = self._create_slider_with_label(
            "对比度:", -100, 100, 0, preprocess_layout
        )
        
        # 锐化
        self.sharpen_slider = self._create_slider_with_label(
            "锐化:", 0, 100, 0, preprocess_layout
        )
        
        # 伽马
        self.gamma_slider = self._create_slider_with_label(
            "伽马:", 10, 300, 100, preprocess_layout, scale=0.01
        )
        
        # 平滑
        self.smooth_slider = self._create_slider_with_label(
            "平滑:", 0, 100, 0, preprocess_layout
        )
        
        preprocess_group.setLayout(preprocess_layout)
        settings_layout.addWidget(preprocess_group)
        
        # === RGB 通道调整 ===
        rgb_group = QGroupBox("RGB 通道")
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
        self.red_channel_slider = self._create_slider_with_label(
            "红色通道:", -100, 100, 0, rgb_layout
        )
        
        # 绿色通道
        self.green_channel_slider = self._create_slider_with_label(
            "绿色通道:", -100, 100, 0, rgb_layout
        )
        
        # 蓝色通道
        self.blue_channel_slider = self._create_slider_with_label(
            "蓝色通道:", -100, 100, 0, rgb_layout
        )
        
        rgb_group.setLayout(rgb_layout)
        settings_layout.addWidget(rgb_group)
        
        # === 边缘检测 ===
        edge_group = QGroupBox("边缘检测")
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
        edge_mode_label = QLabel("边缘模式:")
        edge_mode_label.setMinimumWidth(70)
        edge_mode_row.addWidget(edge_mode_label)
        
        # 添加占位空间（对齐数值标签位置）
        edge_mode_row.addSpacing(25)
        
        self.edge_mode_combo = QComboBox()
        self.edge_mode_combo.setFixedWidth(120)
        self.edge_mode_combo.addItem("关闭", 0)
        self.edge_mode_combo.addItem("Canny 边缘", 1)
        self.edge_mode_combo.addItem("边缘增强", 2)
        self.edge_mode_combo.addItem("轮廓保留", 3)
        
        edge_mode_row.addWidget(self.edge_mode_combo)
        edge_mode_row.addStretch()
        edge_layout.addLayout(edge_mode_row)
        
        # 边缘强度
        self.edge_strength_slider = self._create_slider_with_label(
            "边缘强度:", 0, 100, 50, edge_layout
        )
        
        # 边缘阈值（仅 Canny 模式显示）- 手动创建以便隐藏整行
        self.edge_threshold_row = QHBoxLayout()
        
        edge_threshold_label = QLabel("边缘阈值:")
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
        
        # 创建一个容器 widget 来包装边缘阈值行，方便隐藏
        self.edge_threshold_container = QWidget()
        self.edge_threshold_container.setLayout(self.edge_threshold_row)
        edge_layout.addWidget(self.edge_threshold_container)
        
        edge_group.setLayout(edge_layout)
        settings_layout.addWidget(edge_group)
        
        # === 二值化方法 ===
        binarization_group = QGroupBox("二值化")
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
        method_label = QLabel("二值化方法:")
        method_label.setMinimumWidth(70)
        method_row.addWidget(method_label)
        
        # 添加占位空间（对齐数值标签位置）
        method_row.addSpacing(25)
        
        self.method_combo = QComboBox()
        self.method_combo.setFixedWidth(120)
        self.method_combo.addItem("固定阈值", 0)
        self.method_combo.addItem("自适应阈值", 1)
        self.method_combo.addItem("Otsu 自动阈值", 2)
        self.method_combo.addItem("Sauvola 阈值", 3)
        self.method_combo.addItem("Wolf 阈值", 4)
        self.method_combo.addItem("Nick 阈值", 5)
        self.method_combo.addItem("Bernsen 阈值", 6)
        self.method_combo.setCurrentIndex(1)  # 默认自适应阈值
        
        method_row.addWidget(self.method_combo)
        method_row.addStretch()
        binarization_layout.addLayout(method_row)
        
        # 阈值（左右布局）- 手动创建以便隐藏整行
        self.threshold_row = QHBoxLayout()
        threshold_label_text = QLabel("阈值:")
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
        
        binarization_group.setLayout(binarization_layout)
        settings_layout.addWidget(binarization_group)
        
        # === 降噪功能 ===
        denoise_group = QGroupBox("降噪")
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
        denoise_method_label = QLabel("降噪方法:")
        denoise_method_label.setMinimumWidth(70)
        denoise_method_row.addWidget(denoise_method_label)
        
        # 添加占位空间（对齐数值标签位置）
        denoise_method_row.addSpacing(25)
        
        self.denoise_method_combo = QComboBox()
        self.denoise_method_combo.setFixedWidth(120)
        self.denoise_method_combo.addItem("高斯降噪", 0)
        self.denoise_method_combo.addItem("中值滤波", 1)
        self.denoise_method_combo.addItem("双边滤波", 2)
        self.denoise_method_combo.addItem("NLMeans降噪", 3)
        self.denoise_method_combo.addItem("形态学-开运算", 4)
        self.denoise_method_combo.addItem("形态学-闭运算", 5)
        
        denoise_method_row.addWidget(self.denoise_method_combo)
        denoise_method_row.addStretch()
        denoise_layout.addLayout(denoise_method_row)
        
        # 降噪强度
        self.denoise_slider = self._create_slider_with_label(
            "降噪强度:", 0, 100, 0, denoise_layout
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
    
    def _create_slider_with_label(self, label_text, min_val, max_val, default_val, 
                                  parent_layout, scale=1.0):
        """创建带标签的滑块（左右布局）"""
        # 标签和滑块的水平布局
        row_layout = QHBoxLayout()
        
        # 左侧：标签
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
        
        return slider
    
    def _create_adaptive_params(self):
        """创建自适应阈值参数容器"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # 块大小
        self.adaptive_block_size_slider = self._create_slider_with_label(
            "块大小:", 3, 51, 11, layout
        )
        
        return container
    
    def _create_sauvola_params(self):
        """创建 Sauvola 参数容器"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # 窗口大小
        self.sauvola_window_slider = self._create_slider_with_label(
            "窗口大小:", 3, 51, 15, layout
        )
        
        # k 参数
        self.sauvola_k_slider = self._create_slider_with_label(
            "k 参数:", 0, 100, 20, layout, scale=0.01
        )
        
        # R 参数
        self.sauvola_r_slider = self._create_slider_with_label(
            "R 参数:", 0, 255, 128, layout
        )
        
        return container
    
    def _create_wolf_params(self):
        """创建 Wolf 参数容器"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # 窗口大小
        self.wolf_window_slider = self._create_slider_with_label(
            "窗口大小:", 3, 51, 15, layout
        )
        
        # k 参数
        self.wolf_k_slider = self._create_slider_with_label(
            "k 参数:", 0, 100, 50, layout, scale=0.01
        )
        
        return container
    
    def _create_nick_params(self):
        """创建 Nick 参数容器"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # 窗口大小
        self.nick_window_slider = self._create_slider_with_label(
            "窗口大小:", 3, 51, 15, layout
        )
        
        # k 参数 (-1.0 到 0.0)
        self.nick_k_slider = self._create_slider_with_label(
            "k 参数:", -100, 0, -10, layout, scale=0.01
        )
        
        return container
    
    def _create_bernsen_params(self):
        """创建 Bernsen 参数容器"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # 窗口大小
        self.bernsen_window_slider = self._create_slider_with_label(
            "窗口大小:", 3, 51, 15, layout
        )
        
        # 对比度阈值
        self.bernsen_contrast_slider = self._create_slider_with_label(
            "对比度阈值:", 0, 255, 15, layout
        )
        
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
        self.edge_mode_combo.setEnabled(enabled)
        self.edge_strength_slider.setEnabled(enabled)
        self.edge_threshold_slider.setEnabled(enabled)
        self.threshold_slider.setEnabled(enabled)
        self.denoise_method_combo.setEnabled(enabled)
        self.denoise_slider.setEnabled(enabled)
        
        if enabled:
            self._update_threshold_enabled()
            self._update_edge_threshold_enabled()
