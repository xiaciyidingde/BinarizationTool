"""
二值化设置面板

提供预处理和二值化参数调整控件。
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                QComboBox, QSlider, QGroupBox, QScrollArea, QCheckBox)
from PySide6.QtCore import Qt, Signal


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
        
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """设置 UI 布局"""
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 内容部件
        content = QWidget()
        layout = QVBoxLayout(content)
        
        # === 预处理参数组 ===
        preprocess_group = QGroupBox("图像预处理")
        preprocess_layout = QVBoxLayout()
        
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
        
        # 平滑/降噪
        self.smooth_slider = self._create_slider_with_label(
            "平滑:", 0, 100, 0, preprocess_layout
        )
        
        preprocess_group.setLayout(preprocess_layout)
        layout.addWidget(preprocess_group)
        
        # === 二值化方法组 ===
        method_group = QGroupBox("二值化方法")
        method_layout = QVBoxLayout()
        
        # 方法选择下拉框
        self.method_combo = QComboBox()
        self.method_combo.addItem("固定阈值", 0)
        self.method_combo.addItem("自适应阈值", 1)
        self.method_combo.addItem("Otsu 自动阈值", 2)
        self.method_combo.addItem("Sauvola 阈值", 3)
        self.method_combo.addItem("Wolf 阈值", 4)
        self.method_combo.addItem("Nick 阈值", 5)
        self.method_combo.addItem("Bernsen 阈值", 6)
        self.method_combo.setCurrentIndex(1)  # 默认自适应阈值
        method_layout.addWidget(self.method_combo)
        
        method_group.setLayout(method_layout)
        layout.addWidget(method_group)
        
        # === 阈值参数组 ===
        threshold_group = QGroupBox("阈值参数")
        threshold_layout = QVBoxLayout()
        
        # 阈值标签
        threshold_label_layout = QHBoxLayout()
        threshold_label_layout.addWidget(QLabel("阈值:"))
        self.threshold_label = QLabel("127")
        threshold_label_layout.addWidget(self.threshold_label)
        threshold_label_layout.addStretch()
        threshold_layout.addLayout(threshold_label_layout)
        
        # 阈值滑块
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setMinimum(0)
        self.threshold_slider.setMaximum(255)
        self.threshold_slider.setValue(127)
        self.threshold_slider.setTickPosition(QSlider.TicksBelow)
        self.threshold_slider.setTickInterval(25)
        threshold_layout.addWidget(self.threshold_slider)
        
        threshold_group.setLayout(threshold_layout)
        layout.addWidget(threshold_group)
        
        # 添加弹性空间
        layout.addStretch()
        
        # 设置滚动区域
        scroll.setWidget(content)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        
        # 初始状态：固定阈值控件启用
        self._update_threshold_enabled()
    
    def _create_slider_with_label(self, label_text, min_val, max_val, default_val, 
                                  parent_layout, scale=1.0):
        """创建带标签的滑块"""
        # 标签行
        label_layout = QHBoxLayout()
        label_layout.addWidget(QLabel(label_text))
        value_label = QLabel(str(int(default_val * scale)))
        label_layout.addWidget(value_label)
        label_layout.addStretch()
        parent_layout.addLayout(label_layout)
        
        # 滑块
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(default_val)
        slider.setTickPosition(QSlider.TicksBelow)
        slider.setTickInterval((max_val - min_val) // 4)
        parent_layout.addWidget(slider)
        
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
        
        if enabled:
            self._update_threshold_enabled()
        else:
            self.threshold_slider.setEnabled(False)
