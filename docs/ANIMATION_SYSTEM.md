# 动画系统使用指南

## 概述

动画系统提供了统一的动画管理接口，支持全局和局部动画开关控制。

## 架构

### 全局动画配置

使用单例模式的 `AnimationConfig` 类管理全局动画开关：

```python
from src.utils.animations import set_global_animation_enabled, is_global_animation_enabled

# 禁用所有动画
set_global_animation_enabled(False)

# 启用所有动画
set_global_animation_enabled(True)

# 检查动画是否启用
enabled = is_global_animation_enabled()
```

### 局部动画控制

每个动画对象都有自己的局部开关，可以独立控制：

```python
from src.utils.animations import create_rotation_animation

# 创建动画（默认启用）
animation = create_rotation_animation(button)

# 创建动画（禁用）
animation = create_rotation_animation(button, enabled=False)

# 运行时控制
animation.set_enabled(False)  # 禁用
animation.set_enabled(True)   # 启用
```

## 动画类型

### 1. 旋转动画 (RotationAnimation)

用于按钮点击时的旋转反馈效果。

**使用示例：**

```python
from src.utils.animations import create_rotation_animation

# 创建旋转动画
animation = create_rotation_animation(
    widget=reset_button,
    duration=300,  # 300ms
    angle=360,     # 旋转360度
    enabled=True   # 启用动画
)

# 播放动画
animation.start()
```

**应用场景：**
- 重置按钮点击反馈
- 刷新按钮点击反馈
- 任何需要旋转反馈的按钮

### 2. 滑动动画 (ViewModeSwitcher)

用于视图模式切换器的指示器滑动效果。

**使用示例：**

```python
# 在 ViewModeSwitcher 中
switcher = ViewModeSwitcher()

# 禁用滑动动画
switcher.set_animation_enabled(False)

# 启用滑动动画
switcher.set_animation_enabled(True)
```

**应用场景：**
- 分段控件切换
- Tab 切换
- 任何需要滑动指示器的场景

## 双重控制机制

动画系统采用双重控制机制：

1. **全局开关**：控制所有动画的启用/禁用
2. **局部开关**：控制单个动画的启用/禁用

只有当全局开关和局部开关都启用时，动画才会播放。

```python
# 全局禁用所有动画
set_global_animation_enabled(False)

# 即使局部启用，动画也不会播放
animation.set_enabled(True)
animation.start()  # 不会播放动画

# 全局启用
set_global_animation_enabled(True)

# 现在动画会播放
animation.start()  # 播放动画
```

## 在设置对话框中集成

### 添加动画开关选项

在 `SettingsDialog` 中添加动画开关：

```python
from src.utils.animations import set_global_animation_enabled, is_global_animation_enabled

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 创建动画开关复选框
        self.animation_checkbox = QCheckBox("启用 UI 动画")
        self.animation_checkbox.setChecked(is_global_animation_enabled())
        self.animation_checkbox.stateChanged.connect(self._on_animation_changed)
        
        # 添加到布局...
    
    def _on_animation_changed(self, state):
        """动画开关改变"""
        enabled = state == Qt.Checked
        set_global_animation_enabled(enabled)
        
        # 保存到配置
        self.config_manager.set('ui.animations_enabled', enabled)
```

### 从配置加载动画设置

在应用启动时加载动画设置：

```python
from src.utils.config_manager import ConfigManager
from src.utils.animations import set_global_animation_enabled

# 加载配置
config = ConfigManager()
animations_enabled = config.get('ui.animations_enabled', True)  # 默认启用

# 应用设置
set_global_animation_enabled(animations_enabled)
```

## 性能考虑

- 动画使用 Qt 的 `QPropertyAnimation`，性能优异
- 动画禁用时不会创建动画对象，零开销
- 所有动画都使用缓动曲线，视觉效果流畅自然

## 扩展动画类型

系统预留了以下动画类型接口：

- `FadeAnimation` - 淡入淡出动画
- `ScaleAnimation` - 缩放动画
- `SlideAnimation` - 滑动动画

可以按照 `RotationAnimation` 的模式实现这些动画类型。

## 最佳实践

1. **默认启用动画**：提供更好的用户体验
2. **提供全局开关**：让用户可以根据性能需求禁用动画
3. **使用合适的时长**：
   - 快速反馈：200-300ms
   - 状态切换：250-400ms
   - 避免过长的动画（>500ms）
4. **选择合适的缓动曲线**：
   - `OutCubic`：适合大多数场景
   - `InOutCubic`：适合往返动画
   - `OutBack`：适合弹性效果

## 测试

动画系统不影响现有测试，所有测试用例都能正常通过。

如需测试动画效果，可以：

1. 手动测试：运行应用，观察动画效果
2. 性能测试：禁用动画，对比性能差异
3. 兼容性测试：在不同平台测试动画流畅度
