# BinarizationTool - 二值化图片编辑器

基于 PySide6 的二值化图片编辑应用程序，提供类似 Photoshop 的画笔编辑功能。

**版本**: v1.0.0.0  
**作者**: 夏次一定de  

## 功能特性

- 加载和显示二值化图片（PNG, JPG, BMP）
- 多种二值化算法（固定阈值、Otsu、自适应）
- 画笔工具（可调节大小、硬度、颜色）
- 裁剪工具
- 撤销/重做功能
- 缩放和平移视图
- 预览模式和编辑模式切换

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行应用

```bash
python main.py
```

## 运行测试

```bash
pytest
```

## 打包应用

使用 PyInstaller 打包为独立可执行文件：

```bash
# 安装 PyInstaller
pip install pyinstaller

# 打包
pyinstaller image-brush-editor.spec

# 可执行文件位于 dist/ 目录
```

## 使用说明

### 基本工作流程

1. **打开图片**: 文件 → 打开，选择图片文件
2. **调整二值化**: 在左侧面板选择二值化方法和参数
3. **进入编辑模式**: 点击"进入编辑模式"按钮
4. **使用画笔**: 选择画笔工具（快捷键 B），在图片上绘制
5. **保存图片**: 文件 → 保存

### 快捷键

- `Ctrl+O`: 打开文件
- `Ctrl+S`: 保存文件
- `Ctrl+Z`: 撤销
- `Ctrl+Y`: 重做
- `B`: 选择画笔工具
- `C`: 选择裁剪工具
- `Space + 拖动`: 平移视图
- `鼠标滚轮`: 缩放视图

### 画笔工具

- 左键拖动绘制
- 可调节画笔大小、硬度
- 支持黑色和白色两种颜色

### 裁剪工具

- 选择裁剪工具（快捷键 C）
- 按住左键拖动选择裁剪区域
- 释放左键后立即执行裁剪（保留选中区域，删除其余部分）
- 裁剪后图片会自动重新适配视图
- 支持撤销/重做

## 项目结构

```
.
├── src/
│   ├── models/          # 数据模型
│   │   ├── view_transform.py    # 坐标变换
│   │   ├── image_data.py        # 图片数据
│   │   ├── brush_stroke.py      # 画笔笔画
│   │   ├── brush_tool.py        # 画笔工具
│   │   ├── crop_tool.py         # 裁剪工具
│   │   └── history_manager.py   # 历史管理
│   ├── views/           # UI 组件
│   │   ├── canvas.py            # 画布组件
│   │   ├── binarization_panel.py # 二值化面板
│   │   └── main_window.py       # 主窗口
│   └── utils/           # 工具函数
│       ├── binarization_engine.py # 二值化引擎
│       └── file_io.py           # 文件 I/O
├── tests/               # 测试文件
├── main.py              # 应用入口
├── requirements.txt     # 依赖列表
└── README.md            # 本文件
```

## 技术栈

- **GUI 框架**: PySide6 (Qt 6)
- **图片处理**: NumPy, Pillow, OpenCV
- **测试**: pytest, Hypothesis

## 开发状态

✅ 核心功能已完成：
- 坐标变换系统
- 图片数据模型
- 二值化引擎
- 文件 I/O
- 画笔工具
- 裁剪工具
- 撤销/重做系统
- Canvas 画布
- 二值化设置面板
- 主窗口和布局

## 许可证

MIT License

## 作者

**夏次一定de**

- 项目创建者和主要维护者
- 版本: v1.0.0.0
- 发布日期: 2026-03-20

## 贡献

欢迎提交 Issue 和 Pull Request！

---

© 2026 夏次一定de. All rights reserved.
