"""
滑块开关组件

自定义的滑块开关控件，类似移动端的开关样式。
"""

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton

from ..utils.animations import is_global_animation_enabled


class ToggleSwitch(QAbstractButton):
    """
    滑块开关控件

    提供类似移动端的滑块开关效果，带有平滑的动画过渡。
    支持全局动画开关控制。
    """

    def __init__(self, parent=None):
        """初始化滑块开关"""
        super().__init__(parent)

        # 设置为可选中
        self.setCheckable(True)

        # 尺寸设置（紧凑型）
        self._width = 40
        self._height = 20
        self._margin = 2

        # 颜色设置
        self._on_color = QColor("#007bff")  # 蓝色
        self._off_color = QColor("#ced4da")  # 灰色
        self._knob_color = QColor("#ffffff")  # 白色
        self._border_color = QColor("#cccccc")  # 边框颜色

        # 滑块位置
        self._knob_diameter = self._height - 2 * self._margin
        self._knob_off_x = self._margin
        self._knob_on_x = self._width - self._knob_diameter - self._margin
        self._circle_position = float(self._knob_off_x)

        # 设置固定尺寸
        self.setFixedSize(self._width, self._height)

        # 创建动画
        self._animation = QPropertyAnimation(self, b"circle_position", self)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.setDuration(200)

        # 连接信号
        self.toggled.connect(self._on_toggled)

        # 设置光标
        self.setCursor(Qt.PointingHandCursor)

    @Property(float)
    def circle_position(self):
        """获取圆圈位置"""
        return self._circle_position

    @circle_position.setter
    def circle_position(self, pos):
        """设置圆圈位置"""
        self._circle_position = pos
        self.update()

    def _on_toggled(self, checked):
        """状态改变时的处理"""
        # 计算目标位置
        target_pos = self._knob_on_x if checked else self._knob_off_x

        # 检查是否启用动画
        if is_global_animation_enabled():
            # 启动动画
            self._animation.stop()
            self._animation.setStartValue(self._circle_position)
            self._animation.setEndValue(target_pos)
            self._animation.start()
        else:
            # 无动画，直接设置位置
            self._circle_position = target_pos
            self.update()

    def setChecked(self, checked):
        """设置选中状态（重写以支持初始化时的位置）"""
        old_checked = self.isChecked()
        super().setChecked(checked)

        # 计算目标位置
        target_pos = self._knob_on_x if checked else self._knob_off_x

        # 如果状态未改变，直接设置位置（用于初始化）
        if old_checked == checked and self._circle_position != target_pos:
            self._circle_position = target_pos
            self.update()

    def paintEvent(self, event):
        """绘制开关"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 计算颜色渐变（基于滑块位置）
        progress = (self._circle_position - self._knob_off_x) / (self._knob_on_x - self._knob_off_x)
        progress = max(0.0, min(1.0, progress))

        # 颜色插值
        bg_color = QColor(
            int(self._off_color.red() + (self._on_color.red() - self._off_color.red()) * progress),
            int(self._off_color.green() + (self._on_color.green() - self._off_color.green()) * progress),
            int(self._off_color.blue() + (self._on_color.blue() - self._off_color.blue()) * progress),
        )

        # 绘制背景轨道（带边框）
        radius = self._height // 2 - 2
        painter.setPen(QPen(self._border_color, 1))
        painter.setBrush(bg_color)
        painter.drawRoundedRect(1, 1, self._width - 2, self._height - 2, radius, radius)

        # 绘制滑块阴影
        shadow_color = QColor(0, 0, 0, 30)
        painter.setPen(Qt.NoPen)
        painter.setBrush(shadow_color)
        painter.drawEllipse(
            int(self._circle_position + 1),
            self._margin + 1,
            self._knob_diameter,
            self._knob_diameter,
        )

        # 绘制滑块圆圈
        painter.setBrush(self._knob_color)
        painter.setPen(QPen(self._border_color, 1))
        painter.drawEllipse(
            int(self._circle_position),
            self._margin,
            self._knob_diameter,
            self._knob_diameter,
        )

    def sizeHint(self):
        """返回推荐尺寸"""
        from PySide6.QtCore import QSize
        return QSize(self._width, self._height)
