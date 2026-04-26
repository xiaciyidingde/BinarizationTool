"""
属性面板模块

显示图片属性和工具设置的右侧面板。
"""

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..utils.translation_manager import get_translator
from ..widgets.animated_tab_widget import AnimatedTabWidget
from ..widgets.layers_panel import LayersPanel


class PropertiesPanel(QWidget):
    """
    属性面板类

    使用分页设计：
    - 第一页：图片属性
    - 第二页：工具设置（预留）
    """

    def __init__(self, parent=None):
        """初始化属性面板"""
        super().__init__(parent)

        # 获取翻译器
        self.tr = get_translator()

        self.setup_ui()

    def setup_ui(self):
        """设置 UI"""
        # 主布局（垂直布局，包含上下两部分）
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(6)
        
        # ========== 上半部分：属性和工具 ==========
        # 创建滚动区域
        from PySide6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 外层容器（用于居中和限制宽度）
        outer_container = QWidget()
        outer_layout = QVBoxLayout(outer_container)
        outer_layout.setContentsMargins(6, 6, 6, 6)

        # 内容容器（带背景和圆角）
        content = QWidget()
        content.setObjectName("propertiesPanelContent")
        # 移除内联样式，让主题文件控制
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 创建选项卡
        self.tab_widget = AnimatedTabWidget()
        # 移除内联样式，让主题文件控制
        layout.addWidget(self.tab_widget)

        # 第一页：属性
        self.properties_page = self._create_properties_page()
        self.tab_widget.addTab(self.properties_page, self.tr.tr('properties_panel.properties'))

        # 第二页：工具
        self.tools_page = self._create_tools_page()
        self.tab_widget.addTab(self.tools_page, self.tr.tr('properties_panel.tools'))

        # 将内容容器添加到外层布局
        outer_layout.addWidget(content)

        # 设置滚动区域
        scroll.setWidget(outer_container)
        
        # 添加到主布局
        main_layout.addWidget(scroll, stretch=38)
        
        # ========== 下半部分：图层面板 ==========
        # 创建图层面板容器（带背景和圆角）
        layers_outer = QWidget()
        layers_outer_layout = QVBoxLayout(layers_outer)
        layers_outer_layout.setContentsMargins(6, 0, 6, 6)
        
        layers_container = QWidget()
        layers_container.setObjectName("propertiesPanelContent")
        # 移除最大高度限制，让比例自动调整
        layers_container_layout = QVBoxLayout(layers_container)
        layers_container_layout.setContentsMargins(8, 8, 8, 8)  # 添加内边距让框线居中
        layers_container_layout.setSpacing(0)
        
        # 图层面板
        self.layers_panel = LayersPanel()
        layers_container_layout.addWidget(self.layers_panel)
        
        layers_outer_layout.addWidget(layers_container)
        
        # 添加到主布局
        main_layout.addWidget(layers_outer, stretch=34)

        # 设置面板尺寸
        self.setMinimumWidth(270)
        self.setMaximumWidth(270)

    def _create_properties_page(self) -> QWidget:
        """创建属性页"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 图片属性分组
        image_group = QGroupBox(self.tr.tr('properties_panel.properties'))
        image_layout = QFormLayout()
        image_layout.setSpacing(8)

        # 文件名（使用容器限制宽度，文本省略）
        filename_container = QWidget()
        filename_container_layout = QHBoxLayout(filename_container)
        filename_container_layout.setContentsMargins(0, 0, 0, 0)
        filename_container_layout.setSpacing(0)

        self.filename_label = QLabel(self.tr.tr('properties_panel.no_image'))
        self.filename_label.setWordWrap(False)  # 禁用自动换行
        self.filename_label.setObjectName("propertyValue")
        self.filename_label.setMaximumWidth(180)  # 限制最大宽度（从 160 增加到 180）
        self.filename_label.setTextFormat(Qt.PlainText)
        self.filename_label.setTextInteractionFlags(Qt.TextSelectableByMouse)  # 允许选择复制
        # 使用省略号模式
        from PySide6.QtWidgets import QSizePolicy
        self.filename_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        filename_container_layout.addWidget(self.filename_label)

        image_layout.addRow(self.tr.tr('properties_panel.filename'), filename_container)

        # 图层信息
        self.layer_label = QLabel("-")
        self.layer_label.setObjectName("propertyValue")
        image_layout.addRow(self.tr.tr('properties_panel.layer'), self.layer_label)

        # 图片尺寸
        self.size_label = QLabel("-")
        self.size_label.setObjectName("propertyValue")
        image_layout.addRow(self.tr.tr('properties_panel.size'), self.size_label)

        # 文件大小
        self.filesize_label = QLabel("-")
        self.filesize_label.setObjectName("propertyValue")
        image_layout.addRow(self.tr.tr('properties_panel.filesize'), self.filesize_label)

        # 缩放比例
        self.zoom_label = QLabel("-")
        self.zoom_label.setObjectName("propertyValue")
        image_layout.addRow(self.tr.tr('properties_panel.zoom'), self.zoom_label)

        image_group.setLayout(image_layout)
        layout.addWidget(image_group)

        # 添加弹性空间
        layout.addStretch()

        return page

    def _create_tools_page(self) -> QWidget:
        """创建工具页"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 提示信息（默认显示）
        self.tool_hint_label = QLabel(self.tr.tr('properties_panel.no_tool'))
        self.tool_hint_label.setAlignment(Qt.AlignCenter)
        self.tool_hint_label.setObjectName("toolHint")
        layout.addWidget(self.tool_hint_label)

        # 画笔工具设置
        self.brush_settings = self._create_brush_settings()
        self.brush_settings.setVisible(False)  # 默认隐藏
        layout.addWidget(self.brush_settings)

        # 选择工具设置
        self.selection_settings = self._create_selection_settings()
        self.selection_settings.setVisible(False)  # 默认隐藏
        layout.addWidget(self.selection_settings)
        
        # 测量工具设置
        self.measure_settings = self._create_measure_settings()
        self.measure_settings.setVisible(False)  # 默认隐藏
        layout.addWidget(self.measure_settings)

        # 添加弹性空间
        layout.addStretch()

        return page

    def _create_brush_settings(self) -> QGroupBox:
        """创建画笔工具设置"""
        from PySide6.QtWidgets import QHBoxLayout

        group = QGroupBox(self.tr.tr('properties_panel.basic_settings'))
        layout = QVBoxLayout()
        layout.setSpacing(12)

        # 大小设置
        size_layout = QHBoxLayout()
        size_layout.setSpacing(8)
        size_label = QLabel(self.tr.tr('properties_panel.brush_size', value='').split(':')[0] + ':')
        size_label.setMinimumWidth(40)
        self.brush_size_spinbox = QSpinBox()
        self.brush_size_spinbox.setRange(1, 500)
        self.brush_size_spinbox.setValue(10)
        size_layout.addWidget(size_label)
        size_layout.addWidget(self.brush_size_spinbox)
        size_layout.addStretch()
        layout.addLayout(size_layout)

        # 颜色设置
        color_layout = QHBoxLayout()
        color_layout.setSpacing(12)
        color_label = QLabel(self.tr.tr('properties_panel.brush_color'))
        color_label.setMinimumWidth(40)
        color_layout.addWidget(color_label)

        self.brush_color_group = QButtonGroup(self)
        self.brush_black_radio = QRadioButton(self.tr.tr('properties_panel.color_black'))
        self.brush_white_radio = QRadioButton(self.tr.tr('properties_panel.color_white'))
        self.brush_color_group.addButton(self.brush_black_radio, 0)
        self.brush_color_group.addButton(self.brush_white_radio, 255)
        self.brush_black_radio.setChecked(True)

        color_layout.addWidget(self.brush_black_radio)
        color_layout.addWidget(self.brush_white_radio)
        color_layout.addStretch()
        layout.addLayout(color_layout)

        group.setLayout(layout)
        return group

    def _create_selection_settings(self) -> QWidget:
        """创建选择工具设置"""
        from PySide6.QtWidgets import QHBoxLayout

        # 主容器
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(8)

        # 基础设置组
        basic_group = QGroupBox(self.tr.tr('properties_panel.basic_settings'))
        basic_layout = QVBoxLayout()
        basic_layout.setSpacing(12)

        # 范围设置
        size_layout = QHBoxLayout()
        size_layout.setSpacing(8)
        size_label = QLabel(self.tr.tr('properties_panel.selection_size', value='').split(':')[0] + ':')
        size_label.setMinimumWidth(40)
        self.selection_size_spinbox = QSpinBox()
        self.selection_size_spinbox.setRange(1, 500)
        self.selection_size_spinbox.setValue(50)
        size_layout.addWidget(size_label)
        size_layout.addWidget(self.selection_size_spinbox)
        size_layout.addStretch()
        basic_layout.addLayout(size_layout)

        # 模式设置
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(12)
        mode_label = QLabel(self.tr.tr('properties_panel.selection_mode'))
        mode_label.setMinimumWidth(40)
        mode_layout.addWidget(mode_label)

        self.selection_mode_group = QButtonGroup(self)
        self.add_mode_radio = QRadioButton(self.tr.tr('properties_panel.mode_add'))
        self.subtract_mode_radio = QRadioButton(self.tr.tr('properties_panel.mode_subtract'))
        self.selection_mode_group.addButton(self.add_mode_radio, 0)
        self.selection_mode_group.addButton(self.subtract_mode_radio, 1)
        self.add_mode_radio.setChecked(True)

        mode_layout.addWidget(self.add_mode_radio)
        mode_layout.addWidget(self.subtract_mode_radio)
        mode_layout.addStretch()
        basic_layout.addLayout(mode_layout)

        # 选择方式设置
        method_layout = QHBoxLayout()
        method_layout.setSpacing(12)
        method_label = QLabel(self.tr.tr('properties_panel.selection_method'))
        method_label.setMinimumWidth(40)
        method_layout.addWidget(method_label)

        self.selection_method_group = QButtonGroup(self)
        self.brush_method_radio = QRadioButton(self.tr.tr('properties_panel.method_paint'))
        self.rect_method_radio = QRadioButton(self.tr.tr('properties_panel.method_rect'))
        self.selection_method_group.addButton(self.brush_method_radio, 0)
        self.selection_method_group.addButton(self.rect_method_radio, 1)
        self.brush_method_radio.setChecked(True)

        method_layout.addWidget(self.brush_method_radio)
        method_layout.addWidget(self.rect_method_radio)
        method_layout.addStretch()
        basic_layout.addLayout(method_layout)

        # 智能选择设置
        smart_layout = QHBoxLayout()
        smart_layout.setSpacing(8)
        smart_label = QLabel(self.tr.tr('properties_panel.smart_selection'))
        smart_label.setMinimumWidth(40)
        smart_layout.addWidget(smart_label)
        
        from ..widgets.toggle_switch import ToggleSwitch
        self.smart_selection_switch = ToggleSwitch()
        self.smart_selection_switch.setChecked(False)  # 默认关闭
        
        smart_layout.addWidget(self.smart_selection_switch)
        
        # AI 标识（仅在预处理/原图视图显示）
        self.smart_selection_ai_label = QLabel("AI")
        self.smart_selection_ai_label.setStyleSheet("""
            QLabel {
                color: #4CAF50;
                font-weight: bold;
                font-size: 11px;
                padding: 2px 6px;
                background-color: rgba(76, 175, 80, 0.1);
                border: 1px solid #4CAF50;
                border-radius: 3px;
            }
        """)
        self.smart_selection_ai_label.setVisible(False)  # 默认隐藏
        smart_layout.addWidget(self.smart_selection_ai_label)
        
        smart_layout.addStretch()
        basic_layout.addLayout(smart_layout)

        # 填充选区（两个按钮：黑色和白色）
        fill_layout = QHBoxLayout()
        fill_layout.setSpacing(8)
        fill_label = QLabel(self.tr.tr('properties_panel.fill_selection'))
        fill_label.setMinimumWidth(40)
        fill_layout.addWidget(fill_label)

        self.fill_black_button = QPushButton(self.tr.tr('properties_panel.fill_black'))
        self.fill_white_button = QPushButton(self.tr.tr('properties_panel.fill_white'))
        self.fill_black_button.setFixedWidth(60)
        self.fill_white_button.setFixedWidth(60)
        fill_layout.addWidget(self.fill_black_button)
        fill_layout.addWidget(self.fill_white_button)
        fill_layout.addStretch()
        basic_layout.addLayout(fill_layout)

        basic_group.setLayout(basic_layout)
        container_layout.addWidget(basic_group)

        # 快捷操作组
        actions_group = QGroupBox(self.tr.tr('properties_panel.quick_actions'))
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(8)

        # 第一行按钮
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(8)
        self.deselect_button = QPushButton(self.tr.tr('properties_panel.deselect'))
        self.invert_button = QPushButton(self.tr.tr('properties_panel.invert'))
        row1_layout.addWidget(self.deselect_button)
        row1_layout.addWidget(self.invert_button)
        actions_layout.addLayout(row1_layout)

        # 第二行按钮：填充选区空洞
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(8)
        self.fill_selection_holes_button = QPushButton(self.tr.tr('properties_panel.fill_selection_holes'))
        self.fill_selection_holes_button.setToolTip(self.tr.tr('properties_panel.fill_selection_holes_tooltip'))
        row2_layout.addWidget(self.fill_selection_holes_button)
        row2_layout.addStretch()  # 右侧留空
        actions_layout.addLayout(row2_layout)

        actions_group.setLayout(actions_layout)
        container_layout.addWidget(actions_group)

        return container
    
    def _create_measure_settings(self) -> QGroupBox:
        """创建测量工具设置"""
        group = QGroupBox(self.tr.tr('properties_panel.quick_actions'))
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        # 清除测量按钮
        self.clear_measure_button = QPushButton(self.tr.tr('properties_panel.clear_measure'))
        self.clear_measure_button.setToolTip(self.tr.tr('properties_panel.clear_measure_tooltip'))
        layout.addWidget(self.clear_measure_button)
        
        group.setLayout(layout)
        return group

    def set_image_info(self, image_data, file_path: str | None = None):
        """
        更新图片信息

        Args:
            image_data: ImageData 对象
            file_path: 文件路径（可选）
        """
        if image_data is None:
            self.clear_info()
            return

        # 文件名（手动处理省略）
        if file_path:
            filename = os.path.basename(file_path)
            # 如果文件名太长，手动截断
            max_length = 23  # 最大字符数（从 20 增加到 23）
            if len(filename) > max_length:
                # 保留前10个字符和后8个字符，中间用...连接
                name_part = filename[:10]
                ext_part = filename[-8:]
                display_name = f"{name_part}...{ext_part}"
            else:
                display_name = filename

            self.filename_label.setText(display_name)
            self.filename_label.setToolTip(filename)  # 完整文件名显示在工具提示中
        else:
            self.filename_label.setText(self.tr.tr('properties_panel.unsaved'))
            self.filename_label.setToolTip("")

        # 图层信息（默认显示根图层）
        self.layer_label.setText(self.tr.tr('properties_panel.root_layer'))

        # 图片尺寸
        size_text = f"{image_data.width} x {image_data.height} {self.tr.tr('properties_panel.pixels')}"
        self.size_label.setText(size_text)

        # 文件大小
        if file_path and os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            size_text = self._format_file_size(file_size)
            self.filesize_label.setText(size_text)
        else:
            self.filesize_label.setText("-")

        # 缩放比例保持当前值

    def set_layer_info(self, layer_name: str, selected_pixels: int | None = None):
        """
        更新图层信息

        Args:
            layer_name: 图层名称
            selected_pixels: 选中的像素数量（仅用户图层）
        """
        if selected_pixels is not None:
            # 用户图层：显示图层名和选中像素数
            self.layer_label.setText(layer_name)
            self.size_label.setText(f"{selected_pixels} {self.tr.tr('properties_panel.pixels')}")
        else:
            # 根图层：只显示图层名
            self.layer_label.setText(layer_name)

    def set_zoom_level(self, zoom: float):
        """
        更新缩放比例

        Args:
            zoom: 缩放因子
        """
        zoom_percent = int(zoom * 100)
        self.zoom_label.setText(f"{zoom_percent}%")

    def clear_info(self):
        """清除信息（未加载图片时）"""
        self.filename_label.setText(self.tr.tr('properties_panel.no_image'))
        self.layer_label.setText("-")
        self.size_label.setText("-")
        self.filesize_label.setText("-")
        self.zoom_label.setText("-")

    def show_brush_settings(self):
        """显示画笔工具设置，隐藏其他"""
        self.tab_widget.setCurrentIndex(1)  # 切换到"工具"页
        self.tool_hint_label.setVisible(False)
        self.brush_settings.setVisible(True)
        self.selection_settings.setVisible(False)
        self.measure_settings.setVisible(False)

    def show_selection_settings(self):
        """显示选择工具设置，隐藏其他"""
        self.tab_widget.setCurrentIndex(1)  # 切换到"工具"页
        self.tool_hint_label.setVisible(False)
        self.brush_settings.setVisible(False)
        self.selection_settings.setVisible(True)
        self.measure_settings.setVisible(False)
    
    def update_smart_selection_ai_label(self, view_mode: str, smart_enabled: bool):
        """
        更新智能选择AI标识的显示状态
        
        Args:
            view_mode: 当前视图模式 ('original', 'preprocessed', 'binary')
            smart_enabled: 智能选择是否开启
        """
        # 只在预处理或原图视图且智能选择开启时显示AI标识
        should_show = (view_mode in ['original', 'preprocessed']) and smart_enabled
        if hasattr(self, 'smart_selection_ai_label'):
            self.smart_selection_ai_label.setVisible(should_show)
    
    def show_measure_settings(self):
        """显示测量工具设置，隐藏其他"""
        self.tab_widget.setCurrentIndex(1)  # 切换到"工具"页
        self.tool_hint_label.setVisible(False)
        self.brush_settings.setVisible(False)
        self.selection_settings.setVisible(False)
        self.measure_settings.setVisible(True)

    def hide_all_tool_settings(self):
        """隐藏所有工具设置，切换回属性页"""
        # 切换回"属性"页
        self.tab_widget.setCurrentIndex(0)
        # 隐藏所有工具设置
        self.tool_hint_label.setText(self.tr.tr('properties_panel.no_settings'))
        self.tool_hint_label.setVisible(True)
        self.brush_settings.setVisible(False)
        self.selection_settings.setVisible(False)
        self.measure_settings.setVisible(False)

    def _format_file_size(self, size_bytes: int) -> str:
        """
        格式化文件大小

        Args:
            size_bytes: 字节数

        Returns:
            格式化后的字符串
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

