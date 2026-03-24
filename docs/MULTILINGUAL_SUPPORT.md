# 多语言支持文档

## 概述

BinarizationTool v1.4.3.0 实现了完整的多语言支持系统，目前支持中文（zh_CN）和英文（en_US）。

## 架构设计

### 翻译管理器 (TranslationManager)

位置：`src/utils/translation_manager.py`

核心功能：
- 加载和管理翻译文件
- 支持嵌套键访问（如 `menu.file.open`）
- 支持占位符替换（如 `"已加载: {filename}"`）
- 单例模式全局访问

### 翻译文件

位置：`locales/`

文件结构：
```
locales/
├── zh_CN.json  # 中文翻译
└── en_US.json  # 英文翻译
```

## 使用方法

### 用户切换语言

1. 打开应用
2. 点击工具栏的"设置"按钮
3. 在"通用"选项卡中选择语言（中文/English）
4. 点击"确定"保存
5. 重启应用生效

### 开发者集成翻译

#### 1. 在组件中导入翻译器

```python
from ..utils.translation_manager import get_translator

class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.tr = get_translator()
```

#### 2. 使用翻译键

```python
# 简单翻译
label = QLabel(self.tr.tr('app.title'))

# 带占位符的翻译
message = self.tr.tr('message.loaded', path='test.png')
# 结果：中文 "已加载: test.png"，英文 "Loaded: test.png"
```

#### 3. 添加新的翻译键

在 `locales/zh_CN.json` 和 `locales/en_US.json` 中添加对应的键值对：

```json
{
  "my_component": {
    "title": "我的组件",
    "message": "这是一条消息"
  }
}
```

## 已翻译的组件

### ✅ 完全翻译
- **主窗口** (`MainWindow`)
  - 窗口标题
  - 状态栏消息
  - 工具栏按钮
  - 文件对话框
  - 错误和确认对话框
  - 关于对话框

- **设置对话框** (`SettingsDialog`)
  - 所有选项卡标题
  - 所有设置项标签
  - 按钮文本
  - 提示消息

- **属性面板** (`PropertiesPanel`)
  - 选项卡标题
  - 属性信息标签
  - 工具设置标签
  - 按钮文本

### 🔄 部分翻译
- **二值化面板** (`BinarizationPanel`)
  - 组标题已翻译
  - 控件标签翻译键已准备，待集成

## 翻译文件结构

### 主要翻译键分类

```
app.*                    # 应用程序级别
toolbar.*                # 工具栏
tool.*                   # 工具名称
tooltip.*                # 工具提示
message.*                # 状态消息
color.*                  # 颜色
mode.*                   # 模式
view_mode.*              # 视图模式
dialog.*                 # 对话框
file_dialog.*            # 文件对话框
settings.*               # 设置界面
about.*                  # 关于对话框
binarization_panel.*     # 二值化面板
properties_panel.*       # 属性面板
```

## 扩展新语言

### 1. 创建翻译文件

在 `locales/` 目录下创建新的翻译文件，如 `ja_JP.json`（日语）：

```json
{
  "app": {
    "title": "BinarizationTool - バイナリ画像エディタ",
    "ready": "準備完了"
  },
  ...
}
```

### 2. 更新配置管理器

在 `src/utils/config_manager.py` 的 `VALUE_MAPPING` 中添加新语言：

```python
"language": {
    "中文": "zh_CN",
    "English": "en_US",
    "日本語": "ja_JP"  # 新增
}
```

### 3. 更新设置对话框

在 `src/views/settings_dialog.py` 的语言下拉框中添加新选项：

```python
self.language_combo.addItems(["中文", "English", "日本語"])
```

## 技术细节

### 翻译键命名规范

- 使用小写字母和下划线
- 使用点号分隔层级
- 保持简洁明了

示例：
```
good: app.title, toolbar.open, message.loaded
bad: AppTitle, TOOLBAR_OPEN, Message_Loaded
```

### 占位符使用

翻译文件中使用 `{key}` 格式的占位符：

```json
{
  "message": {
    "loaded": "已加载: {path}",
    "saved": "已保存: {path}"
  }
}
```

代码中传入参数：

```python
self.tr.tr('message.loaded', path=file_path)
```

### 性能考虑

- 翻译文件在应用启动时一次性加载到内存
- 翻译查询是简单的字典查找，性能优异
- 建议在组件初始化时获取翻译器实例并缓存

## 未来改进

### 计划中的功能

1. **热重载语言切换**
   - 无需重启应用即可切换语言
   - 需要实现 UI 组件的动态更新机制

2. **更多语言支持**
   - 日语 (ja_JP)
   - 韩语 (ko_KR)
   - 法语 (fr_FR)
   - 德语 (de_DE)

3. **翻译工具**
   - 自动提取可翻译字符串
   - 翻译完整性检查
   - 翻译文件格式验证

4. **区域设置**
   - 日期时间格式
   - 数字格式
   - 货币格式

## 测试

### 手动测试

1. 切换到英文：设置 → 通用 → English → 确定 → 重启
2. 验证所有界面文本是否正确显示英文
3. 切换回中文验证

### 自动化测试

```python
from src.utils.translation_manager import get_translator, set_language

# 测试中文
tr = get_translator()
assert tr.tr('app.title') == 'BinarizationTool - 二值化图片编辑器'

# 测试英文
set_language('en_US')
tr = get_translator()
assert tr.tr('app.title') == 'BinarizationTool - Binary Image Editor'
```

## 贡献指南

### 添加新翻译

1. Fork 项目
2. 在 `locales/` 中添加或修改翻译文件
3. 确保翻译准确、自然
4. 提交 Pull Request

### 翻译质量标准

- 准确性：忠实原意
- 自然性：符合目标语言习惯
- 一致性：术语翻译保持统一
- 简洁性：避免冗长表达

## 常见问题

### Q: 为什么切换语言后需要重启？

A: 当前版本的 UI 组件在初始化时加载翻译文本。未来版本将实现热重载功能。

### Q: 如何添加新的翻译键？

A: 在两个翻译文件（zh_CN.json 和 en_US.json）中同时添加相同的键，然后在代码中使用 `self.tr.tr('your.key')`。

### Q: 翻译文件的编码是什么？

A: UTF-8 编码，支持所有 Unicode 字符。

### Q: 可以在运行时动态添加翻译吗？

A: 当前版本不支持。翻译文件在应用启动时加载。

## 版本历史

- **v1.4.3.0** (2026-03-24)
  - 初始多语言支持实现
  - 支持中文和英文
  - 主要 UI 组件完整翻译

---

更新日期：2026-03-24
