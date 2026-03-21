"""
快捷键处理模块

统一管理应用程序的快捷键，根据当前工具分发到相应的处理函数。
"""

from PySide6.QtGui import QAction
from ..models.brush_tool import BrushTool
from ..models.selection_tool import SelectionTool


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
        
        # 更新设置面板（如果可见）
        if hasattr(self.main_window, 'brush_settings_panel') and \
           self.main_window.brush_settings_panel.isVisible():
            if new_color == 0:
                self.main_window.black_radio.setChecked(True)
            else:
                self.main_window.white_radio.setChecked(True)
        
        self.main_window.statusbar.showMessage(
            f"画笔颜色: {'黑色' if new_color == 0 else '白色'}"
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
        
        # 更新设置面板（如果可见）
        if hasattr(self.main_window, 'brush_settings_panel') and \
           self.main_window.brush_settings_panel.isVisible():
            self.main_window.brush_size_spinbox.setValue(int(new_size))
        
        self.main_window.statusbar.showMessage(f"画笔大小: {int(new_size)}")
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
        
        # 更新设置面板（如果可见）
        if hasattr(self.main_window, 'brush_settings_panel') and \
           self.main_window.brush_settings_panel.isVisible():
            self.main_window.brush_size_spinbox.setValue(int(new_size))
        
        self.main_window.statusbar.showMessage(f"画笔大小: {int(new_size)}")
        self.canvas.update()  # 更新光标显示
    
    # ========== 选择工具快捷键 ==========
    
    def _toggle_selection_tool_mode(self):
        """切换选择工具模式"""
        current_mode = self.canvas.selection_tool.selection_mode
        new_mode = 'subtract' if current_mode == 'add' else 'add'
        self.canvas.selection_tool.selection_mode = new_mode
        
        # 更新设置面板（如果可见）
        if hasattr(self.main_window, 'selection_tool_settings_panel') and \
           self.main_window.selection_tool_settings_panel.isVisible():
            if new_mode == 'add':
                self.main_window.add_mode_radio.setChecked(True)
            else:
                self.main_window.subtract_mode_radio.setChecked(True)
        
        mode_text = "添加" if new_mode == 'add' else "删除"
        self.main_window.statusbar.showMessage(f"选择模式: {mode_text}")
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
        
        # 更新设置面板（如果可见）
        if hasattr(self.main_window, 'selection_tool_settings_panel') and \
           self.main_window.selection_tool_settings_panel.isVisible():
            self.main_window.selection_tool_size_spinbox.setValue(int(new_size))
        
        self.main_window.statusbar.showMessage(f"选择范围: {int(new_size)}")
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
        
        # 更新设置面板（如果可见）
        if hasattr(self.main_window, 'selection_tool_settings_panel') and \
           self.main_window.selection_tool_settings_panel.isVisible():
            self.main_window.selection_tool_size_spinbox.setValue(int(new_size))
        
        self.main_window.statusbar.showMessage(f"选择范围: {int(new_size)}")
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
        
        # 更新设置面板（如果可见）
        if hasattr(self.main_window, 'selection_tool_settings_panel') and \
           self.main_window.selection_tool_settings_panel.isVisible():
            if new_color == 0:
                self.main_window.wand_black_radio.setChecked(True)
            else:
                self.main_window.wand_white_radio.setChecked(True)
        
        color_text = "黑色" if new_color == 0 else "白色"
        self.main_window.statusbar.showMessage(f"选择目标颜色: {color_text}")
        self.canvas.update()  # 更新光标显示
