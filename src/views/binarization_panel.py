"""
二值化设置面板

提供预处理和二值化参数调整控件。
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                QComboBox, QSlider, QGroupBox, QScrollArea, QCheckBox, QStyledItemDelegate)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QIcon, QPainter
from ..utils.resources import THREE_BARS_BYTES
import tempfile
import os


class BinarizationPanel(QWidget):
    """
    二值化设置面板类
    
    提供预处理参数和二值化方法选择控件。
    """
    
    # 信号：参数改变 (preprocess_params, binarization_method, threshold)
    parameters_changed = Signal(dict, int, int)
    
    def __init__(self, parent=None):
        """
        初始化二值化面板
        
        Args:
            parent: 父窗口部件
        """
        super().__init__(parent)
        
        # 初始化临时图标路径
        self._temp_icon_path = None
        
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """设置 UI 布局"""
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 外层容器（用于居中和限制宽度）
        outer_container = QWidget()
        outer_layout = QHBoxLayout(outer_container)
        outer_layout.setContentsMargins(6, 6, 6, 6)
        
        # 内容容器（带背景和圆角）
        content = QWidget()
        content.setObjectName("binarizationPanelContent")
        content.setStyleSheet("""
            QWidget#binarizationPanelContent {
                background-color: #ffffff;
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
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
        layout.addWidget(preprocess_group)
        
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
        
        # 设置自定义下拉图标
        self._set_combobox_icon(self.method_combo)
        
        method_row.addWidget(self.method_combo)
        method_row.addStretch()
        binarization_layout.addLayout(method_row)
        
        # 阈值（左右布局）
        threshold_row = QHBoxLayout()
        threshold_label_text = QLabel("阈值:")
        threshold_label_text.setMinimumWidth(70)
        threshold_row.addWidget(threshold_label_text)
        
        self.threshold_label = QLabel("127")
        self.threshold_label.setMinimumWidth(25)
        self.threshold_label.setMaximumWidth(25)
        self.threshold_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        threshold_row.addWidget(self.threshold_label)
        
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setMinimum(0)
        self.threshold_slider.setMaximum(255)
        self.threshold_slider.setValue(127)
        threshold_row.addWidget(self.threshold_slider, 1)
        binarization_layout.addLayout(threshold_row)
        
        binarization_group.setLayout(binarization_layout)
        layout.addWidget(binarization_group)
        
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
        
        # 设置自定义下拉图标
        self._set_combobox_icon(self.denoise_method_combo)
        
        denoise_method_row.addWidget(self.denoise_method_combo)
        denoise_method_row.addStretch()
        denoise_layout.addLayout(denoise_method_row)
        
        # 降噪强度
        self.denoise_slider = self._create_slider_with_label(
            "降噪强度:", 0, 100, 0, denoise_layout
        )
        
        denoise_group.setLayout(denoise_layout)
        layout.addWidget(denoise_group)
        
        # 添加弹性空间
        layout.addStretch()
        
        # 将内容容器添加到外层布局
        outer_layout.addWidget(content)
        
        # 设置滚动区域
        scroll.setWidget(outer_container)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        
        # 初始状态：固定阈值控件启用
        self._update_threshold_enabled()
    
    def _set_combobox_icon(self, combobox):
        """为 QComboBox 设置自定义下拉图标"""
        # 如果还没有创建临时图标文件，创建一个
        if self._temp_icon_path is None:
            # 创建临时文件
            temp_dir = tempfile.gettempdir()
            self._temp_icon_path = os.path.join(temp_dir, 'three_bars_icon.png')
            
            # 保存图标到临时文件
            pixmap = QPixmap()
            pixmap.loadFromData(THREE_BARS_BYTES)
            pixmap.save(self._temp_icon_path, 'PNG')
        
        # 使用 QSS 设置图标
        # 注意：Windows 路径需要转换为正斜杠
        icon_path = self._temp_icon_path.replace('\\', '/')
        combobox.setStyleSheet(f"""
            QComboBox::down-arrow {{
                image: url({icon_path});
                width: 16px;
                height: 16px;
                border: none;
                border-left: none;
                border-right: none;
                border-top: none;
                border-bottom: none;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 24px;
                border: none;
                border-left: none;
                background: transparent;
            }}
        """)
    
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
        self.denoise_method_combo.currentIndexChanged.connect(self._on_parameters_changed)
        self.denoise_slider.valueChanged.connect(self._on_parameters_changed)
    
    def _on_parameters_changed(self):
        """参数改变事件"""
        self._update_threshold_enabled()
        self._emit_change()
    
    def _on_threshold_changed(self, value):
        """阈值改变事件"""
        self.threshold_label.setText(str(value))
        self._emit_change()
    
    def _update_threshold_enabled(self):
        """更新阈值控件的启用状态"""
        method = self.method_combo.currentData()
        # 固定阈值(0)和自适应阈值(1)需要手动设置阈值参数
        enabled = (method == 0 or method == 1)
        self.threshold_slider.setEnabled(enabled)
        self.threshold_label.setEnabled(enabled)
    
    def _emit_change(self):
        """发射参数改变信号"""
        preprocess_params = self.get_preprocess_params()
        method = self.get_method()
        threshold = self.get_threshold()
        self.parameters_changed.emit(preprocess_params, method, threshold)
    
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
        self.denoise_method_combo.setEnabled(enabled)
        self.denoise_slider.setEnabled(enabled)
        
        if enabled:
            self._update_threshold_enabled()
        else:
            self.threshold_slider.setEnabled(False)
