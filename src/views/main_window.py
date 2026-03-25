"""
主窗口模块

应用程序的主窗口，包含菜单栏、工具栏和主要布局。
"""

from typing import Optional
import os
import numpy as np
from datetime import datetime
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                                QSplitter, QToolBar, QFileDialog, QMessageBox,
                                QPushButton, QLabel, QStatusBar, QSizePolicy,
                                QSpinBox, QRadioButton, QButtonGroup, QFrame,
                                QApplication)
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QAction, QIcon, QEnterEvent

from .canvas import Canvas
from .binarization_panel import BinarizationPanel
from .shortcut_handler import ShortcutHandler
from ..models.image_data import ImageData
from ..models.history_manager import HistoryManager
from ..models.brush_tool import BrushTool
from ..models.selection_tool import SelectionTool
from ..utils.file_io import load_image, save_image
from ..utils.binarization_engine import BinarizationEngine
from ..utils.binarization_worker import BinarizationWorker
from ..utils.theme_manager import ThemeManager
from ..utils.config_manager import get_config_manager
from ..utils.translation_manager import get_translator


class MainWindow(QMainWindow):
    """
    主窗口类
    
    管理应用程序的整体布局和功能集成。
    """
    
    # 布局常量
    LEFT_PANEL_WIDTH = 300  # 左侧二值化面板宽度
    RIGHT_PANEL_WIDTH = 250  # 右侧属性面板宽度
    CANVAS_MIN_WIDTH = 400  # 画布最小宽度
    
    def __init__(self):
        """初始化主窗口"""
        super().__init__()
        
        # 配置管理器
        self.config_manager = get_config_manager()
        
        # 翻译管理器
        self.tr = get_translator()
        
        # 主题管理器
        self.theme_manager = ThemeManager()
        
        # 数据
        self.image_data: Optional[ImageData] = None
        self.history_manager = HistoryManager()
        self.current_file_path: Optional[str] = None
        self.saved_file_path: Optional[str] = None  # 记录已保存的文件路径
        
        # 异步二值化
        self.binarization_worker: Optional[BinarizationWorker] = None
        self.pending_binarization_params: Optional[tuple] = None  # (preprocess_params, method, threshold, method_params)
        self.binarization_debounce_timer = QTimer()
        self.binarization_debounce_timer.setSingleShot(True)
        self.binarization_debounce_timer.timeout.connect(self._start_binarization)
        
        # 从配置加载防抖延迟
        debounce_delay = self.config_manager.get('performance', 'debounce_delay', 150)
        self.binarization_debounce_timer.setInterval(debounce_delay)
        
        # 设置窗口
        self.setWindowTitle(self.tr.tr('app.title'))
        self.setGeometry(100, 100, 1550, 800)  # 宽度从 1450 增加到 1550
        
        # 创建 UI
        self.setup_ui()
        self.create_actions()
        self.create_toolbars()
        self.create_statusbar()
        
        # 连接信号
        self.connect_signals()
        
        # 应用配置
        self.apply_config()
        
        # 初始状态
        self._update_ui_state()
    
    def closeEvent(self, event):
        """窗口关闭事件 - 清理资源"""
        # 停止防抖定时器
        if self.binarization_debounce_timer.isActive():
            self.binarization_debounce_timer.stop()
        
        # 取消并等待后台线程完成
        if self.binarization_worker is not None and self.binarization_worker.isRunning():
            self.binarization_worker.cancel()
            self.binarization_worker.wait(1000)  # 最多等待1秒
        
        # 接受关闭事件
        event.accept()
    
    def setup_ui(self):
        """设置 UI 布局"""
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建主分割器（左侧面板 + 中右部分）
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setHandleWidth(0)  # 设置分隔条宽度为 0
        main_splitter.setChildrenCollapsible(False)  # 禁止折叠
        
        # 左侧：二值化面板
        self.binarization_panel = BinarizationPanel(panel_width=self.LEFT_PANEL_WIDTH)
        self.binarization_panel.setMinimumWidth(self.LEFT_PANEL_WIDTH)
        self.binarization_panel.setMaximumWidth(self.LEFT_PANEL_WIDTH)
        main_splitter.addWidget(self.binarization_panel)
        
        # 中右部分：Canvas + 属性面板
        center_right_splitter = QSplitter(Qt.Horizontal)
        center_right_splitter.setHandleWidth(1)  # 设置分隔条宽度
        center_right_splitter.setChildrenCollapsible(False)
        
        # 中间：Canvas
        self.canvas = Canvas()
        self.canvas.setMinimumWidth(self.CANVAS_MIN_WIDTH)
        center_right_splitter.addWidget(self.canvas)
        
        # 右侧：属性面板
        # 右侧：属性面板
        from .properties_panel import PropertiesPanel
        self.properties_panel = PropertiesPanel()
        self.properties_panel.setMinimumWidth(self.RIGHT_PANEL_WIDTH)
        self.properties_panel.setMaximumWidth(self.RIGHT_PANEL_WIDTH)
        center_right_splitter.addWidget(self.properties_panel)
        # 设置中右分割器比例（重要：让画布优先占用空间）
        center_right_splitter.setStretchFactor(0, 3)  # Canvas 高优先级伸缩
        center_right_splitter.setStretchFactor(1, 0)  # 属性面板固定
        
        main_splitter.addWidget(center_right_splitter)
        
        # 设置主分割器比例
        main_splitter.setStretchFactor(0, 0)  # 左侧面板固定
        main_splitter.setStretchFactor(1, 4)  # 中右部分高优先级伸缩
        
        # 设置初始大小比例
        main_splitter.setSizes([self.LEFT_PANEL_WIDTH, 1000])
        
        # 禁用左侧面板的拖动（通过设置固定宽度已经实现）
        main_splitter.handle(1).setEnabled(False)  # 禁用第一个分隔条
        
        main_layout.addWidget(main_splitter)
    
    def create_actions(self):
        """创建动作"""
        # 文件菜单动作
        self.open_action = QAction(self.tr.tr('toolbar.open'), self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.setToolTip(self.tr.tr('tooltip.open'))
        self.open_action.triggered.connect(self._open_file)
        self.addAction(self.open_action)
        
        self.save_action = QAction(self.tr.tr('toolbar.save'), self)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.setToolTip(self.tr.tr('tooltip.save'))
        self.save_action.triggered.connect(self._save_file)
        self.addAction(self.save_action)
        
        self.save_as_action = QAction(self.tr.tr('menu.save_as'), self)
        self.save_as_action.setShortcut("Ctrl+Shift+S")
        self.save_as_action.setToolTip(self.tr.tr('tooltip.save_as'))
        self.save_as_action.triggered.connect(self._save_file_as)
        self.addAction(self.save_as_action)
        
        self.exit_action = QAction(self.tr.tr('menu.exit'), self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.setToolTip(self.tr.tr('tooltip.exit'))
        self.exit_action.triggered.connect(self.close)
        self.addAction(self.exit_action)
        
        # 编辑菜单动作
        self.undo_action = QAction(self.tr.tr('toolbar.undo'), self)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.setToolTip(self.tr.tr('tooltip.undo'))
        self.undo_action.triggered.connect(self._undo)
        self.addAction(self.undo_action)
        
        self.redo_action = QAction(self.tr.tr('toolbar.redo'), self)
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.setToolTip(self.tr.tr('tooltip.redo'))
        self.redo_action.triggered.connect(self._redo)
        self.addAction(self.redo_action)
        
        self.reset_action = QAction(self.tr.tr('toolbar.reset'), self)
        self.reset_action.setShortcut("Ctrl+R")
        self.reset_action.setToolTip(self.tr.tr('tooltip.reset'))
        self.reset_action.triggered.connect(self._reset_to_initial)
        self.addAction(self.reset_action)
        
        # 工具动作 - 创建自定义按钮以支持悬浮事件
        self.brush_button = QPushButton(self.tr.tr('toolbar.brush'))
        self.brush_button.setCheckable(True)
        self.brush_button.setFlat(True)
        self.brush_button.setToolTip(self.tr.tr('tooltip.brush_tool'))
        self.brush_button.clicked.connect(self._select_brush_tool)
        self.brush_button.installEventFilter(self)
        
        # 为画笔按钮添加快捷键
        self.brush_shortcut = QAction(self)
        self.brush_shortcut.setShortcut("B")
        self.brush_shortcut.triggered.connect(self._select_brush_tool)
        self.addAction(self.brush_shortcut)
        
        # 初始化快捷键处理器
        self.shortcut_handler = ShortcutHandler(self)
        
        # 抓取工具动作
        self.pan_action = QAction(self.tr.tr('toolbar.pan'), self)
        self.pan_action.setShortcut("H")
        self.pan_action.setCheckable(True)
        self.pan_action.setToolTip(self.tr.tr('tooltip.pan_tool'))
        self.pan_action.triggered.connect(self._select_pan_tool)
        self.addAction(self.pan_action)
        
        self.crop_action = QAction(self.tr.tr('toolbar.crop'), self)
        self.crop_action.setShortcut("C")
        self.crop_action.setCheckable(True)
        self.crop_action.setToolTip(self.tr.tr('tooltip.crop_tool'))
        self.crop_action.triggered.connect(self._select_crop_tool)
        self.addAction(self.crop_action)
        
        # 选择工具动作
        self.selection_tool_action = QAction(self.tr.tr('toolbar.selection'), self)
        self.selection_tool_action.setShortcut("W")
        self.selection_tool_action.setCheckable(True)
        self.selection_tool_action.setToolTip(self.tr.tr('tooltip.selection_tool'))
        self.selection_tool_action.triggered.connect(self._select_selection_tool)
        self.addAction(self.selection_tool_action)
        
        # 选区菜单动作
        self.deselect_action = QAction(self.tr.tr('tooltip.deselect'), self)
        self.deselect_action.setShortcut("Ctrl+D")
        self.deselect_action.triggered.connect(self._deselect)
        self.addAction(self.deselect_action)
        
        self.invert_selection_action = QAction(self.tr.tr('tooltip.invert_selection'), self)
        self.invert_selection_action.setShortcut("Ctrl+Shift+I")
        self.invert_selection_action.triggered.connect(self._invert_selection)
        self.addAction(self.invert_selection_action)
        
        self.select_black_action = QAction(self.tr.tr('menu.select_black'), self)
        self.select_black_action.triggered.connect(lambda: self._select_by_color(0))
        
        self.select_white_action = QAction(self.tr.tr('menu.select_white'), self)
        self.select_white_action.triggered.connect(lambda: self._select_by_color(255))
    
    def create_toolbars(self):
        """创建工具栏"""
        self.toolbar = QToolBar(self.tr.tr('toolbar.title'))
        self.toolbar.setMovable(False)
        self.toolbar.setContextMenuPolicy(Qt.PreventContextMenu)  # 禁用右键菜单
        
        # 创建工具栏容器
        toolbar_container = QWidget()
        toolbar_layout = QHBoxLayout(toolbar_container)
        toolbar_layout.setContentsMargins(8, 4, 8, 4)
        toolbar_layout.setSpacing(8)
        
        # 创建按钮辅助函数
        def create_toolbar_button(text, tooltip, checkable=False):
            btn = QPushButton(text)
            btn.setCheckable(checkable)
            btn.setToolTip(tooltip)
            btn.setMinimumHeight(28)
            btn.setMaximumHeight(28)
            return btn
        
        # 创建按钮组容器辅助函数
        def create_button_group():
            group = QFrame()
            group.setObjectName("toolbarButtonGroup")
            group_layout = QHBoxLayout(group)
            group_layout.setContentsMargins(3, 1, 3, 1)
            group_layout.setSpacing(0)
            return group, group_layout
            group_layout.setSpacing(0)
            return group, group_layout
        
        # 文件操作组
        file_group, file_layout = create_button_group()
        open_btn = create_toolbar_button(self.tr.tr('toolbar.open'), self.tr.tr('tooltip.open'))
        open_btn.clicked.connect(self._open_file)
        file_layout.addWidget(open_btn)
        
        save_btn = create_toolbar_button(self.tr.tr('toolbar.save'), self.tr.tr('tooltip.save'))
        save_btn.clicked.connect(self._save_file)
        file_layout.addWidget(save_btn)
        self.save_action_btn = save_btn
        toolbar_layout.addWidget(file_group)
        
        # 编辑操作组
        edit_group, edit_layout = create_button_group()
        undo_btn = create_toolbar_button(self.tr.tr('toolbar.undo'), self.tr.tr('tooltip.undo'))
        undo_btn.clicked.connect(self._undo)
        edit_layout.addWidget(undo_btn)
        self.undo_action_btn = undo_btn
        
        redo_btn = create_toolbar_button(self.tr.tr('toolbar.redo'), self.tr.tr('tooltip.redo'))
        redo_btn.clicked.connect(self._redo)
        edit_layout.addWidget(redo_btn)
        self.redo_action_btn = redo_btn
        
        reset_btn = create_toolbar_button(self.tr.tr('toolbar.reset'), self.tr.tr('tooltip.reset'))
        reset_btn.clicked.connect(self._reset_to_initial)
        edit_layout.addWidget(reset_btn)
        self.reset_action_btn = reset_btn
        toolbar_layout.addWidget(edit_group)
        
        # 工具选择组
        tool_group, tool_layout = create_button_group()
        self.pan_button = create_toolbar_button(self.tr.tr('toolbar.pan'), self.tr.tr('tooltip.pan_tool'), checkable=True)
        self.pan_button.clicked.connect(self._select_pan_tool)
        tool_layout.addWidget(self.pan_button)
        
        self.brush_button = create_toolbar_button(self.tr.tr('toolbar.brush'), self.tr.tr('tooltip.brush_tool'), checkable=True)
        self.brush_button.clicked.connect(self._select_brush_tool)
        self.brush_button.installEventFilter(self)
        tool_layout.addWidget(self.brush_button)
        
        self.crop_button = create_toolbar_button(self.tr.tr('toolbar.crop'), self.tr.tr('tooltip.crop_tool'), checkable=True)
        self.crop_button.clicked.connect(self._select_crop_tool)
        tool_layout.addWidget(self.crop_button)
        
        self.selection_tool_button = create_toolbar_button(self.tr.tr('toolbar.selection'), self.tr.tr('tooltip.selection_tool'), checkable=True)
        self.selection_tool_button.setEnabled(False)
        self.selection_tool_button.clicked.connect(self._select_selection_tool)
        self.selection_tool_button.installEventFilter(self)
        tool_layout.addWidget(self.selection_tool_button)
        toolbar_layout.addWidget(tool_group)
        
        # 添加弹性空间
        toolbar_layout.addStretch()
        
        # 应用操作组（设置、关于）
        app_group, app_layout = create_button_group()
        settings_btn = create_toolbar_button(self.tr.tr('toolbar.settings'), self.tr.tr('settings.title'))
        settings_btn.clicked.connect(self._show_settings)
        app_layout.addWidget(settings_btn)
        
        about_btn = create_toolbar_button(self.tr.tr('toolbar.about'), self.tr.tr('about.title', app_name='BinarizationTool'))
        about_btn.clicked.connect(self._show_about)
        app_layout.addWidget(about_btn)
        toolbar_layout.addWidget(app_group)
        
        # 当前工具显示
        self.current_tool_label = QLabel(self.tr.tr('toolbar.current_tool', tool=self.tr.tr('tool.none')))
        self.current_tool_label.setStyleSheet("padding: 0 10px; color: #495057; font-size: 14px; font-weight: 500;")
        toolbar_layout.addWidget(self.current_tool_label)
        
        # 将容器添加到工具栏
        self.addToolBar(self.toolbar)
        self.toolbar.addWidget(toolbar_container)
    
    def create_statusbar(self):
        """创建状态栏"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage(self.tr.tr('app.ready'))
        
        # 创建菜单栏（但隐藏，功能通过工具栏和快捷键访问）
        self._create_menus()
        self.menuBar().hide()  # 隐藏菜单栏
    
    def connect_signals(self):
        """连接信号"""
        # 二值化参数改变
        self.binarization_panel.parameters_changed.connect(self._on_parameters_changed)
        
        # 视图模式切换
        self.binarization_panel.view_mode_changed.connect(self._on_view_mode_changed)
        
        # Canvas 图片修改
        self.canvas.image_modified.connect(self._on_image_modified)
        
        # Canvas 文件拖放
        self.canvas.file_dropped.connect(self._load_file_from_path)
        
        # Canvas 缩放变化
        self.canvas.zoom_changed.connect(self.properties_panel.set_zoom_level)
        
        # 属性面板工具设置信号
        self._connect_tool_settings()
    
    def _create_menus(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu(self.tr.tr('menu.file'))
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu(self.tr.tr('menu.edit'))
        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.redo_action)
        
        # 选择菜单
        select_menu = menubar.addMenu(self.tr.tr('menu.select'))
        select_menu.addAction(self.deselect_action)
        select_menu.addAction(self.invert_selection_action)
        select_menu.addSeparator()
        select_menu.addAction(self.select_black_action)
        select_menu.addAction(self.select_white_action)
    
    def _select_pan_tool(self):
        """选择抓取工具"""
        if self.image_data is None:
            self.statusbar.showMessage(self.tr.tr('message.load_image_first'))
            return
        
        self.canvas.set_tool(self.canvas.pan_tool)
        self.pan_button.setChecked(True)
        self.brush_button.setChecked(False)
        self.crop_button.setChecked(False)
        self.selection_tool_button.setChecked(False)
        self.current_tool_label.setText(self.tr.tr('toolbar.current_tool', tool=self.tr.tr('tool.pan')))
        self.statusbar.showMessage(self.tr.tr('message.pan_activated'))
        
        # 隐藏所有工具设置（抓取工具没有设置）
        self.properties_panel.hide_all_tool_settings()
        
        # 确保 Canvas 获得焦点
        self.canvas.setFocus()
    
    def _select_brush_tool(self):
        """选择画笔工具"""
        if self.image_data is None:
            self.statusbar.showMessage(self.tr.tr('message.load_image_first'))
            return
        
        self.canvas.set_tool(self.canvas.brush_tool)
        self.pan_button.setChecked(False)
        self.brush_button.setChecked(True)
        self.crop_button.setChecked(False)
        self.selection_tool_button.setChecked(False)
        self.current_tool_label.setText(self.tr.tr('toolbar.current_tool', tool=self.tr.tr('tool.brush')))
        self.statusbar.showMessage(self.tr.tr('message.brush_activated'))
        
        # 显示画笔工具设置
        self.properties_panel.show_brush_settings()
        
        # 确保 Canvas 获得焦点以接收键盘事件
        self.canvas.setFocus()
    
    def _select_crop_tool(self):
        """选择裁剪工具"""
        if self.image_data is None:
            return
        
        self.canvas.set_tool(self.canvas.crop_tool)
        self.pan_button.setChecked(False)
        self.brush_button.setChecked(False)
        self.crop_button.setChecked(True)
        self.selection_tool_button.setChecked(False)
        self.current_tool_label.setText(self.tr.tr('toolbar.current_tool', tool=self.tr.tr('tool.crop')))
        self.statusbar.showMessage(self.tr.tr('message.crop_activated'))
        
        # 隐藏所有工具设置（裁剪工具没有设置）
        self.properties_panel.hide_all_tool_settings()
    
    def _select_selection_tool(self):
        """选择选择工具"""
        if self.image_data is None:
            self.statusbar.showMessage(self.tr.tr('message.load_image_first'))
            return
        
        self.canvas.set_tool(self.canvas.selection_tool)
        self.pan_button.setChecked(False)
        self.brush_button.setChecked(False)
        self.crop_button.setChecked(False)
        self.selection_tool_button.setChecked(True)
        self.current_tool_label.setText(self.tr.tr('toolbar.current_tool', tool=self.tr.tr('tool.selection')))
        mode_text = self.tr.tr('mode.add') if self.canvas.selection_tool.selection_mode == 'add' else self.tr.tr('mode.subtract')
        self.statusbar.showMessage(self.tr.tr('message.selection_activated', mode=mode_text))
        
        # 显示选择工具设置
        self.properties_panel.show_selection_settings()
        
        # 确保 Canvas 获得焦点以接收键盘事件
        self.canvas.setFocus()
    
    def _deselect(self):
        """取消选择"""
        if self.image_data is None:
            return
        
        self.canvas.selection_tool.clear_selection()
        self.image_data.selection_mask = None
        # 更新分块缓存以清除选区
        self._safe_update_tile_cache(None)
        
        # 保存到历史管理器
        self.history_manager.push_state(self.image_data)
        
        self._update_ui_state()  # 更新 UI 状态
        self.statusbar.showMessage(self.tr.tr('message.deselected'))
    
    def _invert_selection(self):
        """反选"""
        if self.image_data is None:
            return
        
        self.canvas.selection_tool.selection_mask = self.image_data.selection_mask
        self.canvas.selection_tool.invert_selection(
            self.image_data.width,
            self.image_data.height
        )
        self.image_data.selection_mask = self.canvas.selection_tool.selection_mask
        # 更新分块缓存以显示选区
        self._safe_update_tile_cache(self.image_data.selection_mask)
        
        # 保存到历史管理器（重要！）
        self.history_manager.push_state(self.image_data)
        
        self._update_ui_state()  # 更新 UI 状态
        self.statusbar.showMessage(self.tr.tr('message.inverted'))
    
    def _select_by_color(self, color: int):
        """按颜色选择"""
        if self.image_data is None:
            return
        
        self.canvas.selection_tool.select_by_color(self.image_data, color)
        self.image_data.selection_mask = self.canvas.selection_tool.selection_mask
        # 更新分块缓存以显示选区
        self._safe_update_tile_cache(self.image_data.selection_mask)
        
        # 保存到历史管理器（重要！）
        self.history_manager.push_state(self.image_data)
        
        self._update_ui_state()  # 更新 UI 状态
        color_name = self.tr.tr('color.black') if color == 0 else self.tr.tr('color.white')
        self.statusbar.showMessage(self.tr.tr('message.selected_color', color=color_name))
    
    def _open_file(self):
        """打开文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr.tr('file_dialog.open_image'),
            "",
            self.tr.tr('file_dialog.image_files')
        )
        
        if file_path:
            self._load_file_from_path(file_path)
    
    def _load_file_from_path(self, file_path: str):
        """从文件路径加载图片（支持打开文件和拖放）"""
        # 显示处理中状态
        self.canvas.set_processing(True)
        self.statusbar.showMessage(self.tr.tr('app.processing'))
        
        # 使用 QTimer 延迟加载，确保 UI 有时间更新
        QTimer.singleShot(50, lambda: self._do_load_file(file_path))
    
    def _do_load_file(self, file_path: str):
        """实际执行文件加载（延迟调用）"""
        try:
            # 加载图片（不自动二值化）
            self.image_data = load_image(file_path, binarize=False)
            
            # 设置初始视图模式为二值化
            self.image_data.set_view_mode('binary')
            self.binarization_panel.view_mode_switcher.set_mode('binary')
            
            # 获取二值化参数
            preprocess_params = self.binarization_panel.get_preprocess_params()
            method = self.binarization_panel.get_method()
            threshold = self.binarization_panel.get_threshold()
            method_params = self.binarization_panel.get_method_params()
            
            # 使用异步工作线程进行二值化
            self.binarization_worker = BinarizationWorker(
                self.image_data.original_pixels,
                preprocess_params,
                method,
                threshold,
                method_params
            )
            
            # 连接信号
            self.binarization_worker.finished.connect(
                lambda binary_pixels: self._on_initial_binarization_finished(
                    binary_pixels, file_path
                )
            )
            self.binarization_worker.error.connect(self._on_binarization_error)
            
            # 启动工作线程
            self.binarization_worker.start()
            
        except Exception as e:
            # 隐藏处理中状态
            self.canvas.set_processing(False)
            QMessageBox.critical(self, self.tr.tr('error.title'), 
                               self.tr.tr('error.load_failed', error=str(e)))
    
    def _on_initial_binarization_finished(self, binary_pixels: np.ndarray, file_path: str):
        """初始二值化完成的回调"""
        try:
            # 更新图片数据
            self.image_data.pixels = binary_pixels
            
            # 设置到 Canvas
            self.canvas.set_image(self.image_data)
            
            # 清除历史并保存初始状态
            self.history_manager.clear()
            self.history_manager.push_state(self.image_data)
            
            # 保存文件路径
            self.current_file_path = file_path
            self.saved_file_path = None  # 重置保存路径，新文件需要重新保存
            
            # 更新属性面板
            self.properties_panel.set_image_info(self.image_data, file_path)
            
            # 隐藏处理中状态
            self.canvas.set_processing(False)
            
            # 更新状态
            self.statusbar.showMessage(self.tr.tr('message.loaded', path=file_path))
            self._update_ui_state()
            
        except Exception as e:
            self.canvas.set_processing(False)
            QMessageBox.critical(self, self.tr.tr('error.title'), str(e))
    
    def _save_file(self):
        """保存文件（第一次另存为，之后覆盖）"""
        if self.image_data is None:
            return
        
        # 如果已经保存过，直接覆盖
        if self.saved_file_path:
            self._save_to_file(self.saved_file_path)
            return
        
        # 第一次保存：生成默认文件名并弹出对话框
        default_name = self._generate_default_save_name()
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存图片",
            default_name,
            "PNG 图片 (*.png);;JPEG 图片 (*.jpg);;BMP 图片 (*.bmp)"
        )
        
        if file_path:
            self._save_to_file(file_path)
            self.saved_file_path = file_path  # 记录保存路径
    
    def _save_file_as(self):
        """另存为（总是弹出对话框）"""
        if self.image_data is None:
            return
        
        # 生成默认文件名
        default_name = self._generate_default_save_name()
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr.tr('file_dialog.save_as'),
            default_name,
            self.tr.tr('file_dialog.png_files')
        )
        
        if file_path:
            self._save_to_file(file_path)
            self.saved_file_path = file_path  # 更新保存路径
    
    def _generate_default_save_name(self) -> str:
        """
        生成默认保存文件名（原名_时间戳）
        
        Returns:
            默认文件名路径
        """
        if self.current_file_path:
            # 获取原文件信息
            dir_path = os.path.dirname(self.current_file_path)
            file_name = os.path.basename(self.current_file_path)
            name_without_ext, ext = os.path.splitext(file_name)
            
            # 生成时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 组合新文件名
            new_name = f"{name_without_ext}_{timestamp}{ext}"
            return os.path.join(dir_path, new_name)
        else:
            # 如果没有原文件路径，使用默认名称
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"image_{timestamp}.png"
    
    def _save_to_file(self, file_path: str):
        """保存到文件"""
        try:
            save_image(self.image_data, file_path)
            self.current_file_path = file_path
            self.statusbar.showMessage(self.tr.tr('message.saved', path=file_path))
        except Exception as e:
            QMessageBox.critical(self, self.tr.tr('dialog.error'), self.tr.tr('dialog.save_error', error=str(e)))
    
    def _undo(self):
        """撤销"""
        if self.image_data is None:
            return
        
        if self.history_manager.can_undo():
            self.image_data = self.history_manager.undo(self.image_data)
            self.canvas.set_image(self.image_data)
            
            # 同步选择工具的选区状态
            if self.canvas.selection_tool:
                self.canvas.selection_tool.selection_mask = self.image_data.selection_mask
            
            self.statusbar.showMessage(self.tr.tr('message.undone'))
            self._update_ui_state()
            # 更新属性面板（撤销可能恢复裁剪前的尺寸）
            self.properties_panel.set_image_info(self.image_data, self.current_file_path)
    
    def _redo(self):
        """重做"""
        if self.image_data is None:
            return
        
        if self.history_manager.can_redo():
            self.image_data = self.history_manager.redo()
            self.canvas.set_image(self.image_data)
            
            # 同步选择工具的选区状态
            if self.canvas.selection_tool:
                self.canvas.selection_tool.selection_mask = self.image_data.selection_mask
            
            self.statusbar.showMessage(self.tr.tr('message.redone'))
            self._update_ui_state()
            # 更新属性面板（重做可能改变尺寸）
            self.properties_panel.set_image_info(self.image_data, self.current_file_path)
    
    def _reset_to_initial(self):
        """重置到初始状态"""
        if self.image_data is None:
            return
        
        # 检查是否有编辑内容
        if not self._has_edits():
            self.statusbar.showMessage(self.tr.tr('message.no_edits'))
            return
        
        # 弹窗确认
        reply = QMessageBox.question(
            self,
            self.tr.tr('dialog.confirm'),
            self.tr.tr('dialog.reset_confirm'),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 重新加载图片（最简单可靠的方式）
            if self.current_file_path:
                self._load_file_from_path(self.current_file_path)
                self.statusbar.showMessage(self.tr.tr('message.reset'))
            else:
                self.statusbar.showMessage(self.tr.tr('dialog.reset_no_file'))
    
    def _has_edits(self) -> bool:
        """
        检查是否有编辑内容
        
        Returns:
            True 如果有编辑内容（画笔编辑或裁剪），否则 False
        """
        if self.image_data is None:
            return False
        
        # 检查是否有画笔编辑（转换为 Python bool）
        has_brush_edits = (self.image_data.edit_mask is not None and 
                          bool(self.image_data.edit_mask.any()))
        
        # 检查是否有裁剪（通过比较当前尺寸和原始尺寸）
        has_crop = (self.image_data.pixels.shape != 
                   self.image_data.original_pixels.shape)
        
        return has_brush_edits or has_crop
    
    def _on_parameters_changed(self, preprocess_params: dict, method: int, threshold: int):
        """参数改变（预处理或二值化）- 根据当前模式决定是否重新计算"""
        if self.image_data is None:
            return
        
        mode = self.image_data.view_mode
        
        # 根据模式决定是否重新计算
        if mode == 'original':
            # 原图模式：只使缓存失效，不重新计算
            self.image_data.invalidate_preprocessed_cache()
            return
        
        elif mode == 'preprocessed':
            # 预处理模式：使缓存失效并重新计算预处理结果
            self.image_data.invalidate_preprocessed_cache()
            self._compute_preprocessed_pixels()
            self._update_canvas_display()
        
        elif mode == 'binary':
            # 二值化模式：使缓存失效并重新计算二值化结果
            self.image_data.invalidate_preprocessed_cache()
            
            # 获取方法特定参数
            method_params = self.binarization_panel.get_method_params()
            
            # 保存待处理的参数
            self.pending_binarization_params = (preprocess_params, method, threshold, method_params)
            
            # 重启防抖定时器（150ms 延迟，避免频繁触发）
            self.binarization_debounce_timer.start(150)
            
            # 显示处理中状态
            self.statusbar.showMessage(self.tr.tr('app.processing'))
    
    def _start_binarization(self):
        """启动异步二值化处理"""
        if self.image_data is None or self.pending_binarization_params is None:
            return
        
        # 取消之前的工作线程
        if self.binarization_worker is not None and self.binarization_worker.isRunning():
            self.binarization_worker.cancel()
            self.binarization_worker.wait()
        
        # 获取参数
        preprocess_params, method, threshold, method_params = self.pending_binarization_params
        
        # 创建新的工作线程
        self.binarization_worker = BinarizationWorker(
            self.image_data.original_pixels,
            preprocess_params,
            method,
            threshold,
            method_params
        )
        
        # 连接信号
        self.binarization_worker.finished.connect(self._on_binarization_finished)
        self.binarization_worker.error.connect(self._on_binarization_error)
        
        # 设置画布处理状态
        self.canvas.set_processing(True)
        
        # 启动线程
        self.binarization_worker.start()
    
    def _on_binarization_finished(self, binary_pixels):
        """二值化完成"""
        # 清除画布处理状态
        self.canvas.set_processing(False)
        
        if self.image_data is None:
            return
        
        try:
            # 只更新基础图层，保留编辑图层
            self.image_data.update_base_layer(binary_pixels)
            
            # 更新分块缓存
            self._safe_update_tile_cache(self.image_data.selection_mask)
            
            self.statusbar.showMessage(self.tr.tr('app.processing_complete'))
            
        except Exception as e:
            QMessageBox.warning(self, self.tr.tr('dialog.warning'), self.tr.tr('dialog.update_error', error=str(e)))
    
    def _on_binarization_error(self, error_message: str):
        """二值化出错"""
        # 清除画布处理状态
        self.canvas.set_processing(False)
        
        QMessageBox.warning(self, self.tr.tr('dialog.warning'), self.tr.tr('app.processing_failed') + f":\n{error_message}")
        self.statusbar.showMessage(self.tr.tr('app.processing_failed'))
    
    def _on_image_modified(self):
        """图片被修改"""
        if self.image_data is not None:
            # 使预处理缓存失效（裁剪等操作会修改原图）
            self.image_data.invalidate_preprocessed_cache()
            
            # 保存到历史
            self.history_manager.push_state(self.image_data)
            self._update_ui_state()
            
            # 更新属性面板（裁剪后尺寸会变化）
            self.properties_panel.set_image_info(self.image_data, self.current_file_path)
    
    def _update_ui_state(self):
        """更新 UI 状态"""
        has_image = self.image_data is not None
        
        # 文件操作
        self.save_action_btn.setEnabled(has_image)
        
        # 编辑操作
        self.undo_action_btn.setEnabled(self.history_manager.can_undo())
        self.redo_action_btn.setEnabled(self.history_manager.can_redo())
        self.reset_action_btn.setEnabled(has_image and self._has_edits())
        
        # 工具
        self.brush_button.setEnabled(has_image)
        self.crop_button.setEnabled(has_image)
        self.selection_tool_button.setEnabled(has_image)
        
        # 选区操作（保留 action 引用用于快捷键）
        has_selection = (self.image_data is not None and 
                        self.image_data.selection_mask is not None and
                        bool(self.image_data.selection_mask.any()))  # 转换为 Python bool
        self.deselect_action.setEnabled(has_selection)
        self.invert_selection_action.setEnabled(has_image)
        self.select_black_action.setEnabled(has_image)
        self.select_white_action.setEnabled(has_image)
    
    def _fill_selection(self, color: int):
        """
        填充选区（使用画笔批量填充逻辑）
        
        直接修改像素，不使用复杂的图层系统，保持性能一致。
        
        Args:
            color: 填充颜色（0=黑色, 255=白色）
        """
        if self.image_data is None:
            return
        
        # 检查是否有选区
        if not self.canvas.selection_tool.has_selection():
            self.statusbar.showMessage(self.tr.tr('message.no_selection'))
            return
        
        # 获取选区蒙版
        selection_mask = self.canvas.selection_tool.selection_mask
        
        # 检查选区尺寸是否匹配
        if selection_mask.shape != (self.image_data.height, self.image_data.width):
            self.statusbar.showMessage(self.tr.tr('message.selection_size_mismatch'))
            self.canvas.selection_tool.clear_selection()
            self.image_data.selection_mask = None
            self._safe_update_tile_cache(None)
            return
        
        # 使用画笔批量填充逻辑：直接修改像素数据
        import numpy as np
        
        # 初始化编辑掩码（如果不存在）
        if self.image_data.edit_mask is None:
            self.image_data.edit_mask = np.zeros((self.image_data.height, self.image_data.width), dtype=bool)
            self.image_data.edit_values = np.zeros((self.image_data.height, self.image_data.width), dtype=np.uint8)
        
        # 批量填充：直接设置编辑掩码和值
        self.image_data.edit_mask[selection_mask] = True
        self.image_data.edit_values[selection_mask] = color
        
        # 清除选区（这样才能看到填充效果）
        self.canvas.selection_tool.clear_selection()
        self.image_data.selection_mask = None
        
        # 更新分块缓存（不显示选区）
        self._safe_update_tile_cache(None)
        
        # 保存到历史管理器（支持撤销/重做）
        self.history_manager.push_state(self.image_data)
        
        # 更新 UI 状态
        self._update_ui_state()
        
        # 更新显示
        self.canvas.update()
        
        # 显示提示
        color_name = self.tr.tr('color.black') if color == 0 else self.tr.tr('color.white')
        self.statusbar.showMessage(self.tr.tr('message.filled', color=color_name))
    
    def _fill_selection_opposite_color(self):
        """
        填充选区为相反颜色
        
        如果目标颜色是黑色（选择黑色区域），则填充白色
        如果目标颜色是白色（选择白色区域），则填充黑色
        """
        target_color = self.canvas.selection_tool.target_color
        # 填充相反的颜色
        fill_color = 255 if target_color == 0 else 0
        self._fill_selection(fill_color)
   
    def _connect_tool_settings(self):
        """连接属性面板中的工具设置信号"""
        # 画笔工具设置
        self.properties_panel.brush_size_spinbox.valueChanged.connect(
            lambda v: setattr(self.canvas.brush_tool, 'size', float(v))
        )
        self.properties_panel.brush_color_group.buttonClicked.connect(
            lambda: setattr(self.canvas.brush_tool, 'color', 
                          self.properties_panel.brush_color_group.checkedId())
        )
        
        # 选择工具设置
        self.properties_panel.selection_size_spinbox.valueChanged.connect(
            self._on_selection_size_changed_panel
        )
        self.properties_panel.selection_mode_group.buttonClicked.connect(
            self._on_selection_mode_changed_panel
        )
        self.properties_panel.selection_method_group.buttonClicked.connect(
            self._on_selection_method_changed_panel
        )
        self.properties_panel.selection_color_group.buttonClicked.connect(
            self._on_selection_color_changed_panel
        )
        self.properties_panel.fill_button.clicked.connect(
            self._fill_selection_opposite_color
        )
        self.properties_panel.deselect_button.clicked.connect(self._deselect)
        self.properties_panel.invert_button.clicked.connect(self._invert_selection)
    
    def _on_selection_size_changed_panel(self, value: int):
        """属性面板：选择范围改变"""
        self.canvas.selection_tool.size = float(value)
        self.canvas.update()
    
    def _on_selection_mode_changed_panel(self):
        """属性面板：选择模式改变"""
        button_id = self.properties_panel.selection_mode_group.checkedId()
        mode = 'add' if button_id == 0 else 'subtract'
        self.canvas.selection_tool.selection_mode = mode
        self.canvas.update()
    
    def _on_selection_color_changed_panel(self):
        """属性面板：选择目标颜色改变"""
        button_id = self.properties_panel.selection_color_group.checkedId()
        self.canvas.selection_tool.target_color = button_id
        # 更新填充按钮文本
        if button_id == 0:
            self.properties_panel.fill_button.setText(self.tr.tr('properties_panel.fill_white'))
        else:
            self.properties_panel.fill_button.setText(self.tr.tr('properties_panel.fill_black'))
        self.canvas.update()
    
    def _on_selection_method_changed_panel(self):
        """属性面板：选择方式改变（涂抹/框选）"""
        button_id = self.properties_panel.selection_method_group.checkedId()
        is_rect_mode = (button_id == 1)  # 0=涂抹, 1=框选
        self.canvas.selection_tool.rect_select_mode = is_rect_mode
        
        # 更新光标（无论哪种模式都隐藏系统光标，显示自定义光标）
        self.canvas.setCursor(Qt.BlankCursor)
        
        if is_rect_mode:
            self.statusbar.showMessage(self.tr.tr('message.rect_select_mode'))
        else:
            self.statusbar.showMessage(self.tr.tr('message.paint_select_mode'))
        
        self.canvas.update()
    
    def _on_view_mode_changed(self, mode: str):
        """
        处理视图模式切换
        
        Args:
            mode: 新的视图模式 ('original', 'preprocessed', 'binary')
        """
        if self.image_data is None:
            return
        
        # 更新 ImageData 的视图模式
        self.image_data.set_view_mode(mode)
        
        # 根据模式更新显示
        if mode == 'original':
            # 显示原图
            self._update_canvas_display()
        
        elif mode == 'preprocessed':
            # 显示预处理结果
            if self.image_data.preprocessed_pixels is None:
                # 缓存不存在，计算预处理结果
                self._compute_preprocessed_pixels()
            self._update_canvas_display()
        
        elif mode == 'binary':
            # 显示二值化结果
            self._update_canvas_display()
        
        # 更新工具状态
        self._update_tool_states()
        
        mode_name = self.tr.tr(f'view_mode.{mode}')
        self.statusbar.showMessage(self.tr.tr('message.view_mode_changed', mode=mode_name))
    
    def _compute_preprocessed_pixels(self):
        """计算并缓存预处理结果"""
        if self.image_data is None:
            return
        
        try:
            preprocess_params = self.binarization_panel.get_preprocess_params()
            preprocessed = BinarizationEngine.apply_preprocess(
                self.image_data.original_pixels.copy(),
                **preprocess_params
            )
            self.image_data.set_preprocessed_pixels(preprocessed)
        except MemoryError:
            QMessageBox.critical(
                self,
                self.tr.tr('dialog.error'),
                self.tr.tr('dialog.memory_error')
            )
            self.image_data.invalidate_preprocessed_cache()
            # 切换回原图模式
            self.image_data.set_view_mode('original')
            self.binarization_panel.view_mode_switcher.set_mode('original')
        except Exception as e:
            QMessageBox.warning(
                self,
                self.tr.tr('dialog.error'),
                self.tr.tr('dialog.preprocess_error', error=str(e))
            )
            # 保持当前模式不变
            self.binarization_panel.view_mode_switcher.set_mode(self.image_data.view_mode)
    
    def _update_canvas_display(self):
        """更新 Canvas 显示"""
        if self.image_data is None:
            return
        
        self._safe_update_tile_cache(self.image_data.selection_mask)
    
    def _safe_update_tile_cache(self, selection_mask=None):
        """
        安全地更新 tile_cache
        
        Args:
            selection_mask: 选区蒙版（可选）
        """
        if self.image_data is None:
            return
        
        pixels = self.image_data.get_current_pixels()
        
        # 注意：不再强制转换为灰度图，TileCache 现在支持彩色图像
        
        self.canvas.tile_cache.set_image(pixels, selection_mask)
        self.canvas.update()
    
    def _update_tool_states(self):
        """根据当前视图模式更新工具状态"""
        if self.image_data is None:
            # 没有图片时，所有工具都不可用
            self.pan_button.setEnabled(False)
            self.brush_button.setEnabled(False)
            self.crop_button.setEnabled(False)
            self.selection_tool_button.setEnabled(False)
            return
        
        mode = self.image_data.view_mode
        
        # 抓取工具和裁剪工具：在所有模式下可用
        self.pan_button.setEnabled(True)
        self.crop_button.setEnabled(True)
        
        # 画笔工具：仅在二值化模式下可用
        brush_enabled = (mode == 'binary')
        self.brush_button.setEnabled(brush_enabled)
        if not brush_enabled and self.canvas.current_tool == self.canvas.brush_tool:
            self.canvas.set_tool(None)
            self.brush_button.setChecked(False)
            self.current_tool_label.setText(self.tr.tr('toolbar.current_tool', tool=self.tr.tr('tool.none')))
        
        # 选择工具：仅在二值化模式下可用
        selection_enabled = (mode == 'binary')
        self.selection_tool_button.setEnabled(selection_enabled)
        if not selection_enabled and self.canvas.current_tool == self.canvas.selection_tool:
            self.canvas.set_tool(None)
            self.selection_tool_button.setChecked(False)
            self.current_tool_label.setText(self.tr.tr('toolbar.current_tool', tool=self.tr.tr('tool.none')))
    
    def _get_mode_display_name(self, mode: str) -> str:
        """获取模式的显示名称"""
        names = {
            'original': '原图',
            'preprocessed': '预处理',
            'binary': '二值化'
        }
        return names.get(mode, mode)

    def _show_settings(self):
        """显示设置对话框"""
        from src.views.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(self)
        if dialog.exec():
            # 设置已保存，立即应用新配置
            self.apply_config()
            self.statusbar.showMessage(self.tr.tr('message.settings_applied'), 3000)
    
    def apply_config(self):
        """应用配置到各个组件"""
        config = self.config_manager
        
        # 0. 界面设置
        # 动画开关
        animations_enabled = config.get('interface', 'animations_enabled', True)
        from ..utils.animations import set_global_animation_enabled
        set_global_animation_enabled(animations_enabled)
        
        # 1. 编辑器设置
        # 画笔默认大小
        default_brush_size = config.get('editor', 'default_brush_size', 20)
        self.canvas.brush_tool.size = default_brush_size
        # 更新属性面板 UI
        self.properties_panel.brush_size_spinbox.setValue(default_brush_size)
        
        # 选择工具默认大小
        default_selection_size = config.get('editor', 'default_selection_size', 50)
        self.canvas.selection_tool.size = default_selection_size
        # 更新属性面板 UI
        self.properties_panel.selection_size_spinbox.setValue(default_selection_size)
        
        # 撤销历史限制
        undo_limit = config.get('editor', 'undo_history_limit', 50)
        self.history_manager.max_history = undo_limit
        
        # 2. 性能设置
        # Tile 缓存大小
        tile_cache_size = config.get('performance', 'tile_cache_size', 1000)
        self.canvas.tile_cache.max_tiles = tile_cache_size
        
        # 二值化防抖延迟
        debounce_delay = config.get('performance', 'debounce_delay', 150)
        self.binarization_debounce_timer.setInterval(debounce_delay)
        
        # 3. 文件设置（暂时不需要应用，在保存时使用）
        
        # 刷新画布以应用新设置
        if self.image_data is not None:
            self.canvas.update()
    
    def _show_about(self):
        """显示关于对话框"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox
        from src.__version__ import __version__, __app_name__, __author__, __release_date__
        
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr.tr('about.title', app_name=__app_name__))
        dialog.setMinimumWidth(450)
        dialog.setMinimumHeight(350)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 应用名称
        app_name_label = QLabel(__app_name__)
        app_name_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #212529;")
        layout.addWidget(app_name_label)
        
        # 版本号
        version_label = QLabel(self.tr.tr('about.version', version=__version__))
        version_label.setStyleSheet("font-size: 16px; color: #212529; margin-bottom: 10px;")
        layout.addWidget(version_label)
        
        # 发布日期
        date_label = QLabel(self.tr.tr('about.release_date', date=__release_date__))
        date_label.setStyleSheet("font-size: 14px; color: #212529;")
        layout.addWidget(date_label)
        
        # 分隔线
        separator = QLabel()
        separator.setStyleSheet("border-top: 1px solid #dee2e6; margin: 10px 0;")
        layout.addWidget(separator)
        
        # 描述
        desc_label = QLabel(self.tr.tr('about.description'))
        desc_label.setStyleSheet("font-size: 14px; color: #212529; line-height: 1.6;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # 作者
        author_label = QLabel(self.tr.tr('about.author', author=__author__))
        author_label.setStyleSheet("font-size: 14px; color: #212529; margin-top: 10px;")
        layout.addWidget(author_label)
        
        # 版权
        copyright_label = QLabel(self.tr.tr('about.copyright'))
        copyright_label.setStyleSheet("font-size: 12px; color: #212529; margin-top: 5px;")
        layout.addWidget(copyright_label)
        
        # 许可证
        license_label = QLabel(self.tr.tr('about.license'))
        license_label.setStyleSheet("font-size: 12px; color: #212529;")
        layout.addWidget(license_label)
        
        # 添加弹性空间
        layout.addStretch()
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)
        
        dialog.exec()
