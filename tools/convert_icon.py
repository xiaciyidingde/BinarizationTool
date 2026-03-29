# -*- coding: utf-8 -*-
# pylint: skip-file
"""
图标转换脚本

将图片文件转换为二进制数据，保存为txt文件。
用户可手动复制内容到 resources.py 中。

使用方法:
    python tools/convert_icon.py <图片路径>
    
示例:
    python tools/convert_icon.py tools/icon.png
"""
import os
import sys
from pathlib import Path


def convert_image_to_bytes(image_path: str, output_path: str = None) -> str:
    """将图片转换为二进制数据字符串
    
    Args:
        image_path: 图片文件路径
        output_path: 输出txt文件路径，默认为同目录下的 {文件名}_bytes.txt
        
    Returns:
        输出文件路径
    """
    image_path = Path(image_path)
    
    if not image_path.exists():
        raise FileNotFoundError(f"图片文件不存在: {image_path}")
    
    # 读取图片二进制数据
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    # 转换为 Python bytes 字符串格式
    bytes_str = repr(image_bytes)
    
    # 生成输出路径
    if output_path is None:
        output_path = image_path.parent / f"{image_path.stem}_bytes.txt"
    else:
        output_path = Path(output_path)
    
    # 写入txt文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(bytes_str)
    
    print(f"转换完成!")
    print(f"  源文件: {image_path}")
    print(f"  输出文件: {output_path}")
    print(f"  数据大小: {len(image_bytes)} bytes")
    
    return str(output_path)


def main():
    if len(sys.argv) < 2:
        print("用法: python convert_icon.py <图片路径> [输出路径]")
        print("示例: python convert_icon.py icon.png")
        sys.exit(1)
    
    image_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        convert_image_to_bytes(image_path, output_path)
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
