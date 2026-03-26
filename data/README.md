# 配置文件说明

## 文件位置

- `config.json` - 用户配置文件（自动生成，不提交到 Git）
- `config.template.json` - 配置模板文件（供参考）

## 配置项说明

### general（通用设置）

- `language`: 界面语言
  - `zh_CN`: 中文
  - `en_US`: English（待支持）

### interface（界面设置）

- `theme`: 主题
  - `light`: 浅色主题
  - `dark`: 深色主题（待支持）
  - `system`: 跟随系统（待支持）

- `window_geometry`: 窗口几何信息
  - `width`: 窗口宽度
  - `height`: 窗口高度
  - `x`: 窗口 X 坐标
  - `y`: 窗口 Y 坐标
  - `maximized`: 是否最大化

### editor（编辑器设置）

- `default_brush_size`: 默认画笔大小（1-500）
- `default_selection_size`: 默认选择范围（1-500）
- `undo_history_limit`: 撤销历史数量（10-100）
- `canvas_background`: 画布背景色
  - `white`: 白色
  - `gray`: 灰色
  - `black`: 黑色

### performance（性能设置）

- `tile_cache_size`: Tile 缓存大小（100-2000）
- `debounce_delay`: 二值化防抖延迟（50-500 ms）
- `hardware_acceleration`: 启用硬件加速（true/false，待支持）
- `max_image_size`: 最大图像尺寸（1000-50000 px）

### file（文件设置）

- `default_save_format`: 默认保存格式
  - `follow_original`: 跟随原文件
  - `png`: PNG
  - `jpg`: JPG
  - `bmp`: BMP
  - `webp`: WebP

- `filename_format`: 文件名格式
  - `timestamp`: 原名_时间戳
  - `copy`: 原名_副本
  - `custom`: 自定义

- `custom_prefix`: 自定义前缀
- `custom_suffix`: 自定义后缀
- `recent_files`: 最近文件列表（自动维护）
- `last_open_directory`: 上次打开目录（自动维护）
- `last_save_directory`: 上次保存目录（自动维护）

## 重置配置

删除 `config.json` 文件，程序会自动创建默认配置。
或在设置对话框中点击"恢复默认"按钮。
