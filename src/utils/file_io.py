"""
文件 I/O 模块

处理图片文件的加载和保存，支持 PNG, JPG, BMP 格式。
"""

from pathlib import Path

import numpy as np
from PIL import Image

from ..models.image_data import ImageData
from .binarization_engine import BinarizationEngine


def load_image(file_path: str, binarize: bool = True,
               binarization_method: str = "otsu",
               threshold: int = 127) -> ImageData:
    """
    加载图片文件

    Args:
        file_path: 图片文件路径
        binarize: 是否自动二值化，默认 True
        binarization_method: 二值化方法 ("fixed", "otsu", "adaptive")，默认 "otsu"
        threshold: 固定阈值（仅当 method="fixed" 时使用），默认 127

    Returns:
        ImageData 对象

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 不支持的文件格式
        IOError: 文件损坏或无法读取
    """
    # 检查文件是否存在
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    # 检查文件格式
    supported_formats = {'.png', '.jpg', '.jpeg', '.bmp', '.webp'}
    if path.suffix.lower() not in supported_formats:
        raise ValueError(f"不支持的文件格式: {path.suffix}。支持的格式: {', '.join(supported_formats)}")

    try:
        # 使用 Pillow 加载图片
        with Image.open(file_path) as img:
            # 转换为 RGB 模式（如果是 RGBA 或其他模式）
            if img.mode == 'RGBA':
                # 创建白色背景
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])  # 使用 alpha 通道作为 mask
                img = background
            elif img.mode != 'RGB' and img.mode != 'L':
                img = img.convert('RGB')

            # 转换为 NumPy 数组
            original_pixels = np.array(img)

            # 如果需要二值化
            if binarize:
                if binarization_method == "fixed":
                    binary_pixels = BinarizationEngine.apply_fixed_threshold(original_pixels, threshold)
                elif binarization_method == "otsu":
                    binary_pixels = BinarizationEngine.apply_otsu(original_pixels)
                elif binarization_method == "adaptive":
                    binary_pixels = BinarizationEngine.apply_adaptive(original_pixels)
                else:
                    raise ValueError(f"不支持的二值化方法: {binarization_method}")
            else:
                # 不二值化，直接转换为灰度图
                binary_pixels = BinarizationEngine.convert_to_grayscale(original_pixels)

            # 创建 ImageData 对象
            return ImageData(binary_pixels, original_pixels)

    except Exception as e:
        if isinstance(e, (FileNotFoundError, ValueError)):
            raise
        raise OSError(f"无法读取图片文件: {file_path}。错误: {str(e)}") from e


def save_image(image_data: ImageData, file_path: str, format: str | None = None):
    """
    保存图片文件

    Args:
        image_data: ImageData 对象
        file_path: 保存路径
        format: 图片格式 ("PNG", "JPEG", "BMP", "WEBP")，如果为 None 则从文件扩展名推断

    Raises:
        ValueError: 不支持的文件格式
        IOError: 无法写入文件
    """
    path = Path(file_path)

    # 推断格式
    if format is None:
        format = path.suffix.upper().lstrip('.')
        if format == 'JPG':
            format = 'JPEG'

    # 检查格式
    supported_formats = {'PNG', 'JPEG', 'BMP', 'WEBP'}
    if format not in supported_formats:
        raise ValueError(f"不支持的文件格式: {format}。支持的格式: {', '.join(supported_formats)}")

    try:
        # 获取当前像素数据
        pixels = image_data.get_current_pixels()

        # 转换为 PIL Image
        img = Image.fromarray(pixels, mode='L')

        # 保存文件
        img.save(file_path, format=format)

    except Exception as e:
        raise OSError(f"无法保存图片文件: {file_path}。错误: {str(e)}") from e
