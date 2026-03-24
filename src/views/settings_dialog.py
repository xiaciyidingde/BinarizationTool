"""
设置对话框

提供应用程序的各种设置选项。
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QSlider, QCheckBox, QGroupBox, QPushButton,
    QTabWidget, QWidget, QRadioButton, QButtonGroup, QLineEdit,
    QMessageBox
)
from PySide6.QtCore import Qt
from src.utils.config_manager import get_config_manager


class SettingsDialog(QDialog):
    """设置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        # 获取配置管理器
        self.config_manager = get_config_manager()
        
        self.setup_ui()
        self.load_settings()
    
    def load_settings(self):
        """从配置文件加载设置"""
        config = self.config_manager
        
        # 通用设置
        language = config.get('general', 'language', 'zh_CN')
        ui_language = config.config_to_ui('language', language)
        self.language_combo.setCurrentText(ui_language)
        
        # 界面设置
        theme = config.get('interface', 'theme', 'light')
        if theme == 'light':
            self.theme_light.setChecked(True)
        elif theme == 'dark':
            self.theme_dark.setChecked(True)
        else:
            self.theme_system.setChecked(True)
        
        # 编辑器设置
        self.brush_size_slider.setValue(config.get('editor', 'default_brush_size', 20))
        self.selection_size_slider.setValue(config.get('editor', 'default_selection_size', 50))
        self.undo_limit_slider.setValue(config.get('editor', 'undo_history_limit', 50))
        
        canvas_bg = config.get('editor', 'canvas_background', 'white')
        if canvas_bg == 'white':
            self.canvas_white.setChecked(True)
        elif canvas_bg == 'gray':
            self.canvas_gray.setChecked(True)
        else:
            self.canvas_black.setChecked(True)
        
        # 性能设置
        self.tile_cache_slider.setValue(config.get('performance', 'tile_cache_size', 1000))
        self.debounce_slider.setValue(config.get('performance', 'debounce_delay', 150))
        self.hw_accel_checkbox.setChecked(config.get('performance', 'hardware_acceleration', True))
        self.max_size_spinbox.setValue(config.get('performance', 'max_image_size', 20000))
        
        # 文件设置
        save_format = config.get('file', 'default_save_format', 'follow_original')
        ui_format = config.config_to_ui('save_format', save_format)
        self.format_combo.setCurrentText(ui_format)
        
        filename_format = config.get('file', 'filename_format', 'timestamp')
        if filename_format == 'timestamp':
            self.filename_timestamp.setChecked(True)
        elif filename_format == 'copy':
            self.filename_copy.setChecked(True)
        else:
            self.filename_custom.setChecked(True)
        
        self.prefix_edit.setText(config.get('file', 'custom_prefix', ''))
        self.suffix_edit.setText(config.get('file', 'custom_suffix', ''))
    
    def setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建选项卡
        tab_widget = QTabWidget()
        # 设置选项卡样式（参考属性面板）
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background: #ffffff;
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
        
        # 1. 通用设置
        tab_widget.addTab(self.create_general_tab(), "通用")
        
        # 2. 界面设置
        tab_widget.addTab(self.create_interface_tab(), "界面")
        
        # 3. 编辑器设置
        tab_widget.addTab(self.create_editor_tab(), "编辑器")
        
        # 4. 性能设置
        tab_widget.addTab(self.create_performance_tab(), "性能")
        
        # 5. 文件设置
        tab_widget.addTab(self.create_file_tab(), "文件")
        
        layout.addWidget(tab_widget)
        
        # 按钮容器
        button_container = QWidget()
        button_container.setStyleSheet("background: #f8f9fa; border-top: 1px solid #dee2e6;")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(10, 10, 10, 10)
        
        # 恢复默认按钮（左侧）
        restore_btn = QPushButton("恢复默认")
        restore_btn.clicked.connect(self.restore_defaults)
        button_layout.addWidget(restore_btn)
        
        button_layout.addStretch()
        
        # 确定和取消按钮（右侧）
        ok_btn = QPushButton("确定")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept_settings)
        ok_btn.setMinimumWidth(80)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setMinimumWidth(80)
        
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addWidget(button_container)
    
    def create_general_tab(self):
        """创建通用设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignTop)
        
        # 语言设置
        lang_group = QGroupBox("语言")
        lang_layout = QVBoxLayout()
        
        lang_label = QLabel("界面语言：")
        self.language_combo = QComboBox()
        self.language_combo.addItems(["中文", "English (即将支持)"])
        self.language_combo.setEnabled(False)  # 暂时禁用，只有中文
        
        lang_row = QHBoxLayout()
        lang_row.addWidget(lang_label)
        lang_row.addWidget(self.language_combo)
        lang_row.addStretch()
        lang_layout.addLayout(lang_row)
        
        note_label = QLabel("注：英文界面将在后续版本中支持")
        note_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        lang_layout.addWidget(note_label)
        
        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)
        
        layout.addStretch()
        return widget
    
    def create_interface_tab(self):
        """创建界面设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignTop)
        
        # 主题设置
        theme_group = QGroupBox("主题")
        theme_layout = QVBoxLayout()
        
        self.theme_group = QButtonGroup()
        
        self.theme_light = QRadioButton("浅色主题（当前）")
        self.theme_dark = QRadioButton("深色主题")
        self.theme_system = QRadioButton("跟随系统")
        
        self.theme_group.addButton(self.theme_light, 0)
        self.theme_group.addButton(self.theme_dark, 1)
        self.theme_group.addButton(self.theme_system, 2)
        
        # 连接信号
        self.theme_dark.toggled.connect(self._on_theme_changed)
        self.theme_system.toggled.connect(self._on_theme_changed)
        
        theme_layout.addWidget(self.theme_light)
        theme_layout.addWidget(self.theme_dark)
        theme_layout.addWidget(self.theme_system)
        
        note_label = QLabel("注：深色主题和跟随系统功能将在后续版本中支持")
        note_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        theme_layout.addWidget(note_label)
        
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        
        layout.addStretch()
        return widget
    
    def create_editor_tab(self):
        """创建编辑器设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignTop)
        
        # 默认工具大小
        tool_group = QGroupBox("默认工具大小")
        tool_layout = QVBoxLayout()
        
        # 默认画笔大小
        brush_label = QLabel("默认画笔大小：20")
        self.brush_size_slider = QSlider(Qt.Horizontal)
        self.brush_size_slider.setRange(1, 500)
        self.brush_size_slider.valueChanged.connect(
            lambda v: brush_label.setText(f"默认画笔大小：{v}")
        )
        tool_layout.addWidget(brush_label)
        tool_layout.addWidget(self.brush_size_slider)
        
        # 默认选择范围
        selection_label = QLabel("默认选择范围：50")
        self.selection_size_slider = QSlider(Qt.Horizontal)
        self.selection_size_slider.setRange(1, 500)
        self.selection_size_slider.valueChanged.connect(
            lambda v: selection_label.setText(f"默认选择范围：{v}")
        )
        tool_layout.addWidget(selection_label)
        tool_layout.addWidget(self.selection_size_slider)
        
        tool_group.setLayout(tool_layout)
        layout.addWidget(tool_group)
        
        # 历史记录
        history_group = QGroupBox("历史记录")
        history_layout = QVBoxLayout()
        
        undo_label = QLabel("撤销历史数量：50")
        self.undo_limit_slider = QSlider(Qt.Horizontal)
        self.undo_limit_slider.setRange(10, 100)
        self.undo_limit_slider.valueChanged.connect(
            lambda v: undo_label.setText(f"撤销历史数量：{v}")
        )
        history_layout.addWidget(undo_label)
        history_layout.addWidget(self.undo_limit_slider)
        
        history_group.setLayout(history_layout)
        layout.addWidget(history_group)
        
        # 画布背景
        canvas_group = QGroupBox("画布背景色")
        canvas_layout = QVBoxLayout()
        
        self.canvas_bg_group = QButtonGroup()
        
        self.canvas_white = QRadioButton("白色")
        self.canvas_gray = QRadioButton("灰色")
        self.canvas_black = QRadioButton("黑色")
        
        self.canvas_bg_group.addButton(self.canvas_white, 0)
        self.canvas_bg_group.addButton(self.canvas_gray, 1)
        self.canvas_bg_group.addButton(self.canvas_black, 2)
        
        canvas_layout.addWidget(self.canvas_white)
        canvas_layout.addWidget(self.canvas_gray)
        canvas_layout.addWidget(self.canvas_black)
        
        canvas_group.setLayout(canvas_layout)
        layout.addWidget(canvas_group)
        
        layout.addStretch()
        return widget
    
    def create_performance_tab(self):
        """创建性能设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignTop)
        
        # 缓存设置
        cache_group = QGroupBox("缓存设置")
        cache_layout = QVBoxLayout()
        
        tile_label = QLabel("Tile 缓存大小：1000")
        self.tile_cache_slider = QSlider(Qt.Horizontal)
        self.tile_cache_slider.setRange(100, 2000)
        self.tile_cache_slider.setSingleStep(100)
        self.tile_cache_slider.valueChanged.connect(
            lambda v: tile_label.setText(f"Tile 缓存大小：{v}")
        )
        cache_layout.addWidget(tile_label)
        cache_layout.addWidget(self.tile_cache_slider)
        
        cache_note = QLabel("提示：增大缓存可提高大图片浏览性能，但会占用更多内存")
        cache_note.setStyleSheet("color: #6c757d; font-size: 12px;")
        cache_layout.addWidget(cache_note)
        
        cache_group.setLayout(cache_layout)
        layout.addWidget(cache_group)
        
        # 处理延迟
        delay_group = QGroupBox("处理延迟")
        delay_layout = QVBoxLayout()
        
        debounce_label = QLabel("二值化防抖延迟：150 ms")
        self.debounce_slider = QSlider(Qt.Horizontal)
        self.debounce_slider.setRange(50, 500)
        self.debounce_slider.setSingleStep(50)
        self.debounce_slider.valueChanged.connect(
            lambda v: debounce_label.setText(f"二值化防抖延迟：{v} ms")
        )
        delay_layout.addWidget(debounce_label)
        delay_layout.addWidget(self.debounce_slider)
        
        delay_note = QLabel("提示：增大延迟可减少频繁计算，但响应会稍慢")
        delay_note.setStyleSheet("color: #6c757d; font-size: 12px;")
        delay_layout.addWidget(delay_note)
        
        delay_group.setLayout(delay_layout)
        layout.addWidget(delay_group)
        
        # 硬件加速
        hw_group = QGroupBox("硬件加速")
        hw_layout = QVBoxLayout()
        
        self.hw_accel_checkbox = QCheckBox("启用硬件加速")
        hw_layout.addWidget(self.hw_accel_checkbox)
        
        hw_note = QLabel("注：硬件加速功能将在后续版本中支持")
        hw_note.setStyleSheet("color: #6c757d; font-size: 12px;")
        hw_layout.addWidget(hw_note)
        
        hw_group.setLayout(hw_layout)
        layout.addWidget(hw_group)
        
        # 图像尺寸限制
        size_group = QGroupBox("图像尺寸限制")
        size_layout = QVBoxLayout()
        
        size_row = QHBoxLayout()
        size_label = QLabel("最大图像尺寸：")
        self.max_size_spinbox = QSpinBox()
        self.max_size_spinbox.setRange(1000, 50000)
        self.max_size_spinbox.setSingleStep(1000)
        self.max_size_spinbox.setSuffix(" px")
        size_row.addWidget(size_label)
        size_row.addWidget(self.max_size_spinbox)
        size_row.addStretch()
        size_layout.addLayout(size_row)
        
        size_note = QLabel("提示：限制可打开的最大图像宽度或高度（默认 20000 px）")
        size_note.setStyleSheet("color: #6c757d; font-size: 12px;")
        size_layout.addWidget(size_note)
        
        size_group.setLayout(size_layout)
        layout.addWidget(size_group)
        
        layout.addStretch()
        return widget
    
    def create_file_tab(self):
        """创建文件设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignTop)
        
        # 保存格式
        format_group = QGroupBox("默认保存格式")
        format_layout = QVBoxLayout()
        
        format_row = QHBoxLayout()
        format_label = QLabel("保存格式：")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["跟随原文件", "PNG", "JPG", "BMP", "WebP"])
        format_row.addWidget(format_label)
        format_row.addWidget(self.format_combo)
        format_row.addStretch()
        format_layout.addLayout(format_row)
        
        format_note = QLabel('提示：选择"跟随原文件"将使用原始文件的格式')
        format_note.setStyleSheet("color: #6c757d; font-size: 12px;")
        format_layout.addWidget(format_note)
        
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)
        
        # 文件名格式
        filename_group = QGroupBox("保存时文件名格式")
        filename_layout = QVBoxLayout()
        
        self.filename_format_group = QButtonGroup()
        
        self.filename_timestamp = QRadioButton("原名_时间戳（例：image_20260324_143025.png）")
        self.filename_copy = QRadioButton("原名_副本（例：image_副本.png）")
        self.filename_custom = QRadioButton("自定义前缀/后缀")
        
        self.filename_format_group.addButton(self.filename_timestamp, 0)
        self.filename_format_group.addButton(self.filename_copy, 1)
        self.filename_format_group.addButton(self.filename_custom, 2)
        
        filename_layout.addWidget(self.filename_timestamp)
        filename_layout.addWidget(self.filename_copy)
        filename_layout.addWidget(self.filename_custom)
        
        # 自定义前缀/后缀
        custom_layout = QHBoxLayout()
        custom_layout.setContentsMargins(30, 5, 0, 5)
        
        prefix_label = QLabel("前缀：")
        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText("例：edited_")
        self.prefix_edit.setEnabled(self.filename_custom.isChecked())
        
        suffix_label = QLabel("后缀：")
        self.suffix_edit = QLineEdit()
        self.suffix_edit.setPlaceholderText("例：_final")
        self.suffix_edit.setEnabled(self.filename_custom.isChecked())
        
        custom_layout.addWidget(prefix_label)
        custom_layout.addWidget(self.prefix_edit, 1)
        custom_layout.addWidget(suffix_label)
        custom_layout.addWidget(self.suffix_edit, 1)
        
        filename_layout.addLayout(custom_layout)
        
        # 连接信号
        self.filename_custom.toggled.connect(self.prefix_edit.setEnabled)
        self.filename_custom.toggled.connect(self.suffix_edit.setEnabled)
        
        filename_group.setLayout(filename_layout)
        layout.addWidget(filename_group)
        
        layout.addStretch()
        return widget
    
    def _on_theme_changed(self, checked):
        """主题改变时的处理"""
        if not checked:
            return
        
        sender = self.sender()
        if sender == self.theme_dark or sender == self.theme_system:
            # 提示功能未支持
            QMessageBox.information(
                self,
                "功能开发中",
                "深色主题和跟随系统功能将在后续版本中支持。\n当前将恢复为浅色主题。"
            )
            # 恢复为浅色主题
            self.theme_light.setChecked(True)
    
    def accept_settings(self):
        """接受设置并保存到配置文件"""
        config = self.config_manager
        
        # 通用设置
        ui_language = self.language_combo.currentText()
        config.set('general', 'language', config.ui_to_config('language', ui_language))
        
        # 界面设置
        if self.theme_light.isChecked():
            config.set('interface', 'theme', 'light')
        elif self.theme_dark.isChecked():
            config.set('interface', 'theme', 'dark')
        else:
            config.set('interface', 'theme', 'system')
        
        # 编辑器设置
        config.set('editor', 'default_brush_size', self.brush_size_slider.value())
        config.set('editor', 'default_selection_size', self.selection_size_slider.value())
        config.set('editor', 'undo_history_limit', self.undo_limit_slider.value())
        
        if self.canvas_white.isChecked():
            config.set('editor', 'canvas_background', 'white')
        elif self.canvas_gray.isChecked():
            config.set('editor', 'canvas_background', 'gray')
        else:
            config.set('editor', 'canvas_background', 'black')
        
        # 性能设置
        config.set('performance', 'tile_cache_size', self.tile_cache_slider.value())
        config.set('performance', 'debounce_delay', self.debounce_slider.value())
        config.set('performance', 'hardware_acceleration', self.hw_accel_checkbox.isChecked())
        config.set('performance', 'max_image_size', self.max_size_spinbox.value())
        
        # 文件设置
        ui_format = self.format_combo.currentText()
        config.set('file', 'default_save_format', config.ui_to_config('save_format', ui_format))
        
        if self.filename_timestamp.isChecked():
            config.set('file', 'filename_format', 'timestamp')
        elif self.filename_copy.isChecked():
            config.set('file', 'filename_format', 'copy')
        else:
            config.set('file', 'filename_format', 'custom')
        
        config.set('file', 'custom_prefix', self.prefix_edit.text())
        config.set('file', 'custom_suffix', self.suffix_edit.text())
        
        # 保存到文件
        if config.save():
            self.accept()  # 关闭对话框并返回 Accepted
        else:
            QMessageBox.critical(
                self,
                "保存失败",
                "无法保存设置到配置文件，请检查文件权限。"
            )
    
    def restore_defaults(self):
        """恢复默认设置"""
        reply = QMessageBox.question(
            self,
            "恢复默认设置",
            "确定要恢复所有设置为默认值吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 重置配置管理器
            self.config_manager.reset_to_default()
            
            # 重新加载设置到UI
            self.load_settings()
            
            QMessageBox.information(
                self,
                "已恢复默认",
                "所有设置已恢复为默认值。"
            )
