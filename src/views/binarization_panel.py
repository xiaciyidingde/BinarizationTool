"""
二值化设置面板

提供预处理和二值化参数调整控件。
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..utils.translation_manager import get_translator
from ..widgets.animated_tab_widget import AnimatedTabWidget
from ..widgets.custom_combobox import CustomComboBox
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

    # 信号：图像变换操作 (operation: 'invert', 'flip_horizontal', 'flip_vertical')
    image_transform = Signal(str)
    
    # 信号：请求 AI 处理 (model_type: str)
    ai_process_requested = Signal(str)

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
        # 计算 QGroupBox 的最大宽度
        # 面板宽度 - 外层左右边距(12*2) - 标签页内容左右边距(12*2) = 300 - 48 = 252
        self.group_max_width = panel_width - 48

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
        outer_layout.setContentsMargins(12, 6, 12, 6)  # 恢复左右边距12px
        outer_layout.setSpacing(8)

        # === 视图模式切换器区域（独立背景） ===
        view_mode_container = QWidget()
        view_mode_container.setObjectName("viewModeContainer")
        # 移除内联样式，让主题文件控制
        view_mode_layout = QVBoxLayout(view_mode_container)
        view_mode_layout.setContentsMargins(12, 8, 12, 8)  # 左右边距12px
        view_mode_layout.setSpacing(0)

        self.view_mode_switcher = ViewModeSwitcher()
        view_mode_layout.addWidget(self.view_mode_switcher)

        outer_layout.addWidget(view_mode_container)

        # === 当前图层显示区域（独立背景） ===
        layer_info_outer = QWidget()
        layer_info_outer.setObjectName("currentLayerContainer")
        layer_info_outer_layout = QVBoxLayout(layer_info_outer)
        layer_info_outer_layout.setContentsMargins(12, 8, 12, 8)
        layer_info_outer_layout.setSpacing(0)
        
        # 当前图层标签
        self.current_layer_label = QLabel(self.tr.tr('binarization_panel.current_layer', layer=self.tr.tr('binarization_panel.root_layer')))
        self.current_layer_label.setObjectName("currentLayerLabel")
        self.current_layer_label.setAlignment(Qt.AlignCenter)  # 居中对齐
        layer_info_outer_layout.addWidget(self.current_layer_label)
        
        outer_layout.addWidget(layer_info_outer)

        # === 标签页组件 ===
        # 创建标签页组件
        self.tab_widget = AnimatedTabWidget()
        self.tab_widget.setObjectName("binarizationPanelTabs")
        # 移除内联样式，让主题文件控制

        # 创建预处理标签页
        preprocess_tab = self._create_preprocess_tab()
        self.tab_widget.addTab(preprocess_tab, self.tr.tr('binarization_panel.tab_preprocess'))

        # 创建二值化标签页
        binarization_tab = self._create_binarization_tab()
        self.tab_widget.addTab(binarization_tab, self.tr.tr('binarization_panel.tab_binarization'))

        # 创建其他标签页
        other_tab = self._create_other_tab()
        self.tab_widget.addTab(other_tab, self.tr.tr('binarization_panel.tab_other'))

        # 默认显示预处理标签页
        self.tab_widget.setCurrentIndex(0)

        outer_layout.addWidget(self.tab_widget)

        # 设置滚动区域
        scroll.setWidget(outer_container)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

        # 初始状态:固定阈值控件启用
        self._update_threshold_enabled()
        self._update_edge_threshold_enabled()

    def _create_preprocess_tab(self):
        """创建预处理标签页"""
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)

        # 标签页内容容器
        tab_content = QWidget()
        tab_content.setStyleSheet("background-color: transparent;")
        settings_layout = QVBoxLayout(tab_content)
        settings_layout.setContentsMargins(12, 8, 12, 8)  # 左右边距12px
        settings_layout.setSpacing(8)

        # === AI 工具（如果有模型） ===
        import os
        model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'model')
        has_rmbg_model = False
        has_onnxruntime = False
        
        # 检查是否安装了 onnxruntime
        try:
            import onnxruntime
            has_onnxruntime = True
        except ImportError:
            pass
        
        # 检查是否有模型文件
        if has_onnxruntime and os.path.exists(model_dir):
            for filename in os.listdir(model_dir):
                if filename.startswith('RMBG') and filename.endswith('.onnx'):
                    has_rmbg_model = True
                    break
        
        # 始终显示 AI 工具组
        ai_tools_group = QGroupBox(self.tr.tr('binarization_panel.ai_tools'))
        ai_tools_layout = QVBoxLayout()
        ai_tools_layout.setSpacing(6)
        
        # 始终显示"去除背景"按钮
        self.remove_bg_button = QPushButton(self.tr.tr('binarization_panel.remove_background'))
        self.remove_bg_button.setEnabled(False)  # 初始禁用，加载图片后启用
        self.remove_bg_button.clicked.connect(self._on_remove_bg_clicked)
        ai_tools_layout.addWidget(self.remove_bg_button)
        
        # 保存模型状态
        self.has_rmbg_model = has_rmbg_model
        self.has_onnxruntime = has_onnxruntime
        
        # 如果没有 onnxruntime，显示提示
        if not has_onnxruntime:
            hint_label = QLabel(self.tr.tr('binarization_panel.install_onnxruntime_hint'))
            hint_label.setWordWrap(True)
            hint_label.setStyleSheet("QLabel { color: #666; font-size: 10px; }")
            ai_tools_layout.addWidget(hint_label)
        
        ai_tools_group.setLayout(ai_tools_layout)
        settings_layout.addWidget(ai_tools_group)

        # === 预处理参数 ===
        preprocess_group = QGroupBox(self.tr.tr('binarization_panel.preprocess'))
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

        # 添加弹性空间
        settings_layout.addStretch()

        scroll.setWidget(tab_content)
        return scroll

    def _create_binarization_tab(self):
        """创建二值化标签页"""
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)

        # 标签页内容容器
        tab_content = QWidget()
        tab_content.setStyleSheet("background-color: transparent;")
        settings_layout = QVBoxLayout(tab_content)
        settings_layout.setContentsMargins(12, 8, 12, 8)  # 左右边距12px
        settings_layout.setSpacing(8)

        # === 边缘检测 ===
        edge_group = QGroupBox(self.tr.tr('binarization_panel.edge_detection'))
        edge_layout = QVBoxLayout()
        edge_layout.setSpacing(6)

        # 边缘模式（左右布局）
        edge_mode_row = QHBoxLayout()
        edge_mode_label = QLabel(self.tr.tr('binarization_panel.edge_mode'))
        edge_mode_label.setMinimumWidth(70)
        edge_mode_row.addWidget(edge_mode_label)

        self.edge_mode_combo = CustomComboBox()
        self.edge_mode_combo.setFixedWidth(130)
        self.edge_mode_combo.addItem(self.tr.tr('binarization_panel.edge_off'), 0)
        self.edge_mode_combo.addItem(self.tr.tr('binarization_panel.edge_canny'), 1)
        self.edge_mode_combo.addItem(self.tr.tr('binarization_panel.edge_enhance'), 2)
        self.edge_mode_combo.addItem(self.tr.tr('binarization_panel.edge_contour'), 3)

        edge_mode_row.addWidget(self.edge_mode_combo)

        edge_layout.addLayout(edge_mode_row)

        # 边缘强度 - 创建行布局以便隐藏
        self.edge_strength_row = QHBoxLayout()
        self.edge_strength_row.setContentsMargins(0, 0, 0, 0)

        # 提取标签文本
        full_text = self.tr.tr('binarization_panel.edge_strength', value='')
        label_text = full_text.replace('{value}', '').strip()
        if not label_text.endswith('：') and not label_text.endswith(':'):
            label_text += '：' if '：' in full_text else ':'

        edge_strength_label = QLabel(label_text)
        edge_strength_label.setMinimumWidth(70)
        self.edge_strength_row.addWidget(edge_strength_label)

        self.edge_strength_value_label = QLabel("50")
        self.edge_strength_value_label.setMinimumWidth(25)
        self.edge_strength_value_label.setMaximumWidth(25)
        self.edge_strength_value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.edge_strength_row.addWidget(self.edge_strength_value_label)

        self.edge_strength_slider = QSlider(Qt.Horizontal)
        self.edge_strength_slider.setMinimum(0)
        self.edge_strength_slider.setMaximum(100)
        self.edge_strength_slider.setValue(50)
        self.edge_strength_slider.valueChanged.connect(
            lambda v: self.edge_strength_value_label.setText(str(v))
        )
        self.edge_strength_row.addWidget(self.edge_strength_slider, 1)

        # 重置按钮
        from ..utils.animations import create_rotation_animation
        from ..utils.resources import REFRESH
        edge_strength_reset_btn = QPushButton()
        edge_strength_reset_btn.setObjectName("resetButton")
        edge_strength_reset_btn.setIcon(QIcon(QPixmap.fromImage(QImage.fromData(REFRESH))))
        edge_strength_reset_btn.setFixedSize(24, 24)
        # 移除内联样式，让主题文件控制

        def reset_edge_strength():
            # 如果按钮已禁用（动画中），忽略点击
            if not edge_strength_reset_btn.isEnabled():
                return

            # 禁用按钮防止重复点击
            edge_strength_reset_btn.setEnabled(False)

            animation = create_rotation_animation(edge_strength_reset_btn, duration=300, angle=360)

            # 动画结束后重新启用按钮
            animation.on_finished(lambda: edge_strength_reset_btn.setEnabled(True))

            animation.start()
            self.edge_strength_slider.setValue(50)

        edge_strength_reset_btn.clicked.connect(reset_edge_strength)
        self.edge_strength_row.addWidget(edge_strength_reset_btn)

        # 创建容器以便隐藏
        self.edge_strength_container = QWidget()
        self.edge_strength_container.setLayout(self.edge_strength_row)
        self.edge_strength_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        edge_layout.addWidget(self.edge_strength_container)

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
        edge_threshold_reset_btn = QPushButton()
        edge_threshold_reset_btn.setObjectName("resetButton")
        edge_threshold_reset_btn.setIcon(QIcon(QPixmap.fromImage(QImage.fromData(REFRESH))))
        edge_threshold_reset_btn.setFixedSize(24, 24)
        # 移除内联样式，让主题文件控制

        def reset_edge_threshold():
            # 如果按钮已禁用（动画中），忽略点击
            if not edge_threshold_reset_btn.isEnabled():
                return

            # 禁用按钮防止重复点击
            edge_threshold_reset_btn.setEnabled(False)

            animation = create_rotation_animation(edge_threshold_reset_btn, duration=300, angle=360)

            # 动画结束后重新启用按钮
            animation.on_finished(lambda: edge_threshold_reset_btn.setEnabled(True))

            animation.start()
            self.edge_threshold_slider.setValue(150)

        edge_threshold_reset_btn.clicked.connect(reset_edge_threshold)
        self.edge_threshold_row.addWidget(edge_threshold_reset_btn)

        # 创建一个容器 widget 来包装边缘阈值行，方便隐藏
        self.edge_threshold_container = QWidget()
        self.edge_threshold_container.setLayout(self.edge_threshold_row)
        self.edge_threshold_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        edge_layout.addWidget(self.edge_threshold_container)

        edge_group.setLayout(edge_layout)
        settings_layout.addWidget(edge_group)

        # === 二值化方法 ===
        binarization_group = QGroupBox(self.tr.tr('binarization_panel.binarization'))
        binarization_layout = QVBoxLayout()
        binarization_layout.setSpacing(6)

        # 方法选择（左右布局）
        method_row = QHBoxLayout()
        method_label = QLabel(self.tr.tr('binarization_panel.method'))
        method_label.setMinimumWidth(70)
        method_row.addWidget(method_label)

        self.method_combo = CustomComboBox()
        self.method_combo.setFixedWidth(130)
        self.method_combo.addItem(self.tr.tr('binarization_panel.method_fixed'), 0)
        self.method_combo.addItem(self.tr.tr('binarization_panel.method_adaptive'), 1)
        self.method_combo.addItem(self.tr.tr('binarization_panel.method_otsu'), 2)
        self.method_combo.addItem(self.tr.tr('binarization_panel.method_sauvola'), 3)
        self.method_combo.addItem(self.tr.tr('binarization_panel.method_wolf'), 4)
        self.method_combo.addItem(self.tr.tr('binarization_panel.method_nick'), 5)
        self.method_combo.addItem(self.tr.tr('binarization_panel.method_bernsen'), 6)
        # 添加分隔线
        self.method_combo.insertSeparator(7)
        self.method_combo.addItem(self.tr.tr('binarization_panel.method_floyd'), 7)
        self.method_combo.addItem(self.tr.tr('binarization_panel.method_ordered'), 8)
        self.method_combo.addItem(self.tr.tr('binarization_panel.method_atkinson'), 9)
        self.method_combo.setCurrentIndex(1)  # 默认自适应阈值

        method_row.addWidget(self.method_combo)

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
        threshold_reset_btn = QPushButton()
        threshold_reset_btn.setIcon(QIcon(QPixmap.fromImage(QImage.fromData(REFRESH))))
        threshold_reset_btn.setFixedSize(24, 24)
        threshold_reset_btn.setObjectName("resetButton")

        def reset_threshold():
            # 如果按钮已禁用（动画中），忽略点击
            if not threshold_reset_btn.isEnabled():
                return

            # 禁用按钮防止重复点击
            threshold_reset_btn.setEnabled(False)

            animation = create_rotation_animation(threshold_reset_btn, duration=300, angle=360)

            # 动画结束后重新启用按钮
            animation.on_finished(lambda: threshold_reset_btn.setEnabled(True))

            animation.start()
            self.threshold_slider.setValue(127)

        threshold_reset_btn.clicked.connect(reset_threshold)
        self.threshold_row.addWidget(threshold_reset_btn)

        # 创建一个容器 widget 来包装阈值行，方便隐藏
        self.threshold_container = QWidget()
        self.threshold_container.setLayout(self.threshold_row)
        self.threshold_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
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
        denoise_layout = QVBoxLayout()
        denoise_layout.setSpacing(6)

        # 降噪方法（左右布局）
        denoise_method_row = QHBoxLayout()
        denoise_method_label = QLabel(self.tr.tr('binarization_panel.denoise_method'))
        denoise_method_label.setMinimumWidth(70)
        denoise_method_row.addWidget(denoise_method_label)

        self.denoise_method_combo = CustomComboBox()
        self.denoise_method_combo.setFixedWidth(130)
        self.denoise_method_combo.addItem(self.tr.tr('binarization_panel.denoise_gaussian'), 0)
        self.denoise_method_combo.addItem(self.tr.tr('binarization_panel.denoise_median'), 1)
        self.denoise_method_combo.addItem(self.tr.tr('binarization_panel.denoise_bilateral'), 2)
        self.denoise_method_combo.addItem(self.tr.tr('binarization_panel.denoise_nlmeans'), 3)
        self.denoise_method_combo.addItem(self.tr.tr('binarization_panel.denoise_morph_open'), 4)
        self.denoise_method_combo.addItem(self.tr.tr('binarization_panel.denoise_morph_close'), 5)

        denoise_method_row.addWidget(self.denoise_method_combo)

        denoise_layout.addLayout(denoise_method_row)

        # 降噪强度
        self.denoise_slider = self._create_slider_with_reset(
            "denoise_strength", 0, 100, 0, denoise_layout
        )

        denoise_group.setLayout(denoise_layout)
        settings_layout.addWidget(denoise_group)

        # 添加弹性空间
        settings_layout.addStretch()

        scroll.setWidget(tab_content)
        return scroll

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
        from ..utils.animations import create_rotation_animation
        from ..utils.resources import REFRESH
        reset_btn = QPushButton()
        reset_btn.setIcon(QIcon(QPixmap.fromImage(QImage.fromData(REFRESH))))
        reset_btn.setFixedSize(24, 24)
        reset_btn.setObjectName("resetButton")

        # 重置按钮点击事件（带动画）
        def reset_value():
            # 如果按钮已禁用（动画中），忽略点击
            if not reset_btn.isEnabled():
                return

            # 禁用按钮防止重复点击
            reset_btn.setEnabled(False)

            # 播放旋转动画
            animation = create_rotation_animation(reset_btn, duration=300, angle=360)

            # 动画结束后重新启用按钮
            animation.on_finished(lambda: reset_btn.setEnabled(True))

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

    def _create_other_tab(self):
        """创建其他标签页"""
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)

        # 标签页内容容器
        tab_content = QWidget()
        tab_content.setStyleSheet("background-color: transparent;")
        settings_layout = QVBoxLayout(tab_content)
        settings_layout.setContentsMargins(12, 8, 12, 8)
        settings_layout.setSpacing(8)

        # === 图像变换 ===
        transform_group = QGroupBox(self.tr.tr('binarization_panel.image_transform'))
        transform_layout = QVBoxLayout()
        transform_layout.setSpacing(8)

        # 导入图标资源
        from ..utils.resources import CHECKED, UNCHECKED

        # 反相
        invert_row = QHBoxLayout()
        invert_row.setSpacing(8)
        self.invert_checkbox = QPushButton()
        self.invert_checkbox.setObjectName("iconCheckbox")
        self.invert_checkbox.setFixedSize(32, 32)
        self.invert_checkbox.setCheckable(True)
        self.invert_checkbox.setEnabled(False)
        self.invert_checkbox.setStyleSheet("QPushButton { border: none; background: transparent; }")
        self.invert_checkbox.setIcon(QIcon(QPixmap.fromImage(QImage.fromData(UNCHECKED))))
        self.invert_checkbox.setIconSize(QPixmap.fromImage(QImage.fromData(UNCHECKED)).size().scaled(24, 24, Qt.KeepAspectRatio))
        self.invert_checkbox.clicked.connect(self._on_invert_changed)
        invert_label = QLabel(self.tr.tr('binarization_panel.invert_image'))
        invert_label.setMinimumHeight(32)
        invert_row.addWidget(self.invert_checkbox)
        invert_row.addWidget(invert_label, 1)
        transform_layout.addLayout(invert_row)

        # 水平翻转
        flip_h_row = QHBoxLayout()
        flip_h_row.setSpacing(8)
        self.flip_horizontal_checkbox = QPushButton()
        self.flip_horizontal_checkbox.setObjectName("iconCheckbox")
        self.flip_horizontal_checkbox.setFixedSize(32, 32)
        self.flip_horizontal_checkbox.setCheckable(True)
        self.flip_horizontal_checkbox.setEnabled(False)
        self.flip_horizontal_checkbox.setStyleSheet("QPushButton { border: none; background: transparent; }")
        self.flip_horizontal_checkbox.setIcon(QIcon(QPixmap.fromImage(QImage.fromData(UNCHECKED))))
        self.flip_horizontal_checkbox.setIconSize(QPixmap.fromImage(QImage.fromData(UNCHECKED)).size().scaled(24, 24, Qt.KeepAspectRatio))
        self.flip_horizontal_checkbox.clicked.connect(self._on_flip_horizontal_changed)
        flip_h_label = QLabel(self.tr.tr('binarization_panel.flip_horizontal'))
        flip_h_label.setMinimumHeight(32)
        flip_h_row.addWidget(self.flip_horizontal_checkbox)
        flip_h_row.addWidget(flip_h_label, 1)
        transform_layout.addLayout(flip_h_row)

        # 垂直翻转
        flip_v_row = QHBoxLayout()
        flip_v_row.setSpacing(8)
        self.flip_vertical_checkbox = QPushButton()
        self.flip_vertical_checkbox.setObjectName("iconCheckbox")
        self.flip_vertical_checkbox.setFixedSize(32, 32)
        self.flip_vertical_checkbox.setCheckable(True)
        self.flip_vertical_checkbox.setEnabled(False)
        self.flip_vertical_checkbox.setStyleSheet("QPushButton { border: none; background: transparent; }")
        self.flip_vertical_checkbox.setIcon(QIcon(QPixmap.fromImage(QImage.fromData(UNCHECKED))))
        self.flip_vertical_checkbox.setIconSize(QPixmap.fromImage(QImage.fromData(UNCHECKED)).size().scaled(24, 24, Qt.KeepAspectRatio))
        self.flip_vertical_checkbox.clicked.connect(self._on_flip_vertical_changed)
        flip_v_label = QLabel(self.tr.tr('binarization_panel.flip_vertical'))
        flip_v_label.setMinimumHeight(32)
        flip_v_row.addWidget(self.flip_vertical_checkbox)
        flip_v_row.addWidget(flip_v_label, 1)
        transform_layout.addLayout(flip_v_row)

        transform_group.setLayout(transform_layout)
        settings_layout.addWidget(transform_group)

        # 添加弹性空间
        settings_layout.addStretch()

        scroll.setWidget(tab_content)
        return scroll

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

    def _on_invert_changed(self):
        """反相按钮点击事件"""
        from ..utils.resources import CHECKED, UNCHECKED
        # 更新图标
        if self.invert_checkbox.isChecked():
            self.invert_checkbox.setIcon(QIcon(QPixmap.fromImage(QImage.fromData(CHECKED))))
        else:
            self.invert_checkbox.setIcon(QIcon(QPixmap.fromImage(QImage.fromData(UNCHECKED))))
        # 发送信号
        self.image_transform.emit('invert')

    def _on_flip_horizontal_changed(self):
        """水平翻转按钮点击事件"""
        from ..utils.resources import CHECKED, UNCHECKED
        # 更新图标
        if self.flip_horizontal_checkbox.isChecked():
            self.flip_horizontal_checkbox.setIcon(QIcon(QPixmap.fromImage(QImage.fromData(CHECKED))))
        else:
            self.flip_horizontal_checkbox.setIcon(QIcon(QPixmap.fromImage(QImage.fromData(UNCHECKED))))
        # 发送信号
        self.image_transform.emit('flip_horizontal')

    def _on_flip_vertical_changed(self):
        """垂直翻转按钮点击事件"""
        from ..utils.resources import CHECKED, UNCHECKED
        # 更新图标
        if self.flip_vertical_checkbox.isChecked():
            self.flip_vertical_checkbox.setIcon(QIcon(QPixmap.fromImage(QImage.fromData(CHECKED))))
        else:
            self.flip_vertical_checkbox.setIcon(QIcon(QPixmap.fromImage(QImage.fromData(UNCHECKED))))
        # 发送信号
        self.image_transform.emit('flip_vertical')

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

        # 关闭模式(0)：隐藏强度和阈值
        # 其他模式：显示强度
        # Canny 模式(1)：显示强度和阈值
        if edge_mode == 0:
            self.edge_strength_container.setVisible(False)
            self.edge_threshold_container.setVisible(False)
        else:
            self.edge_strength_container.setVisible(True)
            # 仅 Canny 模式(1)显示边缘阈值
            self.edge_threshold_container.setVisible(edge_mode == 1)

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
        self.edge_mode_combo.setEnabled(enabled)
        self.denoise_method_combo.setEnabled(enabled)
        self.invert_checkbox.setEnabled(enabled)
        self.flip_horizontal_checkbox.setEnabled(enabled)
        self.flip_vertical_checkbox.setEnabled(enabled)
        self.flip_vertical_checkbox.setEnabled(enabled)
        # 启用/禁用去除背景按钮
        if hasattr(self, 'remove_bg_button') and self.remove_bg_button is not None:
            self.remove_bg_button.setEnabled(enabled)

    def set_current_layer(self, layer_name: str):
        """
        设置当前图层显示
        
        Args:
            layer_name: 图层名称
        """
        self.current_layer_label.setText(
            self.tr.tr('binarization_panel.current_layer', layer=layer_name)
        )
    
    def get_all_params(self) -> dict:
        """
        获取所有参数（预处理 + 二值化）
        
        Returns:
            包含所有参数的字典
        """
        return {
            'preprocess': self.get_preprocess_params(),
            'method': self.get_method(),
            'threshold': self.get_threshold(),
            'block_size': self.block_size_slider.value() if hasattr(self, 'block_size_slider') else 11,
            'window_size': self.window_size_slider.value() if hasattr(self, 'window_size_slider') else 15,
            'k_param': self.k_param_slider.value() * 0.01 if hasattr(self, 'k_param_slider') else 0.2,
            'r_param': self.r_param_slider.value() if hasattr(self, 'r_param_slider') else 128,
            'contrast_threshold': self.contrast_threshold_slider.value() if hasattr(self, 'contrast_threshold_slider') else 15,
            'dither_strength': self.dither_strength_slider.value() * 0.01 if hasattr(self, 'dither_strength_slider') else 1.0,
            'matrix_size': self.matrix_size_slider.value() if hasattr(self, 'matrix_size_slider') else 8,
        }
    
    def load_params(self, params: dict):
        """
        加载参数到控件
        
        Args:
            params: 参数字典
        """
        # 阻止信号，避免触发参数变化
        self.blockSignals(True)
        
        try:
            # 加载预处理参数
            if 'preprocess' in params:
                preprocess = params['preprocess']
                if 'exposure' in preprocess:
                    self.exposure_slider.setValue(preprocess['exposure'])
                if 'contrast' in preprocess:
                    self.contrast_slider.setValue(preprocess['contrast'])
                if 'sharpen' in preprocess:
                    self.sharpen_slider.setValue(preprocess['sharpen'])
                if 'gamma' in preprocess:
                    self.gamma_slider.setValue(int(preprocess['gamma'] * 100))
                if 'smooth' in preprocess:
                    self.smooth_slider.setValue(preprocess['smooth'])
                if 'red_channel' in preprocess:
                    self.red_channel_slider.setValue(preprocess['red_channel'])
                if 'green_channel' in preprocess:
                    self.green_channel_slider.setValue(preprocess['green_channel'])
                if 'blue_channel' in preprocess:
                    self.blue_channel_slider.setValue(preprocess['blue_channel'])
                if 'edge_mode' in preprocess:
                    for i in range(self.edge_mode_combo.count()):
                        if self.edge_mode_combo.itemData(i) == preprocess['edge_mode']:
                            self.edge_mode_combo.setCurrentIndex(i)
                            break
                if 'edge_strength' in preprocess:
                    self.edge_strength_slider.setValue(preprocess['edge_strength'])
                if 'edge_threshold' in preprocess:
                    self.edge_threshold_slider.setValue(preprocess['edge_threshold'])
                if 'denoise_method' in preprocess:
                    for i in range(self.denoise_method_combo.count()):
                        if self.denoise_method_combo.itemData(i) == preprocess['denoise_method']:
                            self.denoise_method_combo.setCurrentIndex(i)
                            break
                if 'denoise' in preprocess:
                    self.denoise_slider.setValue(preprocess['denoise'])
            
            # 加载二值化参数
            if 'method' in params:
                self.set_method(params['method'])
            if 'threshold' in params:
                self.set_threshold(params['threshold'])
            
            # 加载其他二值化参数（如果存在）
            if 'block_size' in params and hasattr(self, 'block_size_slider'):
                self.block_size_slider.setValue(params['block_size'])
            if 'window_size' in params and hasattr(self, 'window_size_slider'):
                self.window_size_slider.setValue(params['window_size'])
            if 'k_param' in params and hasattr(self, 'k_param_slider'):
                self.k_param_slider.setValue(int(params['k_param'] * 100))
            if 'r_param' in params and hasattr(self, 'r_param_slider'):
                self.r_param_slider.setValue(params['r_param'])
            if 'contrast_threshold' in params and hasattr(self, 'contrast_threshold_slider'):
                self.contrast_threshold_slider.setValue(params['contrast_threshold'])
            if 'dither_strength' in params and hasattr(self, 'dither_strength_slider'):
                self.dither_strength_slider.setValue(int(params['dither_strength'] * 100))
            if 'matrix_size' in params and hasattr(self, 'matrix_size_slider'):
                self.matrix_size_slider.setValue(params['matrix_size'])
                
        finally:
            # 恢复信号
            self.blockSignals(False)

    def retranslate_ui(self):
        """重新翻译 UI 文本（用于语言切换）"""
        # 更新组标题
        # 注意：QGroupBox 的标题需要通过 setTitle 更新
        # 这里只是示例，实际需要保存对 QGroupBox 的引用
        pass

    def _on_remove_bg_clicked(self):
        """去除背景按钮点击事件"""
        # 如果没有模型，询问用户是否下载
        if not self.has_rmbg_model:
            from PySide6.QtWidgets import QMessageBox
            from ..utils.window_utils import message_box_warning, message_box_question, message_box_information
            import os
            
            # 检查是否安装了 onnxruntime
            if not self.has_onnxruntime:
                message_box_warning(
                    self,
                    self.tr.tr('dialog.warning'),
                    self.tr.tr('binarization_panel.onnxruntime_required')
                )
                return
            
            # 询问用户是否下载模型
            reply = message_box_question(
                self,
                self.tr.tr('binarization_panel.download_model_title'),
                self.tr.tr('binarization_panel.download_model_prompt'),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                # 显示下载对话框
                from ..views.model_download_dialog import ModelDownloadDialog
                
                model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'model')
                dialog = ModelDownloadDialog(model_dir, "RMBG-2.0-q4f16.onnx", self)
                dialog.exec()
                
                # 如果下载成功，更新状态并执行去除背景
                if dialog.is_download_success():
                    self.has_rmbg_model = True
                    message_box_information(
                        self,
                        self.tr.tr('dialog.info'),
                        self.tr.tr('binarization_panel.model_download_success')
                    )
                    # 执行去除背景
                    self.ai_process_requested.emit('rmbg')
        else:
            # 有模型，直接执行去除背景
            self.ai_process_requested.emit('rmbg')
