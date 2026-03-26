"""
快捷键处理模块

统一管理应用程序的快捷键，根据当前工具分发到相应的处理函数。
"""

from PySide6.QtGui import QAction

from ..models.brush_tool import BrushTool
from ..models.selection_tool import SelectionTool
from ..utils.translation_manager import get_translator


class ShortcutHandler:
    """
    快捷键处理器

    管理工具相关的快捷键，根据当前激活的工具自动分发到对应的处理函数。
    """

    def __init__(self, main_window):
        """
        初始化快捷键处理器

        Args:
            main_window: 主窗口对象
        """
        self.main_window = main_window
        self.canvas = main_window.canvas
        self.tr = get_translator()

        # 创建快捷键动作
        self._create_actions()

    def _create_actions(self):
        """创建快捷键动作"""
        # Ctrl+X: 切换工具属性（画笔颜色/选择模式）
        self.tool_toggle_action = QAction(self.main_window)
        self.tool_toggle_action.setShortcut("Ctrl+X")
        self.tool_toggle_action.triggered.connect(self._handle_tool_toggle)
        self.main_window.addAction(self.tool_toggle_action)

        # Ctrl+Up: 增大工具尺寸
        self.tool_size_up = QAction(self.main_window)
        self.tool_size_up.setShortcut("Ctrl+Up")
        self.tool_size_up.triggered.connect(self._handle_tool_size_up)
        self.main_window.addAction(self.tool_size_up)

        # Ctrl+Down: 减小工具尺寸
        self.tool_size_down = QAction(self.main_window)
        self.tool_size_down.setShortcut("Ctrl+Down")
        self.tool_size_down.triggered.connect(self._handle_tool_size_down)
        self.main_window.addAction(self.tool_size_down)

        # Ctrl+Shift+X: 切换选择目标颜色
        self.wand_color_toggle = QAction(self.main_window)
        self.wand_color_toggle.setShortcut("Ctrl+Shift+X")
        self.wand_color_toggle.triggered.connect(self._toggle_wand_color)
        self.main_window.addAction(self.wand_color_toggle)

        # Ctrl+1: 切换到原图模式
        self.view_mode_original = QAction(self.main_window)
        self.view_mode_original.setShortcut("Ctrl+1")
        self.view_mode_original.triggered.connect(lambda: self._switch_view_mode('original'))
        self.main_window.addAction(self.view_mode_original)

        # Ctrl+2: 切换到预处理模式
        self.view_mode_preprocessed = QAction(self.main_window)
        self.view_mode_preprocessed.setShortcut("Ctrl+2")
        self.view_mode_preprocessed.triggered.connect(lambda: self._switch_view_mode('preprocessed'))
        self.main_window.addAction(self.view_mode_preprocessed)

        # Ctrl+3: 切换到二值化模式
        self.view_mode_binary = QAction(self.main_window)
        self.view_mode_binary.setShortcut("Ctrl+3")
        self.view_mode_binary.triggered.connect(lambda: self._switch_view_mode('binary'))
        self.main_window.addAction(self.view_mode_binary)

        # Tab: 循环切换视图模式
        self.view_mode_cycle = QAction(self.main_window)
        self.view_mode_cycle.setShortcut("Tab")
        self.view_mode_cycle.triggered.connect(self._cycle_view_mode)
        self.main_window.addAction(self.view_mode_cycle)

    def _handle_tool_toggle(self):
        """处理 Ctrl+X：根据当前工具切换颜色或模式"""
        if isinstance(self.canvas.current_tool, BrushTool):
            self._toggle_brush_color()
        elif isinstance(self.canvas.current_tool, SelectionTool):
            self._toggle_selection_tool_mode()

    def _handle_tool_size_up(self):
        """处理 Ctrl+Up：根据当前工具增大尺寸"""
        if isinstance(self.canvas.current_tool, BrushTool):
            self._increase_brush_size()
        elif isinstance(self.canvas.current_tool, SelectionTool):
            self._increase_selection_tool_size()

    def _handle_tool_size_down(self):
        """处理 Ctrl+Down：根据当前工具减小尺寸"""
        if isinstance(self.canvas.current_tool, BrushTool):
            self._decrease_brush_size()
        elif isinstance(self.canvas.current_tool, SelectionTool):
            self._decrease_selection_tool_size()

    # ========== 画笔工具快捷键 ==========

    def _toggle_brush_color(self):
        """切换画笔颜色"""
        current_color = self.canvas.brush_tool.color
        new_color = 255 if current_color == 0 else 0
        self.canvas.brush_tool.color = new_color

        # 更新属性面板
        if new_color == 0:
            self.main_window.properties_panel.brush_black_radio.setChecked(True)
        else:
            self.main_window.properties_panel.brush_white_radio.setChecked(True)

        color_name = self.tr.tr('color.black') if new_color == 0 else self.tr.tr('color.white')
        self.main_window.statusbar.showMessage(
            self.tr.tr('message.brush_color', color=color_name)
        )

    def _increase_brush_size(self):
        """增大画笔"""
        current_size = self.canvas.brush_tool.size

        # 根据当前大小选择步长
        if current_size < 20:
            step = 1
        elif current_size < 50:
            step = 5
        else:
            step = 10

        new_size = min(500, current_size + step)
        self.canvas.brush_tool.size = new_size

        # 更新属性面板
        self.main_window.properties_panel.brush_size_spinbox.setValue(int(new_size))

        self.main_window.statusbar.showMessage(self.tr.tr('message.brush_size', size=int(new_size)))
        self.canvas.update()  # 更新光标显示

    def _decrease_brush_size(self):
        """减小画笔"""
        current_size = self.canvas.brush_tool.size

        # 根据当前大小选择步长
        if current_size <= 20:
            step = 1
        elif current_size <= 50:
            step = 5
        else:
            step = 10

        new_size = max(1, current_size - step)
        self.canvas.brush_tool.size = new_size

        # 更新属性面板
        self.main_window.properties_panel.brush_size_spinbox.setValue(int(new_size))

        self.main_window.statusbar.showMessage(self.tr.tr('message.brush_size', size=int(new_size)))
        self.canvas.update()  # 更新光标显示

    # ========== 选择工具快捷键 ==========

    def _toggle_selection_tool_mode(self):
        """切换选择工具模式"""
        current_mode = self.canvas.selection_tool.selection_mode
        new_mode = 'subtract' if current_mode == 'add' else 'add'
        self.canvas.selection_tool.selection_mode = new_mode

        # 更新属性面板
        if new_mode == 'add':
            self.main_window.properties_panel.add_mode_radio.setChecked(True)
        else:
            self.main_window.properties_panel.subtract_mode_radio.setChecked(True)

        mode_name = self.tr.tr('mode.add') if new_mode == 'add' else self.tr.tr('mode.subtract')
        self.main_window.statusbar.showMessage(self.tr.tr('message.selection_mode', mode=mode_name))
        self.canvas.update()  # 更新光标显示

    def _increase_selection_tool_size(self):
        """增大选择范围"""
        current_size = self.canvas.selection_tool.size

        # 根据当前大小选择步长
        if current_size < 20:
            step = 1
        elif current_size < 50:
            step = 5
        else:
            step = 10

        new_size = min(500, current_size + step)
        self.canvas.selection_tool.size = new_size

        # 更新属性面板
        self.main_window.properties_panel.selection_size_spinbox.setValue(int(new_size))

        self.main_window.statusbar.showMessage(self.tr.tr('message.selection_size', size=int(new_size)))
        self.canvas.update()  # 更新光标显示

    def _decrease_selection_tool_size(self):
        """减小选择范围"""
        current_size = self.canvas.selection_tool.size

        # 根据当前大小选择步长
        if current_size <= 20:
            step = 1
        elif current_size <= 50:
            step = 5
        else:
            step = 10

        new_size = max(1, current_size - step)
        self.canvas.selection_tool.size = new_size

        # 更新属性面板
        self.main_window.properties_panel.selection_size_spinbox.setValue(int(new_size))

        self.main_window.statusbar.showMessage(self.tr.tr('message.selection_size', size=int(new_size)))
        self.canvas.update()  # 更新光标显示

    def _toggle_wand_color(self):
        """切换选择目标颜色"""
        # 只在选择工具激活时有效
        if not isinstance(self.canvas.current_tool, SelectionTool):
            return

        current_color = self.canvas.selection_tool.target_color
        # 黑色(0) <-> 白色(255)
        new_color = 255 if current_color == 0 else 0

        self.canvas.selection_tool.target_color = new_color

        # 更新属性面板
        if new_color == 0:
            self.main_window.properties_panel.selection_black_radio.setChecked(True)
            self.main_window.properties_panel.fill_button.setText(self.tr.tr('properties_panel.fill_white'))
        else:
            self.main_window.properties_panel.selection_white_radio.setChecked(True)
            self.main_window.properties_panel.fill_button.setText(self.tr.tr('properties_panel.fill_black'))

        color_name = self.tr.tr('color.black') if new_color == 0 else self.tr.tr('color.white')
        self.main_window.statusbar.showMessage(self.tr.tr('message.selection_target_color', color=color_name))
        self.canvas.update()  # 更新光标显示

    # ========== 视图模式切换快捷键 ==========

    def _switch_view_mode(self, mode: str):
        """
        切换到指定的视图模式

        Args:
            mode: 目标模式 ('original', 'preprocessed', 'binary')
        """
        if self.main_window.image_data is None:
            return

        # 通过 BinarizationPanel 的 ViewModeSwitcher 切换模式
        view_switcher = self.main_window.binarization_panel.view_mode_switcher
        if view_switcher.get_current_mode() != mode:
            view_switcher.set_mode(mode)
            view_switcher.mode_changed.emit(mode)

    def _cycle_view_mode(self):
        """循环切换视图模式（原图 → 预处理 → 二值化 → 原图）"""
        if self.main_window.image_data is None:
            return

        view_switcher = self.main_window.binarization_panel.view_mode_switcher
        current_mode = view_switcher.get_current_mode()

        # 定义循环顺序
        mode_cycle = ['original', 'preprocessed', 'binary']
        current_index = mode_cycle.index(current_mode)
        next_index = (current_index + 1) % len(mode_cycle)
        next_mode = mode_cycle[next_index]

        view_switcher.set_mode(next_mode)
        view_switcher.mode_changed.emit(next_mode)
