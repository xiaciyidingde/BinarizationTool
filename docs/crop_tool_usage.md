# 裁剪工具使用说明

## 功能概述

裁剪工具允许用户选择图片的一个矩形区域，并保留该区域，删除其余部分。

## 使用步骤

1. **进入编辑模式**
   - 点击工具栏上的"进入编辑模式"按钮
   - 或者加载图片后自动进入预览模式，然后切换到编辑模式

2. **激活裁剪工具**
   - 点击工具栏上的裁剪工具按钮
   - 或者按快捷键 `C`

3. **选择并裁剪**
   - 在图片上按住鼠标左键
   - 拖动鼠标到目标位置
   - 释放左键后立即执行裁剪
   - 你会看到一个白色虚线框显示选中的区域
   - 裁剪后图片会自动重新适配视图

4. **撤销裁剪**
   - 如果对裁剪结果不满意，可以使用撤销功能
   - 点击"← 后退"按钮或按 `Ctrl+Z`

## 技术细节

### 坐标系统
- 裁剪工具使用像素坐标系统
- 从 (x1, y1) 到 (x2, y2) 的选择会包含起始和结束像素
- 例如：从 (2, 2) 到 (6, 6) 会裁剪出 5x5 的区域

### 历史管理
- 每次裁剪操作都会自动保存到历史管理器
- 支持撤销和重做
- 裁剪操作会触发 `image_modified` 信号

### 视图适配
- 裁剪后，视图会自动调整缩放级别
- 确保裁剪后的图片完整显示在画布上
- 保持 10% 的边距以获得更好的视觉效果

## 示例代码

```python
from src.models.image_data import ImageData
from src.models.crop_tool import CropTool
import numpy as np

# 创建测试图片
pixels = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
image = ImageData(pixels)

# 创建裁剪工具
crop_tool = CropTool()

# 开始选择
crop_tool.start_selection(10, 10)

# 更新选择
crop_tool.update_selection(50, 50)

# 结束选择
crop_tool.end_selection()

# 确认裁剪
if crop_tool.confirm_crop():
    crop_rect = crop_tool.get_crop_rect()
    x, y, width, height = crop_rect
    
    # 执行裁剪
    image.crop_in_place(x, y, width, height)
    
    print(f"裁剪后尺寸: {image.width}x{image.height}")
```

## 注意事项

1. 裁剪操作是不可逆的（除非使用撤销功能）
2. 裁剪后原始图片数据也会被裁剪
3. 确保在裁剪前保存原始图片的备份
4. 裁剪区域至少为 1x1 像素
5. 裁剪区域会自动限制在图片边界内
