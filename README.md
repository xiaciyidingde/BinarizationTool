# BinarizationTool - 二值化图片编辑器

<div align="center">

**专业的二值化图片编辑工具，让黑白图像处理变得简单高效**

版本: v1.5.10.1 | 许可证: CC BY-NC-SA 4.0 | 语言: 🇨🇳 中文 / 🇺🇸 English

</div>

---

## 📖 项目简介

BinarizationTool 是一款基于 PySide6 开发的专业二值化图片编辑器，专注于将彩色或灰度图像转换为黑白二值图像。它提供了类似 Photoshop 的编辑体验，集成了多种先进的二值化算法、丰富的预处理选项和强大的编辑工具。

### ✨ 核心特色

- **7种专业二值化算法** + **3种抖动算法**：从简单到复杂，满足各种需求
- **实时预览**：所有参数调整立即生效，所见即所得
- **三视图模式**：原图、预处理、二值化三种视图自由切换
- **图层系统**：支持多图层管理，独立编辑不同区域
- **现代化界面**：清晰的布局、流畅的动画、直观的操作

---

## 🚀 功能特性

### 🖼️ 图片处理

#### 支持格式
- 输入/输出：`PNG`, `JPG`, `JPEG`, `BMP`, `WebP`
- 拖放支持：直接拖放图片文件到窗口即可打开

#### 视图模式
- **原图模式** (`Ctrl+1`)：查看原始彩色图像
- **预处理模式** (`Ctrl+2`)：查看预处理效果（曝光、对比度等）
- **二值化模式** (`Ctrl+3`)：查看最终的黑白二值化结果
- **快速切换** (`Tab`)：循环切换三种视图模式

#### 图层系统

**使用选择工具选择的区域可以保存为图层，用户图层支持独立的二值化操作，也就是说，你可以为不同的区域使用不同的二值化参数，获得更加自由的编辑效果**

- **根图层**：最底部图像
- **用户图层**：使用选择工具选择并保存的图层，支持独立的二值化参数

#### 二值化算法

**传统算法**：
- **固定阈值**：简单直接，适合对比度高的图像
- **自适应阈值**：局部自适应，适合光照不均的图像
- **Otsu 自动阈值**：自动计算最佳阈值，无需手动调整
- **Sauvola 阈值**：适合文档图像，保留细节
- **Wolf 阈值**：改进的 Sauvola，更好的对比度
- **Nick 阈值**：适合低对比度图像
- **Bernsen 阈值**：基于局部对比度的阈值

**抖动算法**：
- **Floyd-Steinberg**：经典误差扩散，保留灰度细节，适合照片
- **Atkinson**：Mac 风格轻量级扩散，适合艺术效果
- **Ordered**：Bayer 矩阵网点效果，适合打印优化

### 🛠️ 编辑工具

#### 抓取工具
- **快捷键**：`H` 或者 `Space + 拖动` `鼠标中键拖动`
- **功能**：拖动画布进行平移

#### 画笔工具
- **快捷键**：`B`
- **功能**：手动绘制黑色或白色像素
- **快捷操作**：
  - `Ctrl+X`：切换黑白颜色
  - `Ctrl+↑/↓`：调整画笔大小（智能步长）
- **智能光标**：
  - 红色圆圈 = 黑色画笔
  - 绿色圆圈 = 白色画笔
  - 小画笔时显示十字准星辅助定位

#### 选择工具
- **快捷键**：`W`
- **功能**：选择指定区域进行操作
- **两种选择方式**：
  - **涂抹模式**：拖动鼠标连续选择
  - **框选模式**：拖动创建矩形选区
- **两种选择模式**：
  - **添加模式**（绿色光标）：添加到选区
  - **删除模式**（红色光标）：从选区减去
- **快捷操作**：
  - `Ctrl+X`：切换添加/删除模式
  - `Ctrl+Shift+X`：切换目标颜色
  - `Ctrl+↑/↓`：调整选择范围
  - `Ctrl+D`：取消选择
  - `Ctrl+Shift+I`：反选
- **选区操作**：
  - 填充选区为黑色或白色

#### 裁剪工具
- **快捷键**：`C`
- **功能**：拖动选择区域，释放立即裁剪

---

## 📦 从源代码开始

### 系统要求

- Python 3.8+
- Windows / Linux / macOS
- C 编译器（用于编译 Cython 扩展）

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/BinarizationTool.git
cd BinarizationTool
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 编译 Cython 扩展（必需）

本项目使用 Cython 优化抖动算法，需要编译原生扩展模块。

```bash
# 首次编译
python setup.py build_ext --inplace

# 强制重新编译（修改 .pyx 文件后）
python setup.py build_ext --inplace --force
```

**注意**：
- 首次运行前必须编译 Cython 扩展
- 编译需要 C 编译器：
  - Windows: MSVC (Visual Studio)
  - Linux: GCC
  - macOS: Clang (Xcode Command Line Tools)

### 4. 运行应用

```bash
# 直接启动
python main.py

# 启动并打开图片
python main.py image.png
```

---

## 🧪 开发与测试

### 运行测试

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 运行所有测试
pytest

# 运行测试并显示覆盖率
pytest --cov=src --cov-report=html
```

### 代码质量检查

```bash
# Ruff linter
ruff check .

# Ruff formatter
ruff format .

# Pylint 静态分析
pylint src/
```

### 打包应用

使用 Nuitka 打包为独立可执行文件：

```bash
python build.py
```

打包后的文件位于 `BinarizationToolv{version}/` 目录。

---

## ⌨️ 快捷键列表

### 文件操作
- `Ctrl+O`：打开文件
- `Ctrl+S`：保存文件
- `Ctrl+Shift+S`：另存为

### 编辑操作
- `Ctrl+Z`：撤销
- `Ctrl+Y`：重做
- `Ctrl+R`：重置到初始状态

### 工具切换
- `H`：抓取工具
- `B`：画笔工具
- `C`：裁剪工具
- `W`：选择工具

### 视图切换
- `Ctrl+1`：原图模式
- `Ctrl+2`：预处理模式
- `Ctrl+3`：二值化模式
- `Tab`：循环切换视图

### 工具操作
- `Ctrl+X`：切换画笔颜色 / 选择模式
- `Ctrl+Shift+X`：切换选择目标颜色
- `Ctrl+↑`：增大画笔/选择范围
- `Ctrl+↓`：减小画笔/选择范围

### 选区操作
- `Ctrl+D`：取消选择
- `Ctrl+Shift+I`：反选

### 视图控制
- `Space + 拖动`：平移视图
- `鼠标滚轮`：缩放视图
- `鼠标中键拖动`：平移视图

---

## 📁 项目结构

```
BinarizationTool/
├── src/
│   ├── cython_core/          # Cython 加速模块
│   │   ├── dithering.pyx     # 抖动算法（Cython）
│   │   ├── contour_extractor.pyx  # 轮廓提取（Cython）
│   │   └── __init__.py
│   ├── models/               # 数据模型
│   │   ├── image_data.py     # 图片数据模型
│   │   ├── view_transform.py # 坐标变换
│   │   ├── brush_tool.py     # 画笔工具
│   │   ├── selection_tool.py # 选择工具
│   │   ├── crop_tool.py      # 裁剪工具
│   │   ├── pan_tool.py       # 抓取工具
│   │   ├── tile_cache.py     # 分块缓存
│   │   ├── history_manager.py # 历史管理
│   │   └── user_layer.py     # 用户图层
│   ├── views/                # UI 视图
│   │   ├── main_window.py    # 主窗口
│   │   ├── canvas.py         # 画布组件
│   │   ├── binarization_panel.py  # 二值化面板
│   │   ├── properties_panel.py    # 属性面板
│   │   ├── settings_dialog.py     # 设置对话框
│   │   └── shortcut_handler.py    # 快捷键处理
│   ├── widgets/              # 自定义控件
│   │   ├── animated_tab_widget.py # 动画选项卡
│   │   ├── custom_combobox.py     # 自定义下拉框
│   │   ├── toggle_switch.py       # 开关控件
│   │   ├── view_mode_switcher.py  # 视图切换器
│   │   └── layers_panel.py        # 图层面板
│   └── utils/                # 工具函数
│       ├── binarization_engine.py # 二值化引擎
│       ├── binarization_worker.py # 异步处理
│       ├── config_manager.py      # 配置管理
│       ├── theme_manager.py       # 主题管理
│       ├── translation_manager.py # 翻译管理
│       ├── animations.py          # 动画系统
│       └── resources.py           # 资源管理
├── themes/                   # 主题文件
│   ├── light_theme.qss       # 浅色主题
│   └── dark_theme.qss        # 深色主题
├── locales/                  # 多语言文件
│   ├── zh_CN.json            # 简体中文
│   └── en_US.json            # 英文
├── docs/                     # 文档
│   ├── CODE_TOOLS.md
│   ├── ANIMATION_SYSTEM.md
│   └── MULTILINGUAL_SUPPORT.md
├── tests/                    # 测试文件
├── icon/                     # 应用图标
├── data/                     # 配置数据
├── main.py                   # 应用入口
├── build.py                  # 打包脚本
├── setup.py                  # Cython 编译配置
├── pyproject.toml            # 项目配置
├── requirements.txt          # 运行依赖
├── requirements-dev.txt      # 开发依赖
├── CHANGELOG.md              # 更新日志
└── README.md                 # 本文件
```

---

## 🔧 技术栈

- **GUI 框架**：PySide6 (Qt 6)
- **图像处理**：NumPy, Pillow, OpenCV
- **性能优化**：Cython（C 级优化）
- **测试框架**：pytest, Hypothesis
- **代码质量**：Ruff (linter + formatter), Pylint
- **打包工具**：Nuitka

---

## 📝 更新日志

查看 [CHANGELOG.md](CHANGELOG.md) 了解详细的版本更新历史。

## 📄 许可证

本项目采用 **CC BY-NC-SA 4.0**（知识共享署名-非商业性使用-相同方式共享 4.0 国际许可协议）。

**这意味着**：
- ✅ 可以自由使用、修改和分享
- ✅ 必须署名原作者
- ❌ 不得用于商业目的
- ✅ 修改后必须使用相同许可证

详见 [LICENSE](LICENSE) 文件。

---

## 👨‍💻 作者

**夏次一定de**

---

<div align="center">

**如果这个项目对你有帮助，请给个 ⭐ Star 支持一下！**

© 2026 夏次一定de. All rights reserved.

</div>
