"""
动画工具模块

提供各种 UI 动画效果，便于复用和扩展。
"""

from PySide6.QtCore import Property, QEasingCurve, QObject, QPropertyAnimation, Qt
from PySide6.QtGui import QIcon, QTransform
from PySide6.QtWidgets import QWidget


class AnimationConfig:
    """
    动画配置类（单例模式）

    统一管理所有动画的启用/禁用状态
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._enabled = True  # 默认启用所有动画

    def set_enabled(self, enabled: bool):
        """设置全局动画开关"""
        self._enabled = enabled

    def is_enabled(self) -> bool:
        """获取全局动画开关状态"""
        return self._enabled


# 全局动画配置实例
_animation_config = AnimationConfig()


class RotatableWidget(QObject):
    """可旋转的控件包装器"""

    def __init__(self, widget: QWidget):
        super().__init__()
        self.widget = widget
        self._rotation = 0.0
        self._original_pixmap = None

        # 保存原始图标
        if hasattr(widget, 'icon') and not widget.icon().isNull():
            self._original_pixmap = widget.icon().pixmap(widget.iconSize())

    def get_rotation(self):
        return self._rotation

    def set_rotation(self, angle):
        self._rotation = angle

        # 如果有图标，旋转图标
        if self._original_pixmap and not self._original_pixmap.isNull():
            # 创建旋转变换
            transform = QTransform()
            transform.translate(self._original_pixmap.width() / 2, self._original_pixmap.height() / 2)
            transform.rotate(angle)
            transform.translate(-self._original_pixmap.width() / 2, -self._original_pixmap.height() / 2)

            # 应用变换到图标
            rotated_pixmap = self._original_pixmap.transformed(transform, Qt.SmoothTransformation)

            # 更新按钮图标
            self.widget.setIcon(QIcon(rotated_pixmap))

    rotation = Property(float, get_rotation, set_rotation)


class RotationAnimation:
    """旋转动画类"""

    def __init__(self, widget: QWidget, duration: int = 300, angle: float = 360.0):
        """
        初始化旋转动画

        Args:
            widget: 要应用动画的控件
            duration: 动画时长（毫秒）
            angle: 旋转角度（度）
        """
        self.widget = widget
        self.duration = duration
        self.angle = angle
        self.rotatable = RotatableWidget(widget)
        self.animation = None
        self._enabled = True  # 动画开关，默认启用
        self._on_finished_callback = None  # 完成回调

    def set_enabled(self, enabled: bool):
        """
        设置是否启用动画

        Args:
            enabled: True 启用动画，False 禁用动画
        """
        self._enabled = enabled

    def is_enabled(self) -> bool:
        """
        获取动画是否启用

        Returns:
            True 表示启用，False 表示禁用
        """
        return self._enabled

    def on_finished(self, callback):
        """
        设置动画完成时的回调函数

        Args:
            callback: 回调函数
        """
        self._on_finished_callback = callback

    def start(self):
        """开始动画"""
        # 检查全局动画开关和局部动画开关
        if not self._enabled or not _animation_config.is_enabled():
            # 动画禁用时直接返回，不执行动画
            # 但仍然调用完成回调
            if self._on_finished_callback:
                self._on_finished_callback()
            return

        # 创建旋转动画
        self.animation = QPropertyAnimation(self.rotatable, b"rotation")
        self.animation.setDuration(self.duration)
        self.animation.setStartValue(0)
        self.animation.setEndValue(self.angle)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)

        # 动画结束后恢复原始状态
        def on_finished():
            self.rotatable.set_rotation(0)
            # 调用用户设置的回调
            if self._on_finished_callback:
                self._on_finished_callback()

        self.animation.finished.connect(on_finished)
        self.animation.start()


def create_rotation_animation(widget: QWidget, duration: int = 300, angle: float = 360.0, enabled: bool = True) -> RotationAnimation:
    """
    快速创建旋转动画

    Args:
        widget: 要应用动画的控件
        duration: 动画时长（毫秒），默认 300ms
        angle: 旋转角度（度），默认 360度（一圈）
        enabled: 是否启用动画，默认 True

    Returns:
        RotationAnimation 实例

    Example:
        animation = create_rotation_animation(button, duration=300, enabled=True)
        animation.start()
    """
    animation = RotationAnimation(widget, duration, angle)
    animation.set_enabled(enabled)
    return animation


def set_global_animation_enabled(enabled: bool):
    """
    设置全局动画开关

    Args:
        enabled: True 启用所有动画，False 禁用所有动画
    """
    _animation_config.set_enabled(enabled)


def is_global_animation_enabled() -> bool:
    """
    获取全局动画开关状态

    Returns:
        True 表示启用，False 表示禁用
    """
    return _animation_config.is_enabled()


class FadeAnimation:
    """淡入淡出动画类（预留，以后实现）"""
    pass


class ScaleAnimation:
    """缩放动画类（预留，以后实现）"""
    pass


class SlideAnimation:
    """滑动动画类（预留，以后实现）"""
    pass
