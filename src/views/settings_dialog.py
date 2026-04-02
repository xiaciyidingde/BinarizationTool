"""
设置对话框

提供应用程序的各种设置选项。
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.utils.config_manager import get_config_manager
from src.utils.translation_manager import get_translator
from src.utils.window_utils import apply_dark_titlebar
from src.widgets.animated_tab_widget import AnimatedTabWidget
from src.widgets.toggle_switch import ToggleSwitch


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # 获取配置管理器和翻译器
        self.config_manager = get_config_manager()
        self.tr = get_translator()

        self.setWindowTitle(self.tr.tr('settings.title'))
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        # 应用深色标题栏
        apply_dark_titlebar(self)

        self.setup_ui()
        self.load_settings()

    def load_settings(self):
        """从配置文件加载设置"""
        config = self.config_manager

        # 通用设置
        language = config.get('general', 'language', 'zh_CN')
        lang_index = config.config_value_to_ui_index('language', language)
        self.language_combo.setCurrentIndex(lang_index)

        # 界面设置
        theme = config.get('interface', 'theme', 'light')
        if theme == 'light':
            self.theme_light.setChecked(True)
        elif theme == 'dark':
            self.theme_dark.setChecked(True)
        else:
            self.theme_system.setChecked(True)

        # 动画设置
        self.animations_checkbox.setChecked(config.get('interface', 'animations_enabled', True))
        
        # 标尺显示设置
        self.ruler_checkbox.setChecked(config.get('interface', 'show_ruler', True))

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
        format_index = config.config_value_to_ui_index('save_format', save_format)
        self.format_combo.setCurrentIndex(format_index)

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
        tab_widget = AnimatedTabWidget()
        tab_widget.setObjectName("settingsTabWidget")
        # 移除内联样式，让主题文件控制

        # 1. 界面设置
        tab_widget.addTab(self.create_interface_tab(), self.tr.tr('settings.interface'))

        # 2. 编辑器设置
        tab_widget.addTab(self.create_editor_tab(), self.tr.tr('settings.editor'))

        # 3. 性能设置
        tab_widget.addTab(self.create_performance_tab(), self.tr.tr('settings.performance'))

        # 4. 文件设置
        tab_widget.addTab(self.create_file_tab(), self.tr.tr('settings.file'))

        layout.addWidget(tab_widget)

        # 按钮容器
        button_container = QWidget()
        button_container.setObjectName("settingsButtonContainer")
        # 移除内联样式，让主题文件控制
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(10, 10, 10, 10)

        # 恢复默认按钮（左侧）
        restore_btn = QPushButton(self.tr.tr('settings.restore_default'))
        restore_btn.clicked.connect(self.restore_defaults)
        button_layout.addWidget(restore_btn)

        button_layout.addStretch()

        # 确定和取消按钮（右侧）
        ok_btn = QPushButton(self.tr.tr('settings.ok'))
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept_settings)
        ok_btn.setMinimumWidth(80)

        cancel_btn = QPushButton(self.tr.tr('settings.cancel'))
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setMinimumWidth(80)

        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)

        layout.addWidget(button_container)

    def create_interface_tab(self):
        """创建界面设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignTop)

        # 语言设置
        lang_group = QGroupBox(self.tr.tr('settings.language'))
        lang_layout = QVBoxLayout()

        lang_label = QLabel(self.tr.tr('settings.ui_language'))
        self.language_combo = QComboBox()
        self.language_combo.addItems([
            self.tr.tr('settings.language_chinese'),
            self.tr.tr('settings.language_english')
        ])

        lang_row = QHBoxLayout()
        lang_row.addWidget(lang_label)
        lang_row.addWidget(self.language_combo)
        lang_row.addStretch()
        lang_layout.addLayout(lang_row)

        note_label = QLabel(self.tr.tr('settings.language_note'))
        note_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        note_label.setWordWrap(True)
        lang_layout.addWidget(note_label)

        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)

        # 主题设置
        theme_group = QGroupBox(self.tr.tr('settings.theme'))
        theme_layout = QVBoxLayout()

        self.theme_group = QButtonGroup()

        self.theme_light = QRadioButton(self.tr.tr('settings.theme_light'))
        self.theme_dark = QRadioButton(self.tr.tr('settings.theme_dark'))
        self.theme_system = QRadioButton(self.tr.tr('settings.theme_system'))

        self.theme_group.addButton(self.theme_light, 0)
        self.theme_group.addButton(self.theme_dark, 1)
        self.theme_group.addButton(self.theme_system, 2)

        # 连接信号
        self.theme_dark.toggled.connect(self._on_theme_changed)
        self.theme_system.toggled.connect(self._on_theme_changed)

        theme_layout.addWidget(self.theme_light)
        theme_layout.addWidget(self.theme_dark)
        theme_layout.addWidget(self.theme_system)

        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        # 动画设置
        animation_group = QGroupBox(self.tr.tr('settings.animations'))
        animation_layout = QHBoxLayout()

        animation_label = QLabel(self.tr.tr('settings.enable_animations'))
        self.animations_checkbox = ToggleSwitch()

        animation_layout.addWidget(animation_label)
        animation_layout.addWidget(self.animations_checkbox)
        animation_layout.addStretch()

        animation_group.setLayout(animation_layout)
        layout.addWidget(animation_group)
        
        # 标尺显示设置
        ruler_group = QGroupBox(self.tr.tr('settings.ruler'))
        ruler_layout = QHBoxLayout()

        ruler_label = QLabel(self.tr.tr('settings.show_ruler'))
        self.ruler_checkbox = ToggleSwitch()

        ruler_layout.addWidget(ruler_label)
        ruler_layout.addWidget(self.ruler_checkbox)
        ruler_layout.addStretch()

        ruler_group.setLayout(ruler_layout)
        layout.addWidget(ruler_group)

        layout.addStretch()
        return widget

    def create_editor_tab(self):
        """创建编辑器设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignTop)

        # 默认工具大小
        tool_group = QGroupBox(self.tr.tr('settings.default_tool_size'))
        tool_layout = QVBoxLayout()

        # 默认画笔大小
        brush_label = QLabel(self.tr.tr('settings.default_brush_size', value=20))
        self.brush_size_slider = QSlider(Qt.Horizontal)
        self.brush_size_slider.setRange(1, 500)
        self.brush_size_slider.valueChanged.connect(
            lambda v: brush_label.setText(self.tr.tr('settings.default_brush_size', value=v))
        )
        tool_layout.addWidget(brush_label)
        tool_layout.addWidget(self.brush_size_slider)

        # 默认选择范围
        selection_label = QLabel(self.tr.tr('settings.default_selection_size', value=50))
        self.selection_size_slider = QSlider(Qt.Horizontal)
        self.selection_size_slider.setRange(1, 500)
        self.selection_size_slider.valueChanged.connect(
            lambda v: selection_label.setText(self.tr.tr('settings.default_selection_size', value=v))
        )
        tool_layout.addWidget(selection_label)
        tool_layout.addWidget(self.selection_size_slider)

        tool_group.setLayout(tool_layout)
        layout.addWidget(tool_group)

        # 历史记录
        history_group = QGroupBox(self.tr.tr('settings.history'))
        history_layout = QVBoxLayout()

        undo_label = QLabel(self.tr.tr('settings.undo_limit', value=50))
        self.undo_limit_slider = QSlider(Qt.Horizontal)
        self.undo_limit_slider.setRange(10, 100)
        self.undo_limit_slider.valueChanged.connect(
            lambda v: undo_label.setText(self.tr.tr('settings.undo_limit', value=v))
        )
        history_layout.addWidget(undo_label)
        history_layout.addWidget(self.undo_limit_slider)

        history_group.setLayout(history_layout)
        layout.addWidget(history_group)

        # 画布背景
        canvas_group = QGroupBox(self.tr.tr('settings.canvas_background'))
        canvas_layout = QVBoxLayout()

        self.canvas_bg_group = QButtonGroup()

        self.canvas_white = QRadioButton(self.tr.tr('settings.canvas_white'))
        self.canvas_gray = QRadioButton(self.tr.tr('settings.canvas_gray'))
        self.canvas_black = QRadioButton(self.tr.tr('settings.canvas_black'))

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
        cache_group = QGroupBox(self.tr.tr('settings.cache_settings'))
        cache_layout = QVBoxLayout()

        tile_label = QLabel(self.tr.tr('settings.tile_cache_size', value=1000))
        self.tile_cache_slider = QSlider(Qt.Horizontal)
        self.tile_cache_slider.setRange(100, 2000)
        self.tile_cache_slider.setSingleStep(100)
        self.tile_cache_slider.valueChanged.connect(
            lambda v: tile_label.setText(self.tr.tr('settings.tile_cache_size', value=v))
        )
        cache_layout.addWidget(tile_label)
        cache_layout.addWidget(self.tile_cache_slider)

        cache_note = QLabel(self.tr.tr('settings.cache_note'))
        cache_note.setStyleSheet("color: #6c757d; font-size: 12px;")
        cache_note.setWordWrap(True)
        cache_layout.addWidget(cache_note)

        cache_group.setLayout(cache_layout)
        layout.addWidget(cache_group)

        # 处理延迟
        delay_group = QGroupBox(self.tr.tr('settings.processing_delay'))
        delay_layout = QVBoxLayout()

        debounce_label = QLabel(self.tr.tr('settings.debounce_delay', value=150))
        self.debounce_slider = QSlider(Qt.Horizontal)
        self.debounce_slider.setRange(50, 500)
        self.debounce_slider.setSingleStep(50)
        self.debounce_slider.valueChanged.connect(
            lambda v: debounce_label.setText(self.tr.tr('settings.debounce_delay', value=v))
        )
        delay_layout.addWidget(debounce_label)
        delay_layout.addWidget(self.debounce_slider)

        delay_note = QLabel(self.tr.tr('settings.delay_note'))
        delay_note.setStyleSheet("color: #6c757d; font-size: 12px;")
        delay_note.setWordWrap(True)
        delay_layout.addWidget(delay_note)

        delay_group.setLayout(delay_layout)
        layout.addWidget(delay_group)

        # 硬件加速
        hw_group = QGroupBox(self.tr.tr('settings.hardware_acceleration'))
        hw_layout = QVBoxLayout()

        hw_switch_layout = QHBoxLayout()
        hw_label = QLabel(self.tr.tr('settings.enable_hw_accel'))
        self.hw_accel_checkbox = ToggleSwitch()
        hw_switch_layout.addWidget(hw_label)
        hw_switch_layout.addWidget(self.hw_accel_checkbox)
        hw_switch_layout.addStretch()
        hw_layout.addLayout(hw_switch_layout)

        hw_note = QLabel(self.tr.tr('settings.hw_accel_note'))
        hw_note.setStyleSheet("color: #6c757d; font-size: 12px;")
        hw_note.setWordWrap(True)
        hw_layout.addWidget(hw_note)

        hw_group.setLayout(hw_layout)
        layout.addWidget(hw_group)

        # 图像尺寸限制
        size_group = QGroupBox(self.tr.tr('settings.image_size_limit'))
        size_layout = QVBoxLayout()

        size_row = QHBoxLayout()
        size_label = QLabel(self.tr.tr('settings.max_image_size'))
        self.max_size_spinbox = QSpinBox()
        self.max_size_spinbox.setRange(1000, 50000)
        self.max_size_spinbox.setSingleStep(1000)
        self.max_size_spinbox.setSuffix(" px")
        size_row.addWidget(size_label)
        size_row.addWidget(self.max_size_spinbox)
        size_row.addStretch()
        size_layout.addLayout(size_row)

        size_note = QLabel(self.tr.tr('settings.size_note'))
        size_note.setStyleSheet("color: #6c757d; font-size: 12px;")
        size_note.setWordWrap(True)
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
        format_group = QGroupBox(self.tr.tr('settings.default_save_format'))
        format_layout = QVBoxLayout()

        format_row = QHBoxLayout()
        format_label = QLabel(self.tr.tr('settings.save_format'))
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            self.tr.tr('settings.format_follow_original'),
            "PNG",
            "JPG",
            "BMP",
            "WebP"
        ])
        format_row.addWidget(format_label)
        format_row.addWidget(self.format_combo)
        format_row.addStretch()
        format_layout.addLayout(format_row)

        format_note = QLabel(self.tr.tr('settings.format_note'))
        format_note.setStyleSheet("color: #6c757d; font-size: 12px;")
        format_note.setWordWrap(True)
        format_layout.addWidget(format_note)

        format_group.setLayout(format_layout)
        layout.addWidget(format_group)

        # 文件名格式
        filename_group = QGroupBox(self.tr.tr('settings.filename_format'))
        filename_layout = QVBoxLayout()

        self.filename_format_group = QButtonGroup()

        self.filename_timestamp = QRadioButton(self.tr.tr('settings.filename_timestamp'))
        self.filename_copy = QRadioButton(self.tr.tr('settings.filename_copy'))
        self.filename_custom = QRadioButton(self.tr.tr('settings.filename_custom'))

        self.filename_format_group.addButton(self.filename_timestamp, 0)
        self.filename_format_group.addButton(self.filename_copy, 1)
        self.filename_format_group.addButton(self.filename_custom, 2)

        filename_layout.addWidget(self.filename_timestamp)
        filename_layout.addWidget(self.filename_copy)
        filename_layout.addWidget(self.filename_custom)

        # 自定义前缀/后缀
        custom_layout = QHBoxLayout()
        custom_layout.setContentsMargins(30, 5, 0, 5)

        prefix_label = QLabel(self.tr.tr('settings.prefix'))
        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText(self.tr.tr('settings.prefix_placeholder'))
        self.prefix_edit.setEnabled(self.filename_custom.isChecked())

        suffix_label = QLabel(self.tr.tr('settings.suffix'))
        self.suffix_edit = QLineEdit()
        self.suffix_edit.setPlaceholderText(self.tr.tr('settings.suffix_placeholder'))
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
        # 移除主题限制，允许用户选择任何主题
        pass

    def accept_settings(self):
        """接受设置并保存到配置文件"""
        config = self.config_manager

        # 检查语言是否改变
        old_language = config.get('general', 'language', 'zh_CN')
        new_language = config.ui_index_to_config_value('language', self.language_combo.currentIndex())
        language_changed = (old_language != new_language)

        # 通用设置
        config.set('general', 'language', new_language)

        # 界面设置
        if self.theme_light.isChecked():
            config.set('interface', 'theme', 'light')
        elif self.theme_dark.isChecked():
            config.set('interface', 'theme', 'dark')
        else:
            config.set('interface', 'theme', 'system')

        # 动画设置
        animations_enabled = self.animations_checkbox.isChecked()
        config.set('interface', 'animations_enabled', animations_enabled)

        # 应用动画设置到全局配置
        from ..utils.animations import set_global_animation_enabled
        set_global_animation_enabled(animations_enabled)
        
        # 标尺显示设置
        config.set('interface', 'show_ruler', self.ruler_checkbox.isChecked())

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
        save_format_value = config.ui_index_to_config_value('save_format', self.format_combo.currentIndex())
        config.set('file', 'default_save_format', save_format_value)

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
            # 如果语言改变，提示用户重启
            if language_changed:
                QMessageBox.information(
                    self,
                    self.tr.tr('dialog.info'),
                    self.tr.tr('message.language_changed')
                )
            self.accept()  # 关闭对话框并返回 Accepted
        else:
            QMessageBox.critical(
                self,
                self.tr.tr('dialog.error'),
                self.tr.tr('settings.save_failed')
            )

    def restore_defaults(self):
        """恢复默认设置"""
        reply = QMessageBox.question(
            self,
            self.tr.tr('settings.restore_default'),
            self.tr.tr('settings.restore_confirm'),
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
                self.tr.tr('settings.restore_default'),
                self.tr.tr('settings.restore_complete')
            )
