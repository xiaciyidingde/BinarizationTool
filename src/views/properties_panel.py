"""
属性面板模块

显示图片属性和工具设置的右侧面板。
"""

from typing import Optional
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QLabel, QGroupBox, 
                                QFormLayout, QSpinBox, QRadioButton, QButtonGroup, 
                                QHBoxLayout, QPushButton, QFrame)
from PySide6.QtCore import Qt
import os


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
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置 UI"""
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
        content.setStyleSheet("""
            QWidget#propertiesPanelContent {
                background-color: #ffffff;
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        # 设置选项卡样式
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background: transparent;
                top: -1px;
            }
            QTabBar::tab {
                background: #f8f9fa;
                color: #6c757d;
                padding: 8px 20px;
                margin-right: 4px;
                border: 1px solid #dee2e6;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #495057;
                font-weight: bold;
                border-bottom: 1px solid #ffffff;
                margin-bottom: -1px;
            }
            QTabBar::tab:hover:!selected {
                background: #e9ecef;
            }
        """)
        layout.addWidget(self.tab_widget)
        
        # 第一页：属性
        self.properties_page = self._create_properties_page()
        self.tab_widget.addTab(self.properties_page, "属性")
        
        # 第二页：工具（预留）
        self.tools_page = self._create_tools_page()
        self.tab_widget.addTab(self.tools_page, "工具")
        
        # 将内容容器添加到外层布局
        outer_layout.addWidget(content)
        
        # 设置滚动区域
        scroll.setWidget(outer_container)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        
        # 设置面板尺寸
        self.setMinimumWidth(270)  # 从 250 增加到 270
        self.setMaximumWidth(270)
    
    def _create_properties_page(self) -> QWidget:
        """创建属性页"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 图片属性分组
        image_group = QGroupBox("图片属性")
        image_group.setStyleSheet("""
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
        image_layout = QFormLayout()
        image_layout.setSpacing(8)
        
        # 文件名（使用容器限制宽度，文本省略）
        filename_container = QWidget()
        filename_container_layout = QHBoxLayout(filename_container)
        filename_container_layout.setContentsMargins(0, 0, 0, 0)
        filename_container_layout.setSpacing(0)
        
        self.filename_label = QLabel("未加载")
        self.filename_label.setWordWrap(False)  # 禁用自动换行
        self.filename_label.setStyleSheet("color: #333;")
        self.filename_label.setMaximumWidth(180)  # 限制最大宽度（从 160 增加到 180）
        self.filename_label.setTextFormat(Qt.PlainText)
        self.filename_label.setTextInteractionFlags(Qt.TextSelectableByMouse)  # 允许选择复制
        # 使用省略号模式
        from PySide6.QtWidgets import QSizePolicy
        self.filename_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        filename_container_layout.addWidget(self.filename_label)
        
        image_layout.addRow("文件名:", filename_container)
        
        # 图片尺寸
        self.size_label = QLabel("-")
        self.size_label.setStyleSheet("color: #333;")
        image_layout.addRow("尺寸:", self.size_label)
        
        # 文件大小
        self.filesize_label = QLabel("-")
        self.filesize_label.setStyleSheet("color: #333;")
        image_layout.addRow("文件大小:", self.filesize_label)
        
        # 缩放比例
        self.zoom_label = QLabel("-")
        self.zoom_label.setStyleSheet("color: #333;")
        image_layout.addRow("缩放比例:", self.zoom_label)
        
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
        self.tool_hint_label = QLabel("请选择一个工具")
        self.tool_hint_label.setAlignment(Qt.AlignCenter)
        self.tool_hint_label.setStyleSheet("color: #999; padding: 20px;")
        layout.addWidget(self.tool_hint_label)
        
        # 画笔工具设置
        self.brush_settings = self._create_brush_settings()
        self.brush_settings.setVisible(False)  # 默认隐藏
        layout.addWidget(self.brush_settings)
        
        # 选择工具设置
        self.selection_settings = self._create_selection_settings()
        self.selection_settings.setVisible(False)  # 默认隐藏
        layout.addWidget(self.selection_settings)
        
        # 添加弹性空间
        layout.addStretch()
        
        return page
    
    def _create_brush_settings(self) -> QGroupBox:
        """创建画笔工具设置"""
        from PySide6.QtWidgets import QSpinBox, QRadioButton, QButtonGroup, QHBoxLayout
        
        group = QGroupBox("基础设置")
        group.setStyleSheet("""
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
        layout = QVBoxLayout()
        layout.setSpacing(12)
        
        # 大小设置
        size_layout = QHBoxLayout()
        size_layout.setSpacing(8)
        size_label = QLabel("大小:")
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
        color_label = QLabel("颜色:")
        color_label.setMinimumWidth(40)
        color_layout.addWidget(color_label)
        
        self.brush_color_group = QButtonGroup(self)
        self.brush_black_radio = QRadioButton("黑色")
        self.brush_white_radio = QRadioButton("白色")
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
        from PySide6.QtWidgets import QSpinBox, QRadioButton, QButtonGroup, QHBoxLayout, QPushButton, QFrame
        
        # 主容器
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(8)
        
        # 基础设置组
        basic_group = QGroupBox("基础设置")
        basic_group.setStyleSheet("""
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
        basic_layout = QVBoxLayout()
        basic_layout.setSpacing(12)
        
        # 范围设置
        size_layout = QHBoxLayout()
        size_layout.setSpacing(8)
        size_label = QLabel("范围:")
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
        mode_label = QLabel("模式:")
        mode_label.setMinimumWidth(40)
        mode_layout.addWidget(mode_label)
        
        self.selection_mode_group = QButtonGroup(self)
        self.add_mode_radio = QRadioButton("添加")
        self.subtract_mode_radio = QRadioButton("删除")
        self.selection_mode_group.addButton(self.add_mode_radio, 0)
        self.selection_mode_group.addButton(self.subtract_mode_radio, 1)
        self.add_mode_radio.setChecked(True)
        
        mode_layout.addWidget(self.add_mode_radio)
        mode_layout.addWidget(self.subtract_mode_radio)
        mode_layout.addStretch()
        basic_layout.addLayout(mode_layout)
        
        # 颜色设置
        color_layout = QHBoxLayout()
        color_layout.setSpacing(12)
        color_label = QLabel("颜色:")
        color_label.setMinimumWidth(40)
        color_layout.addWidget(color_label)
        
        self.selection_color_group = QButtonGroup(self)
        self.selection_black_radio = QRadioButton("黑色")
        self.selection_white_radio = QRadioButton("白色")
        self.selection_color_group.addButton(self.selection_black_radio, 0)
        self.selection_color_group.addButton(self.selection_white_radio, 255)
        self.selection_black_radio.setChecked(True)
        
        color_layout.addWidget(self.selection_black_radio)
        color_layout.addWidget(self.selection_white_radio)
        color_layout.addStretch()
        basic_layout.addLayout(color_layout)
        
        # 填充选区
        fill_layout = QHBoxLayout()
        fill_layout.setSpacing(12)
        fill_label = QLabel("填充选区:")
        fill_label.setMinimumWidth(40)
        fill_layout.addWidget(fill_label)
        
        self.fill_button = QPushButton("填充白色")
        fill_layout.addWidget(self.fill_button)
        fill_layout.addStretch()
        basic_layout.addLayout(fill_layout)
        
        basic_group.setLayout(basic_layout)
        container_layout.addWidget(basic_group)
        
        # 快捷操作组
        actions_group = QGroupBox("快捷操作")
        actions_group.setStyleSheet("""
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
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(8)
        
        # 第一行按钮
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(8)
        self.deselect_button = QPushButton("取消选择")
        self.invert_button = QPushButton("反选")
        row1_layout.addWidget(self.deselect_button)
        row1_layout.addWidget(self.invert_button)
        actions_layout.addLayout(row1_layout)
        
        actions_group.setLayout(actions_layout)
        container_layout.addWidget(actions_group)
        
        return container
    
    def set_image_info(self, image_data, file_path: Optional[str] = None):
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
            self.filename_label.setText("未保存")
            self.filename_label.setToolTip("")
        
        # 图片尺寸
        size_text = f"{image_data.width} x {image_data.height} 像素"
        self.size_label.setText(size_text)
        
        # 文件大小
        if file_path and os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            size_text = self._format_file_size(file_size)
            self.filesize_label.setText(size_text)
        else:
            self.filesize_label.setText("-")
        
        # 缩放比例保持当前值
    
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
        self.filename_label.setText("未加载")
        self.size_label.setText("-")
        self.filesize_label.setText("-")
        self.zoom_label.setText("-")
    
    def show_brush_settings(self):
        """显示画笔工具设置，隐藏其他"""
        self.tab_widget.setCurrentIndex(1)  # 切换到"工具"页
        self.tool_hint_label.setVisible(False)
        self.brush_settings.setVisible(True)
        self.selection_settings.setVisible(False)
    
    def show_selection_settings(self):
        """显示选择工具设置，隐藏其他"""
        self.tab_widget.setCurrentIndex(1)  # 切换到"工具"页
        self.tool_hint_label.setVisible(False)
        self.brush_settings.setVisible(False)
        self.selection_settings.setVisible(True)
    
    def hide_all_tool_settings(self):
        """隐藏所有工具设置，显示提示信息"""
        self.tab_widget.setCurrentIndex(1)  # 切换到"工具"页
        self.tool_hint_label.setText("该工具无设置项")
        self.tool_hint_label.setVisible(True)
        self.brush_settings.setVisible(False)
        self.selection_settings.setVisible(False)

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

